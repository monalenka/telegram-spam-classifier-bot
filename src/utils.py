import os
from dotenv import load_dotenv

def get_path(key: str) -> str:
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    
    path = os.getenv(key)
    
    if not path:
        raise ValueError(f"Переменная окружения {key} не найдена в .env файле")
    
    return path

def create_directories():
    directories = [
        'data/processed',
        'models',
        'results'
    ]
    
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"Директория создана: {dir_path}")

def get_paths():
    load_dotenv(os.path.join(os.path.dirname(__file__), '../.env'))
    paths = {
        'combined': os.getenv('COMBINED_PATH', 'data/combined.csv'),
        'ham': os.getenv('HAM_PATH', 'data/processed/ham.csv'),
        'spam': os.getenv('SPAM_PATH', 'data/processed/spam.csv'),
        'train': os.getenv('TRAIN_PATH', 'data/processed/train_data.csv'),
        'test': os.getenv('TEST_PATH', 'data/processed/test_data.csv'),
        'model': os.getenv('MODEL_PATH', 'models/spam_model.pkl'),
        'vectorizer': os.getenv('VECTORIZER_PATH', 'models/vectorizer.pkl'),
        'confusion_matrix': os.getenv('CONFUSION_MATRIX_PATH', 'results/confusion_matrix.png'),
    }
    return paths