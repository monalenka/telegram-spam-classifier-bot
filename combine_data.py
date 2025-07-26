import pandas as pd
from src import utils

paths = utils.get_paths()

ham_df = pd.read_csv(paths['ham'], header=None, names=['text'])
spam_df = pd.read_csv(paths['spam'], header=None, names=['text'])

ham_df['label'] = 'ham'
spam_df['label'] = 'spam'

combined_df = pd.concat([ham_df, spam_df])

combined_df.to_csv(paths['combined'], index=False)
print("Данные объединены и сохранены в", paths['combined'])
print(f"Всего сообщений: {len(combined_df)}")
print(f"Ham: {len(ham_df)}, Spam: {len(spam_df)}")