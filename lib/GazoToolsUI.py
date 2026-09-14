'''
作成日: 2026年01月05日
作成者: tamate masayuki (Refactored by Antigravity)
機能: GazoTools UI実装 (RatingWindow, InfoWindow, GazoPicture)
'''
import tkinter as tk
from tkinter import simpledialog, messagebox
import os
import ctypes
from ctypes import wintypes
import random
from PIL import ImageTk, Image, ImageOps
from .GazoToolsLogger import get_logger
from .GazoToolsData import (
    load_tags, load_ratings, save_tags, save_ratings, 
    calculate_file_hash, load_vectors
)
from .GazoToolsState import get_app_state
from .GazoToolsVectorInterpreter import get_interpreter

logger = get_logger(__name__)
app_state = get_app_state()

class RatingWindow:
    """評価ウィンドウの管理クラス"""
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.window = None
        self._rating_var = tk.StringVar(value="未選択")
        self._current_rating_name_label = None
        self._star_labels = []

    def create(self):
        """ウィンドウを作成する（既に存在する場合はそれを返す）"""
        if self.window is not None:
            try:
                if self.window.winfo_exists():
                    return self.window
            except:
                self.window = None

        try:
            # メインウィンドウの子として評価ウィンドウを作成
            self.window = tk.Toplevel(self.parent)
            self.window.title("評価")
            self.window.attributes("-topmost", True)
            self.window.overrideredirect(True)  # タイトルバーなし
            self.window.attributes("-alpha", 0.9)  # 半透明

            # ディスプレイ中央の最下部に配置（サイズを大きくする）
            screen_w = self.window.winfo_screenwidth()
            screen_h = self.window.winfo_screenheight()
            win_width = 300
            win_height = 120
            x = (screen_w - win_width) // 2
            y = screen_h - win_height - 10  # 最下部から10px上
            self.window.geometry(f"{win_width}x{win_height}+{x}+{y}")

            # 背景フレーム
            frame = tk.Frame(self.window, bg="#2c3e50", bd=2, relief="raised")
            frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # 評価選択ドロップダウン
            rating_frame = tk.Frame(frame, bg="#34495e")
            rating_frame.pack(fill=tk.X, pady=(5, 2))

            tk.Label(rating_frame, text="評価:", font=("Arial", 9),
                    fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT, padx=(5, 2))

            # 評価リストを作成
            self.update_dropdown()
            
            # 新規評価作成ボタン
            create_btn = tk.Button(rating_frame, text="+", font=("Arial", 8, "bold"),
                                 bg="#27ae60", fg="white", bd=0, padx=3,
                                 command=self._create_new_rating)
            create_btn.pack(side=tk.RIGHT, padx=(2, 5))

            # 現在の評価表示エリア
            display_frame = tk.Frame(frame, bg="#2c3e50")
            display_frame.pack(fill=tk.X, pady=(2, 5))

            # 評価名ラベル
            self._current_rating_name_label = tk.Label(display_frame, text="未選択",
                                                     font=("Arial", 10, "bold"),
                                                     fg="#f39c12", bg="#2c3e50")
            self._current_rating_name_label.pack(anchor="center", pady=(0, 3))

            # 星のラベルを作成
            self._star_labels = []
            star_frame = tk.Frame(display_frame, bg="#2c3e50")
            star_frame.pack(anchor="center")

            for i in range(6):
                star_text = "★" if i < 5 else "☆"  # 6つ目は特別な星マーク
                star_label = tk.Label(star_frame, text=star_text,
                                    font=("Arial", 16, "bold"),
                                    fg="#cccccc", bg="#2c3e50", cursor="hand2")
                star_label.pack(side=tk.LEFT, padx=1)
                star_label.bind("<Button-1>", lambda e, rating=i+1: self._on_rating_value_click(rating))
                self._star_labels.append(star_label)

            # 初期表示
            self._update_star_display(0)

            return self.window

        except Exception as e:
            logger.error(f"評価ウィンドウ作成エラー: {e}")
            return None

    def update_dropdown(self):
        """評価ドロップダウンを更新"""
        if not self.window: return
        try:
            # rating_frame を探す (bg='#34495e' のフレーム)
            rating_frame = None
            main_frame = self.window.winfo_children()[0] # frame defined in create
            for child in main_frame.winfo_children():
                if isinstance(child, tk.Frame) and str(child.cget('bg')) == '#34495e':
                    rating_frame = child
                    break
            
            if rating_frame:
                 # 既存のOptionMenuを削除
                for child in rating_frame.winfo_children():
                    if isinstance(child, tk.OptionMenu):
                        child.destroy()
                        break
                
                # 新しいリスト
                rating_options = ["未選択"] + list(self.controller.rating_dict.keys())
                
                # OptionMenu作成
                rating_menu = tk.OptionMenu(rating_frame, self._rating_var,
                                           *rating_options, command=self._on_rating_selected)
                rating_menu.config(bg="#34495e", fg="#ecf0f1", font=("Arial", 9),
                                 highlightthickness=0, bd=0)
                rating_menu.pack(side=tk.LEFT, padx=(0, 5))
        except Exception as e:
            logger.error(f"ドロップダウン更新エラー: {e}")

    def update(self, image_hash):
        """表示内容を更新"""
        self.create()  # 確実に作成
        if not self.window: return

        if image_hash:
            tag_data = self.controller.tag_dict.get(image_hash)
            current_rating = tag_data["rating"] if tag_data and tag_data.get("rating") else 0
            
             # この画像に割り当てられている評価名を取得して選択
            assigned_rating = self.controller.image_rating_map.get(image_hash)
            if assigned_rating and assigned_rating in self.controller.rating_dict:
                self._rating_var.set(assigned_rating)
                rating_data = self.controller.rating_dict[assigned_rating]
                current_rating = rating_data.get("rating", 0)
            else:
                 self._rating_var.set("未選択")
                 if not current_rating: current_rating = 0

            self._update_star_display(current_rating)
            
            # ラベル更新
            if self._current_rating_name_label:
                val = self._rating_var.get()
                self._current_rating_name_label.config(text=val)

            self.window.deiconify()
        else:
            self.window.withdraw()

    def _update_star_display(self, rating):
        """星の色を更新"""
        try:
            for i, star_label in enumerate(self._star_labels):
                if i < rating:
                    star_label.config(fg="#ffd700")
                else:
                    star_label.config(fg="#cccccc")
        except Exception as e:
            logger.error(f"星表示更新エラー: {e}")

    def _on_rating_selected(self, rating_name):
        """評価名選択時の処理"""
        # Controllerに委譲するか、ここでControllerのデータを叩く
        self.controller.handle_rating_selected(rating_name)
        
        # UI更新（今の値で再描画）
        if rating_name != "未選択":
             rating_data = self.controller.rating_dict.get(rating_name, {})
             rating_val = rating_data.get("rating", 0)
             self._update_star_display(rating_val)
             if self._current_rating_name_label: self._current_rating_name_label.config(text=rating_name)
        else:
             self._update_star_display(0)
             if self._current_rating_name_label: self._current_rating_name_label.config(text="未選択")

    def _create_new_rating(self):
        """新規作成ダイアログ"""
        try:
            rating_name = simpledialog.askstring("新規評価作成", "評価の名前を入力してください:",
                                               parent=self.window)
            if rating_name and rating_name.strip():
                if self.controller.handle_create_rating(rating_name.strip()):
                    self.update_dropdown()
                    self._rating_var.set(rating_name.strip())
                    self._on_rating_selected(rating_name.strip())
                else:
                    messagebox.showwarning("警告", f"評価名「{rating_name}」は既に存在します。", parent=self.window)
        except Exception as e:
            logger.error(f"新規作成エラー: {e}")

    def _on_rating_value_click(self, rating):
        """星クリック処理"""
        selected_rating = self._rating_var.get()
        if selected_rating and selected_rating != "未選択":
            self.controller.handle_rating_value_change(selected_rating, rating)
            self._update_star_display(rating)
        else:
            logger.warning("評価が選択されていません")


class InfoWindow:
    """情報ウィンドウの管理クラス"""
    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.window = None
        self._info_labels = {}

    def create(self):
        if self.window is not None:
            try:
                if self.window.winfo_exists():
                    return self.window
            except:
                self.window = None

        try:
            self.window = tk.Toplevel(self.parent)
            self.window.title("画像情報")
            self.window.attributes("-topmost", True)
            self.window.overrideredirect(True)
            self.window.attributes("-alpha", 0.9)

            screen_w = self.window.winfo_screenwidth()
            # screen_h = self.window.winfo_screenheight()
            win_width = 300
            win_height = 200
            x = screen_w - win_width - 10
            y = 10
            self.window.geometry(f"{win_width}x{win_height}+{x}+{y}")

            frame = tk.Frame(self.window, bg="#2c3e50", bd=2, relief="raised")
            frame.pack(fill=tk.BOTH, expand=True)

            title_label = tk.Label(frame, text="画像情報", font=("Arial", 12, "bold"),
                                 fg="#ffffff", bg="#2c3e50")
            title_label.pack(pady=(10, 5))

            info_frame = tk.Frame(frame, bg="#34495e")
            info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            self._info_labels = {}
            info_items = [
                ("filename", "ファイル名:"),
                ("size", "画像サイズ:"),
                ("filesize", "ファイルサイズ:"),
                ("zoom", "ズーム倍率:"),
                ("tags", "タグ:"),
                ("rating", "評価:")
            ]

            for key, label_text in info_items:
                item_frame = tk.Frame(info_frame, bg="#34495e")
                item_frame.pack(fill=tk.X, pady=1)
                
                label = tk.Label(item_frame, text=label_text, font=("Arial", 9),
                               fg="#ecf0f1", bg="#34495e", anchor="w")
                label.pack(side=tk.LEFT, padx=(0, 5))
                
                value_label = tk.Label(item_frame, text="", font=("Arial", 9),
                                     fg="#f39c12", bg="#34495e", anchor="w")
                value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._info_labels[key] = value_label

            return self.window

        except Exception as e:
            logger.error(f"情報ウィンドウ作成エラー: {e}")
            return None

    def update(self, image_path, image_hash, width=None, height=None, zoom_percent=None):
        """情報を更新して表示"""
        self.create()
        if not self.window: return

        if image_path and image_hash:
            # 各種情報の更新
            filename = os.path.basename(image_path)
            self._info_labels["filename"].config(text=filename)

            if width and height:
                size_text = f"{width} × {height}"
            else:
                size_text = "不明"
            self._info_labels["size"].config(text=size_text)

            try:
                if os.path.exists(image_path):
                    file_size = os.path.getsize(image_path)
                    if file_size < 1024:
                        size_text = f"{file_size} B"
                    elif file_size < 1024 * 1024:
                        size_text = f"{file_size / 1024:.1f} KB"
                    else:
                        size_text = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_text = "不明"
            except:
                size_text = "不明"
            self._info_labels["filesize"].config(text=size_text)

            if zoom_percent:
                zoom_text = f"{zoom_percent}%"
            else:
                zoom_text = "100%"
            self._info_labels["zoom"].config(text=zoom_text)

            # Controllerからデータ取得
            tag_data = self.controller.tag_dict.get(image_hash)
            tags_text = tag_data["tag"] if tag_data and tag_data.get("tag") else "なし"
            self._info_labels["tags"].config(text=tags_text)

            assigned_rating = self.controller.image_rating_map.get(image_hash)
            if assigned_rating and assigned_rating in self.controller.rating_dict:
                rating_data = self.controller.rating_dict[assigned_rating]
                rating_value = rating_data.get("rating", 0)
                rating_text = f"{assigned_rating}: {rating_value}/6" + (" ★" * rating_value)
            else:
                rating_text = "未評価"
            self._info_labels["rating"].config(text=rating_text)

            self.window.deiconify()
        else:
            self.window.withdraw()

    def update_rating(self, image_hash):
        """評価情報のみ更新"""
        if not self.window or not self._info_labels: return
        
        assigned_rating = self.controller.image_rating_map.get(image_hash)
        if assigned_rating and assigned_rating in self.controller.rating_dict:
            rating_data = self.controller.rating_dict[assigned_rating]
            rating_value = rating_data.get("rating", 0)
            rating_text = f"{assigned_rating}: {rating_value}/6" + (" ★" * rating_value)
        else:
            rating_text = "未評価"
        
        if "rating" in self._info_labels:
            self._info_labels["rating"].config(text=rating_text)

class GazoPicture():
    """画像表示制御クラスなのじゃ。のじゃ。"""

    # 評価ウィンドウ（独立した子ウィンドウ）
    _rating_window = None
    _current_image_hash = None

    # 情報ウィンドウ（独立した子ウィンドウ）
    _info_window = None

    def __init__(self, parent, def_folder):
        self.parent = parent
        self.StartFolder = def_folder
        self.random_pos = tk.BooleanVar(value=False)
        self.random_size = tk.BooleanVar(value=False)
        self.open_windows = {}
        self.folder_win = None
        self.file_win = None
        self.tag_dict = load_tags()
        self.rating_dict = load_ratings()  # 評価データ（名前付き評価）
        self.image_rating_map = {}  # 画像ハッシュ -> 評価ID のマッピング
        self.vectors_cache = load_vectors() # キャッシュを追加したのじゃ
        
        # UI Managers
        self.rating_window = RatingWindow(parent, self)
        self.info_window = InfoWindow(parent, self)

        # 既存のタグデータから評価マッピングを復元
        for image_hash, data in self.tag_dict.items():
            if "assigned_rating" in data and data["assigned_rating"]:
                self.image_rating_map[image_hash] = data["assigned_rating"]

    def update_rating_window(self, image_hash=None):
        """評価ウィンドウを更新"""
        self._current_image_hash = image_hash
        self.rating_window.update(image_hash)

    def update_info_window(self, image_path=None, image_hash=None, width=None, height=None, zoom_percent=None):
        """情報ウィンドウを更新"""
        self.info_window.update(image_path, image_hash, width, height, zoom_percent)

    # --- Handlers for UI ---
    def handle_rating_selected(self, rating_name):
        """評価選択時の処理"""
        image_hash = self._current_image_hash
        if not image_hash: return

        if rating_name == "未選択":
            if image_hash in self.image_rating_map:
                del self.image_rating_map[image_hash]
                logger.debug(f"画像から評価を解除: {image_hash[:8]}...")
        else:
            self.image_rating_map[image_hash] = rating_name
            logger.debug(f"画像に評価適用: {image_hash[:8]}... -> {rating_name}")
            
        # InfoWindow も更新
        self.info_window.update_rating(image_hash)

    def handle_create_rating(self, rating_name):
        """新規評価作成処理"""
        if rating_name not in self.rating_dict:
            self.rating_dict[rating_name] = {
                "name": rating_name,
                "rating": 3,
            }
            save_ratings(self.rating_dict)
            logger.debug(f"新規評価作成: {rating_name}")
            return True
        return False

    def handle_rating_value_change(self, rating_name, value):
        """評価値変更処理"""
        if rating_name not in self.rating_dict:
             self.rating_dict[rating_name] = {"name": rating_name, "rating": 0}
        
        self.rating_dict[rating_name]["rating"] = value
        save_ratings(self.rating_dict)
        
        # 現在の画像がこの評価を使っている場合、InfoWindowも更新
        image_hash = self._current_image_hash
        if image_hash and self.image_rating_map.get(image_hash) == rating_name:
            self.info_window.update_rating(image_hash)
        logger.debug(f"評価値変更: {rating_name} = {value}")

    def set_image_tag(self, img_window, image_hash):
        """画像ウィンドウにタグラベルを付与するのじゃ。のじゃ。"""
        if not image_hash: return
        data = self.tag_dict.get(image_hash)
        tag = data["tag"] if data else ""
        
        if tag:
            # 既存のラベルがあれば更新、なければ作成
            if hasattr(img_window, "_tag_label"):
                img_window._tag_label.config(text=tag)
            else:
                lbl = tk.Label(img_window, text=tag, bg="#fffae6", fg="#333", font=("MS Gothic", 9), relief="solid")
                lbl.place(relx=0, rely=0) # 左上に固定
                img_window._tag_label = lbl
        else:
            # タグが空ならラベルを隠す
            if hasattr(img_window, "_tag_label"):
                img_window._tag_label.place_forget()

    def SetUI(self, folder_win, file_win):
        """UIウィンドウの参照を保持するのじゃ。のじゃ。"""
        self.folder_win = folder_win
        self.file_win = file_win

    def SetFolder(self, folder):
        self.StartFolder = folder
        self.CloseAll()

    def CloseAll(self):
        """全ての画像ウィンドウを閉じるのじゃ。のじゃ。"""
        for win in list(self.open_windows.values()):
            try:
                win.destroy()
            except: pass
        self.open_windows.clear()

        # 評価ウィンドウと情報ウィンドウは非表示にする（独立しているため閉じない）
        GazoPicture._current_image_hash = None
        if GazoPicture._rating_window:
            GazoPicture._rating_window.withdraw()
        if GazoPicture._info_window:
            GazoPicture._info_window.withdraw()

    def Drawing(self, fileName):
        if not fileName or not isinstance(fileName, str):
            logger.warning(f"画像表示スキップ: fileName が None/非文字列です ({type(fileName).__name__})")
            return

        fileName = fileName.strip()
        if not fileName:
            logger.warning("画像表示スキップ: fileName が空文字です")
            return
        
        # 相対パスの場合はStartFolderと結合、フルパスの場合はそのまま使用
        if os.path.isabs(fileName):
            fullName = os.path.normcase(os.path.abspath(fileName))
            # ベースフォルダを取得（表示用）
            imageFolder = self.StartFolder
        else:
            imageFolder = self.StartFolder
            fullName = os.path.normcase(os.path.abspath(os.path.join(imageFolder, fileName)))
        
        # 既に開いている場合は一度閉じてから再表示（リフレッシュ）
        if fullName in self.open_windows:
            try:
                self.open_windows[fullName].destroy()
            except: pass
            if fullName in self.open_windows:
                del self.open_windows[fullName]

        try:
            with Image.open(fullName) as img:
                orig_w, orig_h = img.width, img.height
                screen_w = self.parent.winfo_screenwidth()
                screen_h = self.parent.winfo_screenheight()
                
                # 最大サイズの決定（0の場合は画面サイズの80%を使用）
                if app_state.image_max_width > 0:
                    limit_w = app_state.image_max_width
                else:
                    limit_w = screen_w * 0.8
                
                if app_state.image_max_height > 0:
                    limit_h = app_state.image_max_height
                else:
                    limit_h = screen_h * 0.8
                
                # アスペクト比を維持してスケールを計算
                scale = min(limit_w / orig_w, limit_h / orig_h)
                new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                
                # 最小サイズを適用（元の画像が小さい場合に拡大）
                if new_w < app_state.image_min_width and new_h < app_state.image_min_height:
                    # 最小サイズに合わせて拡大（アスペクト比を維持）
                    scale_w = app_state.image_min_width / orig_w
                    scale_h = app_state.image_min_height / orig_h
                    scale = max(scale_w, scale_h)
                    new_w, new_h = int(orig_w * scale), int(orig_h * scale)
                elif new_w < app_state.image_min_width:
                    # 幅が最小サイズ未満の場合
                    scale = app_state.image_min_width / orig_w
                    new_w = app_state.image_min_width
                    new_h = int(orig_h * scale)
                elif new_h < app_state.image_min_height:
                    # 高さが最小サイズ未満の場合
                    scale = app_state.image_min_height / orig_h
                    new_w = int(orig_w * scale)
                    new_h = app_state.image_min_height
                
                # 最大サイズを再チェック（最小サイズ適用後の確認）
                if app_state.image_max_width > 0 and new_w > app_state.image_max_width:
                    scale = app_state.image_max_width / new_w
                    new_w = app_state.image_max_width
                    new_h = int(new_h * scale)
                if app_state.image_max_height > 0 and new_h > app_state.image_max_height:
                    scale = app_state.image_max_height / new_h
                    new_w = int(new_w * scale)
                    new_h = app_state.image_max_height

                # ランダムサイズが有効な場合、スケールをランダムに変更
                if self.random_size.get():
                    # 最小スケールと最大スケールを計算
                    min_scale_w = app_state.image_min_width / new_w if app_state.image_min_width > 0 and new_w > 0 else 0.5
                    min_scale_h = app_state.image_min_height / new_h if app_state.image_min_height > 0 and new_h > 0 else 0.5
                    min_scale = max(min_scale_w, min_scale_h)
                    
                    # 最大サイズが設定されている場合
                    if app_state.image_max_width > 0 or app_state.image_max_height > 0:
                        max_scale_w = app_state.image_max_width / new_w if app_state.image_max_width > 0 and new_w > 0 else 2.0
                        max_scale_h = app_state.image_max_height / new_h if app_state.image_max_height > 0 and new_h > 0 else 2.0
                        max_scale = min(max_scale_w, max_scale_h)
                    else:
                        # 最大サイズが0の場合は画面サイズの80%を上限とする
                        max_scale_w = (screen_w * 0.8) / new_w if new_w > 0 else 2.0
                        max_scale_h = (screen_h * 0.8) / new_h if new_h > 0 else 2.0
                        max_scale = min(max_scale_w, max_scale_h)
                    
                    # ランダムスケールを生成（最小と最大の間、ただし最小は0.5以上）
                    min_scale = max(min_scale, 0.5)
                    max_scale = max(max_scale, min_scale + 0.1)  # 最低限の範囲を確保
                    random_scale = random.uniform(min_scale, max_scale)
                    new_w = int(new_w * random_scale)
                    new_h = int(new_h * random_scale)
                    
                    # 最小サイズを再チェック
                    if app_state.image_min_width > 0 and new_w < app_state.image_min_width:
                        scale = app_state.image_min_width / new_w if new_w > 0 else 1.0
                        new_w = app_state.image_min_width
                        new_h = int(new_h * scale)
                    if app_state.image_min_height > 0 and new_h < app_state.image_min_height:
                        scale = app_state.image_min_height / new_h if new_h > 0 else 1.0
                        new_w = int(new_w * scale)
                        new_h = app_state.image_min_height
                    
                    # 最大サイズを再チェック
                    if app_state.image_max_width > 0 and new_w > app_state.image_max_width:
                        scale = app_state.image_max_width / new_w if new_w > 0 else 1.0
                        new_w = app_state.image_max_width
                        new_h = int(new_h * scale)
                    if app_state.image_max_height > 0 and new_h > app_state.image_max_height:
                        scale = app_state.image_max_height / new_h if new_h > 0 else 1.0
                        new_w = int(new_w * scale)
                        new_h = app_state.image_max_height

                img_resized = img.resize((new_w, new_h), Image.LANCZOS)
                del img_resized # 不要になったので即座に掃除するのじゃ

            # 表示位置の計算
            if self.random_pos.get():
                base_x = random.randint(0, max(0, screen_w - new_w))
                base_y = random.randint(0, max(0, screen_h - new_h))
            else:
                try:
                    # 参照されているUI窓がある場合はその右横に
                    if self.file_win:
                        base_x = self.file_win.winfo_x() + self.file_win.winfo_width() + 20
                        base_y = self.file_win.winfo_y()
                        if base_x + new_w > screen_w and self.folder_win:
                            base_x = max(10, self.folder_win.winfo_x() - new_w - 20)
                    else:
                        base_x, base_y = 400, 100
                except:
                    base_x, base_y = 400, 100

            win = tk.Toplevel(self.parent)
            win._tk_image_refs = getattr(win, '_tk_image_refs', [])
            img_resized = img.resize((new_w, new_h), Image.LANCZOS)
            tkimg = ImageTk.PhotoImage(master=win, image=img_resized)
            win._tk_image_refs.append(tkimg)
            del img_resized

            # ファイル名を表示（相対パスの場合はベースネームを使用）
            if isinstance(fileName, str):
                display_name = os.path.basename(fileName) if os.path.sep in fileName or (os.path.altsep and os.path.altsep in fileName) else fileName
            else:
                display_name = "(無効なファイル名)"
            win.title(f"{display_name} ({int(scale*100)}%)")
            win.attributes("-topmost", True)
            self.open_windows[fullName] = win
            
            def on_img_close():
                if fullName in self.open_windows:
                    del self.open_windows[fullName]
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", on_img_close)

            # 表示するUI要素によって高さを動的に調整
            text_area_h = 0

            # ベクトル表示が有効な場合
            if app_state.vector_display.get("enabled", True):
                text_area_h += 40  # ベクトル表示領域の高さ

            # 評価は独立ウィンドウでのみ管理するため、画像ウィンドウの高さには加算しない

            win.geometry(f"{new_w}x{new_h + text_area_h}+{base_x}+{base_y}")
            
            # メイン領域: 画像キャンバス
            frame = tk.Frame(win)
            frame.pack(expand=True, fill=tk.BOTH)
            canvas = tk.Canvas(frame, width=new_w, height=new_h)
            canvas.pack(side=tk.TOP)
            canvas.image = tkimg
            canvas.create_image(0, 0, image=tkimg, anchor=tk.NW)

                # 解釈テキストを表示するラベル（スクロール不要の短い要約を想定）
            interp_label = tk.Label(frame, text="", justify=tk.LEFT, anchor="w", bg="#ffffff", fg="#000000", wraplength=new_w - 8)
            interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))

            # ベクトルがあれば解釈を取得して表示（設定による）
            if app_state.vector_display.get("enabled", True):
                try:
                    vec = self.vectors_cache.get(win._image_hash)
                    if vec:
                        interpreter = get_interpreter({"vector_display": getattr(app_state, 'vector_display', {})})
                        interp = interpreter.interpret_vector(vec)
                        interp_text = interpreter.format_interpretation_text(interp)
                        interp_label.config(text=interp_text)
                        interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))  # ベクトル表示時はpack
                    else:
                        interp_label.config(text="(ベクトル未登録) ベクトルデータを先に作成してください")
                        interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))  # ベクトル表示時はpack
                except Exception as e:
                    interp_label.config(text=f"解釈取得エラー: {e}")
                    interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))  # ベクトル表示時はpack
            # ベクトル表示が無効の場合、ラベルをpackしない（スペースを取らない）

            # 評価は独立した評価ウィンドウでのみ管理するため、画像ウィンドウ内には表示しない

            # 評価変更時のコールバック登録
            def on_rating_changed(event_name, data):
                if event_name == "image_rating_changed" and data["image_hash"] == win._image_hash:
                    self._update_rating_display(star_labels, data["new_rating"])

            app_state.register_callback(on_rating_changed)

            cleanup_callback_id = None

            # ウィンドウ破棄時にコールバック解除
            def cleanup_callback():
                try:
                    app_state.unregister_callback(on_rating_changed)
                except Exception:
                    pass

            def on_destroy(event=None):
                nonlocal cleanup_callback_id
                if cleanup_callback_id is not None:
                    try:
                        win.after_cancel(cleanup_callback_id)
                    except Exception:
                        pass
                cleanup_callback()

            # ウィンドウ破棄時にコールバック解除（少し遅延させて確実に実行）
            cleanup_callback_id = win.after(100, cleanup_callback)
            win.bind("<Destroy>", on_destroy)

            # ウィンドウドラッグ移動機能の実装なのじゃ（安定版）
            def start_drag(event, target_win):
                target_win._drag_start_x = event.x_root - target_win.winfo_x()
                target_win._drag_start_y = event.y_root - target_win.winfo_y()

            def do_drag(event, target_win):
                nx = event.x_root - target_win._drag_start_x
                ny = event.y_root - target_win._drag_start_y
                target_win.geometry(f"+{nx}+{ny}")

            # --- タグ機能の実装（ハッシュベース） ---
            win._image_path = fileName
            win._image_hash = calculate_file_hash(fullName)
            self.set_image_tag(win, win._image_hash)

            # 評価ウィンドウを更新（画像表示時）
            if app_state.show_rating_window:
                self.update_rating_window(win._image_hash)

            # 情報ウィンドウを更新（画像表示時）
            if app_state.show_info_window:
                zoom_percent = int(scale * 100)
                self.update_info_window(fileName, win._image_hash, new_w, new_h, zoom_percent)

            def open_tag_menu(event):
                menu = tk.Menu(win, tearoff=0)
                menu.add_command(label="タグを編集", command=lambda: self.edit_tag_dialog(win, fileName, win._image_hash, update_target_win=win))
                menu.post(event.x_root, event.y_root)

            canvas.bind("<Button-1>", lambda e: start_drag(e, win))
            canvas.bind("<B1-Motion>", lambda e: do_drag(e, win))
            canvas.bind("<Button-3>", open_tag_menu) # 右クリックでメニュー表示

        except Exception as e:
            import traceback
            logger.error(f"画像表示エラー: {e}")
            traceback.print_exc()
            logger.exception("画像表示中に例外が発生しました: %s", fullName)

    def edit_tag_dialog(self, parent_win, filename, image_hash, update_target_win=None):
        """タグ編集ダイアログを表示するのじゃ。のじゃ。"""
        try:
            if not image_hash:
                logger.error("ハッシュ計算に失敗しているためタグ付けできないのじゃ。")
                return

            data = self.tag_dict.get(image_hash)
            current_tag = data["tag"] if data else ""
            current_rating = data["rating"] if data and data.get("rating") else None

            new_tag = simpledialog.askstring("タグ編集", f"{filename} のタグを入力してください（;区切り）:", initialvalue=current_tag, parent=parent_win)

            if new_tag is not None:
                # ハッシュをキーにして保存するのじゃ（評価も保持）
                if image_hash not in self.tag_dict:
                    self.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None}
                self.tag_dict[image_hash]["tag"] = new_tag
                self.tag_dict[image_hash]["hint"] = filename
                # 既存の評価を保持
                if current_rating is not None:
                    self.tag_dict[image_hash]["rating"] = current_rating
                save_tags(self.tag_dict)
                if update_target_win:
                    self.set_image_tag(update_target_win, image_hash)
        except Exception as e:
            logger.error(f"タグ編集エラー: {e}")

    def disable_all_topmost(self):
        """管理下の全ての画像ウィンドウの最前面表示を解除するのじゃ。のじゃ。"""
        for win in self.open_windows.values():
            try:
                win.attributes("-topmost", False)
            except: pass

    def get_windows_workarea(self):
        """Windows のタスクバーを除いた有効な画面領域（ワークエリア）を取得するのじゃ。のじゃ。"""
        try:
            user32 = ctypes.windll.user32
            rect = wintypes.RECT()
            # SPI_GETWORKAREA (0x0030 = 48) を呼び出してワークエリアを取得するのじゃ
            if user32.SystemParametersInfoW(48, 0, ctypes.byref(rect), 0):
                return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception as e:
            logger.error(f"ワークエリア取得失敗: {e}")
        
        # 失敗した場合は全画面サイズを返す（少しマージンを引くのじゃ）
        sw = self.parent.winfo_screenwidth()
        sh = self.parent.winfo_screenheight()
        return 0, 0, sw, sh - 40

    def TileWindows(self):
        """全ての画像ウィンドウをパズルのように隙間なく画面に敷き詰めるのじゃ。のじゃ。"""
        win_list = list(self.open_windows.items()) # (fullName, win) のリスト
        n = len(win_list)
        if n == 0: return

        # 画面サイズの取得（ワークエリアを考慮するのじゃ）
        avail_x, avail_y, avail_w, avail_h = self.get_windows_workarea()

        # 再帰的に領域を分割する内部関数なのじゃ
        def partition(x, y, w, h, count):
            if count <= 1:
                return [(x, y, w, h)]
            
            # 分割方向の決定（長い方を割るのじゃ）
            if w > h:
                # 縦に割る（横に並べる）
                n1 = count // 2
                n2 = count - n1
                w1 = int(w * (n1 / count))
                return partition(x, y, w1, h, n1) + partition(x + w1, y, w - w1, h, n2)
            else:
                # 横に割る（縦に並べる）
                n1 = count // 2
                n2 = count - n1
                h1 = int(h * (n1 / count))
                return partition(x, y, w, h1, n1) + partition(x, y + h1, w, h - h1, n2)

        # パズルのピース（各窓の領域）を計算
        rects = partition(avail_x, avail_y, avail_w, avail_h, n)

        # 四隅を優先したいという前回の魂を継承し、端の領域から順に画像を割り当てるのじゃ
        # (rectsの順序は分割アルゴリズム上、それなりに端から並ぶはずなのじゃ)
        
        for idx, (fullName, win) in enumerate(win_list):
            if idx >= len(rects): break
            try:
                rx, ry, rw, rh = rects[idx]
                
                # 画像を読み込んで「びっちり」させるのじゃ
                with Image.open(fullName) as img:
                    # ImageOps.fit を使ってアスペクト比を維持しつつ領域を完全に埋める（クロップあり）
                    img_fitted = ImageOps.fit(img, (rw, rh), Image.LANCZOS)
                    tkimg = ImageTk.PhotoImage(master=win, image=img_fitted)
                    del img_fitted
                
                # ウィンドウの更新（枠なし！）
                win.overrideredirect(True)
                win.geometry(f"{rw}x{rh}+{rx}+{ry}")

                win._tk_image_refs = getattr(win, '_tk_image_refs', [])
                win._tk_image_refs.append(tkimg)

                # キャンバスの更新
                canvas = win.winfo_children()[0]
                canvas.config(width=rw, height=rh)
                canvas.delete("all")
                canvas.image = tkimg
                canvas.create_image(0, 0, image=tkimg, anchor=tk.NW)
                
                # ドラッグ情報の更新（枠なし移動を維持）
                def start_drag_puz(event, target_win):
                    target_win._drag_start_x = event.x_root - target_win.winfo_x()
                    target_win._drag_start_y = event.y_root - target_win.winfo_y()
                def do_drag_puz(event, target_win):
                    nx = event.x_root - target_win._drag_start_x
                    ny = event.y_root - target_win._drag_start_y
                    target_win.geometry(f"+{nx}+{ny}")
                
                canvas.bind("<Button-1>", lambda e, w=win: start_drag_puz(e, w))
                canvas.bind("<B1-Motion>", lambda e, w=win: do_drag_puz(e, w))

                logger.info(f"[PUZZLE] {os.path.basename(fullName)} を {rw}x{rh}@{rx},{ry} に敷き詰めたのじゃ。")
            except Exception as e:
                logger.error(f"パズル整列エラー({fullName}): {e}")
