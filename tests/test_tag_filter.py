from lib.GazoToolsTagFilter import (
    parse_tag_text,
    collect_all_tags,
    filter_file_names_by_tags,
    find_files_for_tag,
)


def test_parse_tag_text_splits_and_normalizes():
    tags = parse_tag_text("nature; city, travel ;  portrait")
    assert tags == ["nature", "city", "travel", "portrait"]


def test_collect_all_tags_ignores_empty_entries():
    tag_map = {
        "hash1": {"tag": "nature; city"},
        "hash2": {"tag": "city; portrait"},
        "hash3": {"tag": ""},
    }
    assert collect_all_tags(tag_map) == ["city", "nature", "portrait"]


def test_filter_file_names_by_tags_keeps_matching_files_only():
    files = [
        "/tmp/a.jpg",
        "/tmp/b.jpg",
        "/tmp/c.jpg",
    ]
    tag_map = {
        "hash1": {"tag": "nature; city"},
        "hash2": {"tag": "travel"},
        "hash3": {"tag": "nature"},
    }
    path_to_hash = {
        "/tmp/a.jpg": "hash1",
        "/tmp/b.jpg": "hash2",
        "/tmp/c.jpg": "hash3",
    }
    assert filter_file_names_by_tags(files, path_to_hash, tag_map, {"nature"}) == [
        "/tmp/a.jpg",
        "/tmp/c.jpg",
    ]


def test_find_files_for_tag_returns_matching_file_names():
    files = [
        "/tmp/a.jpg",
        "/tmp/b.jpg",
        "/tmp/c.jpg",
    ]
    tag_map = {
        "hash1": {"tag": "nature; city"},
        "hash2": {"tag": "travel"},
        "hash3": {"tag": "nature"},
    }
    path_to_hash = {
        "/tmp/a.jpg": "hash1",
        "/tmp/b.jpg": "hash2",
        "/tmp/c.jpg": "hash3",
    }
    assert find_files_for_tag(files, path_to_hash, tag_map, "nature") == [
        "/tmp/a.jpg",
        "/tmp/c.jpg",
    ]


def test_filter_file_names_by_tags_supports_or_mode():
    files = [
        "/tmp/a.jpg",
        "/tmp/b.jpg",
        "/tmp/c.jpg",
    ]
    tag_map = {
        "hash1": {"tag": "nature"},
        "hash2": {"tag": "travel"},
        "hash3": {"tag": "city"},
    }
    path_to_hash = {
        "/tmp/a.jpg": "hash1",
        "/tmp/b.jpg": "hash2",
        "/tmp/c.jpg": "hash3",
    }
    assert filter_file_names_by_tags(files, path_to_hash, tag_map, ["nature", "travel"], mode="or") == [
        "/tmp/a.jpg",
        "/tmp/b.jpg",
    ]
