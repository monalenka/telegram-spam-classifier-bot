import re
import nltk
from nltk.corpus import stopwords
from pymorphy2 import MorphAnalyzer
import string

morph = MorphAnalyzer()
stop_words = None

def ensure_nltk_resources():
    try:
        _ = stopwords.words('russian')
    except LookupError:
        nltk.download('stopwords')

def clean_text(text):
    global stop_words
    if stop_words is None:
        ensure_nltk_resources()
        stop_words_set = set(stopwords.words('russian'))
        stop_words = stop_words_set
    text = text.lower()
    text = re.sub(r'http\S+|www\S+|https\S+', '', text, flags=re.MULTILINE)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'[\+\(]?[1-9][0-9 .\-\(\)]{8,}[0-9]', '', text)
    text = text.translate(str.maketrans('', '', string.punctuation + string.digits))
    text = re.sub(r'[^\u0430-\u044f\u0451\s]', '', text)
    tokens = text.split()
    tokens = [word for word in tokens if word not in stop_words]
    tokens = [morph.parse(word)[0].normal_form for word in tokens]
    return ' '.join(tokens)

def extract_features(df):
    df['length'] = df['text'].apply(len)
    df['exclamation_count'] = df['text'].apply(lambda x: x.count('!'))
    df['digit_count'] = df['text'].apply(lambda x: sum(c.isdigit() for c in x))
    spam_keywords = ['бесплатно', 'выиграй', 'только сегодня', 'гарантия', 
                    'срочно', 'акция', 'кэшбэк', 'скидка', 'реклама', 'зарабатываю',
                    'зарабатывать', 'курьером', 'заработала', 'легкие деньги',
                    'быстрый заработок', 'порно', 'легкая работа', 'много денег',
                    'зарабатывать онлайн', 'заработок онлайн', 'зарабатываю онлайн',
                    'пробник', 'пробники', 'пробнички', 'вложений', 'раскид', 'раскида',
                    'нахуй']
    for keyword in spam_keywords:
        df[f'has_{keyword}'] = df['text'].str.contains(keyword).astype(int)
    return df


def detect_single_chars_spam(text, threshold=0.7):
    """
    Обнаружение сообщений с большим количеством одиночных символов
    threshold - порог (если доля одиночных символов > threshold, считаем спамом)
    """
    if not text or len(text.strip()) < 10:
        return False
    
    words = text.split()
    if len(words) < 5:
        return False
    
    single_chars = sum(1 for word in words if len(word.strip()) == 1)
    
    ratio = single_chars / len(words)
    
    return ratio > threshold