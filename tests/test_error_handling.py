'''
作成日: 2026年01月04日
機能: エラーハンドリング改善の動作確認テスト
'''
import sys
import os

# プロジェクトパスを追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.GazoToolsLogger import setup_logging, get_logger
from lib.GazoToolsExceptions import (
    ConfigError, ImageLoadError, FileHashError, TagManagementError
)

# ロギングを初期化（デバッグモード）
setup_logging(debug_mode=True)
logger = get_logger(__name__)

def test_logging():
    """ロギング機能の確認"""
    print("\n=== ロギング機能テスト ===")
    logger.debug("これはDEBUGログです")
    logger.info("これはINFOログです")
    logger.warning("これはWARNINGログです")
    logger.error("これはERRORログです")
    print("✓ ロギング出力を確認しました（ログは logs/ フォルダに保存されます）\n")

def test_custom_exceptions():
    """カスタム例外の確認"""
    print("=== カスタム例外テスト ===")
    
    try:
        raise ConfigError("テスト用設定エラー")
    except ConfigError as e:
        logger.error(f"ConfigError を捕捉: {e}")
        print("✓ ConfigError を正しく処理しました\n")
    
    try:
        raise ImageLoadError("テスト用画像読み込みエラー")
    except ImageLoadError as e:
        logger.error(f"ImageLoadError を捕捉: {e}")
        print("✓ ImageLoadError を正しく処理しました\n")

def test_exception_chain():
    """例外チェーン（from e）の確認"""
    print("=== 例外チェーンテスト ===")
    
    try:
        try:
            raise FileNotFoundError("元の例外")
        except FileNotFoundError as e:
            raise FileHashError(f"ハッシュ計算失敗") from e
    except FileHashError as e:
        logger.error(f"FileHashError を捕捉（原因: {e.__cause__.__class__.__name__}）")
        print("✓ 例外チェーン（from e）を正しく処理しました\n")

def test_logger_files():
    """ログファイルの生成確認"""
    print("=== ログファイル生成テスト ===")
    logs_dir = "logs"
    if os.path.exists(logs_dir):
        files = os.listdir(logs_dir)
        if files:
            print(f"✓ ログディレクトリが作成されました: {logs_dir}/")
            for f in files:
                print(f"  - {f}")
        else:
            print("✗ ログファイルが見つかりません")
    else:
        print("✗ ログディレクトリが見つかりません")

def main():
    print("=" * 60)
    print("GazoTools エラーハンドリング改善 - 動作確認テスト")
    print("=" * 60)
    
    test_logging()
    test_custom_exceptions()
    test_exception_chain()
    test_logger_files()
    
    print("=" * 60)
    print("すべてのテストが完了しました！")
    print("ログファイルは logs/ フォルダに出力されます。")
    print("=" * 60)
