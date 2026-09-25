'''
GazoPicture 側の Dolphin タグ同期のテスト

タグ辞書(ハッシュキー)と拡張属性(パス基準)の間の
書き出し・取り込み(和集合)・評価のマッピングを確認する。
実際の data/tagdata.csv を書き換えないよう save_tags は差し替える。
'''
import os

import pytest

import GazoToolsLogic
from GazoToolsLogic import GazoPicture
from lib import GazoToolsXattrTags as xattr_tags


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
    """保存を伴わない、最小構成の GazoPicture を用意する。"""
    saved = {"tags": 0, "ratings": 0}
    monkeypatch.setattr(GazoToolsLogic, "save_tags", lambda tags: saved.__setitem__("tags", saved["tags"] + 1))
    monkeypatch.setattr(GazoToolsLogic, "save_ratings", lambda ratings: saved.__setitem__("ratings", saved["ratings"] + 1))

    picture = GazoPicture.__new__(GazoPicture)
    picture.open_windows = {}
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    picture.save_counts = saved
    return picture


@pytest.fixture
def image_file(tmp_path):
    path = tmp_path / "画像.png"
    path.write_bytes(b"gazotools test image")
    if not _xattr_writable(str(path)):
        pytest.skip("このファイルシステムは拡張属性に対応していません")
    return str(path)


def _hash_of(path):
    return GazoToolsLogic.calculate_file_hash(path)


# ---------------------------------------------------------------- 書き出し


def test_sync_writes_tags_to_xattr(control, image_file):
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫; 屋外", "hint": "画像.png", "rating": None}

    assert control.sync_xattr_for(image_file, image_hash)
    assert xattr_tags.read_tags(image_file) == ["猫", "屋外"]


def test_sync_writes_rating_as_double_custom_rating(control, image_file):
    image_hash = _hash_of(image_file)
    control.rating_dict["星4"] = {"name": "星4", "rating": 1, "linked": True, "custom_rating": 4}
    control.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None, "assigned_rating": "星4"}

    control.sync_xattr_for(image_file, image_hash)
    assert os.getxattr(image_file, b"user.baloo.rating").decode("utf-8") == "8"


def test_sync_removing_all_tags_clears_xattr(control, image_file):
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫", "hint": "", "rating": None}
    control.sync_xattr_for(image_file, image_hash)

    control.tag_dict[image_hash]["tag"] = ""
    control.sync_xattr_for(image_file, image_hash)
    assert xattr_tags.read_tags(image_file) == []


def test_sync_for_hash_resolves_path_from_index(control, image_file):
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫", "hint": "", "rating": None}
    control.remember_path_for_hash(image_file, image_hash)

    assert control.sync_xattr_for_hash(image_hash)
    assert xattr_tags.read_tags(image_file) == ["猫"]


def test_sync_for_unknown_hash_does_nothing(control):
    assert control.sync_xattr_for_hash("存在しないハッシュ") is False


# ---------------------------------------------------------------- 取り込み(和集合)


def test_import_merges_tags_as_union(control, image_file):
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫; 屋外", "hint": "", "rating": None}
    xattr_tags.write_tags(image_file, ["屋外", "夕焼け"])

    changed, scanned, written = control.import_xattr_tags([image_file])

    assert (changed, scanned) == (1, 1)
    # CSV にしか無かったタグはファイル側へ書き戻される
    assert written == 1
    # CSV 側だけのタグも Dolphin 側だけのタグも残る
    assert control.tag_dict[image_hash]["tag"] == "猫; 屋外; 夕焼け"


def test_import_creates_entry_for_unknown_image(control, image_file):
    xattr_tags.write_tags(image_file, ["新規タグ"])

    control.import_xattr_tags([image_file])

    entry = control.tag_dict[_hash_of(image_file)]
    assert entry["tag"] == "新規タグ"
    assert entry["hint"] == "画像.png"


def test_import_reports_no_change_when_tags_already_present(control, image_file):
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫", "hint": "", "rating": None}
    xattr_tags.write_tags(image_file, ["猫"])

    changed, scanned, _written = control.import_xattr_tags([image_file])
    assert changed == 0
    assert scanned == 1


def test_import_skips_files_without_any_attribute(control, image_file):
    changed, scanned, _written = control.import_xattr_tags([image_file])
    assert changed == 0
    assert scanned == 1
    assert control.tag_dict == {}


def test_import_takes_rating_when_csv_has_none(control, image_file):
    xattr_tags.write_rating(image_file, 3)

    control.import_xattr_tags([image_file])

    entry = control.tag_dict[_hash_of(image_file)]
    assert entry["assigned_rating"] == "星3"
    assert control.rating_dict["星3"]["custom_rating"] == 3


def test_import_keeps_existing_rating(control, image_file):
    image_hash = _hash_of(image_file)
    control.rating_dict["星5"] = {"name": "星5", "rating": 5, "linked": True, "custom_rating": 5}
    control.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None, "assigned_rating": "星5"}
    xattr_tags.write_rating(image_file, 1)

    control.import_xattr_tags([image_file])
    assert control.tag_dict[image_hash]["assigned_rating"] == "星5"


def test_import_ignores_missing_paths(control, tmp_path):
    changed, scanned, written = control.import_xattr_tags([str(tmp_path / "ない.png")])
    assert (changed, scanned, written) == (0, 0, 0)


# ---------------------------------------------------------------- 往復


def test_round_trip_dolphin_to_gazotools_and_back(control, image_file):
    """Dolphin で付けたタグを取り込み、GazoTools で1つ足して書き戻す。"""
    xattr_tags.write_tags(image_file, ["H", "H/満"])
    control.import_xattr_tags([image_file])

    image_hash = _hash_of(image_file)
    assert control.tag_dict[image_hash]["tag"] == "H; H/満"

    control.tag_dict[image_hash]["tag"] = "H; H/満; 追加タグ"
    control.sync_xattr_for(image_file, image_hash)

    # Dolphin 側もカンマ区切りで読める形になっている
    raw = os.getxattr(image_file, b"user.xdg.tags").decode("utf-8")
    assert raw == "H,H/満,追加タグ"


def test_export_writes_only_known_images(control, tmp_path, image_file):
    other = tmp_path / "無関係.png"
    other.write_bytes(b"another image")

    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫", "hint": "", "rating": None}

    written = control.export_xattr_tags([image_file, str(other)])
    assert written == 1
    assert xattr_tags.read_tags(str(other)) == []


def test_sync_for_rating_name_updates_all_known_images(control, tmp_path):
    paths = []
    for index in range(2):
        path = tmp_path / f"星付き_{index}.png"
        path.write_bytes(f"image {index}".encode("utf-8"))
        paths.append(str(path))
    if not _xattr_writable(paths[0]):
        pytest.skip("このファイルシステムは拡張属性に対応していません")

    control.rating_dict["星2"] = {"name": "星2", "rating": 2, "linked": True, "custom_rating": 2}
    for path in paths:
        image_hash = _hash_of(path)
        control.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None, "assigned_rating": "星2"}
        control.image_rating_map[image_hash] = "星2"
        control.remember_path_for_hash(path, image_hash)

    # 星数を 2 -> 5 に変えたら、その評価を付けた画像すべてに反映されること
    control.rating_dict["星2"]["custom_rating"] = 5
    assert control.sync_xattr_for_rating_name("星2") == 2
    for path in paths:
        assert xattr_tags.read_rating(path) == 5


# ---------------------------------------------------------------- 全件そろえ (F5)


def test_full_sync_pushes_csv_only_tags_to_untouched_file(control, image_file):
    """拡張属性が無いファイルにも、CSV 側のタグが書き出されること。"""
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "昔つけたタグ", "hint": "", "rating": None}
    assert xattr_tags.read_tags(image_file) == []

    changed, scanned, written = control.import_xattr_tags([image_file], full=True)

    assert written == 1
    assert xattr_tags.read_tags(image_file) == ["昔つけたタグ"]
    # CSV 側は増えていないので取り込み件数は 0
    assert changed == 0


def test_full_sync_pushes_csv_rating_to_untouched_file(control, image_file):
    image_hash = _hash_of(image_file)
    control.rating_dict["星3"] = {"name": "星3", "rating": 3, "linked": True, "custom_rating": 3}
    control.tag_dict[image_hash] = {"tag": "", "hint": "", "rating": None, "assigned_rating": "星3"}

    control.import_xattr_tags([image_file], full=True)
    assert xattr_tags.read_rating(image_file) == 3


def test_full_sync_leaves_untagged_files_alone(control, image_file):
    """両側とも空のファイルには何も書かず、辞書にも足さないこと。"""
    changed, scanned, written = control.import_xattr_tags([image_file], full=True)

    assert (changed, written) == (0, 0)
    assert scanned == 1
    assert control.tag_dict == {}
    assert xattr_tags.read_tags(image_file) == []


def test_full_sync_makes_both_sides_match(control, image_file):
    """和集合のあと、CSV とファイルのタグの顔ぶれが一致すること。"""
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫; 屋外", "hint": "", "rating": None}
    xattr_tags.write_tags(image_file, ["屋外", "夕焼け"])

    control.import_xattr_tags([image_file], full=True)

    from lib.GazoToolsTagFilter import parse_tag_text
    assert set(parse_tag_text(control.tag_dict[image_hash]["tag"])) == set(xattr_tags.read_tags(image_file))


def test_full_sync_is_stable_when_run_twice(control, image_file):
    """2回目は何も変わらないこと（書き戻しが延々と走らない）。"""
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "猫", "hint": "", "rating": None}
    xattr_tags.write_tags(image_file, ["屋外"])

    control.import_xattr_tags([image_file], full=True)
    changed, _scanned, written = control.import_xattr_tags([image_file], full=True)

    assert (changed, written) == (0, 0)


# ---------------------------------------------------------------- ":" の書き直し


def test_colon_only_file_is_rewritten_with_commas(control, image_file):
    """タグの顔ぶれが同じでも、":" 区切りのままなら "," に直すこと。"""
    import os as _os
    _os.setxattr(image_file, b"user.xdg.tags", "満:ベッド:恥ずかしい".encode("utf-8"))
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "満; ベッド; 恥ずかしい", "hint": "", "rating": None}

    changed, _scanned, written = control.import_xattr_tags([image_file])

    assert written == 1
    raw = _os.getxattr(image_file, b"user.xdg.tags").decode("utf-8")
    assert raw == "満,ベッド,恥ずかしい"


def test_colon_rewrite_happens_without_csv_entry(control, image_file):
    """CSV に無いファイルでも、Dolphin 側の ":" は "," に直る。"""
    import os as _os
    _os.setxattr(image_file, b"user.xdg.tags", "膣内射精:裸:ベッド:愛:大小".encode("utf-8"))

    control.import_xattr_tags([image_file])

    raw = _os.getxattr(image_file, b"user.xdg.tags").decode("utf-8")
    assert raw == "膣内射精,裸,ベッド,愛,大小"


def test_already_comma_form_is_left_untouched(control, image_file):
    """すでに "," 区切りのファイルは書き直さない（無駄な再インデックスを避ける）。"""
    import os as _os
    _os.setxattr(image_file, b"user.xdg.tags", "裸,好き放題,ベッド".encode("utf-8"))
    image_hash = _hash_of(image_file)
    control.tag_dict[image_hash] = {"tag": "裸; 好き放題; ベッド", "hint": "", "rating": None}

    _changed, _scanned, written = control.import_xattr_tags([image_file])

    assert written == 0


def test_fullwidth_colon_is_rewritten(control, image_file):
    import os as _os
    _os.setxattr(image_file, b"user.xdg.tags", "好き：挿入:ベッド".encode("utf-8"))

    control.import_xattr_tags([image_file])

    raw = _os.getxattr(image_file, b"user.xdg.tags").decode("utf-8")
    assert raw == "好き,挿入,ベッド"


def test_colon_rewrite_is_stable_on_second_run(control, image_file):
    import os as _os
    _os.setxattr(image_file, b"user.xdg.tags", "満:ベッド".encode("utf-8"))

    control.import_xattr_tags([image_file])
    _changed, _scanned, written = control.import_xattr_tags([image_file])

    assert written == 0
