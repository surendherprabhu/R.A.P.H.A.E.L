import os

def list_directory(path="."):
    try:
        return os.listdir(path)
    except Exception as e:
        return str(e)
    
meou = list_directory()
print(meou)