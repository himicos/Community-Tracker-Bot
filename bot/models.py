from datetime import datetime
import json
from typing import List, Optional, Dict, Any
from sqlmodel import Field, SQLModel, create_engine, Session, select
import os

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

def save_cookie(session: Session, cookie: str):
    """Save a cookie to the database"""
    # In a production environment, this should be encrypted
    # For this MVP, we'll store it in an environment variable or config file
    with open("data/cookie.txt", "w") as f:
        f.write(cookie)

def get_cookie() -> Optional[str]:
    """Get the cookie from the database"""
    try:
        with open("data/cookie.txt", "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return None
