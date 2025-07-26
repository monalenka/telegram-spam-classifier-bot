# Инструкции

### 1. Подготовка окружения
```bash
#клонируйте репозиторий
git clone https://github.com/your-username/spam_classifier.git
cd spam_classifier

#создайте виртуальное окружение
python -m venv venv

#активируйте его
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

#установите зависимости
pip install -r requirements.txt
```

### 2. Настройка Telegram бота
1. Найдите @BotFather в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

### 3. Настройка переменных окружения
Создайте файл `.env` в корне проекта:
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
```

### 4. Подготовка данных
```bash
python combine_data.py
python src/train_model.py
python src/evaluate.py
```

### 5. Запуск бота
```bash
python bot/telegram_bot.py
```

### Переменные окружения
```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
# Дополнительные настройки (опционально)
LOG_LEVEL=INFO
VOTE_THRESHOLD=3
HINT_DELETE_DELAY=300
``` 