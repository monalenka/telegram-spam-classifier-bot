import os
import re
from datetime import timezone, timedelta
from dotenv import load_dotenv

load_dotenv()


NOVOSIBIRSK_TZ = timezone(timedelta(hours=7))
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN') or 'PASTE_YOUR_TOKEN_HERE'
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x.strip()]
VOTE_THRESHOLD = 2


# шаблоны
TEMPLATE_REGEX = re.compile(r'^#\S+.*?(?:\n|\s)+.*?(координатор:?|Координатор:?|координатор:?|КООРДИНАТОР:?)[ ]*[^\n]+$', re.DOTALL)
TEMPLATE_EXAMPLE = '#Ваша_услуга Текст объявления\nКоординатор: Имя'


HINT_DELETE_DELAY = 300
VOTE_LOG_PATH = 'bot_votes.csv'

# состояния ConversationHandler
(
    MENU, CHOOSE_GROUP, CHOOSE_MODE, CHOOSE_GROUP_HINT, 
    CONTENT_MENU, ADD_CONTENT, ADD_CONTENT_NAME, SCHEDULE_CONTENT, 
    EDIT_CONTENT_ID, EDIT_CONTENT_NAME, DELETE_CONTENT_ID,
    SPAM_EXCEPTIONS_MENU, ADD_EXCEPTIONS, REMOVE_EXCEPTIONS
) = range(14)