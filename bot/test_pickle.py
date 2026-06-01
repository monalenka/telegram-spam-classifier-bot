import pickle

def evil():
    data = b"cos\nsystem\n(S'echo HACKED'\ntR."
    pickle.loads(data)   # B301: pickle