'''
作成者: tamate masayuki (Refactored by Antigravity)
機能: GazoTools のデータ管理、設定管理、およびロジック制御
※ 純粋なビジネスロジック（計算・判断）を集約しているのじゃ。
'''
import os
import json
import random
import csv
import hashlib
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import ImageTk, Image, ImageOps
import math
import ctypes
from ctypes import wintypes
from lib.GazoToolsLib import GetKoFolder, GetGazoFiles
from lib.GazoToolsData import (
    load_config, save_config, calculate_file_hash,
    load_tags, save_tags, load_ratings, save_ratings,
    load_vectors, save_vectors, HakoData
)
from lib.GazoToolsAI import VectorEngine, VectorBatchProcessor
from lib.GazoToolsState import get_app_state
from lib.GazoToolsVectorInterpreter import get_interpreter

# ロギング設定 (循環参照回避のためここで行わない場合もあるが、Loggerは一般的に安全)
from lib.GazoToolsLogger import LoggerManager, record_error
logger = LoggerManager.get_logger(__name__)

app_state = get_app_state()


def get_label_text(widget, default=""):
    """Tkのラベル文字列取得を安全に扱う。cget('text') が None の場合も空文字に正規化する。"""
    try:
        value = widget.cget("text")
    except Exception:
        return default
    return value if isinstance(value, str) else default

from lib.config_defaults import (
    calculate_folder_window_width, calculate_folder_window_height,
    calculate_file_window_width, calculate_file_window_height,
    WINDOW_SPACING
)

# ----------------------------------------------------------------------
# 画面レイアウト計算ロジック
# ----------------------------------------------------------------------
def calculate_window_layout(root_x, root_y, root_w, screen_w, folders, files, current_folder_name):
    """メインウィンドウの位置とサイズを基準に、サブウィンドウの最適な配置を計算するのじゃ。
    
    Args:
        root_x, root_y: メインウィンドウの座標
        root_w: メインウィンドウの幅
        screen_w: 画面幅
        folders: フォルダリスト
        files: ファイルリスト
        current_folder_name: カレントフォルダ名
        
    Returns:
        tuple: (folder_win_geometry, file_win_geometry)
        geometry文字列 ("WxH+X+Y") を返すのじゃ。
    """
    f_count = len(folders) + 1
    current_base = os.path.basename(current_folder_name) or current_folder_name
    
    # フォルダウィンドウ計算
    f_names = [f"({len(files)}) [現在] {current_base}"] + [f"({len(folders)}) {f}" for f in folders]
    max_f = max([len(f) for f in f_names]) if f_names else 5
    w_f = calculate_folder_window_width(max_f)
    h_f = calculate_folder_window_height(f_count)
    x_f, y_f = root_x + root_w + WINDOW_SPACING, root_y
    f_geo = f"{w_f}x{h_f}+{x_f}+{y_f}"
    
    # ファイルウィンドウ計算
    g_count = len(files)
    max_g = max([len(f) for f in files]) if files else 5
    w_g = calculate_file_window_width(max_g)
    h_g = calculate_file_window_height(g_count)
    x_g, y_g = x_f + w_f + WINDOW_SPACING, root_y
    
    # 画面ハミ出しチェック
    if x_g + w_g > screen_w:
        x_g = max(10, root_x - w_g - WINDOW_SPACING)
        
    g_geo = f"{w_g}x{h_g}+{x_g}+{y_g}"
    
    return f_geo, g_geo







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
        self.vectors_cache = load_vectors()  # ベクトルデータをロード

        # 既存のタグデータから評価マッピングを復元
        for image_hash, data in self.tag_dict.items():
            if "assigned_rating" in data and data["assigned_rating"]:
                self.image_rating_map[image_hash] = data["assigned_rating"]

        self._move_callback = None
        self._refresh_callback = None

    def set_move_callback(self, callback):
        """移動処理を実行するコールバックを設定するのじゃ。"""
    def set_move_callback(self, callback):
        """移動処理を実行するコールバックを設定するのじゃ。"""
        self._move_callback = callback

    def set_refresh_callback(self, callback):
        """UI更新を実行するコールバックを設定するのじゃ。"""
        self._refresh_callback = callback

    def create_rating_window(self):
        """独立した子ウィンドウとして評価ウィンドウを作成（評価選択機能付き）"""
        if GazoPicture._rating_window is not None:
            try:
                if GazoPicture._rating_window.winfo_exists():
                    return GazoPicture._rating_window
            except:
                pass

        try:
            # メインウィンドウの子として評価ウィンドウを作成
            rating_win = tk.Toplevel(self.parent)
            rating_win.title("評価")
            rating_win.attributes("-topmost", True)
            rating_win.overrideredirect(True)  # タイトルバーなし
            rating_win.attributes("-alpha", 0.9)  # 半透明

            # 設定に基づいてサイズ・位置を決定
            screen_w = rating_win.winfo_screenwidth()
            screen_h = rating_win.winfo_screenheight()

            # ウィンドウサイズ
            win_width = app_state.rating_ui.get("window_width", 320)
            win_height = app_state.rating_ui.get("window_height", 140)

            # 位置（%ベース）
            pos_x_percent = app_state.rating_ui.get("position_x", 50)
            pos_y_percent = app_state.rating_ui.get("position_y", 85)

            margin = app_state.rating_ui.get("margin", 15)
            x = int((screen_w - win_width) * pos_x_percent / 100)
            y = int((screen_h - win_height) * pos_y_percent / 100)

            # マージンを考慮して画面内に収まるように調整
            x = max(margin, min(x, screen_w - win_width - margin))
            y = max(margin, min(y, screen_h - win_height - margin))

            rating_win.geometry(f"{win_width}x{win_height}+{x}+{y}")

            # パディング設定に基づいて背景フレームを作成
            padding_x = app_state.rating_ui.get("padding_x", 10)
            padding_y = app_state.rating_ui.get("padding_y", 8)

            frame = tk.Frame(rating_win, bg="#2c3e50", bd=2, relief="raised")
            frame.pack(fill=tk.BOTH, expand=True, padx=padding_x, pady=padding_y)

            # 評価選択ドロップダウン
            rating_frame = tk.Frame(frame, bg="#34495e")
            rating_frame.pack(fill=tk.X, pady=(5, 2))

            tk.Label(rating_frame, text="評価:", font=("Arial", 9),
                    fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT, padx=(5, 2))

            # 評価リストを作成（デフォルト評価 + 名前付き評価）
            rating_options = ["未選択"] + [name for name in self.rating_dict.keys()]
            self._rating_var = tk.StringVar(value="未選択")

            rating_menu = tk.OptionMenu(rating_frame, self._rating_var,
                                       *rating_options, command=self._on_rating_selected)
            rating_menu.config(bg="#34495e", fg="#ecf0f1", font=("Arial", 9),
                             highlightthickness=0, bd=0)
            rating_menu.pack(side=tk.LEFT, padx=(0, 5))

            # 新規評価作成ボタン
            create_btn = tk.Button(rating_frame, text="+", font=("Arial", 8, "bold"),
                                 bg="#27ae60", fg="white", bd=0, padx=3,
                                 command=self._create_new_rating)
            create_btn.pack(side=tk.RIGHT, padx=(2, 5))

            # 評価設定エリア
            settings_frame = tk.Frame(frame, bg="#34495e")
            settings_frame.pack(fill=tk.X, pady=(2, 5))

            # 連動設定
            tk.Label(settings_frame, text="星と連動:", font=("Arial", 9),
                    fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT, padx=(5, 2))

            self._linked_var = tk.BooleanVar(value=True)
            linked_check = tk.Checkbutton(settings_frame, variable=self._linked_var,
                                        bg="#34495e", activebackground="#34495e",
                                        command=self._on_linked_changed)
            linked_check.pack(side=tk.LEFT, padx=(0, 10))

            # カスタム星数設定
            tk.Label(settings_frame, text="固定星数:", font=("Arial", 9),
                    fg="#ecf0f1", bg="#34495e").pack(side=tk.LEFT, padx=(5, 2))

            self._custom_rating_var = tk.IntVar(value=3)
            custom_spin = tk.Spinbox(settings_frame, from_=0, to=6,
                                   textvariable=self._custom_rating_var,
                                   width=3, font=("Arial", 9),
                                   command=self._on_custom_rating_changed)
            custom_spin.pack(side=tk.LEFT, padx=(0, 5))

            # 現在の評価表示エリア
            display_frame = tk.Frame(frame, bg="#2c3e50")
            display_frame.pack(fill=tk.X, pady=(2, 5))

            # UI要素のコンテナを作成（レイアウト順序変更用）
            self._ui_containers = {}

            # 評価名ラベル
            text_container = tk.Frame(display_frame, bg="#2c3e50")
            self._ui_containers["text"] = text_container

            self._current_rating_name_label = tk.Label(text_container, text="未選択",
                                                     font=("Arial", 10, "bold"),
                                                     fg="#f39c12", bg="#2c3e50")
            self._current_rating_name_label.pack(anchor="center", pady=(0, 3))

            # 星のラベルを作成（6個：5個の通常評価＋1個の特別評価）
            stars_container = tk.Frame(display_frame, bg="#2c3e50")
            self._ui_containers["stars"] = stars_container

            star_labels = []
            star_frame = tk.Frame(stars_container, bg="#2c3e50")
            star_frame.pack(anchor="center")

            for i in range(6):
                star_text = "★" if i < 5 else "☆"  # 6つ目は特別な星マーク
                star_label = tk.Label(star_frame, text=star_text,
                                    font=("Arial", 16, "bold"),
                                    fg="#cccccc", bg="#2c3e50", cursor="hand2")
                star_label.pack(side=tk.LEFT, padx=1)
                star_label.bind("<Button-1>", lambda e, rating=i+1: self._on_rating_value_click(rating))
                star_labels.append(star_label)

            # 設定エリア
            settings_container = tk.Frame(display_frame, bg="#2c3e50")
            self._ui_containers["settings"] = settings_container

            # 星ラベルを保存
            rating_win._star_labels = star_labels
            GazoPicture._rating_window = rating_win

            # UIレイアウトを適用
            self._apply_ui_layout(rating_win)

            # 初期状態を表示
            self._update_rating_display(star_labels, 0)

            return rating_win

        except Exception as e:
            logger.error(f"評価ウィンドウ作成エラー: {e}")
            return None

    def update_rating_window(self, image_hash=None):
        """評価ウィンドウを更新"""
        try:
            # 評価ウィンドウが存在することを確認
            rating_win = self.create_rating_window()
            if not rating_win:
                return

            # 画像ハッシュを保存
            GazoPicture._current_image_hash = image_hash

            if image_hash:
                # 現在の評価を取得して表示
                tag_data = self.tag_dict.get(image_hash)
                current_rating = tag_data["rating"] if tag_data and tag_data.get("rating") else 0
                self._update_rating_display(rating_win._star_labels, current_rating)

                # ウィンドウを表示
                rating_win.deiconify()
            else:
                # 画像がない場合は非表示
                rating_win.withdraw()

        except Exception as e:
            logger.error(f"評価ウィンドウ更新エラー: {e}")

    def _on_rating_selected(self, rating_name):
        """評価選択時の処理"""
        try:
            if rating_name == "未選択":
                # 現在の画像から評価を解除
                image_hash = GazoPicture._current_image_hash
                if image_hash and image_hash in self.image_rating_map:
                    del self.image_rating_map[image_hash]
                    self._update_current_rating_display(0)
                    self._update_info_window_for_current_image()

                    # タグデータからも評価を解除して保存
                    if image_hash in self.tag_dict:
                        self.tag_dict[image_hash]["assigned_rating"] = None
                        save_tags(self.tag_dict)

                    logger.debug(f"画像から評価を解除: {image_hash[:8]}...")
            else:
                # 選択された評価を現在の画像に適用
                image_hash = GazoPicture._current_image_hash
                if image_hash:
                    self.image_rating_map[image_hash] = rating_name
                    rating_data = self.rating_dict.get(rating_name, {})
                    # 連動設定とカスタム星数をUIに反映
                    self._linked_var.set(rating_data.get("linked", True))
                    self._custom_rating_var.set(rating_data.get("custom_rating", 3))
                    # 表示する星数を決定
                    if rating_data.get("linked", True):
                        rating_value = rating_data.get("rating", 0)
                    else:
                        rating_value = rating_data.get("custom_rating", 0)
                    self._update_current_rating_display(rating_value)
                    self._update_info_window_for_current_image()

                    # タグデータも更新して保存
                    if image_hash in self.tag_dict:
                        self.tag_dict[image_hash]["assigned_rating"] = rating_name
                    else:
                        self.tag_dict[image_hash] = {
                            "tag": "",
                            "hint": "",
                            "rating": None,
                            "assigned_rating": rating_name
                        }
                    save_tags(self.tag_dict)

                    logger.debug(f"画像に評価適用: {image_hash[:8]}... -> {rating_name}")
        except Exception as e:
            logger.error(f"評価選択エラー: {e}")

    def _on_linked_changed(self):
        """連動設定変更時の処理"""
        try:
            selected_rating = self._rating_var.get()
            if selected_rating and selected_rating != "未選択":
                # 連動設定を保存
                if selected_rating not in self.rating_dict:
                    self.rating_dict[selected_rating] = {
                        "name": selected_rating,
                        "rating": 3,
                        "linked": True,
                        "custom_rating": 3
                    }

                self.rating_dict[selected_rating]["linked"] = self._linked_var.get()
                save_ratings(self.rating_dict)

                # 評価変更を即座に保存
                save_tags(self.tag_dict)

                # 表示を更新
                self._update_current_rating_display_from_selected()

                logger.debug(f"連動設定変更: {selected_rating} = {self._linked_var.get()}")
        except Exception as e:
            logger.error(f"連動設定変更エラー: {e}")

    def _on_custom_rating_changed(self):
        """カスタム星数変更時の処理"""
        try:
            selected_rating = self._rating_var.get()
            if selected_rating and selected_rating != "未選択":
                # カスタム星数を保存
                if selected_rating not in self.rating_dict:
                    self.rating_dict[selected_rating] = {
                        "name": selected_rating,
                        "rating": 3,
                        "linked": True,
                        "custom_rating": 3
                    }

                self.rating_dict[selected_rating]["custom_rating"] = self._custom_rating_var.get()
                save_ratings(self.rating_dict)

                # 評価変更を即座に保存
                save_tags(self.tag_dict)

                # 連動OFFの場合のみ表示を更新
                if not self._linked_var.get():
                    self._update_current_rating_display(self._custom_rating_var.get())

                logger.debug(f"カスタム星数変更: {selected_rating} = {self._custom_rating_var.get()}")
        except Exception as e:
            logger.error(f"カスタム星数変更エラー: {e}")

    def _on_rating_value_click(self, rating):
        """星クリック時の処理（評価選択状態に応じて動作）"""
        try:
            selected_rating = self._rating_var.get()
            image_hash = GazoPicture._current_image_hash

            if selected_rating and selected_rating != "未選択":
                # 評価が選択されている場合：既存の評価の値を変更
                if selected_rating not in self.rating_dict:
                    self.rating_dict[selected_rating] = {
                        "name": selected_rating,
                        "rating": 3,
                        "linked": True,
                        "custom_rating": 3
                    }

                # 連動設定に応じて保存する値を決定
                if self._linked_var.get():
                    self.rating_dict[selected_rating]["rating"] = rating
                else:
                    self.rating_dict[selected_rating]["custom_rating"] = rating
                    self._custom_rating_var.set(rating)  # UIも更新

                save_ratings(self.rating_dict)

                # 評価変更を即座に保存
                save_tags(self.tag_dict)

                # 現在の画像がこの評価を使っている場合は画像にも適用
                if image_hash and self.image_rating_map.get(image_hash) == selected_rating:
                    # 表示を更新
                    display_rating = rating if self._linked_var.get() else self.rating_dict[selected_rating]["custom_rating"]
                    self._update_current_rating_display(display_rating)
                    self._update_info_window_for_current_image()

                logger.debug(f"評価値変更: {selected_rating} = {rating}")

            elif image_hash:
                # 評価が選択されていない場合：星クリックで直接評価を保存
                # 評価名を自動生成（例: "星5"）
                rating_name = f"星{rating}"

                # 評価データが存在しない場合は作成
                if rating_name not in self.rating_dict:
                    self.rating_dict[rating_name] = {
                        "name": rating_name,
                        "rating": rating,
                        "linked": True,
                        "custom_rating": rating
                    }
                    save_ratings(self.rating_dict)

                    # ドロップダウンに新しい評価を追加
                    self._update_rating_dropdown()

                # 現在の画像にこの評価を割り当て
                self.image_rating_map[image_hash] = rating_name

                # UIを更新
                self._rating_var.set(rating_name)
                self._linked_var.set(True)
                self._custom_rating_var.set(rating)
                self._update_current_rating_display(rating)
                self._update_info_window_for_current_image()

                # タグデータも更新して保存
                if image_hash in self.tag_dict:
                    self.tag_dict[image_hash]["assigned_rating"] = rating_name
                else:
                    self.tag_dict[image_hash] = {
                        "tag": "",
                        "hint": "",
                        "rating": None,
                        "assigned_rating": rating_name
                    }
                save_tags(self.tag_dict)

                logger.debug(f"星クリック直接保存: {image_hash[:8]}... -> {rating_name} ({rating}星)")
            else:
                logger.warning("評価する画像がありません")
        except Exception as e:
            logger.error(f"星クリック評価エラー: {e}")

    def _update_current_rating_display_from_selected(self):
        """選択されている評価に基づいて表示を更新"""
        try:
            selected_rating = self._rating_var.get()
            if selected_rating and selected_rating != "未選択":
                rating_data = self.rating_dict.get(selected_rating, {})
                if rating_data.get("linked", True):
                    rating_value = rating_data.get("rating", 0)
                else:
                    rating_value = rating_data.get("custom_rating", 0)
                self._update_current_rating_display(rating_value)
        except Exception as e:
            logger.error(f"評価表示更新エラー: {e}")

    def _create_new_rating(self):
        """新規評価作成ダイアログ"""
        try:
            # 新しい評価の名前を入力
            rating_name = simpledialog.askstring("新規評価作成", "評価の名前を入力してください:",
                                               parent=GazoPicture._rating_window)
            if rating_name and rating_name.strip():
                rating_name = rating_name.strip()
                if rating_name not in self.rating_dict:
                    # 新しい評価を作成（デフォルト設定）
                    self.rating_dict[rating_name] = {
                        "name": rating_name,
                        "rating": 3,  # デフォルトで3つ星
                        "linked": True,  # デフォルトで連動ON
                        "custom_rating": 3  # デフォルトで3つ星
                    }
                    save_ratings(self.rating_dict)

                    # ドロップダウンを更新
                    self._update_rating_dropdown()

                    # 新しい評価を選択
                    self._rating_var.set(rating_name)
                    self._on_rating_selected(rating_name)

                    logger.debug(f"新規評価作成: {rating_name}")
                else:
                    messagebox.showwarning("警告", f"評価名「{rating_name}」は既に存在します。")
        except Exception as e:
            logger.error(f"新規評価作成エラー: {e}")

    def _update_rating_dropdown(self):
        """評価ドロップダウンを更新"""
        try:
            if GazoPicture._rating_window:
                # 現在の選択を保存
                current_selection = self._rating_var.get()

                # メニューを再構築
                rating_frame = None
                for child in GazoPicture._rating_window.winfo_children():
                    if isinstance(child, tk.Frame) and str(child.cget('bg')) == '#34495e':
                        rating_frame = child
                        break

                if rating_frame:
                    # OptionMenuを探して更新
                    for child in rating_frame.winfo_children():
                        if isinstance(child, tk.OptionMenu):
                            child.destroy()
                            break

                    # 新しい評価リスト
                    rating_options = ["未選択"] + list(self.rating_dict.keys())

                    # 新しいOptionMenuを作成
                    rating_menu = tk.OptionMenu(rating_frame, self._rating_var,
                                               *rating_options, command=self._on_rating_selected)
                    rating_menu.config(bg="#34495e", fg="#ecf0f1", font=("Arial", 9),
                                     highlightthickness=0, bd=0)
                    rating_menu.pack(side=tk.LEFT, padx=(0, 5))

                    # 選択を復元（可能であれば）
                    if current_selection in rating_options:
                        self._rating_var.set(current_selection)
        except Exception as e:
            logger.error(f"評価ドロップダウン更新エラー: {e}")

    def _update_current_rating_display(self, rating_value):
        """現在の評価表示を更新"""
        try:
            if GazoPicture._rating_window and hasattr(GazoPicture._rating_window, '_star_labels'):
                self._update_rating_display(GazoPicture._rating_window._star_labels, rating_value)

                # 評価名も更新
                selected_rating = self._rating_var.get()
                if selected_rating and selected_rating != "未選択":
                    self._current_rating_name_label.config(text=selected_rating)
                else:
                    self._current_rating_name_label.config(text="未選択")
        except Exception as e:
            logger.error(f"評価表示更新エラー: {e}")

    def _update_info_window_for_current_image(self):
        """現在の画像の情報ウィンドウを更新"""
        try:
            image_hash = GazoPicture._current_image_hash
            if image_hash:
                # 評価情報を更新
                selected_rating = self.image_rating_map.get(image_hash)
                if selected_rating and selected_rating in self.rating_dict:
                    rating_value = self.rating_dict[selected_rating].get("rating", 0)
                else:
                    rating_value = 0

                # 情報ウィンドウの評価情報を更新
                if hasattr(self, 'update_info_window_rating'):
                    self.update_info_window_rating(image_hash, rating_value)
        except Exception as e:
            logger.error(f"情報ウィンドウ更新エラー: {e}")

    def _apply_ui_layout(self, rating_win):
        """評価ウィンドウのUIレイアウトを適用"""
        try:
            layout_order = app_state.rating_ui.get("layout_order", ["text", "stars", "settings"])

            # 一度全てのコンテナをpack_forget
            for container in self._ui_containers.values():
                container.pack_forget()

            # 順序通りにpack
            for element in layout_order:
                if element in self._ui_containers:
                    if element == "settings":
                        # 設定エリアは中央に配置
                        self._ui_containers[element].pack(fill=tk.X, pady=(2, 5))
                    else:
                        # テキストと星は中央に配置
                        self._ui_containers[element].pack(anchor="center", pady=(0, 3) if element == "text" else (0, 0))

            # フォントサイズを適用
            self._apply_font_sizes(rating_win)

        except Exception as e:
            logger.error(f"UIレイアウト適用エラー: {e}")

    def _apply_font_sizes(self, rating_win):
        """フォントサイズを適用"""
        try:
            text_size = app_state.rating_ui.get("text_font_size", 10)
            star_size = app_state.rating_ui.get("star_font_size", 16)

            # 評価名ラベルのフォントサイズを変更
            current_font = self._current_rating_name_label.cget("font")
            if isinstance(current_font, str):
                self._current_rating_name_label.config(font=("Arial", text_size, "bold"))
            else:
                self._current_rating_name_label.config(font=("Arial", text_size, "bold"))

            # 星ラベルのフォントサイズを変更
            if hasattr(rating_win, '_star_labels'):
                for star_label in rating_win._star_labels:
                    current_font = star_label.cget("font")
                    if isinstance(current_font, str):
                        star_label.config(font=("Arial", star_size, "bold"))
                    else:
                        star_label.config(font=("Arial", star_size, "bold"))

        except Exception as e:
            logger.error(f"フォントサイズ適用エラー: {e}")

    def update_rating_ui_settings(self):
        """評価UI設定を更新（設定変更時）"""
        try:
            if GazoPicture._rating_window and GazoPicture._rating_window.winfo_exists():
                # ウィンドウサイズ・位置を更新
                self._update_window_geometry(GazoPicture._rating_window)
                # UIレイアウトを適用
                self._apply_ui_layout(GazoPicture._rating_window)
        except Exception as e:
            logger.error(f"評価UI設定更新エラー: {e}")

    def _update_window_geometry(self, rating_win):
        """ウィンドウのサイズ・位置を更新"""
        try:
            screen_w = rating_win.winfo_screenwidth()
            screen_h = rating_win.winfo_screenheight()

            # 新しいサイズ・位置を計算
            win_width = app_state.rating_ui.get("window_width", 320)
            win_height = app_state.rating_ui.get("window_height", 140)

            pos_x_percent = app_state.rating_ui.get("position_x", 50)
            pos_y_percent = app_state.rating_ui.get("position_y", 85)

            margin = app_state.rating_ui.get("margin", 15)
            x = int((screen_w - win_width) * pos_x_percent / 100)
            y = int((screen_h - win_height) * pos_y_percent / 100)

            # マージンを考慮して画面内に収まるように調整
            x = max(margin, min(x, screen_w - win_width - margin))
            y = max(margin, min(y, screen_h - win_height - margin))

            rating_win.geometry(f"{win_width}x{win_height}+{x}+{y}")

            # パディングも更新
            padding_x = app_state.rating_ui.get("padding_x", 10)
            padding_y = app_state.rating_ui.get("padding_y", 8)

            # 既存のフレームのパディングを更新
            for child in rating_win.winfo_children():
                if isinstance(child, tk.Frame) and str(child.cget('bg')) == '#2c3e50':
                    child.pack_configure(padx=padding_x, pady=padding_y)
                    break

        except Exception as e:
            logger.error(f"ウィンドウジオメトリ更新エラー: {e}")

    def update_rating_window_for_image(self, image_hash):
        """画像ハッシュに基づいて評価ウィンドウを更新"""
        try:
            # 評価ウィンドウが存在することを確認
            rating_win = self.create_rating_window()
            if not rating_win:
                return

            # 画像ハッシュを保存
            GazoPicture._current_image_hash = image_hash

            if image_hash:
                # この画像に割り当てられている評価を取得
                assigned_rating = self.image_rating_map.get(image_hash)
                if assigned_rating and assigned_rating in self.rating_dict:
                    # 割り当てられている評価を選択
                    self._rating_var.set(assigned_rating)
                    rating_data = self.rating_dict[assigned_rating]
                    # UI設定を反映
                    self._linked_var.set(rating_data.get("linked", True))
                    self._custom_rating_var.set(rating_data.get("custom_rating", 3))
                    # 表示する星数を決定
                    if rating_data.get("linked", True):
                        rating_value = rating_data.get("rating", 0)
                    else:
                        rating_value = rating_data.get("custom_rating", 0)
                    self._update_current_rating_display(rating_value)
                else:
                    # 評価が割り当てられていない場合
                    self._rating_var.set("未選択")
                    self._update_current_rating_display(0)

                # ウィンドウを表示
                rating_win.deiconify()
            else:
                # 画像がない場合は非表示
                rating_win.withdraw()

        except Exception as e:
            logger.error(f"評価ウィンドウ更新エラー: {e}")

    def update_info_window_rating(self, image_hash, rating):
        """情報ウィンドウの評価情報を更新"""
        try:
            if GazoPicture._info_window and hasattr(self, '_info_labels'):
                rating_text = f"{rating}/6" + (" ★" * rating)
                self._info_labels["rating"].config(text=rating_text)
        except Exception as e:
            logger.error(f"情報ウィンドウ評価更新エラー: {e}")

    def create_info_window(self):
        """独立した子ウィンドウとして情報ウィンドウを作成"""
        if GazoPicture._info_window is not None:
            try:
                if GazoPicture._info_window.winfo_exists():
                    return GazoPicture._info_window
            except:
                pass

        try:
            # メインウィンドウの子として情報ウィンドウを作成
            info_win = tk.Toplevel(self.parent)
            info_win.title("画像情報")
            info_win.attributes("-topmost", True)
            info_win.overrideredirect(True)  # タイトルバーなし
            info_win.attributes("-alpha", 0.9)  # 半透明

            # ディスプレイ右上に配置
            screen_w = info_win.winfo_screenwidth()
            screen_h = info_win.winfo_screenheight()
            win_width = 300
            win_height = 240
            x = screen_w - win_width - 10  # 右端から10px左
            y = 10  # 上端から10px下
            info_win.geometry(f"{win_width}x{win_height}+{x}+{y}")

            # 背景フレーム
            frame = tk.Frame(info_win, bg="#2c3e50", bd=2, relief="raised")
            frame.pack(fill=tk.BOTH, expand=True)

            # タイトルラベル
            title_label = tk.Label(frame, text="画像情報", font=("Arial", 12, "bold"),
                                 fg="#ffffff", bg="#2c3e50")
            title_label.pack(pady=(10, 5))

            # 情報表示用のフレーム
            info_frame = tk.Frame(frame, bg="#34495e")
            info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

            # 情報ラベル群
            self._info_labels = {}

            info_items = [
                ("filename", "ファイル名:"),
                ("size", "画像サイズ:"),
                ("filesize", "ファイルサイズ:"),
                ("zoom", "ズーム倍率:"),
                ("tags", "タグ:"),
                ("rating", "評価:"),
                ("vector", "ベクトル解釈:")
            ]

            for key, label_text in info_items:
                # ラベルフレーム
                item_frame = tk.Frame(info_frame, bg="#34495e")
                item_frame.pack(fill=tk.X, pady=1)

                # 項目名ラベル
                label = tk.Label(item_frame, text=label_text, font=("Arial", 9),
                               fg="#ecf0f1", bg="#34495e", anchor="w")
                label.pack(side=tk.LEFT, padx=(0, 5))

                # 値ラベル
                value_label = tk.Label(item_frame, text="", font=("Arial", 9),
                                     fg="#f39c12", bg="#34495e", anchor="w")
                value_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self._info_labels[key] = value_label

            GazoPicture._info_window = info_win
            return info_win

        except Exception as e:
            logger.error(f"情報ウィンドウ作成エラー: {e}")
            return None

    def update_info_window(self, image_path=None, image_hash=None, width=None, height=None, zoom_percent=None):
        """情報ウィンドウを更新"""
        try:
            # 情報ウィンドウが存在することを確認
            info_win = self.create_info_window()
            if not info_win or not hasattr(self, '_info_labels'):
                return

            if image_path and image_hash:
                # ファイル名
                filename = os.path.basename(image_path)
                self._info_labels["filename"].config(text=filename)

                # 画像サイズ
                if width and height:
                    size_text = f"{width} × {height}"
                else:
                    size_text = "不明"
                self._info_labels["size"].config(text=size_text)

                # ファイルサイズ
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

                # ズーム倍率
                if zoom_percent:
                    zoom_text = f"{zoom_percent}%"
                else:
                    zoom_text = "100%"
                self._info_labels["zoom"].config(text=zoom_text)

                # タグ情報
                tag_data = self.tag_dict.get(image_hash)
                if tag_data and tag_data.get("tag"):
                    tags_text = tag_data["tag"]
                else:
                    tags_text = "なし"
                self._info_labels["tags"].config(text=tags_text)

                # 評価情報（拡張評価システム）
                assigned_rating = self.image_rating_map.get(image_hash)
                if assigned_rating and assigned_rating in self.rating_dict:
                    rating_data = self.rating_dict[assigned_rating]
                    if rating_data.get("linked", True):
                        rating_value = rating_data.get("rating", 0)
                        rating_type = "連動"
                    else:
                        rating_value = rating_data.get("custom_rating", 0)
                        rating_type = "固定"
                    rating_text = f"{assigned_rating}({rating_type}): {rating_value}/6" + (" ★" * rating_value)
                else:
                    rating_text = "未評価"
                self._info_labels["rating"].config(text=rating_text)

                # ベクトル解釈
                vec = self.vectors_cache.get(image_hash)
                if vec:
                    interpreter = get_interpreter({"vector_display": getattr(app_state, 'vector_display', {})})
                    interp = interpreter.interpret_vector(vec)
                    interp_text = interpreter.format_interpretation_text(interp)
                else:
                    if app_state.vector_display.get("enabled", True):
                        interp_text = "未登録 (画像窓をクリックで解析)"
                    else:
                        interp_text = "表示オフ"
                self._info_labels["vector"].config(text=interp_text)
                
                # 専用ウィンドウにも反映
                if hasattr(self, 'vector_win') and self.vector_win:
                    # ここは image_path = image_path (func arg)
                    self.update_vector_window_content(image_hash, image_path)


                # ウィンドウを表示
                info_win.deiconify()
            else:
                # 情報がない場合は非表示
                info_win.withdraw()
                if hasattr(self, 'vector_win') and self.vector_win:
                    self.vector_win.update_content("")

        except Exception as e:
            logger.error(f"情報ウィンドウ更新エラー: {e}")

    def update_vector_window_content(self, image_hash, image_path=None):
        """指定された画像のベクトル情報をベクトルウィンドウに表示するのじゃ。"""
        if not hasattr(self, 'vector_win') or not self.vector_win:
            return

        try:
            vec = self.vectors_cache.get(image_hash)
            command = None
            if vec:
                interpreter = get_interpreter({"vector_display": getattr(app_state, 'vector_display', {})})
                interp = interpreter.interpret_vector(vec)
                interp_text = interpreter.format_interpretation_text(interp)
                # 再解析も可能にする
                if image_path:
                    command = lambda: self.perform_manual_vectorization(image_path, image_hash)
            else:
                if app_state.vector_display.get("enabled", True):
                    interp_text = "未登録 (画像窓をクリック、または下のボタンで解析)"
                    if image_path:
                         command = lambda: self.perform_manual_vectorization(image_path, image_hash)
                else:
                    interp_text = "表示オフ (設定でベクトル表示が無効になっているのじゃ)"
            
            self.vector_win.update_content(interp_text, command=command)
        except Exception as e:
            logger.error(f"ベクトルウィンドウ更新エラー: {e}")

    def perform_manual_vectorization(self, image_path, image_hash):
        """手動でベクトル解析を実行する共通メソッドなのじゃ。"""
        try:
            # 既にウィンドウが開いている場合、そのラベルを更新したいが、共通化のため
            # ここではキャッシュとベクトルウィンドウの更新を主に行う。
            # 画像ウィンドウ内のラベル更新は、再描画トリガーが必要かも？
            # 手っ取り早く、キャッシュ更新後に update_vector_window_content を呼ぶ。
            
            if hasattr(self, 'vector_win') and self.vector_win:
                 self.vector_win.update_content("解析中... じっこうちゅう～なのじゃ", command=None)
            
            self.parent.update() # UI更新

            engine = VectorEngine.get_instance()
            if engine.check_available():
                v = engine.get_image_feature(image_path)
                if v:
                    self.vectors_cache[image_hash] = v
                    try:
                        save_vectors(self.vectors_cache)
                        logger.info(f"手動ベクトルを保存しました: {image_hash}")
                    except: pass
                    
                    # 結果を表示更新
                    self.update_vector_window_content(image_hash, image_path)
                    
                    # 画像ウィンドウにも反映させたい... 
                    # 簡易的に、現在開いているウィンドウのラベルも更新する？
                    # これは update_vector_window_content だけでは足りない。
                    # しかし、画像ウィンドウ上のクリックロジックは run_manual_vectorize で完結していた。
                    # 今回はベクトルウィンドウからの呼び出しを想定。
                else:
                    if hasattr(self, 'vector_win') and self.vector_win:
                        self.vector_win.update_content("解釈失敗: AIモデルが応答しないのじゃ", command=lambda: self.perform_manual_vectorization(image_path, image_hash))
            else:
                 if hasattr(self, 'vector_win') and self.vector_win:
                        self.vector_win.update_content("解釈失敗: AIエンジンが準備できていないのじゃ", command=lambda: self.perform_manual_vectorization(image_path, image_hash))

        except Exception as e:
             logger.error(f"手動解析エラー: {e}")
             if hasattr(self, 'vector_win') and self.vector_win:
                 self.vector_win.update_content(f"エラー発生: {e}", command=lambda: self.perform_manual_vectorization(image_path, image_hash))

    def _update_rating_display(self, star_labels, rating):
        """評価表示を更新"""
        try:
            for i, star_label in enumerate(star_labels):
                if i < rating:
                    # 評価済みの星（金色）
                    star_label.config(fg="#ffd700")
                else:
                    # 未評価の星（灰色）
                    star_label.config(fg="#cccccc")
        except Exception as e:
            logger.error(f"評価表示更新エラー: {e}")

    def set_window_topmost(self, win, enabled=True):
        """指定ウィンドウの最前面表示を切り替える。"""
        if not win or not hasattr(win, "attributes"):
            return False
        try:
            win.attributes("-topmost", bool(enabled))
            return bool(win.attributes("-topmost"))
        except Exception:
            return False

    def toggle_window_topmost(self, win, button=None):
        """画像ウィンドウの最前面表示を反転してボタン文字も更新する。"""
        if not win or not win.winfo_exists():
            return False
        try:
            current = bool(win.attributes("-topmost"))
            new_state = not current
            updated = self.set_window_topmost(win, new_state)
            if button is not None:
                button.config(text="前面:ON" if updated else "前面:OFF")
            return updated
        except Exception:
            return False

    def add_titlebar_controls(self, win, fullName, image_hash):
        """画像ウィンドウのタイトルバーにタグ編集と最前面切替ボタンを付ける。"""
        try:
            if getattr(win, "_titlebar_controls_added", False):
                return

            titlebar = tk.Frame(win, bg="#ececec", bd=1, relief="raised")
            titlebar.pack(fill="x", side="top")

            tag_btn = tk.Button(
                titlebar,
                text="タグ",
                relief="flat",
                padx=6,
                pady=2,
                font=("MS Gothic", 8),
                command=lambda: self.open_tag_edit_dialog(win, fullName, image_hash, update_target_win=win),
            )
            tag_btn.pack(side="right", padx=(0, 4), pady=2)

            topmost_btn = tk.Button(
                titlebar,
                text="前面:ON" if win.attributes("-topmost") else "前面:OFF",
                relief="flat",
                padx=6,
                pady=2,
                font=("MS Gothic", 8),
                command=lambda: self.toggle_window_topmost(win, topmost_btn),
            )
            topmost_btn.pack(side="right", padx=(0, 4), pady=2)

            win._titlebar_controls_added = True
            win._titlebar_topmost_btn = topmost_btn
        except Exception as e:
            logger.warning(f"タイトルバー制御の追加に失敗: {e}")

    def open_tag_edit_dialog(self, parent_win, file_path, image_hash, update_target_win=None):
        """フォーカス中の画像に対してタグ編集の専用ダイアログを開く。"""
        try:
            if not image_hash:
                messagebox.showerror("エラー", "画像ハッシュが取得できないため、タグを編集できません")
                return

            data = self.tag_dict.get(image_hash, {})
            current_tag = data.get("tag", "") if isinstance(data, dict) else ""

            dialog = tk.Toplevel(parent_win)
            dialog.title(f"タグ編集 - {os.path.basename(file_path)}")
            dialog.attributes("-topmost", True)
            dialog.transient(parent_win)
            dialog.grab_set()

            tk.Label(dialog, text="タグ（; 区切り）:", anchor="w").pack(fill="x", padx=10, pady=(10, 4))
            tag_var = tk.StringVar(value=current_tag)
            entry = tk.Entry(dialog, textvariable=tag_var, width=50)
            entry.pack(fill="x", padx=10, pady=(0, 8))
            entry.focus_set()

            def on_save():
                value = (tag_var.get() or "").strip()
                if image_hash not in self.tag_dict:
                    self.tag_dict[image_hash] = {"tag": "", "hint": os.path.basename(file_path), "rating": None}
                self.tag_dict[image_hash]["tag"] = value
                self.tag_dict[image_hash]["hint"] = os.path.basename(file_path)
                save_tags(self.tag_dict)
                if update_target_win:
                    self.set_image_tag(update_target_win, image_hash)
                dialog.destroy()

            btn_frame = tk.Frame(dialog)
            btn_frame.pack(pady=(0, 10))
            tk.Button(btn_frame, text="保存", width=12, command=on_save).pack(side=tk.LEFT, padx=6)
            tk.Button(btn_frame, text="キャンセル", width=12, command=dialog.destroy).pack(side=tk.LEFT, padx=6)

            dialog.bind("<Escape>", lambda e: dialog.destroy())
        except Exception as e:
            logger.error(f"タグ編集ダイアログ起動エラー: {e}")

    def set_image_tag(self, img_window, image_hash):
        """画像ウィンドウにタグラベルを付与するのじゃ。のじゃ。"""
        if not image_hash:
            record_error("tag_render", "image hash missing for tag render", window_exists=bool(img_window and getattr(img_window, 'winfo_exists', lambda: False)()))
            return
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

    def SetUI(self, folder_win, file_win, vector_win=None):
        """UIウィンドウの参照を保持するのじゃ。のじゃ。"""
        self.folder_win = folder_win
        self.file_win = file_win
        self.vector_win = vector_win

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
            if not hasattr(self, '_last_photo_refs'):
                self._last_photo_refs = []
            self._last_photo_refs.append(tkimg)
            win._tk_image_refs.append(tkimg)
            del img_resized

            # ファイル名を表示（相対パスの場合はベースネームを使用）
            if isinstance(fileName, str):
                display_name = os.path.basename(fileName) if os.path.sep in fileName or (os.path.altsep and os.path.altsep in fileName) else fileName
            else:
                display_name = "(無効なファイル名)"
            win.title(f"{display_name} ({int(scale*100)}%)")
            win.attributes("-topmost", True)

            # ハッシュ計算とパス保持（後の処理で使用）
            win._image_path = fullName
            win._image_hash = calculate_file_hash(fullName)
            self.open_windows[fullName] = win
            
            def on_img_close():
                if fullName in self.open_windows:
                    del self.open_windows[fullName]
                win.destroy()
            win.protocol("WM_DELETE_WINDOW", on_img_close)

            def on_focus_set(event=None):
                try:
                    import sys
                    main_mod = sys.modules.get("__main__")
                    if main_mod and hasattr(main_mod, "update_active_tag_target"):
                        main_mod.update_active_tag_target(fullName, win._image_hash)
                        return

                    app_mod = sys.modules.get("GazoToolsApp")
                    if app_mod and hasattr(app_mod, "update_active_tag_target"):
                        app_mod.update_active_tag_target(fullName, win._image_hash)
                        return
                except Exception:
                    pass

                try:
                    record_error(
                        "tag_sync",
                        "active tag target update failed",
                        file_path=fullName,
                        image_hash=getattr(win, '_image_hash', None),
                        event='FocusIn',
                    )
                except Exception:
                    pass
            win.bind("<FocusIn>", on_focus_set)

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
            win._tk_image_refs = getattr(win, '_tk_image_refs', [])
            win._tk_image_refs.append(tkimg)
            canvas.create_image(0, 0, image=tkimg, anchor=tk.NW)

                # 解釈テキストを表示するラベル（スクロール不要の短い要約を想定）
            interp_label = tk.Label(frame, text="", justify=tk.LEFT, anchor="w", bg="#ffffff", fg="#000000", wraplength=new_w - 8)
            interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))

            def safe_widget_config(widget, **kwargs):
                try:
                    if widget is not None and widget.winfo_exists():
                        widget.config(**kwargs)
                except Exception:
                    pass

            # クリックで手動計算する機能を追加するのじゃ
            def run_manual_vectorize():
                safe_widget_config(interp_label, text="(手動ベクトル計算中...じっこうちゅう～だよ)", fg="blue")
                try:
                    if interp_label.winfo_exists():
                        interp_label.update()
                except Exception:
                    pass

                engine = VectorEngine.get_instance()
                if engine.check_available():
                    v = engine.get_image_feature(fullName)
                    if v:
                        self.vectors_cache[win._image_hash] = v
                        try:
                            save_vectors(self.vectors_cache)
                            logger.info(f"手動ベクトルを保存しました: {win._image_hash}")
                        except: pass

                        # 表示内容を更新
                        interpreter = get_interpreter({"vector_display": getattr(app_state, 'vector_display', {})})
                        interp = interpreter.interpret_vector(v)
                        interp_text = interpreter.format_interpretation_text(interp)
                        safe_widget_config(interp_label, text=interp_text, fg="#000000")
                    else:
                        safe_widget_config(interp_label, text="解釈失敗: AIモデルが応答しないのじゃ", fg="red")
                else:
                    safe_widget_config(interp_label, text="解釈失敗: AIエンジンが準備できていないのじゃ", fg="red")

            def on_interp_click(event):
                # 既に計算済み、あるいは計算中の場合は何もしない（あるいは再試行）
                txt = get_label_text(interp_label)
                if txt is None:
                    print(f"[DEBUG] interp_label.text is None: image={fullName} hash={win._image_hash}")
                if "(ベクトル未登録)" in txt or "エラー" in txt or "失敗" in txt or not self.vectors_cache.get(win._image_hash):
                    run_manual_vectorize()

            interp_label.bind("<Button-1>", on_interp_click)

            # ベクトルがあれば解釈を取得して表示（設定による）
            if app_state.vector_display.get("enabled", True):
                try:
                    vec = self.vectors_cache.get(win._image_hash)
                    
                    # ベクトルが未登録ならリアルタイムで計算するのじゃ（オンデマンド計算）
                    if not vec and app_state.vector_display.get("auto_vectorize", True):
                        run_manual_vectorize()
                        vec = self.vectors_cache.get(win._image_hash) # 計算結果を取得

                    if not vec and not app_state.vector_display.get("auto_vectorize", True):
                        safe_widget_config(interp_label, text="(ベクトル未登録) ここをクリックして手動で解析するのじゃ", fg="blue", cursor="hand2")
                        interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))

                    if vec:
                        interpreter = get_interpreter({"vector_display": getattr(app_state, 'vector_display', {})})
                        interp = interpreter.interpret_vector(vec)
                        interp_text = interpreter.format_interpretation_text(interp)
                        safe_widget_config(interp_label, text=interp_text, fg="#000000", cursor="")
                        interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))  # ベクトル表示時はpack
                except Exception as e:
                    import traceback
                    tb = traceback.format_exc()
                    logger.error(f"ベクトル解釈エラー詳細:\n{tb}")
                    error_msg = f"解釈取得エラー: {type(e).__name__}: {e}"
                    safe_widget_config(interp_label, text=error_msg, fg="red")
                    interp_label.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))
                    
                    # エラー詳細コピーボタンを追加するのじゃ
                    def copy_error_details():
                        win.clipboard_clear()
                        win.clipboard_append(f"【エラー概要】\n{error_msg}\n\n【詳細トレースバック】\n{tb}")
                        messagebox.showinfo("コピー完了", "詳細なエラー情報をクリップボードにコピーしたのじゃ！")
                    
                    copy_btn = tk.Button(frame, text="⚠️ エラー詳細をコピー", command=copy_error_details, 
                                         bg="#fff0f0", fg="#cc0000", font=("MS Gothic", 8, "bold"))
                    copy_btn.pack(side=tk.TOP, pady=(0, 5))

            # 右クリックでいつでもコピーできるようにするのじゃ
            def on_interp_right_click(event):
                m = tk.Menu(win, tearoff=0)
                txt = get_label_text(interp_label)
                if txt:
                    m.add_command(label="表示テキストをコピー", command=lambda: (win.clipboard_clear(), win.clipboard_append(txt)))
                    m.post(event.x_root, event.y_root)

            interp_label.bind("<Button-3>", on_interp_right_click)
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
                
                # クリック時に評価システムと情報を連動させるのじゃ
                try:
                    if app_state.show_rating_window:
                        self.update_rating_window_for_image(target_win._image_hash)
                    
                    if app_state.show_info_window:
                        cur_zoom = int(scale * 100)
                        self.update_info_window(fullName, target_win._image_hash, new_w, new_h, cur_zoom)

                    # ベクトルウィンドウも更新するのじゃ
                    if hasattr(self, 'vector_win') and self.vector_win:
                         # target_win._image_path を渡す
                         self.update_vector_window_content(target_win._image_hash, target_win._image_path)

                         # もしウィンドウが非表示なら表示する？（ユーザーの好みによるが、切り替わる＝表示と解釈）
                         # ここでは内容更新のみとする
                except Exception as e:
                    logger.error(f"クリック連動エラー: {e}")

            def do_drag(event, target_win):
                nx = event.x_root - target_win._drag_start_x
                ny = event.y_root - target_win._drag_start_y
                target_win.geometry(f"+{nx}+{ny}")

            # ハッシュベースのタグ情報を設定
            self.set_image_tag(win, win._image_hash)


            # タイトルバー上のタグ/前面切替ボタンを最後に追加
            titlebar_h = 30
            win.geometry(f"{new_w}x{new_h + text_area_h + titlebar_h}+{base_x}+{base_y}")
            self.add_titlebar_controls(win, fullName, win._image_hash)

            # 評価ウィンドウを更新（画像表示時）
            if app_state.show_rating_window:
                self.update_rating_window_for_image(win._image_hash)

            # 情報ウィンドウを更新（画像表示時）
            if app_state.show_info_window:
                zoom_percent = int(scale * 100)
                self.update_info_window(fullName, win._image_hash, new_w, new_h, zoom_percent)

            def open_tag_menu(event):
                menu = tk.Menu(win, tearoff=0)
                menu.add_command(label="タグを編集", command=lambda: self.edit_tag_dialog(win, fullName, win._image_hash, update_target_win=win))
                
                # --- 移動メニューの追加 ---
                move_menu = tk.Menu(menu, tearoff=0)
                menu.add_cascade(label="登録フォルダに移動", menu=move_menu)
                
                move_dest_count = app_state.move_dest_count
                move_dest_list = app_state.move_dest_list
                
                # 移動コールバックラッパー（共通化）
                def create_wrapped_move_cb():
                    def wrapped_move_cb(f_path, d_folder, refresh=True):
                        if self._move_callback:
                            self._move_callback(f_path, d_folder, refresh)
                        
                        # 移動したファイルが表示中の画像ならウィンドウを閉じる
                        if f_path == fullName:
                            try:
                                win.destroy()
                            except: pass
                            if fullName in self.open_windows:
                                del self.open_windows[fullName]
                    return wrapped_move_cb

                def make_move_func(dest):
                    def _move():
                        # スマート移動ダイアログを表示するのじゃ
                        target_folder = os.path.dirname(fullName)
                        try:
                            from lib.GazoToolsGUI import SimilarityMoveDialog
                            SimilarityMoveDialog(self.parent, fullName, dest, target_folder, create_wrapped_move_cb(), self._refresh_callback)
                        except ImportError:
                            logger.error("GazoToolsGUIが見つからないため表示できないのじゃ")
                    return _move

                for i in range(move_dest_count):
                    dest = move_dest_list[i]
                    if dest:
                        move_menu.add_command(label=f"{i+1}: {os.path.basename(dest)}", command=make_move_func(dest))
                    else:
                        move_menu.add_command(label=f"{i+1}: (未登録)", state="disabled")

                # --- 類似画像検索 ---
                def search_similar():
                    target_folder = os.path.dirname(fullName)
                    # 現在選択中の移動先をデフォルトにする
                    idx = app_state.move_reg_idx
                    dest = move_dest_list[idx] if idx < len(move_dest_list) else ""
                    try:
                        from lib.GazoToolsGUI import SimilarityMoveDialog
                        SimilarityMoveDialog(self.parent, fullName, dest, target_folder, create_wrapped_move_cb(), self._refresh_callback)
                    except ImportError:
                        messagebox.showerror("エラー", "GUIモジュールが見つからないのじゃ")

                menu.add_command(label="類似画像を探す", command=search_similar)

                menu.post(event.x_root, event.y_root)

            canvas.bind("<Button-1>", lambda e: start_drag(e, win))
            canvas.bind("<B1-Motion>", lambda e: do_drag(e, win))
            canvas.bind("<Button-3>", open_tag_menu) # 右クリックでメニュー表示

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print(f"画像表示エラー: {e}")
            traceback.print_exc()
            logger.exception("画像表示中に例外が発生しました: %s", fullName)
            record_error(
                "image_render",
                str(e),
                file_path=fullName,
                file_name=os.path.basename(fullName),
                folder=self.StartFolder,
                win_exists=bool(self.parent and getattr(self.parent, 'winfo_exists', lambda: False)()),
                screen_w=getattr(self.parent, 'winfo_screenwidth', lambda: None)() if getattr(self.parent, 'winfo_screenwidth', None) else None,
                screen_h=getattr(self.parent, 'winfo_screenheight', lambda: None)() if getattr(self.parent, 'winfo_screenheight', None) else None,
                traceback=tb,
            )

    def edit_tag_dialog(self, parent_win, filename, image_hash, update_target_win=None):
        """タグ編集ダイアログを表示するのじゃ。のじゃ。"""
        try:
            if not image_hash:
                print("ハッシュ計算に失敗しているためタグ付けできないのじゃ。")
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
            print(f"タグ編集エラー: {e}")

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
            print(f"ワークエリア取得失敗: {e}")
        
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

                print(f"[PUZZLE] {os.path.basename(fullName)} を {rw}x{rh}@{rx},{ry} に敷き詰めたのじゃ。")
            except Exception as e:
                print(f"パズル整列エラー({fullName}): {e}")



