'''
作成日: 2026年01月04日
機能: UIコンポーネント (MVCのView層)
'''
import os
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
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

# 相対インポートではなく、ルートからのインポートを使用
# (アプリ実行時のパス構成に依存)
import sys

# Logicとの循環参照を避けるため、必要な関数は可能な限りここでインポートするか、
# コールバックや遅延インポートを使用します。
# 現在の構造上、GazoToolsLogicにある関数(calculate_file_hash, load_vectorsなど)が必要です。
# GazoToolsLogicがGazoToolsGUIをトップレベルでインポートしていなければ、ここでインポートしても安全です。
try:
    from GazoToolsLogic import calculate_file_hash, load_vectors
except ImportError:
    # パスが通っていない場合（単体テストなど）の対策
    # 本番実行時は GazoToolsApp.py がルートにあるので通るはず
    pass

logger = get_logger(__name__)
app_state = get_app_state()

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
