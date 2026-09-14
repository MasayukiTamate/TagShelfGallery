'''
作成日: 2025年09月29日
修正日: 2026年01月01日
作成者: tamate masayuki

【機能概要】
行程１：画像管理フォルダの選択（今回追加）
行程２：主窓表示
行程３：子絵窓表示
行程４：子データ窓表示
行程５：絵のフォルダスキャン

【修正内容】
- 起動時にフォルダ選択ダイアログを表示するように改善。
- random.random の誤用を修正。
- データの重複保持問題を修正。
- 複数の tk.Tk() 生成を tk.Toplevel() に適正化。
'''
from lib.GazoToolsBasicLib import tkConvertWinSize
from lib.GazoToolsLib import GetKoFolder, GetGazoFiles
import os
import sys
import tkinter as tk
from tkinter import filedialog
from PIL import ImageTk, Image
from tkinterdnd2 import *
import random
import json

CONFIG_FILE = "config.json"

def load_config():
    """
    設定ファイルから前回のフォルダパス、ウィンドウ位置、各種フラグを読み込みます。
    """
    config = {
        "last_folder": os.getcwd(),
        "geometries": {},
        "settings": {
            "random_pos": False,
            "topmost": True,
            "show_folder": True,
            "show_file": True
        }
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config["last_folder"] = data.get("last_folder", os.getcwd())
                config["geometries"] = data.get("geometries", {})
                
                # 設定フラグの読み込み（デフォルト値を維持しつつ上書き）
                saved_settings = data.get("settings", {})
                config["settings"].update(saved_settings)
                
                if not os.path.exists(config["last_folder"]):
                    config["last_folder"] = os.getcwd()
        except:
            pass
    return config

def save_config(path, geometries=None, settings=None):
    """
    現在の状態（フォルダ、位置、各種設定）を設定ファイルに保存します。
    """
    try:
        prev = load_config()
        data = {
            "last_folder": path,
            "geometries": geometries if geometries is not None else prev.get("geometries", {}),
            "settings": settings if settings is not None else prev.get("settings", {})
        }
            
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"設定保存エラー: {e}")

def select_initial_folder():
    """
    起動時に画像フォルダを選択させるためのダイアログを表示します。
    @return: 選択されたフォルダパス。キャンセルされた場合は空文字。
    """
    temp_root = tk.Tk()
    temp_root.withdraw() # 一時的な窓を非表示にする
    folder_path = filedialog.askdirectory(title="画像フォルダを選択してください")
    temp_root.destroy()
    return folder_path

# --- 設定の読み込みと初期化 ---
CONFIG_DATA = load_config()
DEFOLDER = CONFIG_DATA["last_folder"]
SAVED_GEOS = CONFIG_DATA.get("geometries", {})
SAVED_SETTINGS = CONFIG_DATA.get("settings", {})

'''/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
クラス定義セクション
/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/_/
'''

class HakoData():
    """
    画像データと管理フラグを保持するクラスです。
    """
    def __init__(self):
        """
        インスタンスの初期化を行います。
        """
        self.StartFolder = DEFOLDER
        self.GazoFiles = []
        self.GazoDrawingFlag = []
        self.GazoDrawingNumFlag = []
        pass
    def GetGazoFiles(self, GazoFiles):
        self.GazoFiles.append(GazoFiles)
        
        for _ in range(len(GazoFiles)):
            self.GazoDrawingFlag.append(0)
        pass

    def RandamGazoSet(self):
        """
        全画像ファイルからランダムに1つ選択して返します。
        重複して選ばれる可能性があるため、トグル（閉じる）機能が動作します。
        """
        if not self.GazoFiles:
            return None
        return random.choice(self.GazoFiles)

class GazoPicture():
    """
    画像の描画およびウィンドウ表示を制御するクラスです。
    """
    def __init__(self, parent):
        self.parent = parent
        self.StartFolder = DEFOLDER
        self.random_pos = tk.BooleanVar(value=False) # 表示位置ランダムフラグ
        self.open_windows = {} # 現在開いている画像ウィンドウを管理 {フルパス: ウィンドウオブジェクト}

    def SetFolder(self, folder):
        '''
        画像のあるフォルダをセット
        '''
        self.StartFolder = folder
        self.CloseAll() # フォルダ変更時に一度全ての画像を閉じる

    def CloseAll(self):
        """表示中の全ての画像ウィンドウを閉じ、管理をクリアします。"""
        for win in list(self.open_windows.values()):
            try:
                win.destroy()
            except: pass
        self.open_windows.clear()

    def Drawing(self, fileName):
        """
        指定された画像ファイルを読み込み、最適なサイズと位置で表示します。
        既に開いている場合は、ウィンドウを閉じます（トグル動作）。
        """
        if not fileName: return
        imageFolder = self.StartFolder
        
        # パスの正規化（大文字小文字を無視し、絶対パスで統一）
        fullName = os.path.normcase(os.path.abspath(os.path.join(imageFolder, fileName)))
        
        # --- トグル再表示の実装: 既に開いている場合は一度閉じてから再表示 ---
        if fullName in self.open_windows:
            print(f"[RE-OPEN] 既に出ているため、一度閉じてから再表示します: {fullName}")
            try:
                self.open_windows[fullName].destroy()
            except: pass
            if fullName in self.open_windows:
                del self.open_windows[fullName]
            # ここで return せず、下の「新規表示」の処理へ進むことで「閉じたら表示」を実現します

        print(f"[OPEN IMAGE] 表示処理を開始: {fullName}")
        
        try:
            # 画像の読み込み
            img = Image.open(fullName)
            orig_w, orig_h = img.width, img.height

            # ディスプレイサイズの取得
            screen_w = self.parent.winfo_screenwidth()
            screen_h = self.parent.winfo_screenheight()

            # 表示上限サイズ（画面の80%）
            limit_w = screen_w * 0.8
            limit_h = screen_h * 0.8

            # 縮小・拡大倍率の計算（アスペクト比を維持）
            scale = min(limit_w / orig_w, limit_h / orig_h)
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)

            # 画像のリサイズ
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(img_resized)
            
            # --- 表示位置の計算 (他の窓に被らないように) ---
            if self.random_pos.get():
                # ランダムモード
                base_x = random.randint(0, max(0, screen_w - new_w))
                base_y = random.randint(0, max(0, screen_h - new_h))
            else:
                # ファイル一覧窓の現在の位置とサイズを取得
                try:
                    base_x = file_win.winfo_x() + file_win.winfo_width() + 20
                    base_y = file_win.winfo_y()
                    
                    # 画面の右端を越えてしまう場合は、左側
                    if base_x + new_w > screen_w:
                        base_x = max(10, folder_win.winfo_x() - new_w - 20)
                except:
                    base_x, base_y = 400, 100 # 万が一窓が取得できない場合

            # 画像表示用のウィンドウ（Toplevel）を生成
            win = tk.Toplevel(self.parent)
            win.title(f"{fileName} ({int(scale*100)}%)")
            win.attributes("-topmost", True)
            
            # 管理に登録
            self.open_windows[fullName] = win
            
            # ウィンドウを閉じる際の処理をカスタマイズ (管理辞書からの削除)
            def on_img_close():
                # 辞書から削除（正規化パスで比較）
                if fullName in self.open_windows:
                    del self.open_windows[fullName]
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", on_img_close)

            # ウィンドウサイズと位置の設定
            win.geometry(f"{new_w}x{new_h}+{base_x}+{base_y}")
            
            # キャンバスの配置
            canvas = tk.Canvas(win, width=new_w, height=new_h)
            canvas.pack()
            canvas.image = tkimg
            canvas.create_image(0, 0, image=tkimg, anchor=tk.NW)
        except Exception as e:
            print(f"画像表示エラー: {e}")

# ポンコツでした。重複定義を掃除する際に、大切な関数まで消してしまいました。
# --- 共通のUI更新処理 ---
def refresh_ui(new_path):
    """
    指定されたパスに基づいて、全てのデータとウィンドウ表示を更新します。
    """
    global DEFOLDER
    if not os.path.exists(new_path): return
    DEFOLDER = new_path
    
    # データの再読み込み
    try:
        all_items = os.listdir(DEFOLDER)
        folders = GetKoFolder(all_items, DEFOLDER)
        files = GetGazoFiles(all_items, DEFOLDER)
    except Exception as e:
        print(f"再読み込みエラー: {e}")
        return

    # データマネージャの更新
    data_manager.SetGazoFiles(files, DEFOLDER)
    GazoControl.SetFolder(DEFOLDER)
    
    # ウィンドウタイトルの更新
    koRoot.title("画像tools - " + DEFOLDER)
    save_config(DEFOLDER) # 設定を保存
    
    # フォルダリストボックスの更新 (画像数を添える)
    folder_listbox.delete(0, tk.END)
    
    # 先頭に現在のフォルダを分かりやすい名前で追加
    try:
        current_name = os.path.basename(DEFOLDER)
        if not current_name: current_name = DEFOLDER # ドライブ直下など
        display_current = f"({len(files)}) [現在] {current_name}"
        folder_listbox.insert(tk.END, display_current)
    except:
        folder_listbox.insert(tk.END, "(-) [現在] ???")

    for f in folders:
        try:
            # フォルダ内の画像数をカウント
            sub_items = os.listdir(os.path.join(DEFOLDER, f))
            count = len(GetGazoFiles(sub_items, os.path.join(DEFOLDER, f)))
            display_name = f"({count}) {f}"
        except:
            display_name = f"(-) {f}"
        folder_listbox.insert(tk.END, display_name)
    
    # ファイルリストボックスの更新
    file_listbox.delete(0, tk.END)
    for f in files:
        file_listbox.insert(tk.END, f)

    # ウィンドウサイズと座標の再調整
    if 'folder_win' in globals() and 'file_win' in globals():
        adjust_window_layouts(folders, files)

def adjust_window_layouts(folders, files):
    """
    リストの内容に合わせて、かつメイン窓の位置に合わせて
    子ウィンドウのサイズ(縦横)と座標を再計算します。
    """
    # メイン窓の情報
    root_x = koRoot.winfo_x()
    root_y = koRoot.winfo_y()
    root_w = koRoot.winfo_width()

    # --- フォルダ窓の計算 ---
    f_count = len(folders) + 1 # 現在地含む
    # 横幅計算用の文字列リスト ( (枚数) [現在地]... と 各 (枚数) フォルダ名)
    current_base = os.path.basename(DEFOLDER) or DEFOLDER
    f_names = [f"({len(files)}) [現在] {current_base}"] + [f"({len(folders)}) {f}" for f in folders]
    max_f = max([len(f) for f in f_names]) if f_names else 5
    
    w_f = max(200, min(600, max_f * 10 + 60))
    h_f = max(120, min(800, f_count * 20 + 90)) # ボタン・ヘッダー分
    
    # 座標: メイン窓の右隣
    x_f = root_x + root_w + 10
    y_f = root_y
    folder_win.geometry(f"{w_f}x{h_f}+{x_f}+{y_f}")
    
    # --- ファイル窓の計算 ---
    g_count = len(files)
    max_g = max([len(f) for f in files]) if files else 5
    w_g = max(200, min(600, max_g * 8 + 80))
    h_g = max(120, min(800, g_count * 20 + 70))
    
    # 座標: フォルダ窓のさらに右隣
    x_g = x_f + w_f + 10
    y_g = root_y
    
    # 画面右端を越える場合のガード
    screen_w = koRoot.winfo_screenwidth()
    if x_g + w_g > screen_w:
        # 左側に回り込ませる
        x_g = max(10, root_x - w_g - 10)
        
    file_win.geometry(f"{w_g}x{h_g}+{x_g}+{y_g}")

# --- 子フォルダ表示窓（子データ窓）の作成 ---
def create_folder_list_window(parent, folders):
    """
    サブフォルダの一覧を表示するウィンドウを作成します。
    """
    win = tk.Toplevel(parent)
    win.title("子データ窓 - フォルダ一覧")
    win.attributes("-topmost", True)
    
    # ボタンエリア
    btn_frame = tk.Frame(win)
    btn_frame.pack(fill=tk.X, padx=5, pady=5)
    
    def go_up():
        parent_dir = os.path.dirname(DEFOLDER)
        if parent_dir != DEFOLDER:
            refresh_ui(parent_dir)

    btn_up = tk.Button(btn_frame, text="↑ 上のフォルダへ", command=go_up)
    btn_up.pack(fill=tk.X)

    # リストボックス
    frame = tk.Frame(win)
    frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    for folder in folders:
        lb.insert(tk.END, folder)
    lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    scrollbar.config(command=lb.yview)

    def on_double_click(event):
        try:
            idx = lb.curselection()[0]
            sel = lb.get(idx)
            
            # 先頭の項目（現在地）の場合は再読み込みのみ
            if idx == 0:
                refresh_ui(DEFOLDER)
                return

            # 子フォルダの場合は名前を抽出して移動
            if ") " in sel:
                sel = sel.split(") ", 1)[1]
            
            refresh_ui(os.path.join(DEFOLDER, sel))
        except: pass
    lb.bind("<Double-Button-1>", on_double_click)

    return win, lb

# --- 画像ファイル名表示窓（子絵窓）の作成 ---
def create_file_list_window(parent, files, draw_func):
    """
    画像ファイルの一覧を表示するウィンドウを作成します。
    """
    win = tk.Toplevel(parent)
    win.title("子絵窓 - ファイル一覧")
    win.attributes("-topmost", True)
    
    lbl = tk.Label(win, text="画像ファイル一覧 (クリックで表示)", font=("Helvetica", "9", "bold"))
    lbl.pack(pady=5)
    
    frame = tk.Frame(win)
    frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    for file in files:
        lb.insert(tk.END, file)
    lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    scrollbar.config(command=lb.yview)
    
    def on_select(event):
        try:
            idx = lb.curselection()
            if idx:
                draw_func(lb.get(idx[0]))
        except: pass
    lb.bind("<<ListboxSelect>>", on_select)
    
    return win, lb

# --- メイン処理 ---
koRoot = TkinterDnD.Tk()
koRoot.attributes("-topmost", True)
koRoot.geometry(tkConvertWinSize(list([250, 180, 50, 100])))
koRoot.title("画像tools")

def on_closing_main():
    """メインウィンドウの[X]が押された時、全ての設定を保存して完全に終了します。"""
    try:
        # 位置情報の収集
        geos = {
            "main": koRoot.winfo_geometry(),
            "folder": folder_win.winfo_geometry(),
            "file": file_win.winfo_geometry()
        }
        # チェック状態の収集
        sets = {
            "random_pos": GazoControl.random_pos.get(),
            "topmost": koRoot.attributes("-topmost"),
            "show_folder": show_folder_win.get(),
            "show_file": show_file_win.get()
        }
        save_config(DEFOLDER, geos, sets)
    except: pass
    koRoot.destroy()
    sys.exit()

def safe_select_folder():
    """
    最前面属性を一時的に解除してフォルダ選択ダイアログを表示します。
    """
    # アクティブな窓のリストを作成
    wins = [koRoot]
    try:
        if 'folder_win' in globals(): wins.append(folder_win)
        if 'file_win' in globals(): wins.append(file_win)
    except: pass
    
    prev_states = [w.attributes("-topmost") for w in wins]
    for w in wins: w.attributes("-topmost", False)
    
    # ダイアログ表示
    path = filedialog.askdirectory(title="画像フォルダを選択してください")
    
    # 属性を元に戻す
    for i, w in enumerate(wins):
        w.attributes("-topmost", prev_states[i])
    
    return path

# メニューバーの作成
menubar = tk.Menu(koRoot)
koRoot.config(menu=menubar)

# ファイルメニュー
file_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ファイル(F)", menu=file_menu)
file_menu.add_command(label="フォルダを開く...", command=lambda: refresh_ui(safe_select_folder()))
file_menu.add_separator()
file_menu.add_command(label="終了(X)", command=on_closing_main)

# 表示管理変数の定義
show_folder_win = tk.BooleanVar(value=SAVED_SETTINGS.get("show_folder", True))
show_file_win = tk.BooleanVar(value=SAVED_SETTINGS.get("show_file", True))

def update_visibility():
    """メニューのチェック状態に合わせてウィンドウの表示/非表示を切り替えます。"""
    if show_folder_win.get(): folder_win.deiconify()
    else: folder_win.withdraw()
    
    if show_file_win.get(): file_win.deiconify()
    else: file_win.withdraw()

def on_closing_folder():
    """フォルダ窓の[X]が押された時の処理。"""
    show_folder_win.set(False)
    folder_win.withdraw()

def on_closing_file():
    """ファイル窓の[X]が押された時の処理。"""
    show_file_win.set(False)
    file_win.withdraw()

def disable_all_topmost():
    """全てのウィンドウの『常に最前面』設定を一括で解除します。"""
    koRoot.attributes("-topmost", False)
    if 'folder_win' in globals() and folder_win:
        folder_win.attributes("-topmost", False)
    if 'file_win' in globals() and file_win:
        file_win.attributes("-topmost", False)

# メニュー構成
data_manager = HakoData()
GazoControl = GazoPicture(koRoot)
# 保存された設定を適用
GazoControl.random_pos.set(SAVED_SETTINGS.get("random_pos", False))
koRoot.attributes("-topmost", SAVED_SETTINGS.get("topmost", True))

# 表示メニュー
view_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="表示(V)", menu=view_menu)
view_menu.add_checkbutton(label="フォルダ一覧を表示", variable=show_folder_win, command=update_visibility)
view_menu.add_checkbutton(label="ファイル一覧を表示", variable=show_file_win, command=update_visibility)
view_menu.add_separator()
view_menu.add_command(label="全ての最前面表示をOFF", command=disable_all_topmost)

# 設定メニュー
config_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="設定(S)", menu=config_menu)
config_menu.add_checkbutton(label="表示位置をランダムにする", variable=GazoControl.random_pos)
config_menu.add_separator()
config_menu.add_command(label="常に最前面(T) ON/OFF", command=lambda: koRoot.attributes("-topmost", not koRoot.attributes("-topmost")))

# 初回データとウィンドウ生成
all_items = os.listdir(DEFOLDER)
folder_win, folder_listbox = create_folder_list_window(koRoot, GetKoFolder(all_items, DEFOLDER))
file_win, file_listbox = create_file_list_window(koRoot, GetGazoFiles(all_items, DEFOLDER), GazoControl.Drawing)

# 座標と表示状態の復元
if "main" in SAVED_GEOS: koRoot.geometry(SAVED_GEOS["main"])
if "folder" in SAVED_GEOS: folder_win.geometry(SAVED_GEOS["folder"])
if "file" in SAVED_GEOS: file_win.geometry(SAVED_GEOS["file"])

update_visibility() # 保存された show_folder/show_file を適用

# ウィンドウの「閉じる」動作をカスタマイズ
folder_win.protocol("WM_DELETE_WINDOW", on_closing_folder)
file_win.protocol("WM_DELETE_WINDOW", on_closing_file)
koRoot.protocol("WM_DELETE_WINDOW", on_closing_main)

# ファイルメニューの終了コマンドも修正
file_menu.entryconfigure("終了(X)", command=on_closing_main)

refresh_ui(DEFOLDER) # タイトルなどの初期化

# UI
text = tk.StringVar(koRoot)
text.set("ドラッグ＆ドロップ")
lbl = tk.Label(koRoot, textvariable=text, bg="lightblue", height=4)
lbl.drop_target_register(DND_FILES)
lbl.dnd_bind("<<Drop>>", lambda e: text.set(e.data))
lbl.pack(fill=tk.BOTH, padx=5, pady=5)

tk.Button(koRoot, text="ランダム画像を表示", command=lambda: GazoControl.Drawing(data_manager.RandamGazoSet())).pack(pady=5)

koRoot.mainloop()
