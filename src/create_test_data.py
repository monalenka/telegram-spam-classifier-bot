import pandas as pd
from sklearn.model_selection import train_test_split
import os
import utils

paths = utils.get_paths()

def create_test_data():
    combined_df = pd.read_csv(paths['combined'])
    print(f"Загружено сообщений: {len(combined_df)}")
    
    train_df, test_df = train_test_split(
        combined_df,
        test_size=0.2,
        stratify=combined_df['label'],
        random_state=42
    )
    
    os.makedirs(os.path.dirname(paths['test']), exist_ok=True)
    
    test_df.to_csv(paths['test'], index=False)
    print(f"Тестовые данные сохранены: {len(test_df)} сообщений")
    
    train_df.to_csv(paths['train'], index=False)
    print(f"Тренировочные данные сохранены: {len(train_df)} сообщений")

if __name__ == "__main__":
    create_test_data()