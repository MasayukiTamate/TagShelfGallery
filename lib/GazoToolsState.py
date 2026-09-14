'''
作成日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools のアプリケーション状態管理クラス
説明: グローバル変数を廃止し、状態管理を一元化するためのクラス
'''
import os
from lib.GazoToolsLogger import get_logger

logger = get_logger(__name__)


class AppState:
    """アプリケーション全体の状態を管理するシングルトンクラス"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初期化（初回のみ実行）"""
        if self._initialized:
            return
        
        self._initialized = True
        
        # フォルダ・ファイル関連
        self.current_folder = os.getcwd()
        self.current_files = []
        self.current_folders = []
        
        # 移動先フォルダ関連
        self.move_dest_list = [""] * 12
        self.move_reg_idx = 0
        self.move_dest_count = 2
        
        # UI 表示設定
        self.show_folder_window = True
        self.show_file_window = True
        self.show_rating_window = True     # 評価ウィンドウ表示
        self.show_info_window = False      # 情報ウィンドウ表示
        self.show_vector_window = False    # ベクトルウィンドウ表示 (初期値False)
        self.random_pos = False
        self.random_size = False
        self.topmost = True
        
        # スクリーンセーバー設定
        self.ss_mode = False
        self.ss_interval = 5
        self.ss_ai_mode = False
        self.ss_ai_threshold = 0.65
        self.ss_include_subfolders = False
        
        # ベクトル表示設定
        self.vector_display = {
            "enabled": True,
            "interpretation_mode": "labels",
            "show_color_features": True,
            "show_edge_features": True,
            "show_texture_features": True,
            "show_shape_features": True,
            "show_semantic_features": True,
            "max_dimensions_to_show": 10,
            "similarity_threshold": 0.05,
            "show_internal_values": False,
            "auto_vectorize": True,
        }

        # スマート移動設定
        self.smart_move_threshold = 0.90
        self.smart_move_show_thumbnails = True

        # スプラッシュ設定
        self.show_splash_tips = False
        
        # ウィンドウジオメトリ
        self.window_geometries = {
            "main": None,
            "folder": None,
            "file": None
        }
        
        # リソース監視設定
        self.cpu_low_color = "#e0ffe0"
        self.cpu_high_color = "#ff8080"
        
        # 画像表示サイズ設定
        from lib.config_defaults import (
            DEFAULT_IMAGE_MIN_WIDTH, DEFAULT_IMAGE_MIN_HEIGHT,
            DEFAULT_IMAGE_MAX_WIDTH, DEFAULT_IMAGE_MAX_HEIGHT
        )
        self.image_min_width = DEFAULT_IMAGE_MIN_WIDTH
        self.image_min_height = DEFAULT_IMAGE_MIN_HEIGHT
        self.image_max_width = DEFAULT_IMAGE_MAX_WIDTH
        self.image_max_height = DEFAULT_IMAGE_MAX_HEIGHT

        # 評価UI設定
        self.rating_ui = {
            "text_font_size": 10,
            "star_font_size": 16,
            "layout_order": ["text", "stars", "settings"],
            "window_width": 320,
            "window_height": 140,
            "position_x": 50,
            "position_y": 85,
            "padding_x": 10,
            "padding_y": 8,
            "margin": 15,
        }

        # 画像評価データ（タグデータから同期）
        self.image_ratings = {}

        # UI更新コールバック
        self._ui_callbacks = []
        
        logger.info("AppState を初期化しました")
    
    # ==================== フォルダ・ファイル管理 ====================
    
    def set_current_folder(self, path):
        """現在のフォルダを設定
        
        Args:
            path (str): フォルダパス
        """
        if not os.path.exists(path):
            logger.warning(f"パスが存在しません: {path}")
            return False
        
        self.current_folder = path
        self.current_files = []
        self.current_folders = []
        
        logger.info(f"現在のフォルダを変更: {path}")
        self._notify_callbacks("folder_changed", {"path": path})
        return True
    
    def set_current_files(self, files):
        """現在のファイルリストを設定
        
        Args:
            files (list): ファイル名のリスト
        """
        self.current_files = files
        logger.debug(f"ファイル一覧を更新: {len(files)}件")
        self._notify_callbacks("files_changed", {"files": files, "count": len(files)})
    
    def set_current_folders(self, folders):
        """現在のフォルダリストを設定
        
        Args:
            folders (list): フォルダ名のリスト
        """
        self.current_folders = folders
        logger.debug(f"フォルダ一覧を更新: {len(folders)}件")
        self._notify_callbacks("folders_changed", {"folders": folders, "count": len(folders)})
    
    # ==================== 移動先管理 ====================
    
    def set_move_destination(self, index, path):
        """指定インデックスに移動先フォルダを登録
        
        Args:
            index (int): スロットインデックス (0-11)
            path (str): フォルダパス
            
        Returns:
            bool: 成功時 True
        """
        if not (0 <= index < len(self.move_dest_list)):
            logger.error(f"無効なインデックス: {index}")
            return False
        
        if path and not os.path.exists(path):
            logger.warning(f"フォルダが存在しません: {path}")
            return False
        
        self.move_dest_list[index] = path
        logger.info(f"移動先スロット{index+1}に登録: {path if path else '(クリア)'}")
        self._notify_callbacks("move_destination_changed", {"index": index, "path": path})
        return True
    
    def set_move_reg_idx(self, index):
        """次の登録先インデックスを設定
        
        Args:
            index (int): インデックス
        """
        self.move_reg_idx = index % self.move_dest_count
        logger.debug(f"次の登録先インデックス: {self.move_reg_idx + 1}")
        self._notify_callbacks("move_reg_idx_changed", {"index": self.move_reg_idx})
    
    def rotate_move_reg_idx(self):
        """次の登録先インデックスを順繰りに進める"""
        self.move_reg_idx = (self.move_reg_idx + 1) % self.move_dest_count
        logger.debug(f"登録インデックスを進める: {self.move_reg_idx + 1}")
        self._notify_callbacks("move_reg_idx_changed", {"index": self.move_reg_idx})
    
    def set_move_dest_count(self, count):
        """移動先フォルダ数を変更
        
        Args:
            count (int): 個数（2, 4, 6, 8, 10, 12）
        """
        valid_counts = [2, 4, 6, 8, 10, 12]
        if count not in valid_counts:
            logger.error(f"無効な個数: {count}")
            return False
        
        old_count = self.move_dest_count
        self.move_dest_count = count
        
        # リスト長を調整
        if count > len(self.move_dest_list):
            self.move_dest_list.extend([""] * (count - len(self.move_dest_list)))
        else:
            self.move_dest_list = self.move_dest_list[:count]
        
        # インデックスをクリップ
        if self.move_reg_idx >= count:
            self.move_reg_idx = 0
        
        logger.info(f"移動先個数を変更: {old_count} → {count}")
        self._notify_callbacks("move_dest_count_changed", {"count": count})
        return True
    
    def reset_move_destinations(self):
        """全ての移動先登録をリセット"""
        self.move_dest_list = [""] * self.move_dest_count
        self.move_reg_idx = 0
        logger.info("移動先をリセットしました")
        self._notify_callbacks("move_destinations_reset", {})
    
    # ==================== UI 設定 ====================
    
    def set_show_folder_window(self, show):
        """フォルダウィンドウ表示設定
        
        Args:
            show (bool): 表示するか
        """
        self.show_folder_window = show
        logger.debug(f"フォルダウィンドウ表示: {show}")
        self._notify_callbacks("show_folder_window_changed", {"show": show})
    
    def set_show_file_window(self, show):
        """ファイルウィンドウ表示設定
        
        Args:
            show (bool): 表示するか
        """
        self.show_file_window = show
        logger.debug(f"ファイルウィンドウ表示: {show}")
        self._notify_callbacks("show_file_window_changed", {"show": show})
    
    def set_random_pos(self, enabled):
        """表示位置ランダム化設定
        
        Args:
            enabled (bool): 有効にするか
        """
        self.random_pos = enabled
        logger.debug(f"表示位置ランダム化: {enabled}")
        self._notify_callbacks("random_pos_changed", {"enabled": enabled})
    
    def set_random_size(self, enabled):
        """表示サイズをランダムにする設定
        
        Args:
            enabled (bool): 有効にするか
        """
        self.random_size = enabled
        logger.debug(f"表示サイズをランダムにする: {enabled}")
        self._notify_callbacks("random_size_changed", {"enabled": enabled})
    
    def set_topmost(self, enabled):
        """常に最前面設定
        
        Args:
            enabled (bool): 有効にするか
        """
        self.topmost = enabled
        logger.debug(f"常に最前面: {enabled}")
        self._notify_callbacks("topmost_changed", {"enabled": enabled})
    
    # ==================== スクリーンセーバー設定 ====================
    
    def set_ss_mode(self, enabled):
        """スクリーンセーバーモード設定"""
        self.ss_mode = enabled
        logger.info(f"スクリーンセーバー: {enabled}")
        self._notify_callbacks("ss_mode_changed", {"enabled": enabled})
    
    def set_ss_interval(self, seconds):
        """スクリーンセーバー再生間隔設定（秒）"""
        self.ss_interval = max(1, seconds)
        logger.debug(f"スクリーンセーバー間隔: {self.ss_interval}秒")
        self._notify_callbacks("ss_interval_changed", {"interval": self.ss_interval})
    
    def set_ss_ai_mode(self, enabled):
        """AI類似度順モード設定"""
        self.ss_ai_mode = enabled
        logger.info(f"AI類似度順モード: {enabled}")
        self._notify_callbacks("ss_ai_mode_changed", {"enabled": enabled})
    
    def set_ss_ai_threshold(self, threshold):
        """AI類似度閾値設定"""
        self.ss_ai_threshold = max(0.0, min(1.0, threshold))
        logger.debug(f"AI類似度閾値: {self.ss_ai_threshold}")
        self._notify_callbacks("ss_ai_threshold_changed", {"threshold": self.ss_ai_threshold})
    
    def set_ss_include_subfolders(self, enabled):
        """子フォルダを含める設定"""
        self.ss_include_subfolders = enabled
        logger.debug(f"子フォルダを含める: {enabled}")
        self._notify_callbacks("ss_include_subfolders_changed", {"enabled": enabled})
    
    def set_smart_move_threshold(self, threshold):
        """スマート移動の閾値設定"""
        self.smart_move_threshold = max(0.0, min(1.0, threshold))
        logger.debug(f"スマート移動閾値: {self.smart_move_threshold}")
        # 特にUI更新は不要かもしれないが、一応通知しても良い
        self._notify_callbacks("smart_move_threshold_changed", {"threshold": self.smart_move_threshold})

    def set_smart_move_show_thumbnails(self, enabled):
        """スマート移動のサムネイル表示設定"""
        self.smart_move_show_thumbnails = enabled
        logger.debug(f"スマート移動サムネイル: {enabled}")
        self._notify_callbacks("smart_move_show_thumbnails_changed", {"enabled": enabled})

    def set_show_splash_tips(self, enabled):
        """スプラッシュスクリーンのTips表示設定"""
        self.show_splash_tips = enabled
        logger.debug(f"スプラッシュTips表示: {enabled}")
        self._notify_callbacks("show_splash_tips_changed", {"enabled": enabled})

    # ==================== ウィンドウジオメトリ ====================
    
    def set_window_geometry(self, window_name, geometry):
        """ウィンドウのジオメトリ（位置・サイズ）を保存
        
        Args:
            window_name (str): "main", "folder", "file"
            geometry (str): "WIDTHxHEIGHT+X+Y"
        """
        if window_name not in self.window_geometries:
            logger.warning(f"不明なウィンドウ: {window_name}")
            return
        
        self.window_geometries[window_name] = geometry
        logger.debug(f"ウィンドウジオメトリを保存: {window_name} = {geometry}")
    
    def get_window_geometry(self, window_name):
        """ウィンドウのジオメトリを取得
        
        Args:
            window_name (str): "main", "folder", "file"
            
        Returns:
            str or None: ジオメトリ文字列、未設定なら None
        """
        return self.window_geometries.get(window_name)
    
    # ==================== リソース表示設定 ====================
    
    def set_cpu_colors(self, low_color, high_color):
        """CPU使用率表示用の色を設定
        
        Args:
            low_color (str): 低負荷時の色（hex）
            high_color (str): 高負荷時の色（hex）
        """
        self.cpu_low_color = low_color
        self.cpu_high_color = high_color
        logger.debug(f"CPU色設定: {low_color} → {high_color}")
        self._notify_callbacks("cpu_colors_changed", {"low": low_color, "high": high_color})
    
    def set_image_size_limits(self, min_w, min_h, max_w, max_h):
        """画像表示サイズ制限を設定
        
        Args:
            min_w (int): 最小幅
            min_h (int): 最小高さ
            max_w (int): 最大幅
            max_h (int): 最大高さ
        """
        self.image_min_width = min_w
        self.image_min_height = min_h
        self.image_max_width = max_w
        self.image_max_height = max_h
        logger.debug(f"画像サイズ制限設定: Min({min_w}x{min_h}), Max({max_w}x{max_h})")
        self._notify_callbacks("image_size_limits_changed", {
            "min_w": min_w, "min_h": min_h, "max_w": max_w, "max_h": max_h
        })
    
    # ==================== コールバック管理 ====================
    
    def register_callback(self, callback):
        """UI更新コールバックを登録
        
        Args:
            callback (callable): func(event_name, data) の形式
        """
        self._ui_callbacks.append(callback)
        logger.debug(f"UI更新コールバックを登録: {callback.__name__}")
    
    def unregister_callback(self, callback):
        """UI更新コールバックを解除
        
        Args:
            callback (callable): 登録済みのコールバック
        """
        if callback in self._ui_callbacks:
            self._ui_callbacks.remove(callback)
            logger.debug(f"UI更新コールバックを解除: {callback.__name__}")
    
    def _notify_callbacks(self, event_name, data):
        """全ての登録済みコールバックを実行
        
        Args:
            event_name (str): イベント名
            data (dict): イベントデータ
        """
        for callback in self._ui_callbacks:
            try:
                callback(event_name, data)
            except Exception as e:
                logger.error(f"コールバック実行エラー ({callback.__name__}): {e}", exc_info=True)
    
    # ==================== 状態の保存・復元 ====================
    
    def to_dict(self):
        """状態辞書に変換（設定保存用）
        
        Returns:
            dict: 状態を表す辞書
        """
        return {
            "last_folder": self.current_folder,
            "geometries": self.window_geometries,
            "settings": {
                "random_pos": self.random_pos,
                "random_size": self.random_size,
                "topmost": self.topmost,
                "show_folder": self.show_folder_window,
                "show_file": self.show_file_window,
                "show_rating_window": self.show_rating_window,
                "show_vector_window": self.show_vector_window,
                "show_info_window": self.show_info_window,
                "rating_ui": self.rating_ui,
                "ss_mode": self.ss_mode,
                "ss_interval": self.ss_interval,
                "ss_ai_mode": self.ss_ai_mode,
                "ss_ai_threshold": self.ss_ai_threshold,
                "ss_include_subfolders": self.ss_include_subfolders,
                "move_dest_list": self.move_dest_list,
                "move_reg_idx": self.move_reg_idx,
                "move_dest_count": self.move_dest_count,
                "cpu_low_color": self.cpu_low_color,
                "cpu_high_color": self.cpu_high_color,
                "image_min_width": self.image_min_width,
                "image_min_height": self.image_min_height,
                "image_max_width": self.image_max_width,
                "image_max_height": self.image_max_height,
                "vector_display": self.vector_display,
                "smart_move_threshold": self.smart_move_threshold,
                "smart_move_show_thumbnails": self.smart_move_show_thumbnails,
                "show_splash_tips": self.show_splash_tips,
            }
        }
    
    def from_dict(self, data):
        """辞書から状態を復元（設定読み込み用）
        
        Args:
            data (dict): 状態を表す辞書
        """
        try:
            if "last_folder" in data:
                self.current_folder = data["last_folder"]
            
            if "geometries" in data:
                self.window_geometries.update(data["geometries"])
            
            if "settings" in data:
                settings = data["settings"]
                self.random_pos = settings.get("random_pos", False)
                self.random_size = settings.get("random_size", False)
                self.topmost = settings.get("topmost", True)
                self.show_folder_window = settings.get("show_folder", True)
                self.show_file_window = settings.get("show_file", True)
                self.show_rating_window = settings.get("show_rating_window", True)
                self.show_vector_window = settings.get("show_vector_window", False)
                self.show_info_window = settings.get("show_info_window", False)
                self.rating_ui = settings.get("rating_ui", {
                    "text_font_size": 10,
                    "star_font_size": 16,
                    "layout_order": ["text", "stars", "settings"],
                    "window_width": 320,
                    "window_height": 140,
                    "position_x": 50,
                    "position_y": 85,
                    "padding_x": 10,
                    "padding_y": 8,
                    "margin": 15,
                })
                self.ss_mode = settings.get("ss_mode", False)
                self.ss_interval = settings.get("ss_interval", 5)
                self.ss_ai_mode = settings.get("ss_ai_mode", False)
                self.ss_ai_threshold = settings.get("ss_ai_threshold", 0.65)
                self.ss_include_subfolders = settings.get("ss_include_subfolders", False)
                self.cpu_low_color = settings.get("cpu_low_color", "#e0ffe0")
                self.cpu_high_color = settings.get("cpu_high_color", "#ff8080")
                
                # 画像表示サイズ設定
                from lib.config_defaults import (
                    DEFAULT_IMAGE_MIN_WIDTH, DEFAULT_IMAGE_MIN_HEIGHT,
                    DEFAULT_IMAGE_MAX_WIDTH, DEFAULT_IMAGE_MAX_HEIGHT
                )
                self.image_min_width = settings.get("image_min_width", DEFAULT_IMAGE_MIN_WIDTH)
                self.image_min_height = settings.get("image_min_height", DEFAULT_IMAGE_MIN_HEIGHT)
                self.image_max_width = settings.get("image_max_width", DEFAULT_IMAGE_MAX_WIDTH)
                self.image_max_height = settings.get("image_max_height", DEFAULT_IMAGE_MAX_HEIGHT)
                

                move_list = settings.get("move_dest_list", [])
                if len(move_list) < 12:
                    move_list = (move_list + [""] * 12)[:12]
                self.move_dest_list = move_list
                
                self.move_reg_idx = settings.get("move_reg_idx", 0)
                self.move_dest_count = settings.get("move_dest_count", 2)
                # vector_display を復元
                vdisp = settings.get("vector_display")
                if isinstance(vdisp, dict):
                    self.vector_display.update(vdisp)
                
                self.smart_move_threshold = settings.get("smart_move_threshold", 0.90)
                self.smart_move_show_thumbnails = settings.get("smart_move_show_thumbnails", True)
                self.show_splash_tips = settings.get("show_splash_tips", False)
            
            logger.info("状態を復元しました")
        except Exception as e:
            logger.error(f"状態復元エラー: {e}", exc_info=True)
    
    def clear(self):
        """全ての状態をリセット"""
        self.__init__()
        logger.info("AppState をリセットしました")


# グローバルシングルトン取得関数
def get_app_state():
    """AppState インスタンスを取得"""
    return AppState()
