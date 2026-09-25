'''
作成日: 2026年01月04日
機能: UIコンポーネント (MVCのView層)
'''
import os
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import simpledialog
from tkinterdnd2 import DND_FILES
from PIL import Image, ImageTk, ImageOps
import random
import threading
import time

# 依存モジュールのインポート
# 注意: GazoToolsLogicからデータ関連の関数をインポートしますが、
# GazoToolsLogicがこのモジュールをインポートしない限り循環参照は起きません。
from lib.GazoToolsLogger import get_logger
from lib.GazoToolsState import get_app_state
from lib.GazoToolsAI import VectorEngine
from lib.GazoToolsLib import GetGazoFiles
from lib.GazoToolsTagFilter import (
    get_tag_filter_state,
    collect_all_tags,
    filter_file_names_by_tags,
    find_files_for_tag,
    parse_tag_text,
)
from lib.config_defaults import (
    COLOR_REGISTER_BG,
    COLOR_MOVE_BG_1,
    COLOR_MOVE_BG_2,
    get_move_grid_columns,
    SHORTCUT_TAG_KEY_COUNT,
)

# 相対インポートではなく、ルートからのインポートを使用
# (アプリ実行時のパス構成に依存)
import sys

# Logicとの循環参照を避けるため、必要な関数は可能な限りここでインポートするか、
# コールバックや遅延インポートを使用します。
# 現在の構造上、GazoToolsLogicにある関数(calculate_file_hash, load_vectorsなど)が必要です。
# GazoToolsLogicがGazoToolsGUIをトップレベルでインポートしていなければ、ここでインポートしても安全です。
try:
    from GazoToolsLogic import calculate_file_hash, load_vectors, save_tags, save_config
except ImportError:
    # パスが通っていない場合（単体テストなど）の対策
    # 本番実行時は GazoToolsApp.py がルートにあるので通るはず
    pass

logger = get_logger(__name__)
app_state = get_app_state()
tag_filter_state = get_tag_filter_state()


def calculate_thumbnail_tile_size(canvas_width, canvas_height, rows, columns, base_width, base_height):
    """固定サムネイルサイズを返す。窓サイズでは画像サイズを変えない。"""
    base_width = max(32, int(base_width))
    base_height = max(32, int(base_height))
    return base_width, base_height


class ThumbnailPanelWindow(tk.Toplevel):
    """画像だけを格子状に並べる、操作可能なサムネイルパネル。"""

    _TARGET_HIGHLIGHT_COLOR = "#4a90e2"

    def __init__(self, parent, files=None, select_callback=None, close_callback=None, window_number=1, gazo_control=None, edit_tag_callback=None):
        super().__init__(parent)
        self.title(f"画像サムネイル {window_number}")
        self.attributes("-topmost", bool(app_state.topmost))
        self.select_callback = select_callback
        self.close_callback = close_callback
        self.edit_tag_callback = edit_tag_callback
        self.gazo_control = gazo_control
        self.all_files = []
        self.files = []
        self.selected_paths = set()
        self.target_path = None
        self._photo_refs = {}
        self._tile_labels = {}
        self._tile_windows = {}
        self._visible_signature = None
        self._tile_size = (app_state.thumbnail_width, app_state.thumbnail_height)
        self._resize_after_id = None
        self._load_after_id = None
        self.rows_var = tk.IntVar(value=app_state.thumbnail_rows)
        self.columns_var = tk.IntVar(value=app_state.thumbnail_columns)
        self.width_var = tk.IntVar(value=app_state.thumbnail_width)
        self.height_var = tk.IntVar(value=app_state.thumbnail_height)

        notebook = ttk.Notebook(self)
        notebook.pack(fill=tk.BOTH, expand=True)
        image_tab = tk.Frame(notebook, bg="#202020")
        settings_tab = tk.Frame(notebook)
        notebook.add(image_tab, text="画像")
        notebook.add(settings_tab, text="設定")
        self.notebook = notebook
        self.image_tab = image_tab
        self.show_images_var = tk.BooleanVar(value=True)
        self.untagged_only_var = tk.BooleanVar(value=False)

        control = tk.Frame(settings_tab)
        control.pack(fill=tk.X, padx=5, pady=5)
        tk.Checkbutton(
            control, text="画像を表示", variable=self.show_images_var,
            command=self._toggle_image_panel,
        ).grid(row=0, column=8, padx=8)
        self._add_spinbox(control, "縦", self.rows_var, 1, 20, 0)
        self._add_spinbox(control, "横", self.columns_var, 1, 20, 2)
        self._add_spinbox(control, "幅", self.width_var, 32, 2000, 4)
        self._add_spinbox(control, "高さ", self.height_var, 32, 2000, 6)
        tk.Checkbutton(
            control, text="タグ未設定のみ表示", variable=self.untagged_only_var,
            command=self._apply_filters,
        ).grid(row=1, column=0, columnspan=4, sticky="w", padx=4, pady=(4, 0))
        tk.Button(
            control, text="選択した画像にタグを付与",
            command=self._apply_tag_to_selection,
        ).grid(row=1, column=4, columnspan=4, sticky="w", padx=4, pady=(4, 0))

        self.canvas = tk.Canvas(image_tab, highlightthickness=0, bg="#202020")
        self.scrollbar = tk.Scrollbar(self, orient=tk.VERTICAL, command=self._scroll)
        self.hscrollbar = tk.Scrollbar(self, orient=tk.HORIZONTAL, command=self._scroll)
        self.canvas.configure(
            yscrollcommand=self.scrollbar.set,
            xscrollcommand=self.hscrollbar.set,
        )
        self.hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<Configure>", self._on_window_resize)
        self.bind("<MouseWheel>", self._on_mousewheel)
        self.geometry("900x700")
        self.bind("<Control-w>", lambda event: self.withdraw())
        self.bind("<Key-t>", self._on_edit_tag_shortcut)
        self.protocol("WM_DELETE_WINDOW", self._close_window)
        self.set_files(files or [])

    def _add_spinbox(self, parent, label, variable, minimum, maximum, column):
        tk.Label(parent, text=label).grid(row=0, column=column, padx=(4, 1))
        spinbox = tk.Spinbox(
            parent, from_=minimum, to=maximum, width=4,
            textvariable=variable, command=self._settings_changed,
        )
        spinbox.grid(row=0, column=column + 1, padx=(0, 4))
        spinbox.bind("<Return>", lambda event: self._settings_changed())
        spinbox.bind("<FocusOut>", lambda event: self._settings_changed())

    def _settings_changed(self):
        try:
            app_state.thumbnail_rows = max(1, int(self.rows_var.get()))
            app_state.thumbnail_columns = max(1, int(self.columns_var.get()))
            app_state.thumbnail_width = max(32, int(self.width_var.get()))
            app_state.thumbnail_height = max(32, int(self.height_var.get()))
            self.render()
        except (tk.TclError, ValueError):
            return

    def _toggle_image_panel(self):
        if self.show_images_var.get():
            self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            self.hscrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        else:
            self.canvas.pack_forget()
            self.scrollbar.pack_forget()
            self.hscrollbar.pack_forget()

    def _close_window(self):
        if self.close_callback:
            self.close_callback(self)
        else:
            self.withdraw()

    def set_files(self, files):
        self.all_files = list(files)
        self._apply_filters()

    def apply_filters(self):
        """タグ一覧窓側の絞り込み変更時に外部から呼ばれる再フィルタ処理。"""
        self._apply_filters()

    def _tag_dict(self):
        return self.gazo_control.tag_dict if self.gazo_control and hasattr(self.gazo_control, 'tag_dict') else {}

    def _build_path_to_hash(self, paths):
        path_to_hash = {}
        for path in paths:
            try:
                path_to_hash[path] = calculate_file_hash(path)
            except Exception:
                continue
        return path_to_hash

    def _filter_untagged(self, paths):
        tag_dict = self._tag_dict()
        path_to_hash = self._build_path_to_hash(paths)
        result = []
        for path in paths:
            image_hash = path_to_hash.get(path)
            entry = tag_dict.get(image_hash) if image_hash else None
            if entry is None or not parse_tag_text(entry.get("tag", "")):
                result.append(path)
        return result

    def _apply_filters(self):
        if self.untagged_only_var.get():
            self.files = self._filter_untagged(self.all_files)
        elif tag_filter_state.active_filter:
            path_to_hash = self._build_path_to_hash(self.all_files)
            self.files = filter_file_names_by_tags(
                self.all_files, path_to_hash, self._tag_dict(),
                tag_filter_state.active_filter, tag_filter_state.mode,
            )
        else:
            self.files = list(self.all_files)
        self.render()

    def _apply_tag_to_selection(self):
        if not self.selected_paths:
            messagebox.showinfo("タグ付与", "画像が選択されていません")
            return
        raw = simpledialog.askstring("タグ付与", "追加するタグ（; 区切り）:", parent=self)
        if raw is None:
            return
        new_tags = set(parse_tag_text(raw))
        if not new_tags:
            return
        tag_dict = self._tag_dict()
        affected_hashes = []
        for path in self.selected_paths:
            try:
                image_hash = calculate_file_hash(path)
            except Exception:
                continue
            entry = tag_dict.get(image_hash)
            if entry is None:
                entry = {"tag": "", "hint": os.path.basename(path), "rating": None}
                tag_dict[image_hash] = entry
            existing = set(parse_tag_text(entry.get("tag", "")))
            entry["tag"] = "; ".join(sorted(existing | new_tags))
            entry["hint"] = os.path.basename(path)
            affected_hashes.append(image_hash)
        if affected_hashes:
            save_tags(tag_dict)
            if self.gazo_control and hasattr(self.gazo_control, 'set_image_tag'):
                for open_win in self.gazo_control.open_windows.values():
                    if getattr(open_win, '_image_hash', None) in affected_hashes:
                        self.gazo_control.set_image_tag(open_win, open_win._image_hash)
        self.selected_paths.clear()
        self._apply_filters()

    def _on_canvas_resize(self, event):
        self._schedule_visible_render()

    def _on_window_resize(self, event):
        if self._resize_after_id is not None:
            self.after_cancel(self._resize_after_id)
        self._resize_after_id = self.after(80, self._schedule_visible_render)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        self._schedule_visible_render()

    def _scroll(self, *args):
        self.canvas.yview(*args)
        self._schedule_visible_render()

    def _schedule_visible_render(self):
        if self._load_after_id is not None:
            self.after_cancel(self._load_after_id)
        self._load_after_id = self.after(30, self._render_visible_rows)

    def render(self):
        if not self.winfo_exists():
            return
        self._clear_visible_tiles()
        self._photo_refs = {}
        self._tile_labels = {}
        self._visible_signature = None
        try:
            rows = max(1, int(self.rows_var.get()))
            columns = max(1, int(self.columns_var.get()))
            base_width = max(32, int(self.width_var.get()))
            base_height = max(32, int(self.height_var.get()))
        except (tk.TclError, ValueError):
            return

        tile_width, tile_height = calculate_thumbnail_tile_size(
            self.canvas.winfo_width(), self.canvas.winfo_height(),
            rows, columns, base_width, base_height,
        )
        self._tile_size = (tile_width, tile_height)

        total_rows = (len(self.files) + columns - 1) // columns
        self.canvas.configure(scrollregion=(0, 0, columns * (tile_width + 4), max(1, total_rows * (tile_height + 4))))
        self._schedule_visible_render()

    def _clear_visible_tiles(self):
        for window_id, tile in self._tile_windows.values():
            self.canvas.delete(window_id)
            tile.destroy()
        self._tile_windows = {}

    def _render_visible_rows(self):
        self._load_after_id = None
        tile_height = self._tile_size[1] + 4
        first_row = max(0, int(self.canvas.canvasy(0) // tile_height) - 1)
        visible_rows = max(1, int(self.canvas.winfo_height() // tile_height) + 2)
        columns = max(1, int(self.columns_var.get()))
        first_index = first_row * columns
        last_index = min(len(self.files), (first_row + visible_rows) * columns)
        signature = (first_index, last_index, self._tile_size, columns)
        if signature == self._visible_signature:
            return

        self._clear_visible_tiles()
        self._photo_refs = {}
        self._tile_labels = {}
        self._visible_signature = signature
        for index in range(first_index, last_index):
            file_path = self.files[index]
            row, column = divmod(index, columns)
            tile = tk.Frame(self.canvas, width=self._tile_size[0], height=self._tile_size[1], bg="#303030")
            window_id = self.canvas.create_window(
                column * (self._tile_size[0] + 4),
                row * (self._tile_size[1] + 4),
                window=tile,
                anchor="nw",
            )
            tile.grid_propagate(False)
            select_var = tk.BooleanVar(value=file_path in self.selected_paths)
            def on_toggle(path=file_path, var=select_var):
                if var.get():
                    self.selected_paths.add(path)
                else:
                    self.selected_paths.discard(path)
            chk = tk.Checkbutton(
                tile, variable=select_var, bg="#303030",
                activebackground="#303030", bd=0, highlightthickness=0,
                command=on_toggle,
            )
            chk.place(x=2, y=2)
            is_target = (file_path == self.target_path)
            label = tk.Label(
                tile, bg="#303030", bd=0, highlightthickness=3,
                highlightbackground=self._TARGET_HIGHLIGHT_COLOR if is_target else "#303030",
            )
            label.pack(fill=tk.BOTH, expand=True)
            label.bind("<Button-1>", lambda event, path=file_path: self._select(path))
            label.bind("<Double-Button-1>", lambda event, path=file_path: self._select(path, open_image=True))
            label.bind("<MouseWheel>", self._on_mousewheel)
            label.bind("<Button-3>", lambda event, path=file_path: self._show_context_menu(event, path))
            self._tile_labels[index] = (label, file_path)
            self._tile_windows[index] = (window_id, tile)
            try:
                with Image.open(file_path) as image:
                    fitted = ImageOps.contain(image, self._tile_size, method=Image.LANCZOS)
                    photo = ImageTk.PhotoImage(master=label, image=fitted)
                self._photo_refs[index] = photo
                label.configure(image=photo)
            except Exception:
                continue

    def _select(self, file_path, open_image=False):
        self.set_target_path(file_path)
        self.focus_set()
        if self.select_callback:
            self.select_callback(file_path, open_image)

    def set_target_path(self, path):
        """タグ編集対象になった画像を記録し、該当タイルをハイライトする。"""
        self.target_path = path
        for label, file_path in self._tile_labels.values():
            try:
                is_target = (file_path == self.target_path)
                label.config(highlightbackground=self._TARGET_HIGHLIGHT_COLOR if is_target else "#303030")
            except tk.TclError:
                continue

    def _edit_tag(self, file_path):
        if self.edit_tag_callback:
            self.edit_tag_callback(file_path)

    def _on_edit_tag_shortcut(self, event=None):
        if self.target_path:
            self._edit_tag(self.target_path)

    def _show_context_menu(self, event, file_path):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="画像を開く", command=lambda: self._select(file_path, open_image=True))
        menu.add_command(label="タグ編集", command=lambda: self._edit_tag(file_path))
        menu.add_command(label="パスをコピー", command=lambda: self._copy_path(file_path))
        menu.add_separator()
        menu.add_command(label="このサムネイル窓を隠す", command=self.withdraw)
        menu.tk_popup(event.x_root, event.y_root)

    def _copy_path(self, file_path):
        self.clipboard_clear()
        self.clipboard_append(file_path)
        self.update()

    def show(self):
        self.deiconify()
        self.lift()

    def set_topmost(self, enabled):
        self.attributes("-topmost", bool(enabled))

class ScrollableFrame(tk.Frame):
    """スクロール可能なフレームウィジェット"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0, bg="#ffffff")
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        
        # コンテンツを表示する内部フレーム
        self.scrollable_frame = tk.Frame(self.canvas, bg="#ffffff")
        
        # フレームのサイズ変更に合わせてCanvasのスクロール領域を更新
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        # Canvas内にフレームを配置
        self.window_id = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Canvasのサイズ変更に合わせてフレームの幅を更新
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window_id, width=e.width)
        )
        
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # マウスホイールイベントのバインド
        self.bind_mouse_wheel(self.canvas)
        self.bind_mouse_wheel(self.scrollable_frame)

    def bind_mouse_wheel(self, widget):
        widget.bind("<MouseWheel>", self._on_mouse_wheel)
        # Linux対応などは省略（今回はWindows前提）

    def _on_mouse_wheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

class RowWidget(tk.Frame):
    """リストの1行を表すウィジェット"""
    def __init__(self, parent, filepath, score, is_target=False, show_thumb=True):
        super().__init__(parent, bg="#e6ffe6" if is_target else "#ffffff", pady=2, padx=2, bd=1, relief=tk.SOLID if is_target else tk.FLAT)
        self.filepath = filepath
        self.score = score
        self.show_thumb = show_thumb
        self.is_target = is_target
        self._image_loaded = False
        self._thumb_img = None
        
        # サムネイル領域
        self.lbl_thumb = tk.Label(self, bg="#dddddd", width=64, height=64) if show_thumb else None
        if self.lbl_thumb:
            self.lbl_thumb.pack(side=tk.LEFT, padx=(0, 5))
            # 遅延ロードはせず、表示時にロード関数を呼ぶ設計にするが、
            # Threadingでロード済みならそれをセットする形がいい。
            # ここではシンプルに「表示が必要ならロード」する。
            if show_thumb:
                self.load_thumbnail()

        # テキスト情報
        text = f"[基準] {os.path.basename(filepath)}" if is_target else f"({score:.1%}) {os.path.basename(filepath)}"
        fg = "blue" if is_target else "black"
        self.lbl_text = tk.Label(self, text=text, font=("MS Gothic", 9), anchor="w", bg=self.cget("bg"), fg=fg)
        self.lbl_text.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def load_thumbnail(self):
        if self._image_loaded: return
        try:
            # 高速化のため最大サイズを指定してロード
            with Image.open(self.filepath) as img:
                img.thumbnail((64, 64))
                self._thumb_img = ImageTk.PhotoImage(img)
                if self.lbl_thumb:
                    self.lbl_thumb.config(image=self._thumb_img, width=0, height=0) # 画像サイズに合わせる
        except Exception:
            pass # ロード失敗時はグレーのまま
        self._image_loaded = True

    def set_thumbnail_visible(self, visible):
        """サムネイル表示切り替え"""
        if visible:
            if not self.lbl_thumb:
                self.lbl_thumb = tk.Label(self, bg="#dddddd")
            self.lbl_thumb.pack(side=tk.LEFT, padx=(0, 5), before=self.lbl_text)
            self.load_thumbnail()
        else:
            if self.lbl_thumb:
                self.lbl_thumb.pack_forget()

class SimilarityMoveDialog(tk.Toplevel):
    """類似画像をまとめて移動するためのダイアログクラスなのじゃ。"""
    def __init__(self, parent, target_file, dest_folder, folder_path, move_callback, refresh_callback=None):
        super().__init__(parent)
        self.title("スマート移動 - 準備中...")
        self.geometry("500x600")
        self.attributes("-topmost", True)
        
        self.target_file = target_file
        self.dest_folder = dest_folder
        self.folder_path = folder_path
        self.move_callback = move_callback
        self.refresh_callback = refresh_callback
        
        self.row_widgets = [] # RowWidgetのリスト
        self.selected_files = [] # Files to move
        self.is_calculating = True
        self.stop_thread = False
        
        # UI Setup
        tk.Label(self, text=f"【基準】 {os.path.basename(target_file)}", font=("MS Gothic", 10, "bold"), fg="blue").pack(pady=5)
        tk.Label(self, text=f"【移動先】 {os.path.basename(dest_folder)}", font=("MS Gothic", 10, "bold"), fg="red").pack(pady=5)
        
        # Control Frame (Slider & Settings)
        frame_ctrl = tk.LabelFrame(self, text="設定 (AI判定)", padx=10, pady=5)
        frame_ctrl.pack(fill=tk.X, padx=10, pady=5)
        
        # 閾値スライダー
        default_threshold = app_state.smart_move_threshold
        self.var_threshold = tk.DoubleVar(value=default_threshold)
        
        self.lbl_threshold = tk.Label(frame_ctrl, text=f"閾値: {int(default_threshold*100)}%")
        self.lbl_threshold.pack(anchor="w")
        
        def on_scale(val):
            self.lbl_threshold.config(text=f"閾値: {float(val)*100:.1f}%")
            self.update_list_filter() # リアルタイムフィルタリング
            
        self.scale = tk.Scale(frame_ctrl, variable=self.var_threshold, from_=0.0, to=1.0, resolution=0.01, orient=tk.HORIZONTAL, command=on_scale)
        self.scale.pack(fill=tk.X, expand=True)

        # サムネイル設定
        self.var_show_thumb = tk.BooleanVar(value=app_state.smart_move_show_thumbnails)
        def on_thumb_toggle():
            app_state.set_smart_move_show_thumbnails(self.var_show_thumb.get())
            self.update_thumbnail_visibility()
            
        tk.Checkbutton(frame_ctrl, text="サムネイルを表示（重い場合はOFF推奨）", variable=self.var_show_thumb, command=on_thumb_toggle).pack(anchor="w")
        
        # Status Label
        self.lb_status = tk.Label(self, text="初期化中...", font=("MS Gothic", 9), fg="#666666")
        self.lb_status.pack()
        
        # List Area (Scrollable)
        frame_list_container = tk.Frame(self, bd=1, relief=tk.SUNKEN)
        frame_list_container.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)
        
        self.scroll_frame = ScrollableFrame(frame_list_container)
        self.scroll_frame.pack(expand=True, fill=tk.BOTH)
        
        # Buttons
        frame_btn = tk.Frame(self)
        frame_btn.pack(fill=tk.X, pady=10)
        self.btn_execute = tk.Button(frame_btn, text="移動実行", bg="#ffcccc", width=15, height=2, command=self.on_execute, state=tk.DISABLED)
        self.btn_execute.pack(side=tk.RIGHT, padx=10)
        tk.Button(frame_btn, text="キャンセル", width=10, height=2, command=self.on_cancel).pack(side=tk.RIGHT, padx=10)
        
        # Threading Start
        self.thread = threading.Thread(target=self.prepare_data_thread, daemon=True)
        self.thread.start()
        
    def on_cancel(self):
        self.stop_thread = True
        self.destroy()

    def prepare_data_thread(self):
        """別スレッドで重い処理を行うのじゃ"""
        try:
            from GazoToolsLogic import calculate_file_hash, load_vectors, save_vectors

            # GUI更新用ヘルパー
            def update_status(text, loaded_count=0, total_count=0):
                 self.after(0, lambda: self.lb_status.config(text=text))
                 if total_count > 0:
                     self.after(0, lambda: self.title(f"準備中... {loaded_count}/{total_count}"))

            engine = VectorEngine.get_instance()
            vectors = load_vectors()
            
            # 基準画像のベクトル
            t_hash = calculate_file_hash(self.target_file)
            if t_hash not in vectors:
                 vec = engine.get_image_feature(self.target_file)
                 if vec: vectors[t_hash] = vec
            t_vec = vectors.get(t_hash)
            
            if not t_vec:
                self.after(0, lambda: messagebox.showerror("エラー", "基準画像のベクトル計算に失敗したのじゃ"))
                self.after(0, self.destroy)
                return

            all_items = os.listdir(self.folder_path)
            files = GetGazoFiles(all_items, self.folder_path)
            total = len(files)
            
            candidates_data = [] # (file_path, score)
            vectors_updated = False
            
            start_time = time.time()
            chunk_start_time = start_time
            
            count = 0
            for i, f in enumerate(files):
                if self.stop_thread: return
                
                full = os.path.join(self.folder_path, f)
                if full == self.target_file: continue
                
                h = calculate_file_hash(full)
                # ベクトルがない場合、ここで計算してしまうのじゃ！
                if h not in vectors:
                    try:
                        vec = engine.get_image_feature(full)
                        if vec:
                            vectors[h] = vec
                            vectors_updated = True
                    except Exception as e:
                        logger.warning(f"オンデマンドベクトル計算失敗: {f} - {e}")

                if h in vectors:
                    score = engine.compare_features(t_vec, vectors[h])
                    candidates_data.append((full, score))
                
                count += 1
                
                # 10個ごとに時間を計測してログ出力（ユーザー要望）
                if count % 10 == 0:
                    current = time.time()
                    elapsed = current - chunk_start_time
                    logger.debug(f"[PERF] Processed 10 items in {elapsed:.4f} sec (Total: {count}/{total})")
                    chunk_start_time = current
                    update_status(f"計算中... {count}/{total}", count, total)

            # ベクトルが更新されていれば保存するのじゃ
            if vectors_updated:
                self.after(0, lambda: self.lb_status.config(text="ベクトル保存中..."))
                try:
                    save_vectors(vectors)
                except Exception as e:
                    logger.error(f"ベクトル保存エラー: {e}")

            # スコア順にソート
            candidates_data.sort(key=lambda x: x[1], reverse=True)
            
            # RowWidgetの生成はメインスレッドで行う必要があるのじゃ（Tkinterの制約）
            # なので、データを渡してメインスレッド側で構築する
            self.after(0, lambda: self.finalize_preparation(candidates_data))
            
        except Exception as e:
            logger.error(f"データ準備スレッドエラー: {e}", exc_info=True)
            self.after(0, lambda: messagebox.showerror("エラー", f"データ準備中にエラーが発生したのじゃ: {e}"))
            self.after(0, self.destroy)

    def finalize_preparation(self, candidates_data):
        """データ準備完了後のUI構築（メインスレッド）"""
        if self.stop_thread: return
        
        self.is_calculating = False
        self.lb_status.config(text="リスト構築中...")
        self.title("スマート移動 - 類似画像も一緒に運ぶのじゃ")
        
        # ウィジェットプール作成
        # 基準画像
        self.row_widgets.append(RowWidget(self.scroll_frame.scrollable_frame, self.target_file, 1.0, is_target=True, show_thumb=self.var_show_thumb.get()))
        
        # 候補画像
        for f, score in candidates_data:
            rw = RowWidget(self.scroll_frame.scrollable_frame, f, score, show_thumb=self.var_show_thumb.get())
            self.row_widgets.append(rw)
            
        self.btn_execute.config(state=tk.NORMAL)
        self.update_list_filter()
        self.lb_status.config(text="準備完了")

    def update_thumbnail_visibility(self):
        """サムネイル表示の一括切り替え"""
        show = self.var_show_thumb.get()
        for rw in self.row_widgets:
            rw.set_thumbnail_visible(show)
    
    def update_list_filter(self):
        """スライダーの値に基づいてリストをフィルタリング（Widget Pooling）"""
        if self.is_calculating: return
        
        threshold = self.var_threshold.get()
        count = 0
        visible_widgets = []
        self.selected_files = []
        
        # 再描画のチラつきを抑えるため、マップ済みかどうかを管理できればベストだが
        # pack/pack_forget は比較的軽量なのでそのままやる
        
        for rw in self.row_widgets:
            if rw.is_target:
                visible_widgets.append(rw)
                self.selected_files.append(rw.filepath)
                count += 1
            elif rw.score >= threshold:
                visible_widgets.append(rw)
                self.selected_files.append(rw.filepath)
                count += 1
        
        # 一括配置更新
        # 現在packされているものと、本来あるべきものの差分だけ操作するのは面倒なので
        # 全リストのpack状態を更新する（順序維持）
        # ただ、毎回全部 forget は遅いので、必要なものだけ pack する
        
        # 一旦すべて forget するのが手っ取り早いが、数が多いと点滅する。
        # ここはシンプルに「grid」ではなく「pack」なので、上から順に並べる必要がある。
        # 既存のslaveリストを取得して...というのは複雑。
        # リストボックス的挙動なら、「Grid」を使って `grid_remove` のほうが状態保持しやすいかもだが、
        # ここは `pack_forget` と `pack` でいく。
        
        for child in self.scroll_frame.scrollable_frame.winfo_children():
            child.pack_forget()
            
        for rw in visible_widgets:
            rw.pack(fill=tk.X, expand=True)
            # 表示された時点で画像ロード（遅延ロード）
            if rw.show_thumb:
                rw.load_thumbnail()
        
        self.lb_status.config(text=f"移動対象: {count}件")

    def on_execute(self):
        if not self.move_callback: return
        count = len(self.selected_files)
        if messagebox.askyesno("確認", f"{count}件のファイルを移動してよいかの？"):
            # 移動処理
            # ★重要★: 基準画像(target_file)を移動すると、呼び出し元のウィンドウが閉じてしまい、
            # このダイアログも道連れで破棄される可能性があるのじゃ。
            # そのため、基準画像はリストの最後に移動させる工夫が必要なのじゃ。
            
            non_target_files = [f for f in self.selected_files if f != self.target_file]
            targets = [f for f in self.selected_files if f == self.target_file] # 通常1つ
            
            # 先に基準以外を移動
            sorted_files = non_target_files + targets
            
            success_count = 0
            for f in sorted_files:
                try:
                    # キーワード引数 refresh=False を渡せるか試みる
                    self.move_callback(f, self.dest_folder, refresh=False)
                    success_count += 1
                except TypeError:
                    # refresh引数がない関数だった場合のフォールバック
                    self.move_callback(f, self.dest_folder)
                    success_count += 1
            
            # ★ 最後に一括リフレッシュを実行するのじゃ ★
            if self.refresh_callback:
                try:
                    self.refresh_callback(self.folder_path)
                except Exception as e:
                    logger.error(f"一括リフレッシュ失敗: {e}")

            # 成功したら閾値を保存するのじゃ
            app_state.set_smart_move_threshold(self.var_threshold.get())

            # ウィンドウがまだ生きていれば完了メッセージ
            try:
                messagebox.showinfo("完了", f"{success_count}件の移動が完了したのじゃ！")
                self.destroy()
            except Exception:
                # 親ウィンドウと共に死んだ場合は無視
                pass

class SplashWindow(tk.Toplevel):
    """起動時のスプラッシュスクリーン"""
    def __init__(self, parent):
        super().__init__(parent)
        self.title("GazoTools")
        
        w, h = 400, 300
        
        # 画面中央に配置
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        
        self.geometry('%dx%d+%d+%d' % (w, h, x, y))
        self.overrideredirect(True) # 枠なし
        self.configure(bg='#2b2b2b')
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.0) # フェードインのため最初は透明
        
        # メインフレーム（Canvasで描画）
        self.canvas = tk.Canvas(self, width=w, height=h, bg="#2b2b2b", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # 背景グラデーション風（簡易）
        self.canvas.create_rectangle(0, 0, w, h, fill="#2b2b2b", outline="")
        self.canvas.create_rectangle(0, 0, w, 5, fill="#4a90e2", outline="") # 上部アクセント
        
        # アプリタイトル
        self.canvas.create_text(w//2, h//2 - 40, text="推し活を推進するための", fill="#aaaaaa", font=("MS Gothic", 16))
        self.canvas.create_text(w//2, h//2 + 10, text="画像整理アプリ（仮）", fill="#ffffff", font=("MS Gothic", 32, "bold"))
        
        # バージョン情報
        self.canvas.create_text(w-20, h-20, text="Ver 2.7.2", fill="#666666", font=("Helvetica", 12), anchor="se")
        
        # Tips（設定依存）
        if app_state.show_splash_tips:
            tips = [
                "Tips: Ctrl+T でパズルみたいに並ぶのじゃ",
                "Tips: 画像の上でスペースキーを押すとランダム移動するのじゃ",
                "Tips: 右クリックでタグ付けができるのじゃ",
                "Tips: スマート移動はサムネイル付きで便利なのじゃ",
                "Tips: Shiftキーを押しながらD&Dでコピーもできるのじゃ"
            ]
            tip = random.choice(tips)
            self.canvas.create_text(w//2, h-60, text=tip, fill="#4a90e2", font=("MS Gothic", 10))
        
        # フェードイン開始
        self.fade_in()
        
    def fade_in(self):
        try:
            alpha = self.attributes("-alpha")
            if alpha < 1.0:
                alpha += 0.05
                self.attributes("-alpha", alpha)
                self.after(20, self.fade_in)
        except:
            pass
            
    def close(self):
        self.destroy()
class VectorWindow(tk.Toplevel):
    """ベクトル解析情報を表示する専用ウィンドウなのじゃ。"""
    def __init__(self, master, font_size=10):
        super().__init__(master)
        self.title("ベクトル解析")
        self.geometry("300x400")
        self.withdraw() # 初期状態は非表示
        self.protocol("WM_DELETE_WINDOW", self.withdraw) # 閉じるボタンで隠すだけ

        # ボタンエリア
        self.btn_frame = tk.Frame(self)
        self.btn_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        self.analyze_btn = tk.Button(self.btn_frame, text="解析開始 (Start Analysis)", state="disabled")
        self.analyze_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # テキストエリア (読み取り専用)
        self.text_area = tk.Text(self, font=("MS Gothic", font_size), state="disabled", wrap="word")
        self.text_area.pack(expand=True, fill="both", padx=5, pady=5)
    
    def update_content(self, text, command=None):
        """表示内容を更新するのじゃ。commandが渡されたらボタンに設定するのじゃ。"""
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert("1.0", text)
        self.text_area.config(state="disabled")

        if command:
            self.analyze_btn.config(state="normal", command=command)
        else:
            self.analyze_btn.config(state="disabled")


    def show(self):
        self.deiconify()
        self.lift()


class MoveDestinationArea(tk.Frame):
    """ドラッグ&ドロップによるファイル移動先の登録・振り分けエリア。"""

    def __init__(self, parent, move_callback, refresh_callback=None):
        super().__init__(parent)
        self.move_callback = move_callback
        self.refresh_callback = refresh_callback
        self.move_labels = []
        self.move_text_vars = []

        self.text_reg = tk.StringVar(self)
        self.lbl_reg = tk.Label(self, textvariable=self.text_reg, bg=COLOR_REGISTER_BG, height=2, bd=2, relief="groove")
        self.lbl_reg.drop_target_register(DND_FILES)
        self.lbl_reg.dnd_bind("<<Drop>>", self._handle_drop_register)
        self.lbl_reg.pack(fill=tk.BOTH, padx=5, pady=(5, 15))

        self.move_frame = tk.Frame(self)
        self.move_frame.pack(fill=tk.BOTH, padx=5, pady=(0, 5), expand=True)

        self.btn_reset = tk.Button(self, text="全登録フォルダをリセット", bg="#fff0f0",
                                    font=("MS Gothic", 8), command=self.reset_destinations)
        self.btn_reset.pack(fill=tk.X, padx=5, pady=(0, 5))

        self.rebuild()

    def refresh_display(self):
        """D&Dエリアの表示内容を app_state の最新状態に合わせる。"""
        move_dest_count = app_state.move_dest_count
        move_reg_idx = app_state.move_reg_idx
        move_dest_list = app_state.move_dest_list

        marks = []
        for i in range(move_dest_count):
            if i == move_reg_idx:
                marks.append("◎")
            elif move_dest_list[i]:
                marks.append("●")
            else:
                marks.append("○")

        self.text_reg.set(f"登録[次:{move_reg_idx+1}]: {' '.join(marks)}")

        for i in range(move_dest_count):
            if i < len(self.move_text_vars):
                path = move_dest_list[i] if i < len(move_dest_list) else ""
                if path:
                    self.move_text_vars[i].set(f"{i+1}: {os.path.basename(path)}")
                else:
                    self.move_text_vars[i].set(f"{i+1}: (未登録)")

    def rebuild(self):
        """移動先エリアを現在の登録数に合わせて作り直す。"""
        for lbl in self.move_labels:
            lbl.destroy()
        self.move_labels.clear()
        self.move_text_vars.clear()

        move_dest_count = app_state.move_dest_count
        cols = get_move_grid_columns(move_dest_count)

        for i in range(move_dest_count):
            tv = tk.StringVar(self)
            bg_color = COLOR_MOVE_BG_1 if (i % 2 == 0) else COLOR_MOVE_BG_2
            f_size = 8 if move_dest_count > 8 else 9

            l = tk.Label(self.move_frame, textvariable=tv, bg=bg_color, font=("MS Gothic", f_size), height=2, bd=1, relief="ridge")
            l.drop_target_register(DND_FILES)
            l.dnd_bind("<<Drop>>", self._make_drop_func(i))
            l.grid(row=i // cols, column=i % cols, sticky="nsew", padx=1, pady=1)

            self.move_labels.append(l)
            self.move_text_vars.append(tv)

        for c in range(cols):
            self.move_frame.columnconfigure(c, weight=1)
        for r in range((move_dest_count + cols - 1) // cols):
            self.move_frame.rowconfigure(r, weight=1)

        self.refresh_display()

    def reset_destinations(self):
        if not messagebox.askyesno("確認", "全ての登録フォルダ設定をリセットしても良いかの？"):
            return
        app_state.reset_move_destinations()
        self.refresh_display()
        logger.info("[RESET] 全ての移動先をリセットしました")

    def _handle_drop_register(self, event):
        data = event.data
        if data.startswith('{') and data.endswith('}'):
            data = data[1:-1]
        path = os.path.normpath(data)

        if os.path.isdir(path):
            app_state.set_move_destination(app_state.move_reg_idx, path)
            app_state.rotate_move_reg_idx()
            self.refresh_display()
            logger.info(f"[REGISTER] スロット{app_state.move_reg_idx}に登録: {path}")
        else:
            messagebox.showwarning("注意", "ここはフォルダ登録用なのじゃ！ファイルを動かしたいなら下へ入れるのじゃ。")

    def _make_drop_func(self, idx):
        def drop_handler(event):
            try:
                files = self.tk.splitlist(event.data)
                count = 0
                for f in files:
                    p = os.path.normpath(f)
                    if os.path.isfile(p):
                        self.move_callback(p, app_state.move_dest_list[idx], refresh=False)
                        count += 1
                    elif os.path.isdir(p):
                        messagebox.showwarning("注意", f"フォルダは移動できないのじゃ: {p}")

                if count > 0:
                    if self.refresh_callback:
                        self.refresh_callback()
                    logger.info(f"[BATCH MOVE] {count}個のファイルを移動して画面を更新")
            except Exception as e:
                logger.error(f"ドロップ処理エラー: {e}", exc_info=True)
        return drop_handler


class FolderListWindow(tk.Toplevel):
    """フォルダ一覧ウィンドウ。移動先フォルダの登録・フォルダ間移動を担当する。"""

    def __init__(self, parent, on_move_registered=None):
        super().__init__(parent)
        self.on_move_registered = on_move_registered
        self.title("子データ窓 - フォルダ一覧")
        self.attributes("-topmost", True)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        tk.Button(btn_frame, text="↑ 上のフォルダへ", command=self._on_up_click).pack(fill=tk.X)

        frame = tk.Frame(self)
        frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
        self.lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.lb.yview)

        self.lb.bind("<Button-3>", self._on_right_click)
        self.lb.bind("<Double-Button-1>", self._on_double_click)

    def refresh(self, folders, files, current_folder):
        """フォルダ・ファイル一覧に基づいて表示内容を更新する。"""
        self.lb.delete(0, tk.END)
        try:
            current_name = os.path.basename(current_folder) or current_folder
            self.lb.insert(tk.END, f"({len(files)}) [現在] {current_name}")
        except Exception:
            self.lb.insert(tk.END, "(-) [現在] ???")

        for f in folders:
            try:
                sub_items = os.listdir(os.path.join(current_folder, f))
                count = len(GetGazoFiles(sub_items, os.path.join(current_folder, f)))
                self.lb.insert(tk.END, f"({count}) {f}")
            except Exception:
                self.lb.insert(tk.END, f"(-) {f}")

    def _on_up_click(self):
        app_state.set_current_folder(os.path.dirname(app_state.current_folder))

    def _on_right_click(self, event):
        """右クリックで移動先スロットに登録するコンテキストメニューを表示する。"""
        try:
            idx = self.lb.nearest(event.y)
            self.lb.selection_clear(0, tk.END)
            self.lb.selection_set(idx)
            self.lb.activate(idx)

            sel = self.lb.get(idx)
            current_folder = app_state.current_folder
            if idx == 0:
                target_path = current_folder
            else:
                if ") " in sel:
                    sel = sel.split(") ", 1)[1]
                target_path = os.path.join(current_folder, sel)

            if not os.path.isdir(target_path):
                return

            popup = tk.Menu(self, tearoff=0)

            def insert_reg():
                idx_reg = app_state.move_reg_idx
                app_state.set_move_destination(idx_reg, target_path)
                app_state.rotate_move_reg_idx()
                logger.info(f"[CONTEXT] スロット{idx_reg+1}に挿入登録: {target_path}")
                if self.on_move_registered:
                    self.on_move_registered()

            popup.add_command(label="登録を挿入", font=("MS Gothic", 9, "bold"), command=insert_reg)
            popup.add_separator()

            def make_reg_func(s_idx, p):
                def reg():
                    app_state.set_move_destination(s_idx, p)
                    logger.info(f"[CONTEXT] スロット{s_idx+1}に直接登録: {p}")
                    if self.on_move_registered:
                        self.on_move_registered()
                return reg

            for i in range(app_state.move_dest_count):
                cur_path = app_state.move_dest_list[i]
                if cur_path:
                    label_text = f"{i+1}: [{os.path.basename(cur_path)}]"
                else:
                    label_text = f"{i+1}: (未登録)"
                popup.add_command(label=label_text, command=make_reg_func(i, target_path))

            popup.tk_popup(event.x_root, event.y_root)
        except Exception as e:
            logger.error(f"右クリックエラー: {e}")

    def _on_double_click(self, event):
        try:
            idx = self.lb.curselection()[0]
            sel = self.lb.get(idx)
            current_folder = app_state.current_folder
            if idx == 0:
                app_state.set_current_folder(current_folder)
                return
            if ") " in sel:
                sel = sel.split(") ", 1)[1]
            app_state.set_current_folder(os.path.join(current_folder, sel))
        except Exception:
            pass


class TagEditorWindow(tk.Toplevel):
    """常に表示するタグ編集・付与窓。連続入力に向いたUIにする。"""

    def __init__(self, parent, gazo_control):
        super().__init__(parent)
        self.gazo_control = gazo_control
        self.title("タグ編集")
        self.attributes("-topmost", True)
        self.geometry("380x260")

        tk.Label(self, text="対象画像:", anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        self.target_var = tk.StringVar(value="未選択")
        tk.Label(self, textvariable=self.target_var, wraplength=340, justify="left", anchor="w").pack(fill="x", padx=10)

        tk.Label(self, text="タグ（; 区切り）:", anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        self.tag_var = tk.StringVar(value="")
        self.entry = tk.Entry(self, textvariable=self.tag_var, width=40)
        self.entry.pack(fill="x", padx=10)
        self.entry.focus_set()

        self.status_var = tk.StringVar(value="保存は Enter または 下のボタン")
        tk.Label(self, textvariable=self.status_var, fg="#555555", anchor="w", font=("MS Gothic", 8)).pack(fill="x", padx=10, pady=(4, 0))

        quick_frame = tk.Frame(self)
        quick_frame.pack(fill="x", padx=10, pady=(6, 0))
        tk.Label(quick_frame, text="よく使うタグ:", anchor="w").pack(fill="x")
        tag_dict = self.gazo_control.tag_dict if hasattr(self.gazo_control, 'tag_dict') else {}
        quick_tags = sorted(collect_all_tags(tag_dict))[:12]
        quick_inner = tk.Frame(quick_frame)
        quick_inner.pack(fill="x")
        for tag_name in quick_tags:
            tk.Button(quick_inner, text=tag_name, font=("MS Gothic", 8), command=lambda t=tag_name: self._append_tag(t), padx=6, pady=2).pack(side=tk.LEFT, padx=2, pady=2)

        btn_frame = tk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=10)
        tk.Button(btn_frame, text="保存 (Enter)", command=self._save_current_tag).pack(side=tk.LEFT, padx=(0, 6))
        tk.Button(btn_frame, text="クリア", command=self._clear_current_tag).pack(side=tk.LEFT)

        self.bind("<Return>", lambda event: self._save_current_tag())
        self.bind("<Escape>", lambda event: self._clear_current_tag())

    def set_target(self, file_path, image_hash=None):
        """フォーカス中の画像をタグ編集対象として設定し、表示を更新する。"""
        tag_filter_state.set_active_target(file_path, image_hash)
        if file_path is None:
            self.target_var.set("未選択")
            self.tag_var.set("")
            return
        self.target_var.set(os.path.basename(file_path))
        tag_dict = self.gazo_control.tag_dict if hasattr(self.gazo_control, 'tag_dict') else {}
        data = tag_dict.get(image_hash or calculate_file_hash(file_path), {})
        tag_text = data.get('tag', '') if isinstance(data, dict) else ''
        self.tag_var.set(tag_text)

    def _append_tag(self, tag_name):
        current = (self.tag_var.get() or "").strip()
        parts = [p.strip() for p in current.split(";") if p.strip()] if current else []
        if tag_name not in parts:
            parts.append(tag_name)
        self.tag_var.set("; ".join(parts))
        self.entry.focus_set()
        self.entry.icursor(len(self.tag_var.get()))

    def _save_current_tag(self):
        file_path = tag_filter_state.active_target.get("file_path")
        if not file_path or not os.path.exists(file_path):
            self.status_var.set("対象画像が選択されていません")
            messagebox.showwarning("タグ編集", "対象画像が選択されていません")
            return
        image_hash = tag_filter_state.active_target.get("image_hash") or calculate_file_hash(file_path)
        if not image_hash:
            self.status_var.set("ハッシュ計算に失敗しました")
            messagebox.showerror("エラー", "画像ハッシュの計算に失敗しました")
            return

        value = (self.tag_var.get() or "").strip()
        normalized = "; ".join(p.strip() for p in value.split(";") if p.strip()) if value else ""
        tag_dict = self.gazo_control.tag_dict
        if image_hash not in tag_dict:
            tag_dict[image_hash] = {"tag": "", "hint": os.path.basename(file_path), "rating": None}
        tag_dict[image_hash]["tag"] = normalized
        tag_dict[image_hash]["hint"] = os.path.basename(file_path)
        save_tags(tag_dict)
        if hasattr(self.gazo_control, 'set_image_tag'):
            try:
                for open_win in self.gazo_control.open_windows.values():
                    if getattr(open_win, '_image_hash', None) == image_hash:
                        self.gazo_control.set_image_tag(open_win, image_hash)
                        break
            except Exception:
                pass

        self.status_var.set(f"保存しました: {normalized or '未設定'}")
        self.tag_var.set("")
        self.entry.focus_set()

        if app_state.continuous_tagging_mode:
            next_path = self._find_next_untagged_image(file_path)
            if next_path:
                self.gazo_control.Drawing(next_path)
                self.status_var.set(f"次の未タグ画像: {os.path.basename(next_path)}")
                self.entry.focus_set()
            else:
                self.status_var.set("未タグの画像はもうありません")

    def _find_next_untagged_image(self, current_file_path):
        """現在フォルダ内で、指定ファイルより後(1周分)にある未タグ画像のパスを返す。"""
        current_folder = app_state.current_folder
        try:
            names = sorted(GetGazoFiles(os.listdir(current_folder), current_folder))
        except Exception:
            return None
        full_paths = [os.path.join(current_folder, name) for name in names]
        if not full_paths:
            return None

        normalized_current = os.path.normcase(os.path.abspath(current_file_path))
        try:
            current_index = [os.path.normcase(os.path.abspath(p)) for p in full_paths].index(normalized_current)
        except ValueError:
            current_index = -1

        tag_dict = self.gazo_control.tag_dict if hasattr(self.gazo_control, 'tag_dict') else {}
        ordered = full_paths[current_index + 1:] + full_paths[:current_index + 1]
        for path in ordered:
            if path == current_file_path:
                continue
            try:
                image_hash = calculate_file_hash(path)
            except Exception:
                continue
            entry = tag_dict.get(image_hash)
            if entry is None or not parse_tag_text(entry.get("tag", "")):
                return path
        return None

    def _clear_current_tag(self):
        self.tag_var.set("")
        self.status_var.set("入力をクリアしました")
        self.entry.focus_set()


class TagListWindow(tk.Toplevel):
    """タグ一覧ウィンドウ。タグごとのファイル件数表示と絞り込みを行う。"""

    def __init__(self, parent, gazo_control, on_filter_applied=None):
        super().__init__(parent)
        self.gazo_control = gazo_control
        self.on_filter_applied = on_filter_applied
        self.title("タグ一覧")
        self.attributes("-topmost", True)
        self.geometry("280x360")

        mode_frame = tk.Frame(self)
        mode_frame.pack(fill=tk.X, padx=8, pady=(8, 4))
        tk.Label(mode_frame, text="検索方式:").pack(side=tk.LEFT)
        self.mode_var = tk.StringVar(value=tag_filter_state.mode)
        tk.Radiobutton(mode_frame, text="AND", variable=self.mode_var, value="and", command=self._on_mode_change).pack(side=tk.LEFT)
        tk.Radiobutton(mode_frame, text="OR", variable=self.mode_var, value="or", command=self._on_mode_change).pack(side=tk.LEFT)
        tk.Button(mode_frame, text="クリア", command=self._on_clear).pack(side=tk.RIGHT)

        tk.Label(self, text="タグ一覧", font=("Helvetica", "10", "bold")).pack(pady=(0, 4))

        list_frame = tk.Frame(self)
        list_frame.pack(expand=True, fill=tk.BOTH, padx=8, pady=8)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tag_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set)
        self.tag_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.config(command=self.tag_listbox.yview)

        self.tag_listbox.bind("<Double-Button-1>", self._on_tag_double_click)
        self.refresh_tag_list()

    def refresh_tag_list(self):
        self.tag_listbox.delete(0, tk.END)
        tag_dict = self.gazo_control.tag_dict if hasattr(self.gazo_control, 'tag_dict') else {}
        tags = collect_all_tags(tag_dict)
        current_folder = app_state.current_folder
        file_names = [
            os.path.join(current_folder, name)
            for name in os.listdir(current_folder)
            if os.path.isfile(os.path.join(current_folder, name))
        ]
        path_to_hash = {}
        for file_path in file_names:
            try:
                path_to_hash[file_path] = calculate_file_hash(file_path)
            except Exception:
                continue

        for tag_name in tags:
            matches = find_files_for_tag(file_names, path_to_hash, tag_dict, tag_name)
            self.tag_listbox.insert(tk.END, f"{tag_name} ({len(matches)})")

    def _on_mode_change(self):
        tag_filter_state.set_mode(self.mode_var.get())
        if self.on_filter_applied:
            self.on_filter_applied()

    def _on_clear(self):
        tag_filter_state.clear_filter()
        if self.on_filter_applied:
            self.on_filter_applied()

    def _on_tag_double_click(self, event):
        try:
            idx = self.tag_listbox.curselection()
            if not idx:
                return
            selected_text = self.tag_listbox.get(idx[0])
            tag_name = selected_text.rsplit(" (", 1)[0]

            tag_filter_state.set_active_filter([tag_name])
            if self.on_filter_applied:
                self.on_filter_applied()

            messagebox.showinfo("タグ検索", f"タグ '{tag_name}' を適用して一覧を更新しました")
        except Exception as e:
            logger.warning(f"タグ詳細表示エラー: {e}")


class ShortcutKeyBarWindow(tk.Toplevel):
    """常時表示するショートカットキー一覧バー（画面下部ドッキング）。"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("ショートカットキー")
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self.slot_buttons = []
        bar = tk.Frame(self, bg="#202020")
        bar.pack(fill=tk.BOTH, expand=True)
        for i in range(SHORTCUT_TAG_KEY_COUNT):
            btn = tk.Button(bar, font=("MS Gothic", 9), command=lambda idx=i: self._edit_slot(idx))
            btn.grid(row=0, column=i, sticky="nsew", padx=1, pady=1)
            bar.columnconfigure(i, weight=1)
            self.slot_buttons.append(btn)

        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        w, h = int(ws * 0.9), 60
        x = (ws - w) // 2
        y = hs - h - 60
        self.geometry(f"{w}x{h}+{x}+{y}")
        self._refresh_labels()

    def _edit_slot(self, idx):
        current = app_state.shortcut_tags[idx]
        result = simpledialog.askstring(
            "ショートカット設定", f"キー {idx + 1} に割り当てるタグ名:",
            initialvalue=current, parent=self,
        )
        if result is None:
            return
        app_state.shortcut_tags[idx] = result.strip()
        cfg = app_state.to_dict()
        save_config(cfg["last_folder"], cfg["geometries"], cfg["settings"])
        self._refresh_labels()

    def _refresh_labels(self):
        for i, btn in enumerate(self.slot_buttons):
            tag = app_state.shortcut_tags[i]
            btn.config(text=f"{i + 1}: {tag or '(未設定)'}")

    def show(self):
        self.deiconify()
        self.lift()
