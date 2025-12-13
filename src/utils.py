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
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    paths = {
        'combined': os.path.join(project_root, 'data', 'combined.csv'),
        'ham': os.path.join(project_root, 'data', 'processed', 'ham.csv'),
        'spam': os.path.join(project_root, 'data', 'processed', 'spam.csv'),
        'train': os.path.join(project_root, 'data', 'processed', 'train_data.csv'),
        'test': os.path.join(project_root, 'data', 'processed', 'test_data.csv'),
        'model': os.path.join(project_root, 'models', 'spam_model.pkl'),
        'vectorizer': os.path.join(project_root, 'models', 'vectorizer.pkl'),
        'confusion_matrix': os.path.join(project_root, 'results', 'confusion_matrix.png'),
    }
    return paths