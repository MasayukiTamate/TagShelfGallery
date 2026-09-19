import re


class TagFilterState:
    """タグフィルタ・タグ編集対象の状態を一元管理するシングルトンクラス。

    AppState と同じ __new__ シングルトンパターンを踏襲し、
    TagEditorWindow / TagListWindow など複数のウィンドウが
    同じフィルタ状態・編集対象を共有できるようにする。
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True

        self.active_filter = []
        self.mode = "and"
        self.active_target = {"file_path": None, "image_hash": None}

    def set_mode(self, mode):
        self.mode = mode if mode in ("and", "or") else "and"

    def set_active_filter(self, tags):
        self.active_filter = list(tags) if tags else []

    def clear_filter(self):
        self.active_filter = []

    def set_active_target(self, file_path, image_hash=None):
        self.active_target = {"file_path": file_path, "image_hash": image_hash}

    def clear_active_target(self):
        self.set_active_target(None)


def get_tag_filter_state():
    return TagFilterState()


def parse_tag_text(raw_text):
    """タグ文字列を正規化してリスト化する。"""
    if raw_text is None:
        return []
    cleaned = str(raw_text)
    parts = re.split(r"[;,]+", cleaned)
    tags = []
    for part in parts:
        tag = part.strip()
        if tag:
            tags.append(tag)
    return tags


def collect_all_tags(tag_map):
    """画像ごとのタグマップから、すべてのタグ一覧を重複なしで取得する。"""
    all_tags = set()
    for data in (tag_map or {}).values():
        if not isinstance(data, dict):
            continue
        raw_text = data.get("tag", "")
        for tag in parse_tag_text(raw_text):
            all_tags.add(tag)
    return sorted(all_tags)


def filter_file_names_by_tags(file_names, path_to_hash, tag_map, selected_tags, mode="and"):
    """ファイル一覧に対してタグ条件に合うものだけを返す。

    mode:
        - "and": すべての選択タグを含む
        - "or": いずれかの選択タグを含む
    """
    selected = {tag.strip() for tag in (selected_tags or []) if str(tag).strip()}
    if not selected:
        return list(file_names)

    filtered = []
    mode = str(mode).lower()
    for file_name in file_names:
        image_hash = path_to_hash.get(file_name)
        if not image_hash:
            continue
        entry = (tag_map or {}).get(image_hash, {})
        raw_tags = entry.get("tag", "")
        tags = set(parse_tag_text(raw_tags))
        if mode == "or":
            if selected.intersection(tags):
                filtered.append(file_name)
        else:
            if selected.issubset(tags):
                filtered.append(file_name)
    return filtered


def find_files_for_tag(file_names, path_to_hash, tag_map, tag_name):
    """特定のタグを持つファイル一覧を返す。タグ別一覧ウィンドウ用。"""
    if not tag_name:
        return []
    target = str(tag_name).strip()
    if not target:
        return []

    matched = []
    for file_name in file_names:
        image_hash = path_to_hash.get(file_name)
        if not image_hash:
            continue
        entry = (tag_map or {}).get(image_hash, {})
        tags = set(parse_tag_text(entry.get("tag", "")))
        if target in tags:
            matched.append(file_name)
    return matched
