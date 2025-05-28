import os
import logging
from dotenv import load_dotenv

from bot.handlers import main

if __name__ == "__main__":
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Check required environment variables
    required_vars = ["BOT_TOKEN"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logging.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logging.error("Please set them in .env file or environment")
        exit(1)
    
    # Run the bot
    import asyncio
    asyncio.run(main())
