'''
作成日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools グローバル設定定数管理
説明: アプリケーション全体で使用される定数を一元管理するモジュール
'''
import os

# ===========================
# 1. ウィンドウサイズ関連の定数
# ===========================
DEFAULT_WINDOW_WIDTH = 800
DEFAULT_WINDOW_HEIGHT = 600

MIN_WINDOW_WIDTH = 200
MIN_WINDOW_HEIGHT = 120
MAX_WINDOW_WIDTH = 600
MAX_WINDOW_HEIGHT = 800

FOLDER_WINDOW_CHAR_MULTIPLIER = 10  # 文字幅あたりのピクセル数
FOLDER_WINDOW_HEIGHT_MULTIPLIER = 20  # 行の高さのピクセル数
FOLDER_WINDOW_HEIGHT_OFFSET = 90  # ボタン・ヘッダー分のオフセット
FOLDER_WINDOW_WIDTH_OFFSET = 60  # パディング

FILE_WINDOW_CHAR_MULTIPLIER = 8
FILE_WINDOW_HEIGHT_MULTIPLIER = 20
FILE_WINDOW_HEIGHT_OFFSET = 70
FILE_WINDOW_WIDTH_OFFSET = 80

WINDOW_SPACING = 10  # ウィンドウ間のスペース
SCREEN_MARGIN = 40  # 画面右端・下部の余白


# ===========================
# 2. UI レイアウト定数
# ===========================
MOVE_DESTINATION_SLOTS = 12      # 移動先スロット数（最大）
MOVE_DESTINATION_MIN = 2         # 最小個数
MOVE_DESTINATION_MAX = 12        # 最大個数
MOVE_DESTINATION_OPTIONS = [2, 4, 6, 8, 10, 12]  # 選択可能な個数

MOVE_GRID_COLUMNS_MULTI = 3   # 4個以上の時の列数
MOVE_GRID_COLUMNS_SINGLE = 2  # 2-3個の時の列数

SHORTCUT_TAG_KEY_COUNT = 9    # タグ割り当てショートカットキー数（1〜9キー）
TAG_FILTER_PANEL_HEIGHT = 120  # ファイル一覧窓のタグフィルタ欄の高さ(px)。超えた分はスクロール


# ===========================
# 3. スクリーンセーバー設定
# ===========================
DEFAULT_SS_INTERVAL = 5          # デフォルト間隔（秒）
MIN_SS_INTERVAL = 1
MAX_SS_INTERVAL = 60
SS_INTERVAL_OPTIONS = [1, 2, 3, 5, 10, 15, 30, 60]  # メニュー選択肢
DEFAULT_SS_INCLUDE_SUBFOLDERS = False  # デフォルトはOFF（子フォルダを含めない）


# ===========================
# 4. AI 処理パラメータ
# ===========================
DEFAULT_AI_THRESHOLD = 0.65      # 類似度スコアのデフォルト閾値
MIN_AI_THRESHOLD = 0.0
MAX_AI_THRESHOLD = 1.0

AI_BATCH_SLEEP = 0.01            # CPU負荷軽減のためのスリープ時間（秒）
VECTOR_PROCESSING_TIMEOUT = 300  # ベクトル処理のタイムアウト（秒）


# ===========================
# 5. ベクトル表示設定
# ===========================
VECTOR_INTERPRETATION_MODES = ["labels", "shap", "custom"]  # 利用可能な解釈モード
DEFAULT_INTERPRETATION_MODE = "labels"  # デフォルト解釈モード

# 特徴カテゴリ表示フラグのデフォルト値
DEFAULT_SHOW_COLOR_FEATURES = True         # 色彩特徴
DEFAULT_SHOW_EDGE_FEATURES = True          # エッジ・線特徴
DEFAULT_SHOW_TEXTURE_FEATURES = True       # テクスチャ・パターン特徴
DEFAULT_SHOW_SHAPE_FEATURES = True         # 形状特徴
DEFAULT_SHOW_SEMANTIC_FEATURES = True      # セマンティック特徴

MAX_VECTOR_DIMENSIONS_DISPLAY = 10         # 表示する最大ベクトル次元数
VECTOR_SIMILARITY_THRESHOLD = 0.05         # 表示の最小類似度スコア


# ===========================
# 6. 画像ファイル設定
# ===========================
SUPPORTED_IMAGE_FORMATS = (
    '.jpg', '.jpeg', '.png',
    '.webp', '.bmp', '.gif'
)

THUMBNAIL_MAX_WIDTH = 150
THUMBNAIL_MAX_HEIGHT = 150
IMAGE_QUALITY_JPEG = 85  # JPEGの品質設定

# 画像表示サイズ設定
DEFAULT_IMAGE_MIN_WIDTH = 100      # 画像表示の最小幅（ピクセル）
DEFAULT_IMAGE_MIN_HEIGHT = 100     # 画像表示の最小高さ（ピクセル）
DEFAULT_IMAGE_MAX_WIDTH = 0        # 画像表示の最大幅（ピクセル、0で画面サイズの80%を使用）
DEFAULT_IMAGE_MAX_HEIGHT = 0       # 画像表示の最大高さ（ピクセル、0で画面サイズの80%を使用）

MIN_IMAGE_SIZE_LIMIT = 50          # 設定可能な最小サイズ
MAX_IMAGE_SIZE_LIMIT = 10000       # 設定可能な最大サイズ


# ===========================
# 7. UI 色設定
# ===========================
# CPU表示の色
COLOR_CPU_LOW = "#e0ffe0"        # CPU低負荷時（淡緑）
COLOR_CPU_HIGH = "#ff8080"       # CPU高負荷時（淡赤）
COLOR_CPU_THRESHOLD = 50         # CPU使用率の色切り替え閾値（%）

# 移動先フォルダの背景色
COLOR_MOVE_BG_1 = "#e0ffe0"      # 移動先背景色1（淡緑）
COLOR_MOVE_BG_2 = "#f0ffe0"      # 移動先背景色2（淡黄緑）

# その他UI要素の色
COLOR_REGISTER_BG = "#e0f0ff"    # 登録エリア背景色（淡青）
COLOR_STATUS_FG = "#000000"      # ステータステキスト色（黒）


# ===========================
# 8. ファイルパス定数
# ===========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TAG_CSV_FILE = os.path.join(DATA_DIR, "tagdata.csv")
VECTOR_DATA_FILE = os.path.join(DATA_DIR, "vectordata.json")
RATING_DATA_FILE = os.path.join(DATA_DIR, "ratings.json")
CONFIG_FILE = "config.json"
LOG_DIR = "logs"


# ===========================
# 9. デフォルト設定辞書
# ===========================
def get_default_config():
    """デフォルト設定を辞書で返す関数
    
    Returns:
        dict: デフォルト設定値
    """
    return {
        "last_folder": os.getcwd(),
        "geometries": {
            "main": "",
            "folder": "",
            "file": ""
        },
        "settings": {
            "random_pos": False,
            "topmost": True,
            "show_folder": True,
            "show_file": True,
            "rating_window_geometry": None,  # 評価ウィンドウの位置とサイズ
            "show_rating_window": True,     # 評価ウィンドウを表示するかどうか
            "vector_window_geometry": None,  # ベクトルウィンドウの位置とサイズ
            "show_vector_window": False,     # ベクトルウィンドウを表示するかどうか
            
            # --- ベクトル検索設定 ---
            "show_info_window": False,           # 情報ウィンドウ表示（デフォルトOFF）
            "ss_mode": False,
            "ss_interval": DEFAULT_SS_INTERVAL,
            "ss_ai_mode": False,
            "ss_ai_threshold": DEFAULT_AI_THRESHOLD,
            "move_dest_list": [""] * MOVE_DESTINATION_SLOTS,
            "move_reg_idx": 0,
            "move_dest_count": MOVE_DESTINATION_MIN,
            "cpu_low_color": COLOR_CPU_LOW,
            "cpu_high_color": COLOR_CPU_HIGH,
        },
        "vector_display": {
            "enabled": True,
            "interpretation_mode": DEFAULT_INTERPRETATION_MODE,
            "show_color_features": DEFAULT_SHOW_COLOR_FEATURES,
            "show_edge_features": DEFAULT_SHOW_EDGE_FEATURES,
            "show_texture_features": DEFAULT_SHOW_TEXTURE_FEATURES,
            "show_shape_features": DEFAULT_SHOW_SHAPE_FEATURES,
            "show_semantic_features": DEFAULT_SHOW_SEMANTIC_FEATURES,
            "max_dimensions_to_show": MAX_VECTOR_DIMENSIONS_DISPLAY,
            "similarity_threshold": VECTOR_SIMILARITY_THRESHOLD,
            "show_internal_values": False,       # 内部数値の表示（デフォルトOFF）
            "auto_vectorize": True,             # 未登録時に自動で計算する（デフォルトON）
        },
        "rating_ui": {
            "text_font_size": 10,      # 評価テキストのフォントサイズ
            "star_font_size": 16,      # 星のフォントサイズ
            "layout_order": ["text", "stars", "settings"],  # UI要素の順序
            "window_width": 320,       # ウィンドウ幅
            "window_height": 140,      # ウィンドウ高さ
            "position_x": 50,          # X座標（%）
            "position_y": 85,          # Y座標（%）
            "padding_x": 10,           # 水平パディング
            "padding_y": 8,            # 垂直パディング
            "margin": 15,              # ウィンドウ外側マージン
        }
    }


# ===========================
# 10. ウィンドウサイズ計算関数
# ===========================
def calculate_folder_window_width(max_item_length: int) -> int:
    """フォルダウィンドウの推奨幅を計算するのじゃ。
    
    Args:
        max_item_length (int): 最長のフォルダ名の文字数
        
    Returns:
        int: 推奨ウィンドウ幅（ピクセル）
        
    Example:
        >>> calculate_folder_window_width(20)
        260  # 20 * 10 + 60
    """
    calculated = max_item_length * FOLDER_WINDOW_CHAR_MULTIPLIER + FOLDER_WINDOW_WIDTH_OFFSET
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, calculated))


def calculate_folder_window_height(item_count: int) -> int:
    """フォルダウィンドウの推奨高さを計算するのじゃ。
    
    Args:
        item_count (int): フォルダ項目数（現在地を含む）
        
    Returns:
        int: 推奨ウィンドウ高さ（ピクセル）
        
    Example:
        >>> calculate_folder_window_height(5)
        190  # 5 * 20 + 90
    """
    calculated = item_count * FOLDER_WINDOW_HEIGHT_MULTIPLIER + FOLDER_WINDOW_HEIGHT_OFFSET
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, calculated))


def calculate_file_window_width(max_item_length: int) -> int:
    """ファイルウィンドウの推奨幅を計算するのじゃ。
    
    Args:
        max_item_length (int): 最長のファイル名の文字数
        
    Returns:
        int: 推奨ウィンドウ幅（ピクセル）
        
    Example:
        >>> calculate_file_window_width(25)
        280  # 25 * 8 + 80
    """
    calculated = max_item_length * FILE_WINDOW_CHAR_MULTIPLIER + FILE_WINDOW_WIDTH_OFFSET
    return max(MIN_WINDOW_WIDTH, min(MAX_WINDOW_WIDTH, calculated))


def calculate_file_window_height(item_count: int) -> int:
    """ファイルウィンドウの推奨高さを計算するのじゃ。
    
    Args:
        item_count (int): ファイル項目数
        
    Returns:
        int: 推奨ウィンドウ高さ（ピクセル）
        
    Example:
        >>> calculate_file_window_height(10)
        270  # 10 * 20 + 70
    """
    calculated = item_count * FILE_WINDOW_HEIGHT_MULTIPLIER + FILE_WINDOW_HEIGHT_OFFSET
    return max(MIN_WINDOW_HEIGHT, min(MAX_WINDOW_HEIGHT, calculated))


def get_move_grid_columns(move_count: int) -> int:
    """移動先グリッドの列数を取得するのじゃ。
    
    Args:
        move_count (int): 移動先スロット数
        
    Returns:
        int: グリッドの列数
        
    Example:
        >>> get_move_grid_columns(2)
        2
        >>> get_move_grid_columns(6)
        3
    """
    if move_count <= 3:
        return MOVE_GRID_COLUMNS_SINGLE  # 2列
    else:
        return MOVE_GRID_COLUMNS_MULTI   # 3列


def validate_ai_threshold(value: float) -> bool:
    """AI類似度スコア閾値の妥当性をチェック。
    
    Args:
        value (float): チェックする値
        
    Returns:
        bool: 有効な値の場合 True、無効な場合 False
    """
    try:
        return MIN_AI_THRESHOLD <= float(value) <= MAX_AI_THRESHOLD
    except (ValueError, TypeError):
        return False


def validate_move_count(count: int) -> bool:
    """移動先スロット数の妥当性をチェック。
    
    Args:
        count (int): チェックする値
        
    Returns:
        bool: 有効な値の場合 True、無効な場合 False
    """
    return count in MOVE_DESTINATION_OPTIONS


def validate_ss_interval(interval: int) -> bool:
    """スクリーンセーバー間隔の妥当性をチェック。
    
    Args:
        interval (int): チェックする値
        
    Returns:
        bool: 有効な値の場合 True、無効な場合 False
    """
    try:
        val = int(interval)
        return MIN_SS_INTERVAL <= val <= MAX_SS_INTERVAL
    except (ValueError, TypeError):
        return False


# ===========================
# 11. 評価UIプリセット
# ===========================
# サイズプリセット
RATING_SIZE_PRESETS = {
    "小": {"width": 280, "height": 120},
    "中": {"width": 320, "height": 140},
    "大": {"width": 380, "height": 160}
}

# 位置プリセット（画面上の9つの位置）
RATING_POSITION_PRESETS = {
    "左上": {"x": 5, "y": 5},
    "中央上": {"x": 50, "y": 5},
    "右上": {"x": 95, "y": 5},
    "左中央": {"x": 5, "y": 50},
    "中央": {"x": 50, "y": 50},
    "右中央": {"x": 95, "y": 50},
    "左下": {"x": 5, "y": 85},
    "中央下": {"x": 50, "y": 85},
    "右下": {"x": 95, "y": 85}
}


# ===========================
# 12. ログ設定
# ===========================
LOG_LEVEL_DEBUG = "DEBUG"
LOG_LEVEL_INFO = "INFO"
LOG_LEVEL_WARNING = "WARNING"
LOG_LEVEL_ERROR = "ERROR"

DEFAULT_LOG_LEVEL = LOG_LEVEL_INFO
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


if __name__ == "__main__":
    # テスト用のスクリプト
    print("=== config_defaults.py テスト ===\n")
    
    print("デフォルト設定:")
    config = get_default_config()
    print(f"  last_folder: {config['last_folder']}")
    print(f"  move_dest_count: {config['settings']['move_dest_count']}")
    print(f"  ss_interval: {config['settings']['ss_interval']}\n")
    
    print("ウィンドウサイズ計算:")
    print(f"  フォルダ幅 (max=20): {calculate_folder_window_width(20)}")
    print(f"  フォルダ高 (count=5): {calculate_folder_window_height(5)}")
    print(f"  ファイル幅 (max=25): {calculate_file_window_width(25)}")
    print(f"  ファイル高 (count=10): {calculate_file_window_height(10)}\n")
    
    print("グリッド列数:")
    print(f"  2個: {get_move_grid_columns(2)}")
    print(f"  6個: {get_move_grid_columns(6)}")
    print(f"  12個: {get_move_grid_columns(12)}\n")
    
    print("バリデーション:")
    print(f"  AI閾値 0.5: {validate_ai_threshold(0.5)}")
    print(f"  AI閾値 1.5: {validate_ai_threshold(1.5)}")
    print(f"  移動先個数 6: {validate_move_count(6)}")
    print(f"  移動先個数 5: {validate_move_count(5)}")
    print(f"  SS間隔 10: {validate_ss_interval(10)}")
    print(f"  SS間隔 120: {validate_ss_interval(120)}")
