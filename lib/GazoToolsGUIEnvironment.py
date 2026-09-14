"""Linux GUI 環境検出と起動可否判定の独立モジュール。"""

import os
import sys


def get_gui_environment_status():
    """GUI 環境が使えるかを判定して、その理由を返す。"""
    display = os.environ.get("DISPLAY")
    wayland = os.environ.get("WAYLAND_DISPLAY")

    is_gui_capable = bool(display or wayland)
    if is_gui_capable:
        return {
            "is_gui_capable": True,
            "display": display,
            "wayland": wayland,
            "reason": "GUI environment is available.",
        }

    return {
        "is_gui_capable": False,
        "display": display,
        "wayland": wayland,
        "reason": (
            "GazoTools を起動できません。\n"
            "Linux のデスクトップ GUI 環境が見つかりません。\n"
            "DISPLAY / WAYLAND_DISPLAY が未設定です。\n"
            "X11 または Wayland を使うデスクトップセッションで実行してください。"
        ),
    }


def ensure_gui_environment():
    """Tkinter と tkinterdnd2 が使えるかを確認し、失敗時は明確なメッセージを投げる。"""
    status = get_gui_environment_status()
    if not status["is_gui_capable"]:
        raise RuntimeError(status["reason"])

    try:
        import tkinter  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "GazoTools を起動できません。\n"
            "Python の tkinter がインストールされていません。\n"
            "python -m pip install tk を実行してください。"
        ) from exc

    if "tkinterdnd2" not in sys.modules:
        try:
            import tkinterdnd2  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(
                "GazoTools を起動できません。\n"
                "tkinterdnd2 がインストールされていません。\n"
                "python -m pip install tkinterdnd2 を実行してください。"
            ) from exc

    return True
