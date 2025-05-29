from datetime import datetime
import json
from typing import List, Optional, Dict, Any
from sqlmodel import Field, SQLModel, create_engine, Session, select
import os
import sqlite3
import logging

# Database setup
DATABASE_URL = "sqlite:///./data/twitter_communities.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

class Target(SQLModel, table=True):
    """Model for storing the target Twitter user"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str
    screen_name: str
    name: str
    added_at: datetime = Field(default_factory=datetime.utcnow)

class SavedCommunity(SQLModel, table=True):
    """Model for storing communities the target belongs to"""
    community_id: str = Field(primary_key=True)
    label: str
    role: str
    first_seen_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen_at: datetime = Field(default_factory=datetime.utcnow)

class Run(SQLModel, table=True):
    """Model for storing run information"""
    run_id: Optional[int] = Field(default=None, primary_key=True)
    run_at: datetime = Field(default_factory=datetime.utcnow)
    joined_ids: str = Field(default="[]")  # JSON string
    left_ids: str = Field(default="[]")    # JSON string
    created_ids: str = Field(default="[]") # JSON string

class ProxyAccount(SQLModel, table=True):
    """Model for storing proxy-account mappings"""
    id: Optional[int] = Field(default=None, primary_key=True)
    proxy_string: str  # Raw proxy string as provided
    proxy_url: str     # Formatted proxy URL for twscrape
    account_name: str  # Identifier for the account
    is_active: bool = Field(default=True)
    added_at: datetime = Field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None

# Pydantic models for API responses
class Community(SQLModel):
    """Model for a Twitter community"""
    id: str
    name: str
    role: str

class TwitterUserCommunityPayload(SQLModel):
    """Model for the Apify actor response"""
    user_id: str
    screen_name: str
    name: Optional[str] = None
    profile_image_url_https: Optional[str] = None
    is_blue_verified: Optional[bool] = None
    verified: Optional[bool] = None
    communities: List[Community]

class DatabaseManager:
    """Enhanced database manager for community tracking"""
    
    def __init__(self, db_path: str = "data/twitter_communities.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create database and tables
        self._init_database()
    
    def _init_database(self):
        """Initialize database with required tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create communities table with enhanced schema
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS communities (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    community_id TEXT NOT NULL,
                    community_name TEXT NOT NULL,
                    community_description TEXT,
                    member_count INTEGER DEFAULT 0,
                    user_role TEXT DEFAULT 'Member',
                    is_nsfw BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    detection_method TEXT DEFAULT 'unknown',
                    confidence_score REAL DEFAULT 0.5,
                    UNIQUE(user_id, community_id)
                )
                """)
                
                # Create tracking runs table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS tracking_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    run_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    communities_found INTEGER DEFAULT 0,
                    communities_joined INTEGER DEFAULT 0,
                    communities_left INTEGER DEFAULT 0,
                    communities_created INTEGER DEFAULT 0,
                    role_changes INTEGER DEFAULT 0,
                    scan_type TEXT DEFAULT 'quick',
                    success BOOLEAN DEFAULT 1,
                    error_message TEXT
                )
                """)
                
                # Create change log table
                cursor.execute("""
                CREATE TABLE IF NOT EXISTS community_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    community_id TEXT NOT NULL,
                    community_name TEXT NOT NULL,
                    change_type TEXT NOT NULL, -- 'joined', 'left', 'created', 'role_change'
                    old_role TEXT,
                    new_role TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_communities_user_id ON communities(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_tracking_runs_user_id ON tracking_runs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_community_changes_user_id ON community_changes(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_community_changes_timestamp ON community_changes(timestamp)")
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise
    
    def get_user_communities(self, user_id: str) -> List[Community]:
        """Get saved communities for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT community_id, community_name, community_description, 
                       member_count, user_role, is_nsfw, created_at
                FROM communities 
                WHERE user_id = ?
                ORDER BY updated_at DESC
                """, (user_id,))
                
                communities = []
                for row in cursor.fetchall():
                    community = Community(
                        id=row[0],
                        name=row[1],
                        description=row[2] or "",
                        member_count=row[3] or 0,
                        role=row[4] or "Member",
                        is_nsfw=bool(row[5]),
                        created_at=row[6] or datetime.utcnow().isoformat()
                    )
                    communities.append(community)
                
                self.logger.debug(f"Retrieved {len(communities)} communities for user {user_id}")
                return communities
                
        except Exception as e:
            self.logger.error(f"Error getting user communities: {e}")
            return []
    
    def update_user_communities(self, user_id: str, communities: List[Community]) -> bool:
        """Update user's communities in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current communities for change tracking
                current_communities = self.get_user_communities(user_id)
                current_ids = {c.id for c in current_communities}
                new_ids = {c.id for c in communities}
                
                # Track changes
                joined_ids = new_ids - current_ids
                left_ids = current_ids - new_ids
                
                # Remove all existing communities for user
                cursor.execute("DELETE FROM communities WHERE user_id = ?", (user_id,))
                
                # Insert new communities
                for community in communities:
                    cursor.execute("""
                    INSERT OR REPLACE INTO communities (
                        id, user_id, community_id, community_name, community_description,
                        member_count, user_role, is_nsfw, updated_at, detection_method
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                    """, (
                        f"{user_id}_{community.id}",  # Unique composite ID
                        user_id,
                        community.id,
                        community.name,
                        community.description,
                        community.member_count,
                        community.role,
                        community.is_nsfw,
                        "enhanced_tracking"
                    ))
                
                # Log changes
                for joined_id in joined_ids:
                    joined_community = next((c for c in communities if c.id == joined_id), None)
                    if joined_community:
                        change_type = "created" if joined_community.role == "Admin" else "joined"
                        cursor.execute("""
                        INSERT INTO community_changes (
                            user_id, community_id, community_name, change_type, new_role
                        ) VALUES (?, ?, ?, ?, ?)
                        """, (user_id, joined_id, joined_community.name, change_type, joined_community.role))
                
                for left_id in left_ids:
                    left_community = next((c for c in current_communities if c.id == left_id), None)
                    if left_community:
                        cursor.execute("""
                        INSERT INTO community_changes (
                            user_id, community_id, community_name, change_type, old_role
                        ) VALUES (?, ?, ?, ?, ?)
                        """, (user_id, left_id, left_community.name, "left", left_community.role))
                
                conn.commit()
                
                self.logger.info(f"Updated communities for {user_id}: {len(communities)} total, "
                               f"{len(joined_ids)} joined, {len(left_ids)} left")
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error updating user communities: {e}")
            return False
    
    def log_tracking_run(self, user_id: str, results: Dict[str, Any]) -> bool:
        """Log a tracking run"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                INSERT INTO tracking_runs (
                    user_id, communities_found, communities_joined, communities_left,
                    communities_created, role_changes, scan_type, success, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id,
                    results.get('total_current', 0),
                    len(results.get('joined', [])),
                    len(results.get('left', [])),
                    len(results.get('created', [])),
                    len(results.get('role_changes', [])),
                    results.get('scan_type', 'quick'),
                    results.get('error') is None,
                    results.get('error')
                ))
                
                conn.commit()
                return True
                
        except Exception as e:
            self.logger.error(f"Error logging tracking run: {e}")
            return False
    
    def get_tracking_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Get tracking history for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT run_timestamp, communities_found, communities_joined, 
                       communities_left, communities_created, role_changes, 
                       scan_type, success, error_message
                FROM tracking_runs 
                WHERE user_id = ?
                ORDER BY run_timestamp DESC
                LIMIT ?
                """, (user_id, limit))
                
                history = []
                for row in cursor.fetchall():
                    history.append({
                        'timestamp': row[0],
                        'communities_found': row[1],
                        'communities_joined': row[2],
                        'communities_left': row[3],
                        'communities_created': row[4],
                        'role_changes': row[5],
                        'scan_type': row[6],
                        'success': bool(row[7]),
                        'error_message': row[8]
                    })
                
                return history
                
        except Exception as e:
            self.logger.error(f"Error getting tracking history: {e}")
            return []
    
    def get_change_history(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get community change history for a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                SELECT community_id, community_name, change_type, old_role, 
                       new_role, timestamp, details
                FROM community_changes 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """, (user_id, limit))
                
                changes = []
                for row in cursor.fetchall():
                    changes.append({
                        'community_id': row[0],
                        'community_name': row[1],
                        'change_type': row[2],
                        'old_role': row[3],
                        'new_role': row[4],
                        'timestamp': row[5],
                        'details': row[6]
                    })
                
                return changes
                
        except Exception as e:
            self.logger.error(f"Error getting change history: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 30) -> bool:
        """Clean up old tracking data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up old tracking runs
                cursor.execute("""
                DELETE FROM tracking_runs 
                WHERE run_timestamp < datetime('now', '-{} days')
                """.format(days_to_keep))
                
                # Clean up old change logs (keep more change history)
                cursor.execute("""
                DELETE FROM community_changes 
                WHERE timestamp < datetime('now', '-{} days')
                """.format(days_to_keep * 2))
                
                conn.commit()
                
                self.logger.info(f"Cleaned up data older than {days_to_keep} days")
                return True
                
        except Exception as e:
            self.logger.error(f"Error cleaning up old data: {e}")
            return False

# Global database manager instance
db_manager = DatabaseManager()

# Database functions
def create_db_and_tables():
    """Create database and tables if they don't exist"""
    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)
    SQLModel.metadata.create_all(engine)

def get_target(session: Session) -> Optional[Target]:
    """Get the current target from the database"""
    statement = select(Target)
    return session.exec(statement).first()

def save_target(session: Session, target: Target) -> Target:
    """Save a target to the database, replacing any existing target"""
    existing = get_target(session)
    if existing:
        session.delete(existing)
    session.add(target)
    session.commit()
    session.refresh(target)
    return target

def get_saved_communities(session: Session) -> List[SavedCommunity]:
    """Get all saved communities from the database"""
    statement = select(SavedCommunity)
    return session.exec(statement).all()

def save_communities(session: Session, communities: List[Community]):
    """Save communities to the database, updating existing ones"""
    # Get existing communities
    existing_communities = get_saved_communities(session)
    existing_ids = {c.community_id for c in existing_communities}
    
    # Update existing communities and add new ones
    for community in communities:
        if community.id in existing_ids:
            # Update existing community
            statement = select(SavedCommunity).where(SavedCommunity.community_id == community.id)
            saved_community = session.exec(statement).one()
            saved_community.label = community.name
            saved_community.role = community.role
            saved_community.last_seen_at = datetime.utcnow()
        else:
            # Add new community
            saved_community = SavedCommunity(
                community_id=community.id,
                label=community.name,
                role=community.role
            )
            session.add(saved_community)
    
    session.commit()

def save_run(session: Session, joined_ids: List[str], left_ids: List[str], created_ids: List[str]) -> Run:
    """Save a run to the database"""
    run = Run(
        joined_ids=json.dumps(joined_ids),
        left_ids=json.dumps(left_ids),
        created_ids=json.dumps(created_ids)
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run

def get_last_run(session: Session) -> Optional[Run]:
    """Get the last run from the database"""
    statement = select(Run).order_by(Run.run_at.desc())
    return session.exec(statement).first()

def save_cookie(cookie: str):
    """Save a cookie using the enhanced cookie manager system"""
    try:
        # Save using the new CookieManager system
        from bot.cookie_manager import CookieManager
        cookie_manager = CookieManager()
        
        # Parse the cookie string
        cookie_set = cookie_manager.parse_manual_cookies(cookie)
        if cookie_set:
            # Save with a default name
            cookie_manager.save_cookies(cookie_set, "default")
        
        # Also save to legacy file for backward compatibility
        with open("data/cookie.txt", "w") as f:
            f.write(cookie)
    except Exception as e:
        # Fallback to legacy save method
        with open("data/cookie.txt", "w") as f:
            f.write(cookie)

def get_cookie() -> Optional[str]:
    """Get the cookie from the enhanced cookie manager system"""
    try:
        # First check if we have cookies in the new CookieManager system
        from bot.cookie_manager import CookieManager
        cookie_manager = CookieManager()
        
        # Get list of saved cookies
        saved_cookies = cookie_manager.list_cookie_sets()
        if saved_cookies:
            # Get the most recently used cookie set
            latest_cookie = sorted(saved_cookies, key=lambda x: x['last_used'], reverse=True)[0]
            cookie_set = cookie_manager.load_cookies(latest_cookie['name'])
            if cookie_set:
                return cookie_set.to_string()
        
        # Fallback to legacy cookie.txt file
        with open("data/cookie.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
    except Exception:
        return None

def parse_residential_proxy(proxy_string: str) -> str:
    """
    Parse residential proxy format and convert to URL format
    
    Args:
        proxy_string: Format like "host:port:username:password"
        
    Returns:
        Formatted proxy URL like "http://username:password@host:port"
    """
    try:
        proxy_string = proxy_string.strip()
        
        # If it's already a proper URL format, return as-is
        if proxy_string.startswith(('http://', 'https://', 'socks5://', 'socks4://')):
            return proxy_string
        
        parts = proxy_string.split(':')
        if len(parts) == 4:
            host, port, username, password = parts
            return f"http://{username}:{password}@{host}:{port}"
        elif len(parts) == 2:
            host, port = parts
            return f"http://{host}:{port}"
        else:
            # If we can't parse it, return as-is
            return proxy_string
    except Exception:
        # If parsing fails, return as-is
        return proxy_string

def save_proxy_list(proxy_list: str):
    """Save a list of proxies to the database"""
    with Session(engine) as session:
        # Clear existing proxies
        existing_proxies = session.exec(select(ProxyAccount)).all()
        for proxy in existing_proxies:
            session.delete(proxy)
        session.commit()
        
        # Parse and save new proxies
        for i, proxy_line in enumerate(proxy_list.strip().split('\n')):
            proxy_line = proxy_line.strip()
            if proxy_line:
                proxy_url = parse_residential_proxy(proxy_line)
                proxy_account = ProxyAccount(
                    proxy_string=proxy_line,
                    proxy_url=proxy_url,
                    account_name=f"account_{i+1}"
                )
                session.add(proxy_account)
        
        session.commit()

def get_proxy_accounts() -> List[ProxyAccount]:
    """Get all proxy accounts from database"""
    with Session(engine) as session:
        statement = select(ProxyAccount).where(ProxyAccount.is_active == True)
        return session.exec(statement).all()

def get_next_available_proxy() -> Optional[ProxyAccount]:
    """Get the next available proxy for rotation"""
    with Session(engine) as session:
        # Get least recently used proxy
        statement = select(ProxyAccount).where(ProxyAccount.is_active == True).order_by(
            ProxyAccount.last_used_at.asc().nulls_first()
        )
        proxy = session.exec(statement).first()
        return proxy

def update_proxy_last_used(proxy_id: int):
    """Update the last used time for a proxy"""
    with Session(engine) as session:
        proxy = session.get(ProxyAccount, proxy_id)
        if proxy:
            proxy.last_used_at = datetime.utcnow()
            session.commit()

def save_single_proxy(proxy_string: str) -> ProxyAccount:
    """Save a single proxy to the database and return the ProxyAccount"""
    with Session(engine) as session:
        # Clear existing proxies
        existing_proxies = session.exec(select(ProxyAccount)).all()
        for proxy in existing_proxies:
            session.delete(proxy)
        session.commit()
        
        # Parse and save the single proxy
        proxy_url = parse_residential_proxy(proxy_string)
        proxy_account = ProxyAccount(
            proxy_string=proxy_string,
            proxy_url=proxy_url,
            account_name="single_proxy"
        )
        session.add(proxy_account)
        session.commit()
        session.refresh(proxy_account)
        return proxy_account

def save_proxy(proxy: str):
    """Save a single proxy to the filesystem AND database"""
    # Save to filesystem for legacy compatibility
    with open("data/proxy.txt", "w") as f:
        f.write(proxy)
    
    # Also save to database
    save_single_proxy(proxy)

def get_proxy() -> Optional[str]:
    """Get the proxy from database first, then filesystem as fallback"""
    # Try database first
    proxy_accounts = get_proxy_accounts()
    if proxy_accounts:
        return proxy_accounts[0].proxy_url
    
    # Fallback to filesystem
    try:
        with open("data/proxy.txt", "r") as f:
            proxy = f.read().strip()
            return proxy if proxy else None
    except FileNotFoundError:
        return None

def clear_proxy():
    """Clear all proxies from database and filesystem"""
    clear_all_proxies()
    try:
        os.remove("data/proxy.txt")
    except FileNotFoundError:
        pass

def clear_all_proxies():
    """Clear all proxy accounts from database"""
    with Session(engine) as session:
        proxies = session.exec(select(ProxyAccount)).all()
        for proxy in proxies:
            session.delete(proxy)
        session.commit()
