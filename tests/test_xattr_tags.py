'''
Dolphin (KDE) 互換タグ連携のテスト

user.xdg.tags / user.baloo.rating の読み書きと、
GazoTools 側のハッシュキー方式タグ辞書との和集合マージを確認する。
'''
import os

import pytest

from lib import GazoToolsXattrTags as xattr_tags
from lib.GazoToolsTagFilter import filter_file_names_by_tags, get_tag_filter_state


def _xattr_writable(path):
    """このファイルシステムで拡張属性が書けるか確かめる。"""
    if not xattr_tags.is_available():
        return False
    try:
        os.setxattr(path, b"user.gazotools.probe", b"1")
        os.removexattr(path, b"user.gazotools.probe")
        return True
    except OSError:
        return False


@pytest.fixture
def tagged_file(tmp_path):
    path = tmp_path / "sample.png"
    path.write_bytes(b"dummy image content")
    if not _xattr_writable(str(path)):
        pytest.skip("このファイルシステムは拡張属性に対応していません")
    return str(path)


# ---------------------------------------------------------------- 変換


def test_stars_to_baloo_is_double_the_stars():
    assert xattr_tags.stars_to_baloo(0) == 0
    assert xattr_tags.stars_to_baloo(3) == 6
    assert xattr_tags.stars_to_baloo(5) == 10


def test_stars_to_baloo_clamps_out_of_range():
    assert xattr_tags.stars_to_baloo(-2) == 0
    assert xattr_tags.stars_to_baloo(99) == 10
    assert xattr_tags.stars_to_baloo(None) == 0


def test_baloo_to_stars_round_trips():
    for stars in range(0, 6):
        assert xattr_tags.baloo_to_stars(xattr_tags.stars_to_baloo(stars)) == stars


def test_normalize_tags_removes_separators_and_duplicates():
    tags = xattr_tags.normalize_tags(["  猫  ", "猫", "犬,狐", "", None])
    assert tags == ["猫", "犬／狐"]


# ---------------------------------------------------------------- 読み書き


def test_write_and_read_tags_round_trip(tagged_file):
    assert xattr_tags.write_tags(tagged_file, ["H", "H/満", "風景"])
    assert xattr_tags.read_tags(tagged_file) == ["H", "H/満", "風景"]


def test_written_tags_use_dolphin_comma_format(tagged_file):
    xattr_tags.write_tags(tagged_file, ["猫", "屋外"])
    raw = os.getxattr(tagged_file, b"user.xdg.tags").decode("utf-8")
    assert raw == "猫,屋外"


def test_read_tags_on_untagged_file_returns_empty(tagged_file):
    assert xattr_tags.read_tags(tagged_file) == []


def test_write_empty_tags_removes_attribute(tagged_file):
    xattr_tags.write_tags(tagged_file, ["猫"])
    assert xattr_tags.write_tags(tagged_file, [])
    assert xattr_tags.read_tags(tagged_file) == []
    with pytest.raises(OSError):
        os.getxattr(tagged_file, b"user.xdg.tags")


def test_write_and_read_rating_round_trip(tagged_file):
    assert xattr_tags.write_rating(tagged_file, 4)
    assert os.getxattr(tagged_file, b"user.baloo.rating").decode("utf-8") == "8"
    assert xattr_tags.read_rating(tagged_file) == 4


def test_write_rating_none_removes_attribute(tagged_file):
    xattr_tags.write_rating(tagged_file, 5)
    assert xattr_tags.write_rating(tagged_file, None)
    assert xattr_tags.read_rating(tagged_file) is None


def test_read_all_returns_tags_and_stars(tagged_file):
    xattr_tags.write_tags(tagged_file, ["猫"])
    xattr_tags.write_rating(tagged_file, 2)
    assert xattr_tags.read_all(tagged_file) == {"tags": ["猫"], "stars": 2}


def test_missing_file_is_handled_quietly(tmp_path):
    ghost = str(tmp_path / "存在しない.png")
    assert xattr_tags.read_tags(ghost) == []
    assert xattr_tags.read_rating(ghost) is None
    assert xattr_tags.write_tags(ghost, ["猫"]) is False


# ---------------------------------------------------------------- NOT フィルタ


def test_exclude_tags_filter_out_matching_files():
    tag_map = {
        "h1": {"tag": "猫; 屋外"},
        "h2": {"tag": "猫; 室内"},
        "h3": {"tag": "犬"},
    }
    path_to_hash = {"a.png": "h1", "b.png": "h2", "c.png": "h3"}
    names = ["a.png", "b.png", "c.png"]

    assert filter_file_names_by_tags(names, path_to_hash, tag_map, [], exclude_tags=["室内"]) == ["a.png", "c.png"]


def test_exclude_wins_over_include():
    tag_map = {"h1": {"tag": "猫; 室内"}}
    path_to_hash = {"a.png": "h1"}
    assert filter_file_names_by_tags(["a.png"], path_to_hash, tag_map, ["猫"], "and", ["室内"]) == []


def test_include_and_exclude_combined():
    tag_map = {
        "h1": {"tag": "猫; 屋外"},
        "h2": {"tag": "猫; 室内"},
        "h3": {"tag": "屋外"},
    }
    path_to_hash = {"a.png": "h1", "b.png": "h2", "c.png": "h3"}
    names = ["a.png", "b.png", "c.png"]
    assert filter_file_names_by_tags(names, path_to_hash, tag_map, ["猫"], "and", ["室内"]) == ["a.png"]


def test_no_filters_returns_everything_unchanged():
    names = ["a.png", "b.png"]
    assert filter_file_names_by_tags(names, {}, {}, [], exclude_tags=[]) == names


def test_filter_state_toggles_are_mutually_exclusive():
    state = get_tag_filter_state()
    state.clear_filter()
    try:
        state.toggle_include_tag("猫")
        assert state.active_filter == ["猫"]

        # 同じタグを除外にすると、含む側からは外れる
        state.toggle_exclude_tag("猫")
        assert state.active_filter == []
        assert state.exclude_filter == ["猫"]

        # もう一度押すと解除
        state.toggle_exclude_tag("猫")
        assert state.exclude_filter == []
        assert state.has_any_filter() is False
    finally:
        state.clear_filter()
