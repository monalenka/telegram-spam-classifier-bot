import joblib
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
import utils
import preprocessing
import numpy as np
from scipy.sparse import hstack

paths = utils.get_paths()

TEST_DATA_PATH = paths['test']
RESULTS_PATH = paths['confusion_matrix']


def evaluate_model():
    model = joblib.load(paths['model'])
    vectorizer = joblib.load(paths['vectorizer'])
    
    test_df = pd.read_csv(TEST_DATA_PATH)
    print(f"Загружено тестовых сообщений: {len(test_df)}")
    
    test_df['text'] = test_df['text'].astype(str).apply(preprocessing.clean_text)
    features_df = preprocessing.extract_features(test_df.copy())
    
    X_test_text = features_df['text']
    y_test = features_df['label']
    X_test_vec = vectorizer.transform(X_test_text)
    feature_cols = [col for col in features_df.columns if col not in ['text', 'label']]
    X_test_add = features_df[feature_cols].values
    X_test_full = hstack([X_test_vec, X_test_add])
    
    y_pred = model.predict(X_test_full)
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', 
                xticklabels=['ham', 'spam'], 
                yticklabels=['ham', 'spam'])
    plt.xlabel('Predicted')
    plt.ylabel('True')
    plt.title('Confusion Matrix')
    plt.savefig(RESULTS_PATH)
    print(f"\nМатрица ошибок сохранена в {RESULTS_PATH}")

    mismatches = features_df[y_test != y_pred]
    print(f"\nОшибочно классифицированные сообщения ({len(mismatches)}):")
    for idx, row in mismatches.iterrows():
        print(f"Текст: {row['text']}")
        print(f"Истинная метка: {row['label']}, Предсказание: {y_pred[idx]}")
        print('-' * 40)

if __name__ == "__main__":
    evaluate_model()