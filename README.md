# 🚀 Twitter Community Tracker Bot

An advanced Telegram bot that monitors and tracks Twitter Communities with comprehensive detection algorithms and real-time notifications.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Telegram Bot](https://img.shields.io/badge/telegram-bot-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## ✨ Features

### 🔍 **Comprehensive Community Detection**
- **Multi-Strategy Detection**: Uses 5+ detection methods to find ALL communities
- **Deep Scanning**: Tweet analysis, social graph analysis, content analysis
- **Pattern Recognition**: Hashtags, mentions, URLs, and interaction patterns
- **Role Detection**: Identifies Admin, Creator, Member, and custom roles
- **High Accuracy**: Multiple validation layers and confidence scoring

### 🍪 **Advanced Cookie Management**
- **Two Upload Methods**:
  - 🔧 **Manual**: Copy just `auth_token` + `ct0`
  - 🚀 **Auto-Enriched**: Bot generates missing cookies automatically
- **Browser Export**: JSON cookie import from browser extensions
- **Secure Storage**: Encrypted cookie management with versioning
- **Auto-Validation**: Real-time authentication testing

### 📡 **Real-Time Monitoring**
- **Live Tracking**: Continuous monitoring of community changes
- **Instant Notifications**: Immediate alerts for joins, leaves, creations
- **Role Change Detection**: Track promotions and demotions
- **Smart Intervals**: Configurable polling with rate limit protection
- **Error Recovery**: Automatic retry and failover mechanisms

### 🎯 **Intelligent Notifications**
- **Detailed Reports**: Complete change summaries with context
- **Change Categories**: Joined, Left, Created, Role Changes
- **User Context**: Profile information and verification status
- **Batch Notifications**: Smart grouping for multiple changes
- **Periodic Summaries**: Regular status updates when no changes

### 🛡️ **Security & Privacy**
- **Secure Storage**: No sensitive data in Git repository
- **Message Deletion**: Automatic cleanup of cookie messages
- **Proxy Support**: Rotating residential proxy integration
- **Rate Limiting**: Twitter API compliance and protection
- **Authentication Layers**: Multiple validation checkpoints

## 🚦 Quick Start

### Prerequisites
- Python 3.8+
- Telegram Bot Token
- Twitter Account (for cookies)
- Optional: Residential proxy for enhanced reliability

### Installation

1. **Clone the Repository**
```bash
git clone https://github.com/yourusername/twitter-community-tracker.git
cd twitter-community-tracker
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. **Run the Bot**
```bash
python main.py
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here
TG_CHAT_ID_WHITELIST=your_chat_id_here

# Twitter API Configuration (Optional)
TWITTER_BEARER_TOKEN=your_bearer_token_if_available

# Database Configuration
DATABASE_URL=sqlite:///data/twitter_communities.db

# Monitoring Configuration
POLLING_INTERVAL=15  # minutes
DEEP_SCAN_ENABLED=true

# Proxy Configuration (Optional)
PROXY_ENABLED=false
PROXY_ROTATION=true

# Security Configuration
COOKIE_ENCRYPTION=true
AUTO_CLEANUP=true
```

### Cookie Upload Methods

The bot supports multiple cookie upload methods:

#### 🔧 Method 1: Manual Extraction
Copy only the essential cookies:
```
auth_token=your_auth_token_here; ct0=your_ct0_token_here;
```

#### 🚀 Method 2: Auto-Enriched (Recommended)
Same as Method 1, but the bot automatically generates:
- `guest_id`
- `personalization_id` 
- `guest_id_ads`
- `guest_id_marketing`

#### 📥 Method 3: Browser Export
Export cookies as JSON from browser extensions and paste directly.

## 🎮 Usage

### Starting Monitoring

1. **Set Target User**
   - Use inline buttons to select common targets
   - Or enter custom Twitter handle (without @)

2. **Upload Cookies**
   - Choose your preferred upload method
   - Follow the step-by-step instructions
   - Bot validates authentication automatically

3. **Configure Monitoring**
   - Set polling interval (recommended: 15 minutes)
   - Enable/disable deep scanning
   - Configure notification preferences

4. **Start Tracking**
   - Bot begins comprehensive community monitoring
   - Real-time notifications for all changes
   - Detailed reports with full context

### Command Interface

The bot uses an intuitive button-based interface:

- 🎯 **Set Target**: Choose Twitter user to monitor
- 🍪 **Set Cookie**: Upload authentication cookies  
- ⚙️ **Proxy Settings**: Configure proxy rotation
- 📊 **View Status**: Check monitoring status
- ▶️ **Start/Stop**: Control tracking operations

## 🔧 Advanced Features

### Deep Scanning

Enable comprehensive community detection:

```python
# In bot configuration
DEEP_SCAN_ENABLED=true
```

Deep scanning includes:
- Extended tweet analysis (200+ tweets)
- Social graph analysis (following/followers)
- Content theme detection
- Interaction pattern analysis
- Community URL detection

### Proxy Integration

For enhanced reliability and rate limit avoidance:

1. **Add Proxy Accounts**
   - Use the Proxy Settings menu
   - Supports residential proxy rotation
   - Format: `http://user:pass@host:port`

2. **Automatic Rotation**
   - Bot cycles through available proxies
   - Tracks usage and performance
   - Failover on proxy issues

### Database Management

The bot includes comprehensive data tracking:

- **Community History**: Full change log
- **Tracking Runs**: Performance metrics  
- **User Profiles**: Cached user data
- **Error Logs**: Debugging information

## 📊 Monitoring Capabilities

### Community Changes Detected

- ✅ **Joined Communities**: New community memberships
- ❌ **Left Communities**: Departed communities
- 🆕 **Created Communities**: User-created communities
- 🔄 **Role Changes**: Admin promotions/demotions
- 📈 **Activity Changes**: Engagement pattern shifts

### Detection Methods

1. **Tweet Analysis**: Hashtags, mentions, community URLs
2. **Social Graph**: Following/follower community accounts
3. **Interaction Patterns**: Reply and mention frequency
4. **Content Analysis**: Topic classification and themes
5. **Profile Parsing**: Bio and profile link analysis

### Notification Examples

```
🔔 Community Activity Detected

User: @target_user
Scan type: comprehensive  
Total changes: 3

✅ Joined Communities (2):
   👤 Crypto Builders
      Role: Member
      Info: A community for crypto developers and builders...
   👤 AI Enthusiasts  
      Role: Member
      Info: Discussing the future of artificial intelligence...

🆕 Created Communities (1):
   👑 My New Project
      Role: Admin
      Info: Community for my latest blockchain project...

📊 Current Status:
Total communities: 15
Admin roles: 3
Member roles: 12

⏰ Detected at: 2024-01-15 14:30:22 UTC
```

## 🛠️ Development

### Project Structure

```
Community-Tracker-Bot/
├── bot/
│   ├── __init__.py
│   ├── cookie_manager.py           # Advanced cookie handling
│   ├── enhanced_community_tracker.py  # Comprehensive detection
│   ├── handlers.py                 # Telegram bot handlers
│   ├── keyboards.py               # Interface keyboards
│   ├── models.py                  # Database models
│   ├── scheduler.py               # Monitoring scheduler
│   └── twitter_api.py             # Enhanced Twitter API
├── data/                          # Data directory (excluded from Git)
│   ├── accounts.db               # Twitter accounts
│   ├── twitter_communities.db    # Community tracking data
│   └── cookies/                  # Encrypted cookie storage
├── requirements.txt              # Python dependencies
├── .env.example                 # Environment template
├── .gitignore                   # Git exclusions
├── main.py                      # Application entry point
└── README.md                    # This file
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

### Testing

Run the test suite:

```bash
python -m pytest tests/
```

For integration testing with real Twitter data:

```bash
python test_comprehensive_tracking.py
```

## 🔒 Security & Privacy

### Data Protection

- **No Sensitive Data in Git**: All credentials excluded
- **Encrypted Storage**: Cookies encrypted at rest
- **Message Cleanup**: Automatic deletion of sensitive messages
- **Secure Transmission**: HTTPS/TLS for all API calls

### Best Practices

- Use dedicated Twitter account for monitoring
- Rotate cookies regularly
- Monitor bot logs for unusual activity
- Use residential proxies when possible
- Enable rate limiting and delays

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Support

### Documentation

- [Installation Guide](docs/installation.md)
- [Configuration Guide](docs/configuration.md) 
- [Troubleshooting](docs/troubleshooting.md)
- [API Reference](docs/api.md)

### Community

- [Issues](https://github.com/yourusername/twitter-community-tracker/issues)
- [Discussions](https://github.com/yourusername/twitter-community-tracker/discussions)
- [Wiki](https://github.com/yourusername/twitter-community-tracker/wiki)

### Contact

- 📧 Email: your.email@example.com
- 🐦 Twitter: [@yourusername](https://twitter.com/yourusername)
- 💬 Telegram: [@yourusername](https://t.me/yourusername)

## 🚨 Disclaimer

This bot is for educational and monitoring purposes only. Users are responsible for:

- Complying with Twitter's Terms of Service
- Respecting user privacy and data protection laws
- Using the bot ethically and responsibly
- Not violating any platform policies

The developers are not responsible for any misuse of this software.

## 🎯 Roadmap

### Upcoming Features

- [ ] **Multi-User Monitoring**: Track multiple Twitter accounts
- [ ] **Advanced Analytics**: Community growth trends and insights  
- [ ] **Export Features**: CSV/JSON data export capabilities
- [ ] **Webhook Integration**: Discord, Slack, and custom webhooks
- [ ] **Machine Learning**: AI-powered community prediction
- [ ] **Real-time Dashboard**: Web interface for monitoring
- [ ] **Mobile App**: Native mobile application
- [ ] **API Access**: RESTful API for third-party integration

### Performance Improvements

- [ ] **Caching Layer**: Redis integration for better performance
- [ ] **Database Optimization**: Query optimization and indexing
- [ ] **Horizontal Scaling**: Multi-instance deployment support
- [ ] **Load Balancing**: Request distribution and failover

---

⭐ **Star this repository if you find it useful!**

🔔 **Watch for updates and new features**

🍴 **Fork to contribute and customize**
