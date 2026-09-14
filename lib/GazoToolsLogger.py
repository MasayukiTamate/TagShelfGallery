'''
作成日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools 用のロギング設定・管理
'''
import logging
import os
from datetime import datetime


class LoggerManager:
    """ロギング設定を一元管理するクラス"""

    _loggers = {}
    _log_dir = "logs"
    _debug_mode = False
    _error_backlog = []
    _backlog_limit = 50
    _backlog_callbacks = []

    @classmethod
    def setup(cls, debug_mode=False):
        """ロギングを初期化する
        
        Args:
            debug_mode (bool): デバッグモード有効時は詳細ログを出力
        """
        cls._debug_mode = debug_mode

        # ログディレクトリを作成
        if not os.path.exists(cls._log_dir):
            os.makedirs(cls._log_dir, exist_ok=True)

        log_level = logging.DEBUG if debug_mode else logging.INFO
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)

        for handler in list(root_logger.handlers):
            if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
            elif isinstance(handler, logging.FileHandler):
                root_logger.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        error_log_path = os.path.join(
            cls._log_dir,
            f"error_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(error_log_path, encoding='utf-8')
        file_handler.setLevel(logging.WARNING)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
    
    @classmethod
    def get_logger(cls, name):
        """特定のモジュール用ロガーを取得
        
        Args:
            name (str): モジュール名（通常は __name__）
        
        Returns:
            logging.Logger: ロガーインスタンス
        """
        if name not in cls._loggers:
            logger = logging.getLogger(name)
            cls._loggers[name] = logger
        return cls._loggers[name]
    
    @classmethod
    def record_error(cls, category, message, **context):
        """エラーのバックログを記録する。再発時の切り分け用にコンテキストを残す。"""
        entry = {
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "category": str(category),
            "message": str(message),
        }
        for key, value in context.items():
            if value is None:
                entry[key] = "None"
            elif isinstance(value, (str, int, float, bool)):
                entry[key] = value
            else:
                entry[key] = str(value)

        cls._error_backlog.insert(0, entry)
        cls._error_backlog = cls._error_backlog[:cls._backlog_limit]
        for callback in list(cls._backlog_callbacks):
            try:
                callback(entry)
            except Exception:
                pass
        return entry

    @classmethod
    def get_recent_error_backlog(cls, limit=20):
        return list(cls._error_backlog[:limit])

    @classmethod
    def format_error_backlog(cls, limit=20):
        entries = cls.get_recent_error_backlog(limit)
        if not entries:
            return "エラー履歴はありません"

        lines = []
        for item in entries:
            parts = [f"[{item['timestamp']}] {item['category']}: {item['message']}"]
            for key in sorted(item.keys()):
                if key in {"timestamp", "category", "message"}:
                    continue
                parts.append(f"{key}={item[key]}")
            lines.append(" | ".join(parts))
        return "\n".join(lines)

    @classmethod
    def register_backlog_callback(cls, callback):
        if callback not in cls._backlog_callbacks:
            cls._backlog_callbacks.append(callback)

    @classmethod
    def unregister_backlog_callback(cls, callback):
        if callback in cls._backlog_callbacks:
            cls._backlog_callbacks.remove(callback)

    @classmethod
    def is_debug_mode(cls):
        """デバッグモードの状態を確認
        
        Returns:
            bool: デバッグモードが有効ならTrue
        """
        return cls._debug_mode

    @classmethod
    def enable_debug_mode(cls):
        """デバッグモードを有効にする"""
        cls._debug_mode = True
        for logger in cls._loggers.values():
            logger.setLevel(logging.DEBUG)
            for handler in logger.handlers:
                handler.setLevel(logging.DEBUG)
    
    @classmethod
    def disable_debug_mode(cls):
        """デバッグモードを無効にする"""
        cls._debug_mode = False
        for logger in cls._loggers.values():
            logger.setLevel(logging.INFO)
            for handler in logger.handlers:
                handler.setLevel(logging.INFO)


# グローバルロガーの初期化
def setup_logging(debug_mode=False):
    """ロギングシステムをセットアップ"""
    LoggerManager.setup(debug_mode=debug_mode)


def get_logger(name):
    """モジュール別ロガーを取得"""
    return LoggerManager.get_logger(name)


def record_error(category, message, **context):
    """エラー履歴を記録する."""
    return LoggerManager.record_error(category, message, **context)
