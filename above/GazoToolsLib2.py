import os

def GetKoFolder(files, base_path="."):
    '''
    指定したパス(base_path)内のfilesリストから、子フォルダのみを抽出して返す
    '''
    folder = []
    for f in files:
        if not str(f).startswith("."):
            full_path = os.path.join(base_path, f)
            if os.path.isdir(full_path):
                folder.append(f)
    for f in folder:
        print(f)
    return folder