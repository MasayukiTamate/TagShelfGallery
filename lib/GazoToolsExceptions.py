'''
作成日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools 用のカスタム例外クラス定義
'''


class GazoToolsError(Exception):
    """GazoTools基底例外クラス"""
    pass


class ConfigError(GazoToolsError):
    """設定ファイル関連のエラー"""
    pass


class ImageLoadError(GazoToolsError):
    """画像読み込みエラー"""
    pass


class ImageProcessingError(GazoToolsError):
    """画像処理エラー（リサイズ、表示など）"""
    pass


class FileHashError(GazoToolsError):
    """ファイルハッシュ計算エラー"""
    pass


class TagManagementError(GazoToolsError):
    """タグ管理関連のエラー"""
    pass


class AIModelError(GazoToolsError):
    """AIモデル関連のエラー"""
    pass


class VectorProcessingError(GazoToolsError):
    """ベクトル化処理エラー"""
    pass


class FileOperationError(GazoToolsError):
    """ファイル移動・削除などのエラー"""
    pass


class FolderAccessError(GazoToolsError):
    """フォルダアクセスエラー"""
    pass


class UIError(GazoToolsError):
    """UI操作関連のエラー"""
    pass
