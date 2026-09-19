'''
作成日: 2025年09月29日
修正日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools メインアプリケーション (UI)
'''
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from PIL import ImageTk, Image
from tkinterdnd2 import *
import shutil
import psutil                 # CPU／メモリ取得用
import threading              # バックグラウンドスレッド用
import time                   # スリープ用

# ロギングの初期化
from lib.GazoToolsLogger import setup_logging, get_logger, record_error
setup_logging(debug_mode=False)  # False=本番モード, True=デバッグモード
logger = get_logger(__name__)

# ロジックモジュールのインポート
from GazoToolsLogic import (
    load_config, save_config, HakoData, GazoPicture, calculate_file_hash,
    VectorBatchProcessor, save_ratings, save_tags, calculate_window_layout,
    build_thumbnail_photo,
)
from lib.GazoToolsBasicLib import tkConvertWinSize, blend_color
from lib.GazoToolsLib import GetKoFolder, GetGazoFiles
from lib.GazoToolsState import get_app_state
from lib.GazoToolsImageCache import ImageCache, TileImageLoader
from lib.GazoToolsGUIEnvironment import ensure_gui_environment
from lib.GazoToolsTagFilter import (
    collect_all_tags,
    filter_file_names_by_tags,
    parse_tag_text,
    get_tag_filter_state,
)
from lib.config_defaults import (
    calculate_folder_window_width, calculate_folder_window_height,
    calculate_file_window_width, calculate_file_window_height,
    WINDOW_SPACING, SCREEN_MARGIN, COLOR_CPU_LOW, COLOR_CPU_HIGH,
    MOVE_DESTINATION_SLOTS, MOVE_DESTINATION_MIN,
    MOVE_DESTINATION_OPTIONS, SS_INTERVAL_OPTIONS,
    MIN_AI_THRESHOLD, MAX_AI_THRESHOLD, DEFAULT_AI_THRESHOLD,
    RATING_SIZE_PRESETS, RATING_POSITION_PRESETS
)
from lib.GazoToolsGUI import (
    SplashWindow, SimilarityMoveDialog, VectorWindow, ThumbnailPanelWindow,
    MoveDestinationArea, FolderListWindow, TagEditorWindow, TagListWindow,
    ShortcutKeyBarWindow,
)

# --- アプリケーション状態の初期化 ---
app_state = get_app_state()
tag_filter_state = get_tag_filter_state()


def update_active_tag_target(file_path, image_hash=None):
    """現在フォーカス中の画像をタグ編集窓の対象に設定する。
    互換エントリポイント: GazoPicture.Drawing が sys.modules 経由で呼ぶ。"""
    tag_filter_state.set_active_target(file_path, image_hash)
    if 'tag_edit_window' in globals() and tag_edit_window is not None:
        try:
            tag_edit_window.set_target(file_path, image_hash)
        except Exception:
            pass


def refresh_file_listbox_with_tag_filter(file_names):
    """現在のタグフィルタを適用して file_listbox を更新する。"""
    if 'file_listbox' not in globals():
        return

    file_listbox.delete(0, tk.END)
    if not tag_filter_state.active_filter:
        for name in file_names:
            file_listbox.insert(tk.END, name)
        return

    full_paths = [os.path.join(DEFOLDER, name) for name in file_names]
    path_hash_map = {}
    for full_path in full_paths:
        try:
            if os.path.exists(full_path):
                path_hash_map[full_path] = calculate_file_hash(full_path)
        except Exception:
            continue

    filtered = filter_file_names_by_tags(
        full_paths,
        path_hash_map,
        GazoControl.tag_dict if hasattr(GazoControl, 'tag_dict') else {},
        tag_filter_state.active_filter,
        mode=tag_filter_state.mode,
    )
    for full_path in filtered:
        file_listbox.insert(tk.END, os.path.basename(full_path))


# --- タイトル（スプラッシュ画面）表示：最優先なのじゃ ---
try:
    ensure_gui_environment()
    koRoot = TkinterDnD.Tk()
    koRoot.withdraw() # メインウィンドウを隠す
    splash = SplashWindow(koRoot)
except RuntimeError as e:
    print(f"[GazoTools GUI起動エラー] {e}", file=sys.stderr)
    raise SystemExit(1)

def close_splash():
    try:
        splash.close()
        koRoot.deiconify() # メインウィンドウを表示
        if app_state.topmost:
            koRoot.attributes("-topmost", True)
    except:
        pass

# 最低保証時間のタイマー (1.5秒)
koRoot.after(1500, close_splash)

# --- 画像キャッシュの初期化 ---
try:
    image_cache = ImageCache.get_instance(max_size_mb=256)
    tile_loader = TileImageLoader(tile_size=(200, 200), cache_mb=256)
    logger.info("ImageCache と TileImageLoader を初期化しました")
except Exception as e:
    logger.warning(f"ImageCache 初期化エラー: {e}")
    image_cache = None
    tile_loader = None

# --- 設定の読み込みと初期化 ---
try:
    CONFIG_DATA = load_config()
    logger.info(f"設定ファイル読み込み成功: {CONFIG_DATA.get('last_folder')}")
    # AppState に設定を復元
    app_state.from_dict(CONFIG_DATA)
except Exception as e:
    logger.error(f"設定ファイル読み込み失敗: {e}")
    messagebox.showerror("エラー", f"設定ファイルの読み込みに失敗しました:\n{e}")
    CONFIG_DATA = {
        "last_folder": os.getcwd(),
        "geometries": {},
        "settings": {}
    }
    app_state.current_folder = os.getcwd()

# ショートカット用の変数（後方互換性）
DEFOLDER = app_state.current_folder
SAVED_GEOS = app_state.window_geometries
SAVED_SETTINGS = {
    "random_pos": app_state.random_pos,
    "random_size": app_state.random_size,
    "topmost": app_state.topmost,
    "show_folder": app_state.show_folder_window,
    "show_file": app_state.show_file_window,
    "ss_mode": app_state.ss_mode,
    "ss_interval": app_state.ss_interval,
    "ss_ai_mode": app_state.ss_ai_mode,
    "ss_ai_threshold": app_state.ss_ai_threshold,
}

# --- 共通のUI更新処理 ---
def on_app_state_changed(event_name, data):
    """AppState の変更に応じて UI を更新するコールバック
    
    Args:
        event_name (str): イベント名
        data (dict): イベントデータ
    """
    try:
        if event_name == "folder_changed":
            # フォルダ変更時の UI 更新
            refresh_ui(data["path"])
        
        elif event_name == "move_destination_changed":
            # 移動先変更時の表示更新
            move_area.refresh_display()

        elif event_name == "move_reg_idx_changed":
            # 登録先インデックス変更時の表示更新
            move_area.refresh_display()

        elif event_name == "move_dest_count_changed":
            # 移動先個数変更時
            move_area.rebuild()
        
        elif event_name == "show_folder_window_changed":
            # フォルダウィンドウ表示切り替え
            if data["show"]:
                folder_win.deiconify()
            else:
                folder_win.withdraw()
        
        elif event_name == "show_file_window_changed":
            # ファイルウィンドウ表示切り替え
            if data["show"]:
                file_win.deiconify()
            else:
                file_win.withdraw()
        
        elif event_name == "ss_mode_changed":
            # スクリーンセーバーモード切り替え
            toggle_ss()
        
        elif event_name == "cpu_colors_changed":
            # CPU色設定変更
            logger.debug(f"CPU色が変更されました")
        
        elif event_name == "ss_include_subfolders_changed":
            # 子フォルダ設定変更時
            refresh_ui(DEFOLDER)
    
    except Exception as e:
        logger.error(f"UI更新コールバックエラー ({event_name}): {e}", exc_info=True)

# コールバックを登録
app_state.register_callback(on_app_state_changed)

def refresh_ui(new_path):
    """パスに基づいてUIを全更新するのじゃ。のじゃ。"""
    global DEFOLDER
    if not os.path.exists(new_path):
        logger.warning(f"パスが存在しません: {new_path}")
        return
    
    DEFOLDER = new_path
    
    try:
        all_items = os.listdir(DEFOLDER)
        folders = GetKoFolder(all_items, DEFOLDER)
        files = GetGazoFiles(all_items, DEFOLDER)
        logger.info(f"UI更新: {DEFOLDER} (フォルダ:{len(folders)}件, ファイル:{len(files)}件)")
    except Exception as e:
        logger.error(f"再読み込みエラー: {e}", exc_info=True)
        messagebox.showerror("エラー", f"フォルダの読み込みに失敗しました:\n{e}")
        return

    # AppState に反映
    app_state.set_current_files(files)
    app_state.set_current_folders(folders)
    
    data_manager.SetGazoFiles(files, DEFOLDER, include_subfolders=app_state.ss_include_subfolders)
    GazoControl.SetFolder(DEFOLDER)
    
    koRoot.title("画像tools - " + DEFOLDER)
    save_config(DEFOLDER)
    
    if 'folder_win' in globals():
        folder_win.refresh(folders, files, DEFOLDER)

    refresh_file_listbox_with_tag_filter(files)

    if 'thumbnail_windows' in globals():
        thumbnail_files = [os.path.join(DEFOLDER, name) for name in files]
        for window in list(thumbnail_windows):
            try:
                if window.winfo_exists():
                    window.set_files(thumbnail_files)
                else:
                    thumbnail_windows.remove(window)
            except tk.TclError:
                if window in thumbnail_windows:
                    thumbnail_windows.remove(window)

    if 'folder_win' in globals() and 'file_win' in globals():
        adjust_window_layouts(folders, files)

def adjust_window_layouts(folders, files):
    """ウィンドウ配置の自動調整なのじゃ。のじゃ。"""
    root_x, root_y = koRoot.winfo_x(), koRoot.winfo_y()
    root_w = koRoot.winfo_width()
    screen_w = koRoot.winfo_screenwidth()

    # Logicに計算を依頼
    f_geo, g_geo = calculate_window_layout(
        root_x, root_y, root_w, screen_w, 
        folders, files, DEFOLDER
    )
    
    folder_win.geometry(f_geo)
    file_win.geometry(g_geo)


def add_tag_to_selected_file(file_path):
    """対象ファイルにタグを追加・編集する。"""
    if not file_path or not os.path.exists(file_path):
        messagebox.showwarning("タグ付け", "対象ファイルが見つかりません")
        return

    try:
        image_hash = calculate_file_hash(file_path)
    except Exception as e:
        messagebox.showerror("エラー", f"ハッシュ計算に失敗しました: {e}")
        return

    current_tags = ""
    data = GazoControl.tag_dict.get(image_hash, {}) if hasattr(GazoControl, 'tag_dict') else {}
    if isinstance(data, dict):
        current_tags = data.get("tag", "")

    new_tags = simpledialog.askstring(
        "タグ編集",
        f"{os.path.basename(file_path)} のタグを入力してください（; 区切り）:",
        initialvalue=current_tags,
        parent=koRoot,
    )
    if new_tags is None:
        return

    tag_text = new_tags.strip()
    if image_hash not in GazoControl.tag_dict:
        GazoControl.tag_dict[image_hash] = {"tag": "", "hint": os.path.basename(file_path), "rating": None}
    GazoControl.tag_dict[image_hash]["tag"] = tag_text
    GazoControl.tag_dict[image_hash]["hint"] = os.path.basename(file_path)
    save_tags(GazoControl.tag_dict)
    messagebox.showinfo("タグ更新", f"タグを保存しました: {tag_text or '未設定'}")


def create_file_list_window(parent, files, draw_func):
    win = tk.Toplevel(parent)
    win.title("子絵窓 - ファイル一覧")
    win.attributes("-topmost", True)
    tk.Label(win, text="画像ファイル一覧 (Wクリックで表示)", font=("Helvetica", "9", "bold")).pack(pady=5)

    # タグによる絞り込みのための選択状態
    selected_tags = []
    tag_var_map = {}

    tag_frame = tk.Frame(win)
    tag_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
    tag_label = tk.Label(tag_frame, text="タグフィルタ:")
    tag_label.pack(anchor="w")
    tag_canvas = tk.Canvas(tag_frame, height=40, highlightthickness=0)
    tag_canvas.pack(fill=tk.X)
    tag_inner = tk.Frame(tag_canvas)
    tag_canvas.create_window((0, 0), window=tag_inner, anchor="nw")

    def rebuild_tag_buttons():
        for widget in tag_inner.winfo_children():
            widget.destroy()
        tag_var_map.clear()

        all_tags = collect_all_tags(GazoControl.tag_dict if hasattr(GazoControl, 'tag_dict') else {})
        for tag_name in all_tags:
            var = tk.BooleanVar(value=False)
            tag_var_map[tag_name] = var
            btn = tk.Checkbutton(tag_inner, text=tag_name, variable=var, command=apply_tag_filter)
            btn.pack(anchor="w")

    def apply_tag_filter():
        active = [tag for tag, var in tag_var_map.items() if var.get()]
        tag_filter_state.set_active_filter(active)
        full_paths = [os.path.join(DEFOLDER, name) for name in files]
        path_hash_map = {}
        for full_path in full_paths:
            if os.path.exists(full_path):
                try:
                    path_hash_map[full_path] = calculate_file_hash(full_path)
                except Exception:
                    continue

        filtered = filter_file_names_by_tags(
            full_paths,
            path_hash_map,
            GazoControl.tag_dict if hasattr(GazoControl, 'tag_dict') else {},
            active,
            mode=tag_filter_state.mode,
        )
        lb.delete(0, tk.END)
        for full_path in filtered:
            lb.insert(tk.END, os.path.basename(full_path))

        refresh_file_listbox_with_tag_filter(files)

    def refresh_tag_panel():
        rebuild_tag_buttons()
        apply_tag_filter()

    rebuild_tag_buttons()

    frame = tk.Frame(win)
    frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    lb = tk.Listbox(frame, yscrollcommand=scrollbar.set)
    for f in files: lb.insert(tk.END, f)
    lb.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
    scrollbar.config(command=lb.yview)

    preview_win = tk.Toplevel(parent)
    preview_win.title("画像プレビュー")
    preview_win.attributes("-topmost", True)
    preview_win.transient(win)
    preview_win.geometry("220x220")
    preview_label = tk.Label(preview_win, text="選択中のファイル\nプレビュー", compound="center", justify="center", width=20, height=10)
    preview_label.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    preview_photo = None

    def update_preview_for_selected(event=None):
        nonlocal preview_photo
        try:
            idx = lb.curselection()
            if not idx:
                preview_label.configure(text="選択中のファイル\nプレビュー", image="")
                preview_photo = None
                return
            selected = lb.get(idx[0])
            if not selected:
                preview_label.configure(text="プレビューなし", image="")
                preview_photo = None
                return
            full_path = os.path.join(DEFOLDER, selected)
            if not os.path.exists(full_path):
                preview_label.configure(text="ファイルなし", image="")
                preview_photo = None
                return
            new_photo = build_thumbnail_photo(full_path, size=(180, 180), master=preview_label)
            if new_photo is None:
                preview_label.configure(text="プレビュー不可\n画像形式ではありません", image="")
                preview_photo = None
                return
            preview_label.configure(image=new_photo, text="")
            preview_label.image = new_photo
            preview_photo = new_photo
        except Exception as exc:
            preview_label.configure(text="プレビュー失敗", image="")
            preview_photo = None
            logger.warning(f"ファイル一覧プレビュー更新失敗: {exc}")

    lb.bind("<<ListboxSelect>>", update_preview_for_selected)
    update_preview_for_selected()

    # ダブルクリックで表示
    def on_double_click(event):
        try:
            idx = lb.curselection()
            if not idx:
                return
            selected = lb.get(idx[0])
            if not selected:
                return
            draw_func(selected)
        except: pass
    lb.bind("<Double-Button-1>", on_double_click)

    # 右クリックメニュー
    def on_right_click(event):
        try:
            # クリック位置を選択状態にする
            idx = lb.nearest(event.y)
            lb.selection_clear(0, tk.END)
            lb.selection_set(idx)
            lb.activate(idx)
            filename = lb.get(idx)
            full_path = os.path.join(DEFOLDER, filename)

            popup = tk.Menu(win, tearoff=0)

            # 名前変更
            def rename_file():
                root, ext = os.path.splitext(filename)
                new_root = simpledialog.askstring("名前変更", f"新しいファイル名を入力してほしいのじゃ（{ext}は自動付与）:", initialvalue=root, parent=win)
                if new_root and new_root != root:
                    try:
                        new_name = new_root + ext
                        new_path = os.path.join(DEFOLDER, new_name)
                        os.rename(full_path, new_path)
                        app_state.set_current_folder(DEFOLDER)
                        print(f"[RENAME] {filename} -> {new_name}")
                    except Exception as e:
                        messagebox.showerror("エラー", f"名前変更に失敗したのじゃ: {e}")
            
            popup.add_command(label="名前変更", command=rename_file)

            # 登録フォルダに移動
            move_menu = tk.Menu(popup, tearoff=0)
            popup.add_cascade(label="登録フォルダに移動", menu=move_menu)
            
            def make_move_func(dest):
                return lambda: execute_move(full_path, dest)

            for i in range(app_state.move_dest_count):
                dest = app_state.move_dest_list[i]
                if dest:
                    move_menu.add_command(label=f"{i+1}: {os.path.basename(dest)}", command=make_move_func(dest))
                else:
                    move_menu.add_command(label=f"{i+1}: (未登録)", state="disabled")

            popup.add_command(label="タグ追加/編集", command=lambda: add_tag_to_selected_file(full_path))

            # 類似画像検索 (Smart Move UI再利用)
            def search_similar():
                try:
                    target_dest = app_state.move_dest_list[app_state.move_reg_idx] if app_state.move_dest_list[app_state.move_reg_idx] else ""
                    # move_callbackはexecute_moveでOK
                    # refresh_callbackはこのウィンドウを更新する関数があればそれを渡すが、
                    # ファイルリストは自動更新されない造りっぽいので、refresh= lambda p: draw_func(None) ?
                    # draw_funcは画像を表示する関数なので違う。
                    # リスト更新は... ファイルリストウィンドウ再生成？
                    # まぁ移動機能メインじゃないのでNoneでも良いが、移動したら消えてほしい。
                    
                    # 簡易的に None でいく（移動時は手動でウィンドウ閉じて開き直してもらうか、
                    # SmartMoveDialogが勝手にやってくれるのを期待）
                    # execute_move は成功時に move_dest_count を更新したりするが、UI更新は...
                    
                    dialog = SimilarityMoveDialog(win, full_path, target_dest, DEFOLDER, execute_move, refresh_callback=None)
                except Exception as e:
                    messagebox.showerror("エラー", f"類似画像検索起動エラー: {e}")

            popup.add_command(label="類似画像を探す", command=search_similar)


            popup.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"ファイル一覧右クリックエラー: {e}")

    lb.bind("<Button-3>", on_right_click)

    return win, lb

# --- メイン処理 ---
# (koRootとスプラッシュ表示は最上部に移動したのじゃ)

koRoot.attributes("-topmost", True)
koRoot.geometry(tkConvertWinSize(list([200, 150, 50, 100])))
koRoot.title("画像tools")

# ★ ここからステータスラベルを追加 ★
status_label = tk.Label(koRoot, text="CPU: 0%  MEM: 0 MB", anchor="e")
status_label.pack(fill=tk.X, side=tk.BOTTOM)

# 状態管理 (SS mode)
ss_mode = tk.BooleanVar(value=app_state.ss_mode)
ss_interval = tk.IntVar(value=app_state.ss_interval)
ss_ai_mode = tk.BooleanVar(value=app_state.ss_ai_mode)
ss_ai_threshold = tk.DoubleVar(value=app_state.ss_ai_threshold)
ss_include_subfolders = tk.BooleanVar(value=app_state.ss_include_subfolders)
ss_after_id = None

def auto_slideshow():
    global ss_after_id
    if ss_mode.get():
        # Logicに次の画像を決定してもらう
        next_image = decide_next_image(
            data_manager, 
            ss_ai_mode.get(), 
            ss_ai_threshold.get()
        )

        if not next_image:
            logger.warning("自動スライド: 次の画像が見つからないため表示をスキップします")
            return

        GazoControl.Drawing(next_image)
        ms = max(1000, ss_interval.get() * 1000)
        ss_after_id = koRoot.after(ms, auto_slideshow)
    else:
        ss_after_id = None

def toggle_ss():
    global ss_after_id
    if ss_after_id:
        koRoot.after_cancel(ss_after_id)
    if ss_mode.get():
        auto_slideshow()

def on_closing_main():
    try:
        # ウィンドウジオメトリを保存
        app_state.set_window_geometry("main", koRoot.winfo_geometry())
        app_state.set_window_geometry("folder", folder_win.winfo_geometry())
        app_state.set_window_geometry("file", file_win.winfo_geometry())
        if 'thumbnail_window' in globals() and thumbnail_window.winfo_exists():
            app_state.set_window_geometry("thumbnail", thumbnail_window.geometry())
        
        # UI 設定を保存
        app_state.set_random_pos(GazoControl.random_pos.get())
        app_state.set_random_size(GazoControl.random_size.get())
        app_state.set_topmost(koRoot.attributes("-topmost"))
        app_state.set_show_folder_window(show_folder_win.get())
        app_state.set_show_file_window(show_file_win.get())
        app_state.show_rating_window = show_rating_win.get()
        app_state.show_info_window = show_info_win.get()
        app_state.show_thumbnail_window = show_thumbnail_win.get()
        if thumbnail_windows:
            primary_thumbnail = thumbnail_windows[0]
            app_state.thumbnail_rows = primary_thumbnail.rows_var.get()
            app_state.thumbnail_columns = primary_thumbnail.columns_var.get()
            app_state.thumbnail_width = primary_thumbnail.width_var.get()
            app_state.thumbnail_height = primary_thumbnail.height_var.get()
        app_state.vector_display["enabled"] = show_vector_win.get()
        app_state.set_ss_mode(ss_mode.get())
        app_state.set_ss_interval(ss_interval.get())
        app_state.set_ss_ai_mode(ss_ai_mode.get())
        app_state.set_ss_ai_threshold(ss_ai_threshold.get())
        app_state.set_ss_include_subfolders(ss_include_subfolders.get())
        
        # AppState を設定ファイルに保存
        config_to_save = app_state.to_dict()
        save_config(config_to_save["last_folder"], config_to_save["geometries"], config_to_save["settings"])

        # 評価データを保存
        save_ratings(GazoControl.rating_dict)
        # 画像-評価マッピングを保存（タグデータに追加）
        for image_hash, rating_name in GazoControl.image_rating_map.items():
            if image_hash in GazoControl.tag_dict:
                GazoControl.tag_dict[image_hash]["assigned_rating"] = rating_name
            else:
                GazoControl.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None, "assigned_rating": rating_name}
        save_tags(GazoControl.tag_dict)

        logger.info("アプリケーション終了: 設定と評価データを保存しました")
    except Exception as e:
        logger.error(f"終了処理エラー: {e}", exc_info=True)
    
    koRoot.destroy()
    sys.exit()

def safe_select_folder():
    wins = [koRoot, folder_win, file_win]
    if 'thumbnail_windows' in globals():
        wins.extend(thumbnail_windows)
    prev_states = [w.attributes("-topmost") for w in wins]
    for w in wins: w.attributes("-topmost", False)
    path = filedialog.askdirectory(title="画像フォルダを選択してください")
    for i, w in enumerate(wins): w.attributes("-topmost", prev_states[i])
    return path

def set_all_topmost(enabled):
    """メイン・サブ・画像ウィンドウ全体の最前面設定をまとめて切り替える。"""
    wins = [koRoot, folder_win, file_win]
    if 'thumbnail_windows' in globals():
        wins.extend(thumbnail_windows)
    wins.extend(list(GazoControl.open_windows.values()))
    wins = list(dict.fromkeys([w for w in wins if w and w.winfo_exists()]))
    for w in wins:
        try:
            w.attributes("-topmost", bool(enabled))
        except Exception:
            pass
    app_state.topmost = bool(enabled)
    return bool(enabled)


def disable_all_topmost():
    show_topmost_win.set(False)
    set_all_topmost(False)
    GazoControl.disable_all_topmost()


def enable_all_topmost():
    show_topmost_win.set(True)
    set_all_topmost(True)


# 実体生成
data_manager = HakoData(DEFOLDER)
GazoControl = GazoPicture(koRoot, DEFOLDER)
GazoControl.random_pos.set(SAVED_SETTINGS.get("random_pos", False))
GazoControl.random_size.set(SAVED_SETTINGS.get("random_size", False))
koRoot.attributes("-topmost", SAVED_SETTINGS.get("topmost", True))

# --- リソース表示設定 (ユーザー設定) ---
# 背景色のグラデーション用設定変数 (デフォルトは config_defaults から)
cpu_low_color = tk.StringVar(value=SAVED_SETTINGS.get("cpu_low_color", COLOR_CPU_LOW))
cpu_high_color = tk.StringVar(value=SAVED_SETTINGS.get("cpu_high_color", COLOR_CPU_HIGH))

def set_cpu_low_color():
    val = simpledialog.askstring("リソース表示設定", "CPU低負荷時の背景色 (hex) を入力してください:", initialvalue=cpu_low_color.get())
    if val:
        cpu_low_color.set(val)
        # 設定保存は on_closing_main で行われる

def set_cpu_high_color():
    val = simpledialog.askstring("リソース表示設定", "CPU高負荷時の背景色 (hex) を入力してください:", initialvalue=cpu_high_color.get())
    if val:
        cpu_high_color.set(val)

# カラーブレンド関数は Logic に移動したので削除


# ★ ここからリソース監視スレッドを起動 ★
# ★ ここからリソース監視スレッドを起動 ★
def _update_resource_usage():
    while True:
        try:
            cpu = psutil.cpu_percent(interval=1)          # 1 秒ごとに測定
            mem = psutil.Process().memory_info().rss // (1024 * 1024)  # MB 単位
            
            # メインスレッドでUI更新を行うためのクロージャ
            def update_ui():
                try:
                    # CPU 使用率に応じて背景色をブレンド
                    ratio = min(cpu / 100.0, 1.0)
                    bg = blend_color(cpu_low_color.get(), cpu_high_color.get(), ratio)
                    status_label.config(text=f"CPU: {cpu}%  MEM: {mem} MB", bg=bg)
                except Exception:
                    pass # アプリ終了時などにエラーになるのを防ぐ

            # メインスレッドにスケジュール
            if koRoot.winfo_exists():
                koRoot.after(0, update_ui)
            else:
                break # ウィンドウがなくなったら終了

        except Exception:
            break

threading.Thread(target=_update_resource_usage, daemon=True).start()
# ★ ここまで ★

# --- メニューに設定項目を追加 ---
menubar = tk.Menu(koRoot)
koRoot.config(menu=menubar)
config_menu = tk.Menu(menubar, tearoff=0) 

# 既存の config_menu 定義の直後に以下を追加
resource_sub = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="リソース表示設定", menu=resource_sub)
resource_sub.add_command(label="CPU低負荷時の色設定", command=set_cpu_low_color)
resource_sub.add_command(label="CPU高負荷時の色設定", command=set_cpu_high_color)

# スプラッシュ設定
splash_sub = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="起動画面設定", menu=splash_sub)
splash_tips_var = tk.BooleanVar(value=app_state.show_splash_tips)
def on_splash_tips_change():
    app_state.set_show_splash_tips(splash_tips_var.get())
    # 設定保存
    cfg = app_state.to_dict()
    save_config(cfg["last_folder"], cfg["geometries"], cfg["settings"])
splash_sub.add_checkbutton(label="起動時に豆知識(Tips)を表示", variable=splash_tips_var, command=on_splash_tips_change)

# ベクトル表示設定ダイアログ
def open_vector_settings():
    win = tk.Toplevel(koRoot)
    win.title("ベクトル表示設定")
    win.attributes("-topmost", True)
    cfg = app_state.vector_display.copy() if hasattr(app_state, 'vector_display') else {}

    # 有効/無効のチェックボックスを最初に追加（メインメニューの設定を反映）
    enabled_var = tk.BooleanVar(value=show_vector_win.get())
    tk.Checkbutton(win, text="ベクトル表示を有効にする", variable=enabled_var).grid(row=0, column=0, columnspan=2, sticky="w", padx=6, pady=6)

    # モード選択
    tk.Label(win, text="解釈モード:").grid(row=1, column=0, sticky="w", padx=6, pady=6)
    mode_var = tk.StringVar(value=cfg.get("interpretation_mode", "labels"))
    mode_menu = tk.OptionMenu(win, mode_var, "labels", "shap", "custom")
    mode_menu.grid(row=1, column=1, sticky="w", padx=6, pady=6)

    # カテゴリ表示チェック
    color_var = tk.BooleanVar(value=cfg.get("show_color_features", True))
    edge_var = tk.BooleanVar(value=cfg.get("show_edge_features", True))
    texture_var = tk.BooleanVar(value=cfg.get("show_texture_features", True))
    shape_var = tk.BooleanVar(value=cfg.get("show_shape_features", True))
    semantic_var = tk.BooleanVar(value=cfg.get("show_semantic_features", True))

    tk.Checkbutton(win, text="色彩特徴を表示", variable=color_var).grid(row=1, column=0, columnspan=2, sticky="w", padx=6)
    tk.Checkbutton(win, text="エッジ特徴を表示", variable=edge_var).grid(row=2, column=0, columnspan=2, sticky="w", padx=6)
    tk.Checkbutton(win, text="テクスチャを表示", variable=texture_var).grid(row=3, column=0, columnspan=2, sticky="w", padx=6)
    tk.Checkbutton(win, text="形状特徴を表示", variable=shape_var).grid(row=4, column=0, columnspan=2, sticky="w", padx=6)
    tk.Checkbutton(win, text="セマンティック特徴を表示", variable=semantic_var).grid(row=5, column=0, columnspan=2, sticky="w", padx=6)

    # 表示数・閾値
    tk.Label(win, text="表示最大次元数:").grid(row=6, column=0, sticky="w", padx=6, pady=6)
    max_var = tk.IntVar(value=cfg.get("max_dimensions_to_show", 10))
    tk.Spinbox(win, from_=1, to=50, textvariable=max_var, width=6).grid(row=6, column=1, sticky="w", padx=6, pady=6)

    tk.Label(win, text="類似度閾値:").grid(row=7, column=0, sticky="w", padx=6, pady=6)
    thr_var = tk.DoubleVar(value=cfg.get("similarity_threshold", 0.05))
    tk.Entry(win, textvariable=thr_var, width=8).grid(row=7, column=1, sticky="w", padx=6, pady=6)

    def on_ok():
        new_cfg = {
            "enabled": enabled_var.get(),
            "interpretation_mode": mode_var.get(),
            "show_color_features": color_var.get(),
            "show_edge_features": edge_var.get(),
            "show_texture_features": texture_var.get(),
            "show_shape_features": shape_var.get(),
            "show_semantic_features": semantic_var.get(),
            "max_dimensions_to_show": int(max_var.get()),
            "similarity_threshold": float(thr_var.get()),
        }
        app_state.vector_display.update(new_cfg)
        # 保存は終了時にまとめて行うが、即時反映のため設定ファイルにも書き込む
        cfg_all = app_state.to_dict()
        # settings の中に vector_display を入れて保存
        cfg_all_settings = cfg_all.get("settings", {})
        cfg_all_settings["vector_display"] = app_state.vector_display
        save_config(cfg_all["last_folder"], cfg_all.get("geometries", {}), cfg_all_settings)
        # メインメニューのチェックボックスも更新
        show_vector_win.set(enabled_var.get())
        # 更新完了
        win.destroy()

    def on_cancel():
        win.destroy()

    btn_frame = tk.Frame(win)
    btn_frame.grid(row=8, column=0, columnspan=2, pady=8)
    tk.Button(btn_frame, text="OK", width=10, command=on_ok).pack(side=tk.LEFT, padx=6)
    tk.Button(btn_frame, text="キャンセル", width=10, command=on_cancel).pack(side=tk.LEFT, padx=6)

# メニューに追加
config_menu.add_separator()
config_menu.add_command(label="ベクトル表示設定...", command=open_vector_settings)



file_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="ファイル(F)", menu=file_menu)
file_menu.add_command(label="フォルダを開く...", command=lambda: refresh_ui(safe_select_folder()))
def open_explorer():
    """現在のフォルダをエクスプローラーで開くのじゃ。のじゃ。"""
    try:
        os.startfile(DEFOLDER)
    except Exception as e:
        messagebox.showerror("エラー", f"エクスプローラーを開けなかったのじゃ: {e}")

file_menu.add_command(label="エクスプローラーで開く(E)", command=open_explorer)
file_menu.add_separator()
file_menu.add_command(label="終了(X)", command=on_closing_main)

show_folder_win = tk.BooleanVar(value=app_state.show_folder_window)
show_file_win = tk.BooleanVar(value=app_state.show_file_window)
show_rating_win = tk.BooleanVar(value=app_state.show_rating_window)
show_info_win = tk.BooleanVar(value=app_state.show_info_window)
show_vector_win = tk.BooleanVar(value=app_state.vector_display.get("enabled", True))
show_topmost_win = tk.BooleanVar(value=app_state.topmost)
show_thumbnail_win = tk.BooleanVar(value=app_state.show_thumbnail_window)
show_shortcut_bar_win = tk.BooleanVar(value=app_state.show_shortcut_key_bar)

def update_visibility():
    global thumbnail_window
    if not thumbnail_windows:
        thumbnail_window = create_thumbnail_window()
    if show_folder_win.get(): 
        folder_win.deiconify()
        app_state.set_show_folder_window(True)
    else: 
        folder_win.withdraw()
        app_state.set_show_folder_window(False)
    
    if show_file_win.get(): 
        file_win.deiconify()
        app_state.set_show_file_window(True)
    else: 
        file_win.withdraw()
        app_state.set_show_file_window(False)

    if show_thumbnail_win.get():
        thumbnail_window.show()
        app_state.show_thumbnail_window = True
    else:
        thumbnail_window.withdraw()
        app_state.show_thumbnail_window = False

    if show_shortcut_bar_win.get():
        shortcut_bar_window.show()
        app_state.show_shortcut_key_bar = True
    else:
        shortcut_bar_window.withdraw()
        app_state.show_shortcut_key_bar = False

    if show_rating_win.get():
        app_state.show_rating_window = True
        if hasattr(GazoControl, '_current_image_hash') and GazoControl._current_image_hash:
            GazoControl.update_rating_window(GazoControl._current_image_hash)
        elif hasattr(GazoControl, '_rating_window') and GazoControl._rating_window:
            GazoControl._rating_window.deiconify()
    else:
        app_state.show_rating_window = False
        if hasattr(GazoControl, '_rating_window') and GazoControl._rating_window:
            GazoControl._rating_window.withdraw()

    if show_info_win.get():
        app_state.show_info_window = True
        if hasattr(GazoControl, '_current_image_hash') and GazoControl._current_image_hash:
            current_path = getattr(GazoControl, '_current_image_path', '')
            if current_path and hasattr(GazoControl, 'update_info_window'):
                GazoControl.update_info_window(current_path, GazoControl._current_image_hash)
    else:
        app_state.show_info_window = False
        if hasattr(GazoControl, '_info_window') and GazoControl._info_window:
            GazoControl._info_window.withdraw()

    if hasattr(GazoControl, 'vector_win') and GazoControl.vector_win is not None:
        if show_vector_win.get():
            app_state.vector_display["enabled"] = True
            try:
                GazoControl.vector_win.deiconify()
            except Exception:
                pass
        else:
            app_state.vector_display["enabled"] = False
            try:
                GazoControl.vector_win.withdraw()
            except Exception:
                pass

view_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="表示(V)", menu=view_menu)
view_menu.add_checkbutton(label="フォルダ一覧を表示", variable=show_folder_win, command=update_visibility)
view_menu.add_checkbutton(label="ファイル一覧を表示", variable=show_file_win, command=update_visibility)
view_menu.add_checkbutton(label="評価ウィンドウを表示", variable=show_rating_win, command=update_visibility)
view_menu.add_checkbutton(label="情報ウィンドウを表示", variable=show_info_win, command=update_visibility)
view_menu.add_checkbutton(label="ベクトル情報を表示", variable=show_vector_win, command=update_visibility)
view_menu.add_checkbutton(label="ショートカットキー一覧を表示", variable=show_shortcut_bar_win, command=update_visibility)
view_menu.add_checkbutton(label="サムネイルパネルを表示", variable=show_thumbnail_win, command=update_visibility)
view_menu.add_command(label="新しいサムネイル窓を作成", command=lambda: create_thumbnail_window())
view_menu.add_separator()
view_menu.add_checkbutton(label="全体を最前面に固定", variable=show_topmost_win, command=lambda: set_all_topmost(show_topmost_win.get()))
view_menu.add_command(label="全ての画像を閉じる(R)", command=lambda: GazoControl.CloseAll())
view_menu.add_command(label="全ての画像を整列(T)", command=lambda: GazoControl.TileWindows())

config_menu = tk.Menu(menubar, tearoff=0)
menubar.add_cascade(label="設定(S)", menu=config_menu)

# ランダム位置設定の変更をキャッチする関数
def on_random_pos_change(*args):
    app_state.set_random_pos(GazoControl.random_pos.get())

GazoControl.random_pos.trace_add("write", on_random_pos_change)
config_menu.add_checkbutton(label="表示位置をランダムにする", variable=GazoControl.random_pos)

# ランダムサイズ設定の変更をキャッチする関数
def on_random_size_change(*args):
    app_state.set_random_size(GazoControl.random_size.get())

GazoControl.random_size.trace_add("write", on_random_size_change)
config_menu.add_checkbutton(label="表示サイズをランダムにする", variable=GazoControl.random_size)

config_menu.add_separator()

# 評価ウィンドウ表示設定の変更をキャッチする関数
def on_show_rating_change(*args):
    app_state.show_rating_window = show_rating_win.get()
    if app_state.show_rating_window and hasattr(GazoControl, '_current_image_hash') and GazoControl._current_image_hash:
        GazoControl.update_rating_window(GazoControl._current_image_hash)
    elif hasattr(GazoControl, '_rating_window') and GazoControl._rating_window:
        GazoControl._rating_window.withdraw()
    # 画像ウィンドウのサイズも調整
    update_open_windows_size()

show_rating_win.trace_add("write", on_show_rating_change)
config_menu.add_checkbutton(label="評価ウィンドウを表示", variable=show_rating_win)

# 情報ウィンドウ表示設定の変更をキャッチする関数
def on_show_info_change(*args):
    app_state.show_info_window = show_info_win.get()
    if app_state.show_info_window and hasattr(GazoControl, '_current_image_hash') and GazoControl._current_image_hash:
        # 現在の画像情報を取得して更新
        if hasattr(GazoControl, 'tag_dict') and GazoControl._current_image_hash in GazoControl.tag_dict:
            # 画像パスを取得（保存されている場合は使用）
            image_path = getattr(GazoControl, '_current_image_path', '')
            if not image_path:
                # パスがわからない場合は更新しない
                return
            # サイズ情報なども必要だが、簡易的に更新
            GazoControl.update_info_window(image_path, GazoControl._current_image_hash)
    elif hasattr(GazoControl, '_info_window') and GazoControl._info_window:
        GazoControl._info_window.withdraw()

show_info_win.trace_add("write", on_show_info_change)
config_menu.add_checkbutton(label="情報ウィンドウを表示", variable=show_info_win)

# ベクトル表示設定の変更をキャッチする関数
def on_show_vector_change(*args):
    app_state.vector_display["enabled"] = show_vector_win.get()
    # 現在表示中の画像ウィンドウのサイズを調整
    update_open_windows_size()

show_vector_win.trace_add("write", on_show_vector_change)
config_menu.add_checkbutton(label="ベクトル情報を表示", variable=show_vector_win)

# ベクトル数値表示設定の変更をキャッチする関数
show_vector_values = tk.BooleanVar(value=app_state.vector_display.get("show_internal_values", False))

def on_show_vector_values_change(*args):
    app_state.vector_display["show_internal_values"] = show_vector_values.get()
    # 表示内容を更新するためのトリガー（ウィンドウサイズ調整で再描画されるか？）
    # GazoPicture.update_rating_windowなどは再描画するが、ベクトルテキストは再生成が必要。
    # ここでは簡易的に全ウィンドウ再調整を呼ぶが、テキスト内容は再生成されないかも。
    # 本当は interpret_vector を呼び直す必要があるが、GazoPicture側で描画時に呼ばれるはず。
    # しかし既存のラベルのテキストを変えるには、Logic側の更新が必要。
    # 簡易実装として、次の描画（次画像表示）から反映される、でも良いが、即時反映したい。
    # update_open_windows_size() は pack/unpack だけ。
    # 即時反映は少し手間なので、一旦変数の更新だけにする。ユーザーが画像を切り替えれば反映される。
    pass

show_vector_values.trace_add("write", on_show_vector_values_change)
config_menu.add_checkbutton(label="└ 内部数値も表示する", variable=show_vector_values)

# 自動ベクトル計算設定
auto_vectorize = tk.BooleanVar(value=app_state.vector_display.get("auto_vectorize", True))
def on_auto_vectorize_change(*args):
    app_state.vector_display["auto_vectorize"] = auto_vectorize.get()

auto_vectorize.trace_add("write", on_auto_vectorize_change)
config_menu.add_checkbutton(label="└ 未登録なら自動で計算する", variable=auto_vectorize)

# 連続タグ付けモード
continuous_tagging = tk.BooleanVar(value=app_state.continuous_tagging_mode)
def on_continuous_tagging_change(*args):
    app_state.continuous_tagging_mode = continuous_tagging.get()

continuous_tagging.trace_add("write", on_continuous_tagging_change)
config_menu.add_checkbutton(label="連続タグ付けモード", variable=continuous_tagging)

# 左右キー移動時の窓サイズ維持設定
nav_fit_to_window_size = tk.BooleanVar(value=app_state.nav_fit_to_window_size)
def on_nav_fit_to_window_size_change(*args):
    app_state.nav_fit_to_window_size = nav_fit_to_window_size.get()

nav_fit_to_window_size.trace_add("write", on_nav_fit_to_window_size_change)
config_menu.add_checkbutton(label="前後移動(←→)で窓のサイズを維持する", variable=nav_fit_to_window_size)


# 開いているウィンドウのサイズを再調整する関数
def update_open_windows_size():
    """設定変更時に開いている画像ウィンドウのサイズとUI要素を再調整"""
    if hasattr(GazoControl, 'open_windows') and GazoControl.open_windows:
        for win in list(GazoControl.open_windows.values()):
            try:
                if hasattr(win, '_image_hash') and win._image_hash:
                    # UI要素の表示/非表示を更新
                    for child in win.winfo_children():
                        if isinstance(child, tk.Frame):
                            for subchild in child.winfo_children():
                                if isinstance(subchild, tk.Label) and hasattr(subchild, 'cget'):
                                    # ベクトル表示ラベルを探す
                                    try:
                                        current_text = subchild.cget('text') or ""
                                        if not isinstance(current_text, str):
                                            current_text = ""
                                        if current_text and (current_text.startswith('(') or '解釈' in current_text or 'エラー' in current_text):
                                            # ベクトル表示ラベルの場合
                                            if app_state.vector_display.get("enabled", True):
                                                if not subchild.winfo_ismapped():
                                                    subchild.pack(side=tk.TOP, fill=tk.X, padx=4, pady=(4,6))
                                            else:
                                                if subchild.winfo_ismapped():
                                                    subchild.pack_forget()
                                    except:
                                        pass

                                # 評価UIは画像ウィンドウ内には表示しないため、処理しない

                    # ウィンドウのサイズを再計算
                    width = win.winfo_width()

                    # 画像キャンバスの高さを取得
                    image_height = 0
                    for child in win.winfo_children():
                        if isinstance(child, tk.Frame):
                            for subchild in child.winfo_children():
                                if isinstance(subchild, tk.Canvas):
                                    image_height = subchild.winfo_height()
                                    break
                            break

                    if image_height > 0:
                        # UI要素の高さを再計算（評価UIは画像ウィンドウ内には表示しない）
                        text_area_h = 0
                        if app_state.vector_display.get("enabled", True):
                            text_area_h += 40
                        # 評価UIの高さは加算しない

                        # 新しいウィンドウ高さを設定
                        new_height = image_height + text_area_h
                        win.geometry(f"{width}x{new_height}")
            except Exception as e:
                logger.error(f"ウィンドウサイズ更新エラー: {e}")

show_vector_win.trace_add("write", on_show_vector_change)
config_menu.add_checkbutton(label="ベクトル表示を有効にする", variable=show_vector_win)

config_menu.add_separator()
config_menu.add_checkbutton(label="スクリーンセーバー(自動再生)", variable=ss_mode, command=toggle_ss)

ss_sub = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="SS設定", menu=ss_sub)

# 再生間隔
ss_interval_menu = tk.Menu(ss_sub, tearoff=0)
ss_sub.add_cascade(label="再生間隔（秒）", menu=ss_interval_menu)
for sec in SS_INTERVAL_OPTIONS:
    ss_interval_menu.add_radiobutton(label=f"{sec}秒", variable=ss_interval, value=sec)

# AI設定
ss_sub.add_separator()
ss_sub.add_checkbutton(label="AI類似度順で再生", variable=ss_ai_mode)

def set_ai_threshold():
    val = simpledialog.askfloat("AI設定", "類似度スコアの閾値(0.0〜1.0)を設定してほしいのじゃ：", 
                                initialvalue=ss_ai_threshold.get(), minvalue=MIN_AI_THRESHOLD, maxvalue=MAX_AI_THRESHOLD)
    if val is not None:
        ss_ai_threshold.set(val)
        app_state.set_ss_ai_threshold(val)

ss_sub.add_command(label="類似度の閾値を設定...", command=set_ai_threshold)

# 子フォルダを含める設定
ss_sub.add_separator()

def on_include_subfolders_change():
    """子フォルダを含める設定を変更した時の処理"""
    app_state.set_ss_include_subfolders(ss_include_subfolders.get())
    # 現在のフォルダで画像リストを再構築
    refresh_ui(DEFOLDER)

ss_sub.add_checkbutton(label="子フォルダの画像も含める", variable=ss_include_subfolders, command=on_include_subfolders_change)

# ツールメニュー
tools_menu = tk.Menu(menubar, tearoff=0)

menubar.add_cascade(label="ツール(T)", menu=tools_menu)

processor = None
def run_vector_update():
    """AIベクトル更新を実行するのじゃ。のじゃ。"""
    global processor
    if processor and processor.is_alive():
        messagebox.showinfo("情報", "既にバックグラウンドで処理中なのじゃ。")
        return

    msg = "AI(MobileNetV3)を使って画像のベクトル化を行うのじゃ。\n処理はバックグラウンドで行われるので、ウィンドウ操作は継続できるのじゃ。\n\n開始しても良いかの？"
    if not messagebox.askyesno("確認", msg):
        return

    # プログレスコールバック
    def on_progress(current, total, filename):
        # メインスレッドでUI更新（after経由）
        koRoot.after(0, lambda: koRoot.title(f"画像tools - {current}/{total} {filename} を解析中..."))

    # 完了コールバック
    def on_finish(message):
        def _finish_ui():
            koRoot.title(f"画像tools - {DEFOLDER}")
            messagebox.showinfo("完了", message)
        koRoot.after(0, _finish_ui)

    processor = VectorBatchProcessor(DEFOLDER, on_progress, on_finish)
    processor.start()

tools_menu.add_command(label="AIベクトルを更新・作成", command=run_vector_update)

# 移動先フォルダ数の設定メニュー
count_var = tk.IntVar(value=app_state.move_dest_count)
def change_move_count():
    if app_state.set_move_dest_count(count_var.get()):
        move_area.rebuild()
    else:
        messagebox.showerror("エラー", "無効な個数です")
        count_var.set(app_state.move_dest_count)

count_sub = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="移動先フォルダ数", menu=count_sub)
for c in MOVE_DESTINATION_OPTIONS:
    count_sub.add_radiobutton(label=f"{c}個", variable=count_var, value=c, command=change_move_count)

config_menu.add_separator()
config_menu.add_command(label="全登録フォルダをリセット", command=lambda: move_area.reset_destinations())
config_menu.add_separator()

# 画像表示サイズ設定ダイアログ
def open_image_size_settings():
    """画像表示サイズ設定ダイアログを表示するのじゃ。"""
    win = tk.Toplevel(koRoot)
    win.title("画像表示サイズ設定")
    win.attributes("-topmost", True)
    
    # 現在の設定値を取得
    min_w = tk.IntVar(value=app_state.image_min_width)
    min_h = tk.IntVar(value=app_state.image_min_height)
    max_w = tk.IntVar(value=app_state.image_max_width)
    max_h = tk.IntVar(value=app_state.image_max_height)
    
    from lib.config_defaults import MIN_IMAGE_SIZE_LIMIT, MAX_IMAGE_SIZE_LIMIT
    
    # 最小幅
    tk.Label(win, text="最小幅 (ピクセル):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=MIN_IMAGE_SIZE_LIMIT, to=MAX_IMAGE_SIZE_LIMIT, 
               textvariable=min_w, width=10).grid(row=0, column=1, padx=10, pady=5)
    
    # 最小高さ
    tk.Label(win, text="最小高さ (ピクセル):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=MIN_IMAGE_SIZE_LIMIT, to=MAX_IMAGE_SIZE_LIMIT, 
               textvariable=min_h, width=10).grid(row=1, column=1, padx=10, pady=5)
    
    # 最大幅（0は画面サイズの80%を使用）
    tk.Label(win, text="最大幅 (0=画面の80%):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=0, to=MAX_IMAGE_SIZE_LIMIT, 
               textvariable=max_w, width=10).grid(row=2, column=1, padx=10, pady=5)
    
    # 最大高さ（0は画面サイズの80%を使用）
    tk.Label(win, text="最大高さ (0=画面の80%):").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    tk.Spinbox(win, from_=0, to=MAX_IMAGE_SIZE_LIMIT, 
               textvariable=max_h, width=10).grid(row=3, column=1, padx=10, pady=5)
    
    def on_ok():
        app_state.set_image_size_limits(
            min_w.get(), min_h.get(), max_w.get(), max_h.get()
        )
        # 設定を保存
        cfg_all = app_state.to_dict()
        save_config(cfg_all["last_folder"], cfg_all.get("geometries", {}), cfg_all["settings"])
        win.destroy()
    
    def on_cancel():
        win.destroy()
    
    btn_frame = tk.Frame(win)
    btn_frame.grid(row=4, column=0, columnspan=2, pady=10)
    tk.Button(btn_frame, text="OK", width=10, command=on_ok).pack(side=tk.LEFT, padx=5)
    tk.Button(btn_frame, text="キャンセル", width=10, command=on_cancel).pack(side=tk.LEFT, padx=5)

config_menu.add_command(label="画像表示サイズ設定...", command=open_image_size_settings)

# 評価UI設定ダイアログ
def open_rating_ui_settings():
    """評価UI設定ダイアログを表示するのじゃ。"""
    win = tk.Toplevel(koRoot)
    win.title("評価UI設定")
    win.attributes("-topmost", True)
    win.geometry("400x600")  # ウィンドウサイズを大きくする

    # 現在の設定値を取得
    current_settings = app_state.rating_ui.copy()

    # プリセット変更時のコールバック関数
    def on_size_preset_change(preset_name, width_var, height_var):
        if preset_name in RATING_SIZE_PRESETS:
            preset = RATING_SIZE_PRESETS[preset_name]
            width_var.set(preset["width"])
            height_var.set(preset["height"])

    def on_position_preset_change(preset_name, pos_x_var, pos_y_var):
        if preset_name in RATING_POSITION_PRESETS:
            preset = RATING_POSITION_PRESETS[preset_name]
            pos_x_var.set(preset["x"])
            pos_y_var.set(preset["y"])

    # サイズプリセット
    tk.Label(win, text="サイズプリセット:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    size_preset_var = tk.StringVar(value="カスタム")

    # 現在のサイズに最も近いプリセットを探す
    current_width = current_settings.get("window_width", 320)
    current_height = current_settings.get("window_height", 140)
    for preset_name, preset_data in RATING_SIZE_PRESETS.items():
        if preset_data["width"] == current_width and preset_data["height"] == current_height:
            size_preset_var.set(preset_name)
            break

    size_options = ["カスタム"] + list(RATING_SIZE_PRESETS.keys())
    size_menu = tk.OptionMenu(win, size_preset_var, *size_options, command=lambda v: on_size_preset_change(v, width_var, height_var))
    size_menu.config(width=8)
    size_menu.grid(row=0, column=1, padx=10, pady=5)

    # 詳細サイズ設定
    tk.Label(win, text="幅:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    width_var = tk.IntVar(value=current_width)
    tk.Spinbox(win, from_=200, to=600, textvariable=width_var, width=5).grid(row=1, column=1, padx=10, pady=5)

    tk.Label(win, text="高さ:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    height_var = tk.IntVar(value=current_height)
    tk.Spinbox(win, from_=100, to=400, textvariable=height_var, width=5).grid(row=2, column=1, padx=10, pady=5)

    # 位置プリセット
    tk.Label(win, text="位置プリセット:").grid(row=3, column=0, sticky="w", padx=10, pady=(10,5))
    position_preset_var = tk.StringVar(value="カスタム")

    # 現在の位置に最も近いプリセットを探す
    current_pos_x = current_settings.get("position_x", 50)
    current_pos_y = current_settings.get("position_y", 85)
    for preset_name, preset_data in RATING_POSITION_PRESETS.items():
        if preset_data["x"] == current_pos_x and preset_data["y"] == current_pos_y:
            position_preset_var.set(preset_name)
            break

    position_options = ["カスタム"] + list(RATING_POSITION_PRESETS.keys())
    position_menu = tk.OptionMenu(win, position_preset_var, *position_options, command=lambda v: on_position_preset_change(v, pos_x_var, pos_y_var))
    position_menu.config(width=8)
    position_menu.grid(row=3, column=1, padx=10, pady=(10,5))

    # 詳細位置設定（%）
    tk.Label(win, text="横位置 (%):").grid(row=4, column=0, sticky="w", padx=10, pady=5)
    pos_x_var = tk.IntVar(value=current_pos_x)
    tk.Spinbox(win, from_=0, to=100, textvariable=pos_x_var, width=5).grid(row=4, column=1, padx=10, pady=5)

    tk.Label(win, text="縦位置 (%):").grid(row=5, column=0, sticky="w", padx=10, pady=5)
    pos_y_var = tk.IntVar(value=current_pos_y)
    tk.Spinbox(win, from_=0, to=100, textvariable=pos_y_var, width=5).grid(row=5, column=1, padx=10, pady=5)

    # パディング設定
    tk.Label(win, text="水平パディング:").grid(row=6, column=0, sticky="w", padx=10, pady=5)
    padding_x_var = tk.IntVar(value=current_settings.get("padding_x", 10))
    tk.Spinbox(win, from_=0, to=50, textvariable=padding_x_var, width=5).grid(row=6, column=1, padx=10, pady=5)

    tk.Label(win, text="垂直パディング:").grid(row=7, column=0, sticky="w", padx=10, pady=5)
    padding_y_var = tk.IntVar(value=current_settings.get("padding_y", 8))
    tk.Spinbox(win, from_=0, to=50, textvariable=padding_y_var, width=5).grid(row=7, column=1, padx=10, pady=5)

    tk.Label(win, text="ウィンドウマージン:").grid(row=8, column=0, sticky="w", padx=10, pady=5)
    margin_var = tk.IntVar(value=current_settings.get("margin", 15))
    tk.Spinbox(win, from_=0, to=100, textvariable=margin_var, width=5).grid(row=8, column=1, padx=10, pady=5)

    # フォントサイズ設定
    tk.Label(win, text="評価テキストのフォントサイズ:").grid(row=9, column=0, sticky="w", padx=10, pady=(15,5))
    text_size_var = tk.IntVar(value=current_settings.get("text_font_size", 10))
    tk.Spinbox(win, from_=8, to=24, textvariable=text_size_var, width=5).grid(row=9, column=1, padx=10, pady=(15,5))

    tk.Label(win, text="星のフォントサイズ:").grid(row=10, column=0, sticky="w", padx=10, pady=5)
    star_size_var = tk.IntVar(value=current_settings.get("star_font_size", 16))
    tk.Spinbox(win, from_=12, to=32, textvariable=star_size_var, width=5).grid(row=10, column=1, padx=10, pady=5)

    # UIレイアウト順序設定
    tk.Label(win, text="UI要素の順序:").grid(row=11, column=0, sticky="w", padx=10, pady=(15,5))

    layout_frame = tk.Frame(win)
    layout_frame.grid(row=11, column=1, sticky="w", padx=10, pady=(15,5))

    current_order = current_settings.get("layout_order", ["text", "stars", "settings"])
    order_vars = []

    elements = [("text", "評価名"), ("stars", "星"), ("settings", "設定")]
    for i, (key, label) in enumerate(elements):
        tk.Label(layout_frame, text=f"{i+1}.").grid(row=0, column=i*2, padx=2)
        var = tk.StringVar(value=current_order[i] if i < len(current_order) else key)
        tk.OptionMenu(layout_frame, var, "text", "stars", "settings").grid(row=0, column=i*2+1, padx=2)
        tk.Label(layout_frame, text=f"({label})").grid(row=1, column=i*2+1, sticky="n")
        order_vars.append(var)

    def on_save():
        # 設定を保存
        new_settings = {
            "window_width": width_var.get(),
            "window_height": height_var.get(),
            "position_x": pos_x_var.get(),
            "position_y": pos_y_var.get(),
            "padding_x": padding_x_var.get(),
            "padding_y": padding_y_var.get(),
            "margin": margin_var.get(),
            "text_font_size": text_size_var.get(),
            "star_font_size": star_size_var.get(),
            "layout_order": [var.get() for var in order_vars]
        }
        app_state.rating_ui.update(new_settings)

        # UIを更新
        GazoControl.update_rating_ui_settings()

        # 設定ファイルに保存
        cfg_all = app_state.to_dict()
        save_config(cfg_all["last_folder"], cfg_all.get("geometries", {}), cfg_all["settings"])
        win.destroy()

    def on_cancel():
        win.destroy()

    # ボタン
    btn_frame = tk.Frame(win)
    btn_frame.grid(row=12, column=0, columnspan=2, pady=20)

    tk.Button(btn_frame, text="保存", command=on_save).pack(side=tk.LEFT, padx=10)
    tk.Button(btn_frame, text="キャンセル", command=on_cancel).pack(side=tk.LEFT, padx=10)


def show_error_backlog_window():
    try:
        from lib.GazoToolsLogger import LoggerManager
        text = LoggerManager.format_error_backlog(limit=20)
        win = tk.Toplevel(koRoot)
        win.title("エラー履歴")
        win.geometry("900x300")
        win.attributes("-topmost", True)
        txt = tk.Text(win, wrap="word", state="disabled")
        txt.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)
        txt.configure(state="normal")
        txt.insert(tk.END, text)
        txt.configure(state="disabled")
        win.transient(koRoot)
    except Exception:
        logger.exception("エラー履歴ウィンドウ作成失敗")

config_menu.add_command(label="評価UI設定...", command=open_rating_ui_settings)
config_menu.add_command(label="エラー履歴を表示", command=show_error_backlog_window)
config_menu.add_separator()
config_menu.add_command(label="常に最前面(T) ON/OFF", command=lambda: koRoot.attributes("-topmost", not koRoot.attributes("-topmost")))

all_items = os.listdir(DEFOLDER)
folder_win = FolderListWindow(koRoot, on_move_registered=lambda: move_area.refresh_display())
file_win, file_listbox = create_file_list_window(koRoot, GetGazoFiles(all_items, DEFOLDER), GazoControl.Drawing)

def on_thumbnail_select(file_path, open_image=False):
    """サムネイルのシングルクリックでタグ編集対象に設定し、ダブルクリックで画像を開く。"""
    if not file_path or not os.path.exists(file_path):
        return
    if open_image:
        GazoControl.Drawing(file_path)
    else:
        update_active_tag_target(file_path)

def on_thumbnail_edit_tag(file_path):
    """サムネイルの右クリックメニュー、またはショートカットキー(t)からタグ編集窓を呼び出す。"""
    if not file_path or not os.path.exists(file_path):
        return
    update_active_tag_target(file_path)
    tag_edit_window.deiconify()
    tag_edit_window.lift()
    tag_edit_window.entry.focus_set()

thumbnail_windows = []

def remove_thumbnail_window(window):
    if window in thumbnail_windows:
        thumbnail_windows.remove(window)
    try:
        window.destroy()
    except tk.TclError:
        pass

def create_thumbnail_window():
    window = ThumbnailPanelWindow(
        koRoot,
        [os.path.join(DEFOLDER, name) for name in GetGazoFiles(os.listdir(DEFOLDER), DEFOLDER)],
        select_callback=on_thumbnail_select,
        close_callback=remove_thumbnail_window,
        window_number=len(thumbnail_windows) + 1,
        gazo_control=GazoControl,
        edit_tag_callback=on_thumbnail_edit_tag,
    )
    thumbnail_windows.append(window)
    window.show()
    return window

thumbnail_window = create_thumbnail_window()
# ベクトル表示用ウィンドウ
vector_window = VectorWindow(koRoot)

def _refresh_file_listbox_from_current_folder():
    """タグ一覧での絞り込み変更後、ファイル一覧・サムネイル窓を再描画する。"""
    if 'file_listbox' in globals():
        current_files = [n for n in os.listdir(DEFOLDER) if os.path.isfile(os.path.join(DEFOLDER, n))]
        refresh_file_listbox_with_tag_filter(current_files)
    if 'thumbnail_windows' in globals():
        for window in list(thumbnail_windows):
            try:
                if window.winfo_exists():
                    window.apply_filters()
            except tk.TclError:
                pass

tag_window = TagListWindow(koRoot, GazoControl, on_filter_applied=_refresh_file_listbox_from_current_folder)
tag_edit_window = TagEditorWindow(koRoot, GazoControl)
shortcut_bar_window = ShortcutKeyBarWindow(koRoot)

# UI参照をロジックに渡す
GazoControl.SetUI(folder_win, file_win, vector_window)

# メニューに表示切り替えを追加
def toggle_vector_window():
    if vector_window.winfo_viewable():
        vector_window.withdraw()
    else:
        vector_window.show()

vector_sub = tk.Menu(config_menu, tearoff=0)
config_menu.add_cascade(label="ベクトルウィンドウ", menu=vector_sub)
vector_sub.add_command(label="表示/非表示", command=toggle_vector_window)

if "main" in SAVED_GEOS: koRoot.geometry(SAVED_GEOS["main"])
if "folder" in SAVED_GEOS: folder_win.geometry(SAVED_GEOS["folder"])
if "file" in SAVED_GEOS: file_win.geometry(SAVED_GEOS["file"])
if SAVED_GEOS.get("thumbnail"):
    thumbnail_window.geometry(SAVED_GEOS["thumbnail"])

# ベクトルウィンドウの復元
if SAVED_GEOS.get("vector_window_geometry"):
    vector_window.geometry(SAVED_GEOS["vector_window_geometry"])

if app_state.show_vector_window:
    vector_window.show()
else:
    vector_window.withdraw()

# ショートカットキー一覧バーの復元
if SAVED_GEOS.get("shortcut_key_bar"):
    shortcut_bar_window.geometry(SAVED_GEOS["shortcut_key_bar"])

# タグ関連ウィンドウの位置復元
if SAVED_GEOS.get("tag_window"):
    tag_window.geometry(SAVED_GEOS["tag_window"])
if SAVED_GEOS.get("tag_edit_window"):
    tag_edit_window.geometry(SAVED_GEOS["tag_edit_window"])

update_visibility()

if app_state.show_thumbnail_window:
    thumbnail_window.show()
else:
    thumbnail_window.withdraw()

if app_state.show_shortcut_key_bar:
    shortcut_bar_window.show()
else:
    shortcut_bar_window.withdraw()

folder_win.protocol("WM_DELETE_WINDOW", lambda: (show_folder_win.set(False), folder_win.withdraw()))
file_win.protocol("WM_DELETE_WINDOW", lambda: (show_file_win.set(False), file_win.withdraw()))
koRoot.protocol("WM_DELETE_WINDOW", on_closing_main)

refresh_ui(DEFOLDER)

def execute_move(file_path, dest_folder, refresh=True):
    if not dest_folder or not os.path.exists(dest_folder):
        logger.error(f"移動先フォルダが無効: {dest_folder}")
        messagebox.showerror("エラー", "移動先フォルダが正しく登録されていないのじゃ！")
        return
    try:
        filename = os.path.basename(file_path)
        shutil.move(file_path, os.path.join(dest_folder, filename))
        logger.info(f"ファイル移動成功: {filename} -> {dest_folder}")
        if refresh:
            refresh_ui(DEFOLDER)
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {file_path}")
        messagebox.showerror("エラー", f"ファイルが見つかりません: {filename}")
    except PermissionError as e:
        logger.error(f"ファイル移動: 権限がありません: {file_path}")
        messagebox.showerror("エラー", f"ファイルを移動する権限がありません: {filename}")
    except Exception as e:
        logger.error(f"ファイル移動エラー: {file_path} -> {dest_folder}", exc_info=True)
        messagebox.showerror("失敗", f"移動中にエラーが起きたのじゃ: {e}")

# --- D&Dエリアの構築（2段構え） ---
move_area = MoveDestinationArea(koRoot, move_callback=execute_move, refresh_callback=lambda: refresh_ui(DEFOLDER))
move_area.pack(fill=tk.BOTH, padx=0, pady=0, expand=True)

# 移動処理コールバックをLogic側に登録
GazoControl.set_move_callback(execute_move)
GazoControl.set_refresh_callback(refresh_ui)

def on_escape(event):
    if ss_mode.get():
        ss_mode.set(False)
        toggle_ss()

def on_ctrl_f(event):
    koRoot.attributes("-topmost", True)
    koRoot.focus_force()

def on_ctrl_r(event):
    """Ctrl + R で全ての画像を閉じるのじゃ。のじゃ。"""
    GazoControl.CloseAll()
    print("[HOTKEY] Ctrl+R: 全ての画像を閉じました")

def on_ctrl_e(event):
    """Ctrl + E でエクスプローラーを開くのじゃ。のじゃ。"""
    open_explorer()
    print("[HOTKEY] Ctrl+E: エクスプローラーを開きました")

def on_ctrl_t(event):
    """Ctrl + T で全ての画像をタイル状に並べるのじゃ。のじゃ。"""
    GazoControl.TileWindows()
    print("[HOTKEY] Ctrl+T: 画像をタイル表示にしました")

def on_ctrl_i(event):
    """Ctrl + I で情報ウィンドウの表示/非表示を切り替えるのじゃ。のじゃ。"""
    if hasattr(GazoControl, '_info_window') and GazoControl._info_window:
        try:
            if GazoControl._info_window.winfo_viewable():
                GazoControl._info_window.withdraw()
                print("[HOTKEY] Ctrl+I: 情報ウィンドウを非表示にしました")
            else:
                GazoControl._info_window.deiconify()
                print("[HOTKEY] Ctrl+I: 情報ウィンドウを表示しました")
        except:
            # ウィンドウが存在しない場合は新しく作成
            GazoControl.create_info_window()
            print("[HOTKEY] Ctrl+I: 情報ウィンドウを作成しました")
    else:
        # ウィンドウが存在しない場合は新しく作成
        GazoControl.create_info_window()
        print("[HOTKEY] Ctrl+I: 情報ウィンドウを作成しました")

def on_ctrl_r(event):
    """Ctrl + R で全ての画像ウィンドウを閉じるのじゃ。のじゃ。"""
    GazoControl.CloseAll()
    print("[HOTKEY] Ctrl+R: 全ての画像ウィンドウを閉じました")

def on_space(event):
    next_image = data_manager.RandamGazoSet()
    if not next_image:
        logger.warning("スペースキー: 表示する画像がありません")
        return
    GazoControl.Drawing(next_image)

koRoot.bind("<space>", on_space)
koRoot.bind("<Escape>", on_escape)
koRoot.bind_all("<Control-f>", on_ctrl_f)
koRoot.bind_all("<Control-r>", on_ctrl_r)
koRoot.bind_all("<Control-e>", on_ctrl_e)
koRoot.bind_all("<Control-t>", on_ctrl_t)
koRoot.bind_all("<Control-i>", on_ctrl_i)

if ss_mode.get():
    koRoot.after(1000, auto_slideshow)


def on_closing():
    """アプリ終了時の処理"""
    try:
        # 現在の状態を取得して保存
        # ウィンドウ位置を更新
        if GazoControl.folder_win: app_state.set_window_geometry("folder", GazoControl.folder_win.geometry())
        if GazoControl.file_win: app_state.set_window_geometry("file", GazoControl.file_win.geometry())
        if thumbnail_windows:
            app_state.set_window_geometry("thumbnail", thumbnail_windows[0].geometry())
        # メインウィンドウは koRoot
        app_state.set_window_geometry("main", koRoot.geometry())
        app_state.show_thumbnail_window = show_thumbnail_win.get()
        if thumbnail_windows:
            primary_thumbnail = thumbnail_windows[0]
            app_state.thumbnail_rows = primary_thumbnail.rows_var.get()
            app_state.thumbnail_columns = primary_thumbnail.columns_var.get()
            app_state.thumbnail_width = primary_thumbnail.width_var.get()
            app_state.thumbnail_height = primary_thumbnail.height_var.get()

        # ベクトルウィンドウの位置と表示状態保存
        if vector_window:
             app_state.set_window_geometry("vector_window_geometry", vector_window.geometry())
             app_state.show_vector_window = bool(vector_window.winfo_viewable())

        # ショートカットキー一覧バーの位置と表示状態保存
        if 'shortcut_bar_window' in globals():
            app_state.set_window_geometry("shortcut_key_bar", shortcut_bar_window.geometry())
            app_state.show_shortcut_key_bar = show_shortcut_bar_win.get()

        # タグ関連ウィンドウの位置保存
        if 'tag_window' in globals():
            app_state.set_window_geometry("tag_window", tag_window.geometry())
        if 'tag_edit_window' in globals():
            app_state.set_window_geometry("tag_edit_window", tag_edit_window.geometry())

        cfg = app_state.to_dict()
        save_config(cfg["last_folder"], cfg["geometries"], cfg["settings"])
        logger.info("アプリケーションを終了します (設定を保存しました)")
    except Exception as e:
        logger.error(f"終了時の保存エラー: {e}")
    
    koRoot.destroy()
    sys.exit(0)

koRoot.protocol("WM_DELETE_WINDOW", on_closing)

koRoot.mainloop()
