import tkinter as tk

from GazoToolsLogic import get_label_text


def test_get_label_text_handles_none():
    root = tk.Tk()
    try:
        label = tk.Label(root, text=None)
        assert get_label_text(label) == ""
    finally:
        root.destroy()
