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
