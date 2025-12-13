import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
import numpy as np
from scipy.sparse import hstack
import utils
import preprocessing
import os

paths = utils.get_paths()


df = pd.read_csv(paths['combined'])
print(f"Загружено {len(df)} сообщений")

if 'cleaned_text' not in df.columns:
    df['text'] = df['text'].astype(str).apply(preprocessing.clean_text)

features_df = preprocessing.extract_features(df.copy())

train_df, test_df = train_test_split(
    features_df, 
    test_size=0.2,
    stratify=features_df['label'],
    random_state=42
)
print(f"Тренировочные данные: {len(train_df)} сообщений")
print(f"Тестовые данные: {len(test_df)} сообщений")

X_train_text = train_df['text']
y_train = train_df['label']
X_test_text = test_df['text']
y_test = test_df['label']

print("Векторизация текста...")
vectorizer = TfidfVectorizer(
    max_features=5000,
    stop_words=None,
    ngram_range=(1, 1)
)
X_train_vec = vectorizer.fit_transform(X_train_text)
X_test_vec = vectorizer.transform(X_test_text)
print(f"Размерность данных: {X_train_vec.shape}")

feature_cols = [col for col in train_df.columns if col not in ['text', 'label']]
X_train_add = train_df[feature_cols].values
X_test_add = test_df[feature_cols].values

X_train_full = hstack([X_train_vec, X_train_add])
X_test_full = hstack([X_test_vec, X_test_add])

print("\nОбучение модели")
model = LogisticRegression(
    class_weight='balanced', 
    max_iter=1000
)
model.fit(X_train_full, y_train)
print("Обучение завершено.")

joblib.dump(model, paths['model'])
joblib.dump(vectorizer, paths['vectorizer'])
print("Модель и векторизатор сохранены в папке models/")
