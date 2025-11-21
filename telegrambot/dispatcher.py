# telegrambot/dispatcher.py

import logging
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    Application
)
from .handlers.start import start
from .handlers.predict import predict_command
from .handlers.nextmatch import nextmatch
from .handlers.text import handle_text
from .handlers.inline import inline_handler
from .handlers.gameweek import gameweek_command
from .handlers.subscribe import register_subscribe_handlers
from .handlers.help import help_command

logger = logging.getLogger(__name__)



def setup_application(app: Application) -> None:
    try:
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("predict", predict_command))
        app.add_handler(CommandHandler("nextmatch", nextmatch))
        app.add_handler(CommandHandler("gameweek", gameweek_command))
        app.add_handler(CommandHandler("help", help_command))  # ⬅️ register /help here

        register_subscribe_handlers(app)

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CallbackQueryHandler(inline_handler))

        logger.info("All handlers registered successfully")
    except Exception as e:
        logger.error(f"Failed to setup handlers: {e}")
        raise