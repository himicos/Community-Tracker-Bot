# Twitter Community Tracker Bot

A Telegram bot that tracks when a specific Twitter (X) account creates or joins a Community, using direct Twitter GraphQL integration via twscrape.

## Features

- Button-based console interface for easy interaction
- Set a target Twitter account to track
- Manage Twitter authentication cookies directly from Telegram
- Start/stop tracking with customizable polling intervals
- Receive notifications when the target joins, leaves, or creates communities
- View and browse communities associated with the target
- Secure cookie handling and storage

## Setup

1. Clone this repository
2. Create a `.env` file based on `.env.example`:
   ```
   BOT_TOKEN=your_telegram_bot_token
   POLL_INTERVAL_MIN=5
   TG_CHAT_ID_WHITELIST=comma,separated,chat,ids  # Optional
   ```
3. Run with Docker:
   ```
   docker-compose up -d
   ```

## Usage

The bot provides a simple button-based interface with the following commands:

- `/start` - Start the bot and show the main menu
- Then use the buttons to:
  - Set a target Twitter account to track
  - Set your Twitter authentication cookie
  - Start tracking with customizable intervals
  - Stop tracking
  - Check current status
  - View communities

### Cookie Format

When setting a cookie, use the following format:
```
auth_token=your_auth_token; ct0=your_ct0_token;
```

You can obtain these cookies by logging into Twitter in your browser and extracting them from the browser's developer tools.

## Technical Details

- Built with Python 3.11 and aiogram 3
- Uses twscrape for direct Twitter GraphQL integration
- Implements SQLite database with SQLModel for data persistence
- Uses APScheduler for periodic community checks
- Packaged with Docker for easy deployment

## Project Structure

- `main.py` - Entry point
- `bot/handlers.py` - Telegram command handlers and button interface
- `bot/models.py` - Database models
- `bot/scheduler.py` - Tracking scheduler
- `bot/twitter_api.py` - Twitter API integration using twscrape
- `requirements.txt` - Python dependencies
- `Dockerfile` - Docker configuration
- `docker-compose.yml` - Docker Compose configuration

## Notes on Twitter Terms of Service

Please be aware that using this bot may potentially violate Twitter's Terms of Service. Use at your own risk. The bot uses authentication cookies to access Twitter's GraphQL endpoints, which is not an officially supported method of accessing Twitter data.

## Edge Cases

- If the target account is private/protected, the bot will notify you and continue tracking
- If the authentication cookie expires or becomes invalid, the bot will notify you and pause tracking
- The bot handles rate limiting and network errors with exponential backoff and retries
