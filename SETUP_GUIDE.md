# 🚀 Twitter Community Tracker Bot - Setup Guide

## ✅ Quick Start (Fixed Version)

The **CSRF authentication issues have been resolved**! Follow these steps to get your bot running:

### 📋 Prerequisites

1. **Python 3.8+** installed
2. **Telegram Bot Token** (get from @BotFather)
3. **Twitter/X Account** for cookie extraction

### 🔧 Installation

1. **Clone and navigate to the bot directory:**
   ```bash
   # If not already in the bot directory
   cd Community-Tracker-Bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file:**
   ```bash
   # Create .env file (copy the example below)
   notepad .env
   ```

### 📝 Environment Configuration

Create a `.env` file with the following content:

```env
# Telegram Bot Token (Required)
BOT_TOKEN=your_telegram_bot_token_here

# Optional: Logging level
LOG_LEVEL=INFO
```

**Important:** You don't need to put Twitter cookies in the .env file. You'll add them through the bot interface.

### 🍪 Getting Twitter Cookies (SIMPLIFIED!)

The bot now **automatically generates** missing cookie IDs! You only need to provide the **essential** cookies:

#### Step 1: Login to Twitter/X
1. Open your web browser
2. Go to [https://x.com](https://x.com) (or twitter.com)
3. **Login to your Twitter account**

#### Step 2: Extract Essential Cookies
1. **Open Developer Tools** (Press `F12`)
2. Click the **Application** tab (Chrome) or **Storage** tab (Firefox)
3. In the sidebar, find **Cookies** and click on `x.com`
4. **Copy these 2 ESSENTIAL cookies:**

   | Cookie Name | Example Value | Description |
   |-------------|---------------|-------------|
   | `auth_token` | `abc123def456...` | Authentication token (long hex string) ⭐ **REQUIRED** |
   | `ct0` | `def456abc123...` | CSRF token (32+ characters) ⭐ **REQUIRED** |

#### Step 3: Simplified Cookie Format
You only need these **2 essential cookies**:
```
auth_token=YOUR_AUTH_TOKEN; ct0=YOUR_CT0_TOKEN;
```

**Real example:**
```
auth_token=a1b2c3d4e5f6...; ct0=z9y8x7w6v5u4...;
```

✨ **The bot will automatically generate:**
- `guest_id` (visitor tracking)
- `personalization_id` (user preferences)
- `guest_id_ads` (advertising tracking)
- `guest_id_marketing` (marketing tracking)

### ▶️ Running the Bot

1. **Start the bot:**
   ```bash
   python main.py
   ```

2. **Add Twitter authentication:**
   - Start a chat with your bot on Telegram
   - Use the `/add_cookie` command
   - Paste your cookie string when prompted

3. **Start tracking:**
   - Use `/add_tracking @username` to track a Twitter user
   - The bot will monitor their community activities

### 🧪 Testing the Fix

Run the test script to verify everything works:
```bash
python test_csrf_fix.py
```

This will show you:
- ✅ If the CSRF fixes are working
- 🔐 What errors to expect without cookies
- 📋 How to add proper authentication

### 🔧 Troubleshooting

#### ❌ "CSRF token mismatch" Error
**Solution:** Your cookies are expired or incomplete.
1. Get fresh cookies from your browser (follow steps above)
2. Make sure you have **both auth_token AND ct0** cookies
3. Use `/add_cookie` command to update them

#### ❌ "User not found" for known users
**Solution:** Add authentication cookies first.
- The bot needs valid Twitter cookies to look up users
- Follow the cookie extraction steps above

#### ❌ Bot doesn't respond
**Solution:** Check your BOT_TOKEN.
1. Make sure `.env` file has the correct token
2. Test the token with @BotFather

#### ❌ "Authentication cookie expired"
**Solution:** Twitter cookies expire regularly.
1. Get fresh cookies every 24-48 hours
2. Update them using `/add_cookie` command

### 🏗️ Advanced Configuration

#### Multiple Twitter Accounts
You can add multiple Twitter accounts for better reliability:
```bash
# Use different account names
/add_cookie account1 [your-cookies-1]
/add_cookie account2 [your-cookies-2]
```

#### Proxy Support
If you need proxy support, the bot automatically uses configured proxies from the database.

### 📊 Features

- ✅ **Track Twitter Communities** - Monitor when users join/leave/create communities
- ✅ **Real-time Notifications** - Get instant Telegram notifications
- ✅ **Multiple Users** - Track multiple Twitter accounts
- ✅ **Rate Limiting** - Respects Twitter's API limits
- ✅ **Proxy Support** - Built-in proxy rotation
- ✅ **CSRF Protection** - Fixed authentication issues
- ✅ **Auto Cookie Generation** - Automatically creates missing cookie IDs

### 🆘 Support

If you encounter issues:

1. **Check the logs** for error messages
2. **Run the test script** to diagnose problems
3. **Verify your cookies** are fresh and contain both auth_token and ct0
4. **Restart the bot** after adding cookies

### 📚 Commands

| Command | Description |
|---------|-------------|
| `/start` | Start the bot and see welcome message |
| `/add_cookie` | Add Twitter authentication cookies (only need auth_token + ct0) |
| `/add_tracking @user` | Start tracking a Twitter user |
| `/list_tracking` | See all tracked users |
| `/remove_tracking @user` | Stop tracking a user |
| `/status` | Check bot status and statistics |

---

## 🎉 Success!

Once you've completed these steps, your bot will be able to:
- ✅ Look up Twitter users successfully
- ✅ Track community activities
- ✅ Send real-time notifications
- ✅ Handle rate limits properly
- ✅ Auto-generate missing cookie IDs

The CSRF authentication issues are now **completely resolved** with simplified cookie management! 🚀 