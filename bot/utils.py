import logging
import sys
import csv
import os
import joblib
import pandas as pd
import numpy as np
from storage import spam_exceptions
from datetime import datetime
from scipy.sparse import hstack
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(project_root)
from src import utils as src_utils, preprocessing as p
from config import NOVOSIBIRSK_TZ, ADMIN_IDS, VOTE_LOG_PATH
from storage import known_chats

logger = logging.getLogger(__name__)


def get_spam_exceptions_text(chat_id: int) -> str:
    """Форматирует текст со списком исключений"""
    exceptions = spam_exceptions.get(chat_id, set())
    if not exceptions:
        return "📝 Список исключений пуст. Все сообщения проверяются на спам."
    
    exceptions_list = "\n".join([f"• @{username}" for username in sorted(exceptions)])
    return f"👥 Пользователи в исключениях (не проверяются на спам):\n\n{exceptions_list}"

def is_user_exempted(user, chat_id: int) -> bool:
    """Проверяет, находится ли пользователь в исключениях"""
    if not user or not user.username:
        return False
    
    exceptions = spam_exceptions.get(chat_id, set())
    return user.username.lower() in {username.lower() for username in exceptions}
    
def add_spam_exceptions(chat_id: int, usernames: list) -> int:
    """Добавляет пользователей в исключения, возвращает количество добавленных"""
    if chat_id not in spam_exceptions:
        spam_exceptions[chat_id] = set()
    
    added_count = 0
    for username in usernames:
        username_clean = username.lstrip('@').strip().lower()
        if username_clean and username_clean not in spam_exceptions[chat_id]:
            spam_exceptions[chat_id].add(username_clean)
            added_count += 1
    
    return added_count

def remove_spam_exceptions(chat_id: int, usernames: list) -> int:
    """Удаляет пользователей из исключений, возвращает количество удаленных"""
    if chat_id not in spam_exceptions:
        return 0
    
    removed_count = 0
    for username in usernames:
        username_clean = username.lstrip('@').strip().lower()
        if username_clean in spam_exceptions[chat_id]:
            spam_exceptions[chat_id].remove(username_clean)
            removed_count += 1
    
    if not spam_exceptions[chat_id]:
        del spam_exceptions[chat_id]
    
    return removed_count


def get_novosibirsk_time():
    """Возвращает текущее время в часовом поясе Новосибирска"""
    return datetime.now(NOVOSIBIRSK_TZ)

def log_vote_result(text, label, user_id=None):
    file_exists = os.path.isfile(VOTE_LOG_PATH)
    with open(VOTE_LOG_PATH, 'a', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['text', 'label', 'user_id'])
        writer.writerow([text, label, user_id])

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

def detect_single_chars_spam(text, threshold=0.5):
    """
    Обнаружение сообщений с большим количеством одиночных символов
    threshold - порог (если доля одиночных символов > threshold, считаем спамом)
    """
    if not text or len(text.strip()) < 10:
        return False
    
    words = text.split()
    if len(words) < 3:
        return False
    
    import re
    single_chars = 0
    for word in words:
        clean_word = re.sub(r'[^\w]', '', word)
        if len(clean_word) == 1 and clean_word.isalnum():
            single_chars += 1
    
    ratio = single_chars / len(words)
    
    return ratio > threshold


# загрузка модели и векторайзера
ps = src_utils.get_paths()
m = joblib.load(ps['model'])
v = joblib.load(ps['vectorizer'])

async def check_spam(text):
    """Проверка текста на спам"""
    if detect_single_chars_spam(text):
        return True, 0.95

    x = p.clean_text(text)
    d = pd.DataFrame({'text': [x]})
    f = p.extract_features(d.copy())
    X = v.transform(f['text'])
    add = f[[c for c in f.columns if c != 'text']].values
    
    try:
        expected_total = m.coef_.shape[1]
        expected_add = expected_total - X.shape[1]
        current_add = add.shape[1]
        if current_add < expected_add:
            pad = np.zeros((add.shape[0], expected_add - current_add), dtype=add.dtype)
            add = np.hstack([add, pad])
        elif current_add > expected_add:
            add = add[:, :expected_add]
    except Exception:
        pass
    
    Xf = hstack([X, add])
    pr = m.predict(Xf)[0]
    proba = m.predict_proba(Xf)[0]
    cl = list(m.classes_)
    return pr == 'spam', proba[cl.index('spam')]