import os

from lib.GazoToolsGUIEnvironment import get_gui_environment_status


def test_gui_environment_status_fails_without_display(monkeypatch):
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    status = get_gui_environment_status()

    assert status["is_gui_capable"] is False
    assert "DISPLAY" in status["reason"]
    assert "WAYLAND_DISPLAY" in status["reason"]


def test_gui_environment_status_succeeds_with_display(monkeypatch):
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    status = get_gui_environment_status()

    assert status["is_gui_capable"] is True
    assert status["reason"] == "GUI environment is available."
