#.\venv\Scripts\Activate.ps1 
#python bot/main.py
import logging
from telegram.ext import ApplicationBuilder, JobQueue
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import TOKEN
from handlers import (
    conv, settemplate, unsettemplate, delete_message_command, 
    handle_group_message, vote_callback, content_menu_callback, spam_exceptions_callback
)
from scheduler import check_and_send_scheduled_content

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(conv)
    app.add_handler(CommandHandler('settemplate', settemplate))
    app.add_handler(CommandHandler('unsettemplate', unsettemplate))
    app.add_handler(CommandHandler('delete', delete_message_command))
    
    media_with_caption = (filters.PHOTO | filters.VIDEO | filters.AUDIO | filters.Document.ALL) & filters.Caption(True)
    group_filter = (filters.TEXT | media_with_caption) & (~filters.COMMAND) & (~filters.ChatType.PRIVATE)
    app.add_handler(MessageHandler(group_filter, handle_group_message))
    
    app.add_handler(CallbackQueryHandler(vote_callback, pattern=r'^(spam|ham)\|'))
    app.add_handler(CallbackQueryHandler(content_menu_callback, pattern=r'^cmenu\|'))
    app.add_handler(CallbackQueryHandler(content_menu_callback, pattern=r'^start\|'))
    app.add_handler(CallbackQueryHandler(content_menu_callback, pattern=r'^settings\|'))
    app.add_handler(CallbackQueryHandler(content_menu_callback, pattern=r'^aud\|'))
    app.add_handler(CallbackQueryHandler(content_menu_callback, pattern=r'^tp\|'))
    app.add_handler(CallbackQueryHandler(spam_exceptions_callback, pattern=r'^exceptions\|'))
    
    job_queue = app.job_queue
    job_queue.run_repeating(check_and_send_scheduled_content, interval=60, first=10)
    
    print('Бот запущен!')
    app.run_polling()

if __name__ == '__main__':
    main()