'''
Created on 2025 09 04


'''
print("GazoToolsLib.py loaded!　ロードを確認")  # 追加
import os

#子フォルダの取得
def GetKoFolder(files, base_path):
    '''
    指定したパス(base_path)内のfilesリストから、子フォルダのみを抽出して返す
    '''
    folder = []
    for f in files:
        if not str(f).startswith("."):
            full_path = os.path.join(base_path, f)
            if os.path.isdir(full_path):
                folder.append(f)

    return folder

def GetGazoFiles(folder, base_path):
    '''
    フォルダ内のファイルリストから画像ファイルのみを抽出して返す。
    大文字・小文字を区別せず、主要な画像形式を網羅します。
    '''
    Files = []
    # 判定対象の拡張子（小文字で定義）
    valid_extensions = ('.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif')
    
    for f in folder:
        # 小文字に変換して拡張子チェック
        if str(f).lower().endswith(valid_extensions):
            Files.append(f)

    return Files