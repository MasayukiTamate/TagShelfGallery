'''
フォルダ名をタグとして付ける機能のテスト

直近の親フォルダ名だけをタグにし、既存タグは残し、
Dolphin の拡張属性にも書き出されることを確かめる。
'''
import os

import pytest

import GazoToolsLogic
from GazoToolsLogic import GazoPicture
from lib import GazoToolsXattrTags as xattr_tags
from lib.GazoToolsTagFilter import parse_tag_text


def _xattr_writable(path):
    if not xattr_tags.is_available():
        return False
    try:
        os.setxattr(path, b"user.gazotools.probe", b"1")
        os.removexattr(path, b"user.gazotools.probe")
        return True
    except OSError:
        return False


@pytest.fixture
def control(monkeypatch):
    monkeypatch.setattr(GazoToolsLogic, "save_tags", lambda tags: None)
    monkeypatch.setattr(GazoToolsLogic, "save_ratings", lambda ratings: None)
    picture = GazoPicture.__new__(GazoPicture)
    picture.open_windows = {}
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    return picture


@pytest.fixture
def folder(tmp_path):
    """「風景写真」フォルダに画像3枚、サブフォルダに1枚。"""
    base = tmp_path / "風景写真"
    base.mkdir()
    paths = []
    for index in range(3):
        path = base / f"img_{index}.png"
        path.write_bytes(f"image {index}".encode("utf-8"))
        paths.append(str(path))
    sub = base / "夜景"
    sub.mkdir()
    sub_path = sub / "night.png"
    sub_path.write_bytes(b"night image")

    if not _xattr_writable(paths[0]):
        pytest.skip("このファイルシステムは拡張属性に対応していません")
    return str(base), paths, str(sub_path)


def _tags_of(control, path):
    return parse_tag_text(control.tag_dict[GazoToolsLogic.calculate_file_hash(path)]["tag"])


# ---------------------------------------------------------------- 付与


def test_adds_parent_folder_name_only(control, folder):
    _base, paths, _sub = folder

    tagged, names = control.apply_folder_tag(paths)

    assert tagged == 3
    assert names == ["風景写真"]
    for path in paths:
        assert _tags_of(control, path) == ["風景写真"]


def test_does_not_use_full_path_as_tag(control, folder):
    """階層ではなく、直近の親の名前だけを使うこと。"""
    _base, paths, _sub = folder
    control.apply_folder_tag(paths[:1])
    assert "/" not in _tags_of(control, paths[0])[0]


def test_keeps_existing_tags(control, folder):
    _base, paths, _sub = folder
    image_hash = GazoToolsLogic.calculate_file_hash(paths[0])
    control.tag_dict[image_hash] = {"tag": "猫; 屋外", "hint": "", "rating": None}

    control.apply_folder_tag([paths[0]])

    assert _tags_of(control, paths[0]) == ["猫", "屋外", "風景写真"]


def test_running_twice_adds_nothing(control, folder):
    _base, paths, _sub = folder
    control.apply_folder_tag(paths)

    tagged, names = control.apply_folder_tag(paths)

    assert tagged == 0
    assert names == []
    assert _tags_of(control, paths[0]) == ["風景写真"]


def test_uses_each_files_own_folder(control, folder):
    """別フォルダのファイルが混ざっても、それぞれの親の名前が付く。"""
    _base, paths, sub_path = folder

    tagged, names = control.apply_folder_tag([paths[0], sub_path])

    assert tagged == 2
    assert sorted(names) == ["夜景", "風景写真"]
    assert _tags_of(control, paths[0]) == ["風景写真"]
    assert _tags_of(control, sub_path) == ["夜景"]


def test_writes_tag_to_dolphin_xattr(control, folder):
    _base, paths, _sub = folder

    control.apply_folder_tag([paths[0]])

    assert xattr_tags.read_tags(paths[0]) == ["風景写真"]


def test_folder_name_with_separator_is_sanitized(tmp_path, control):
    """フォルダ名に区切り文字が入っていても1つのタグになること。"""
    base = tmp_path / "猫,犬"
    base.mkdir()
    path = base / "x.png"
    path.write_bytes(b"x")
    if not _xattr_writable(str(path)):
        pytest.skip("このファイルシステムは拡張属性に対応していません")

    tagged, names = control.apply_folder_tag([str(path)])

    assert tagged == 1
    assert names == ["猫／犬"]
    assert xattr_tags.read_tags(str(path)) == ["猫／犬"]


def test_ignores_missing_paths(control, tmp_path):
    tagged, names = control.apply_folder_tag([str(tmp_path / "ない.png")])
    assert (tagged, names) == (0, [])


def test_empty_input_is_safe(control):
    assert control.apply_folder_tag([]) == (0, [])
    assert control.apply_folder_tag(None) == (0, [])


# ---------------------------------------------------------------- 対象集め


def test_collect_images_in_folder_skips_subfolders(control, folder):
    base, paths, _sub = folder
    found = control.collect_images_in_folder(base)
    assert sorted(found) == sorted(paths)


def test_collect_images_can_include_subfolders(control, folder):
    base, paths, sub_path = folder
    found = control.collect_images_in_folder(base, include_subfolders=True)
    assert sorted(found) == sorted(paths + [sub_path])


def test_collect_images_on_missing_folder(control, tmp_path):
    assert control.collect_images_in_folder(str(tmp_path / "ない")) == []
    assert control.collect_images_in_folder(None) == []
