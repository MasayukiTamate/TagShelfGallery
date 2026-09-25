'''
タグ絞り込みUIのスモークテスト

サムネイル窓の NOT フィルタと、タグ一覧窓の含む/除外トグルを
実際のウィジェットを組み立てて確認する。
画面が無い環境では自動的にスキップする。
'''
import os

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def root():
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        pytest.skip("画面が無い環境ではUIテストを行いません")
    try:
        instance = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk を起動できません: {exc}")
    instance.withdraw()
    yield instance
    instance.destroy()


class FakeControl:
    """GazoPicture の代わり。タグ辞書と同期呼び出しの記録だけを持つ。"""

    def __init__(self, tag_dict):
        self.tag_dict = tag_dict
        self.open_windows = {}
        self.synced = []

    def sync_xattr_for(self, file_path, image_hash):
        self.synced.append((file_path, image_hash))
        return True

    def set_image_tag(self, window, image_hash):
        return None


@pytest.fixture
def images(tmp_path):
    """内容の違う3枚を作り、パスとハッシュを返す。"""
    from GazoToolsLogic import calculate_file_hash

    paths = []
    for index, body in enumerate([b"cat-outdoor", b"cat-indoor", b"dog"]):
        path = tmp_path / f"img_{index}.png"
        path.write_bytes(body)
        paths.append(str(path))
    return paths, [calculate_file_hash(p) for p in paths]


@pytest.fixture
def tag_dict(images):
    _, hashes = images
    return {
        hashes[0]: {"tag": "猫; 屋外", "hint": "img_0.png", "rating": None},
        hashes[1]: {"tag": "猫; 室内", "hint": "img_1.png", "rating": None},
        # 3枚目はタグ無し
    }


@pytest.fixture
def panel(root, images, tag_dict):
    from lib.GazoToolsGUI import ThumbnailPanelWindow, get_tag_filter_state

    state = get_tag_filter_state()
    state.clear_filter()
    paths, _ = images
    window = ThumbnailPanelWindow(root, files=paths, gazo_control=FakeControl(tag_dict))
    window.withdraw()
    yield window
    state.clear_filter()
    window.destroy()


# ---------------------------------------------------------------- サムネイル窓


def test_panel_shows_everything_without_filters(panel, images):
    paths, _ = images
    assert sorted(panel.files) == sorted(paths)


def test_panel_not_filter_hides_matching_images(panel, images):
    paths, _ = images
    panel.exclude_tag_var.set("室内")
    panel._apply_exclude_input()

    assert paths[1] not in panel.files
    assert paths[0] in panel.files
    assert paths[2] in panel.files


def test_panel_not_filter_accepts_multiple_tags(panel, images):
    paths, _ = images
    panel.exclude_tag_var.set("室内; 屋外")
    panel._apply_exclude_input()

    assert panel.files == [paths[2]]


def test_panel_clear_exclude_restores_all(panel, images):
    paths, _ = images
    panel.exclude_tag_var.set("猫")
    panel._apply_exclude_input()
    assert len(panel.files) == 1

    panel._clear_exclude_input()
    assert sorted(panel.files) == sorted(paths)


def test_panel_combines_untagged_only_with_not_filter(panel, images):
    """「タグ未設定のみ」と除外タグは重ねて効く。"""
    paths, _ = images
    panel.untagged_only_var.set(True)
    panel.exclude_tag_var.set("室内")
    panel._apply_exclude_input()

    assert panel.files == [paths[2]]


def test_panel_combines_include_and_exclude(panel, images):
    from lib.GazoToolsGUI import get_tag_filter_state

    paths, _ = images
    state = get_tag_filter_state()
    state.set_active_filter(["猫"])
    panel.exclude_tag_var.set("室内")
    panel._apply_exclude_input()

    assert panel.files == [paths[0]]


def test_panel_status_line_reports_counts(panel):
    panel.exclude_tag_var.set("室内")
    panel._apply_exclude_input()
    status = panel.filter_status_var.get()
    assert "除外: 室内" in status
    assert "2/3 件" in status


def test_panel_sync_filter_inputs_picks_up_external_change(panel):
    from lib.GazoToolsGUI import get_tag_filter_state

    get_tag_filter_state().set_exclude_filter(["犬"])
    panel.apply_filters()
    assert panel.exclude_tag_var.get() == "犬"


def test_panel_notifies_other_windows_on_change(panel):
    calls = []
    panel.filter_changed_callback = lambda: calls.append(1)
    panel.exclude_tag_var.set("猫")
    panel._apply_exclude_input()
    assert calls == [1]


def test_panel_bulk_tagging_syncs_to_dolphin(panel, images):
    """選択した画像へのタグ付与が拡張属性の書き出しまで通ること。"""
    import lib.GazoToolsGUI as gui

    paths, _ = images
    panel.selected_paths = {paths[2]}
    gui.simpledialog.askstring = lambda *args, **kwargs: "新規タグ"
    gui.save_tags = lambda tags: None

    panel._apply_tag_to_selection()

    synced_paths = [entry[0] for entry in panel.gazo_control.synced]
    assert synced_paths == [paths[2]]


# ---------------------------------------------------------------- タグ一覧窓


@pytest.fixture
def tag_list(root, images, tag_dict, monkeypatch):
    from lib.GazoToolsGUI import TagListWindow, get_tag_filter_state
    from lib.GazoToolsState import get_app_state

    paths, _ = images
    get_app_state().current_folder = os.path.dirname(paths[0])
    state = get_tag_filter_state()
    state.clear_filter()

    applied = []
    window = TagListWindow(root, FakeControl(tag_dict), on_filter_applied=lambda: applied.append(1))
    window.withdraw()
    window.applied = applied
    yield window
    state.clear_filter()
    window.destroy()


class FakeEvent:
    def __init__(self, y):
        self.y = y


def test_tag_list_lists_every_tag_with_counts(tag_list):
    rows = tag_list.tag_listbox.get(0, tk.END)
    assert tag_list._tag_names == ["室内", "屋外", "猫"]
    assert "猫 (2)" in rows[2]


def test_tag_list_double_click_toggles_include(tag_list):
    from lib.GazoToolsGUI import get_tag_filter_state

    tag_list._on_tag_double_click(FakeEvent(y=0))
    assert get_tag_filter_state().active_filter == ["室内"]
    assert tag_list.tag_listbox.get(0).startswith("[+]")

    tag_list._on_tag_double_click(FakeEvent(y=0))
    assert get_tag_filter_state().active_filter == []
    assert tag_list.tag_listbox.get(0).startswith("[ ]")


def test_tag_list_right_click_toggles_exclude(tag_list):
    from lib.GazoToolsGUI import get_tag_filter_state

    tag_list._on_tag_right_click(FakeEvent(y=0))
    assert get_tag_filter_state().exclude_filter == ["室内"]
    assert tag_list.tag_listbox.get(0).startswith("[-]")


def test_tag_list_exclude_replaces_include_for_same_tag(tag_list):
    from lib.GazoToolsGUI import get_tag_filter_state

    state = get_tag_filter_state()
    tag_list._on_tag_double_click(FakeEvent(y=0))
    tag_list._on_tag_right_click(FakeEvent(y=0))

    assert state.active_filter == []
    assert state.exclude_filter == ["室内"]


def test_tag_list_keeps_counts_after_toggling(tag_list):
    """マーカーを付け替えても件数表示が壊れないこと。"""
    before = tag_list.tag_listbox.get(2)
    tag_list._on_tag_double_click(FakeEvent(y=0))
    after = tag_list.tag_listbox.get(2)
    assert before.split("(")[-1] == after.split("(")[-1]


def test_tag_list_clear_resets_both_sides(tag_list):
    from lib.GazoToolsGUI import get_tag_filter_state

    state = get_tag_filter_state()
    tag_list._on_tag_double_click(FakeEvent(y=0))
    tag_list._on_tag_right_click(FakeEvent(y=100))
    assert state.has_any_filter()

    tag_list._on_clear()
    assert state.active_filter == []
    assert state.exclude_filter == []


def test_tag_list_notifies_on_every_toggle(tag_list):
    tag_list._on_tag_double_click(FakeEvent(y=0))
    tag_list._on_tag_right_click(FakeEvent(y=0))
    assert len(tag_list.applied) == 2


def test_tag_list_status_line_describes_filters(tag_list):
    tag_list._on_tag_double_click(FakeEvent(y=0))
    assert "含む: 室内" in tag_list.status_var.get()
    tag_list._on_tag_right_click(FakeEvent(y=100))
    assert "除外:" in tag_list.status_var.get()


# ---------------------------------------------------------------- タグ編集窓のよく使うタグ


@pytest.fixture
def many_tags():
    """長いものを含む、数の多いタグ辞書。"""
    names = [
        "猫", "犬", "屋外", "室内", "夕焼け", "風景", "人物", "建物", "花", "空",
        "とても長いタグ名のサンプルです", "H/満", "H/ベッド", "H/恥じらい",
        "食べ物", "乗り物", "動物", "海", "山", "川", "夜景", "雪", "雨", "朝",
    ]
    return {f"hash{i}": {"tag": name, "hint": f"{i}.png", "rating": None}
            for i, name in enumerate(names)}, names


@pytest.fixture
def editor(root, many_tags):
    from lib.GazoToolsGUI import TagEditorWindow

    tag_dict, _ = many_tags
    window = TagEditorWindow(root, FakeControl(tag_dict))
    window.geometry("420x440")
    window.update_idletasks()
    window.update()
    yield window
    window.destroy()


def test_editor_shows_every_tag(editor, many_tags):
    """12個で打ち切らず、全タグ分のボタンがあること。"""
    _, names = many_tags
    assert sorted(editor._quick_buttons) == sorted(names)
    assert len(editor._quick_buttons) == len(names)


def test_editor_label_reports_count(editor, many_tags):
    _, names = many_tags
    assert f"({len(names)}件)" in editor.quick_label_var.get()


def test_editor_tags_wrap_into_multiple_rows(editor):
    """1行に詰め込まず、折り返して複数行になること。"""
    editor.update_idletasks()
    rows = {b.winfo_y() for b in editor._quick_buttons.values()}
    assert len(rows) > 1


def test_editor_no_tag_is_clipped_horizontally(editor):
    """どのタグも、スクロール範囲の右端からはみ出さないこと。"""
    editor.update_idletasks()
    region = editor.quick_canvas.cget("scrollregion")
    assert str(region).strip()
    right_edge = int(float(str(region).split()[2]))
    widest = max(b.winfo_x() + b.winfo_reqwidth() for b in editor._quick_buttons.values())
    assert right_edge >= widest


def test_editor_no_tag_is_clipped_vertically(editor):
    """入りきらない分もスクロール範囲に収まっていること。"""
    editor.update_idletasks()
    region = editor.quick_canvas.cget("scrollregion")
    bottom_edge = int(float(str(region).split()[3]))
    lowest = max(b.winfo_y() + b.winfo_reqheight() for b in editor._quick_buttons.values())
    assert bottom_edge >= lowest


def test_editor_relayouts_when_window_narrows(editor):
    """窓を狭めると行が増え、それでも全タグが残ること。"""
    editor.update_idletasks()
    before_rows = len({b.winfo_y() for b in editor._quick_buttons.values()})

    editor.geometry("240x440")
    editor.update()
    editor.update_idletasks()
    after_rows = len({b.winfo_y() for b in editor._quick_buttons.values()})

    assert after_rows >= before_rows
    assert len(editor._quick_buttons) == len(editor.quick_inner.winfo_children())


def test_editor_packs_several_tags_per_row(editor):
    """短いタグは同じ行に詰めて、縦に伸びすぎないこと。"""
    editor.update_idletasks()
    rows = {}
    for button in editor._quick_buttons.values():
        rows.setdefault(button.winfo_y(), []).append(button)
    assert max(len(group) for group in rows.values()) > 1


def test_editor_quick_tag_click_appends(editor):
    editor.tag_var.set("")
    editor._append_tag("猫")
    editor._append_tag("屋外")
    assert editor.tag_var.get() == "猫; 屋外"


def test_editor_refresh_picks_up_new_tags(editor):
    editor.gazo_control.tag_dict["新規"] = {"tag": "あとから足したタグ", "hint": "x.png", "rating": None}
    editor.refresh_quick_tags()
    editor.update_idletasks()
    assert "あとから足したタグ" in editor._quick_buttons
