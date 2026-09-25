'''
作成日: 2026年09月26日
作成者: tamate masayuki
機能: Dolphin (KDE) 互換のタグ・評価を拡張属性 (xattr) として読み書きする
説明:
    Dolphin / Baloo はタグを DB ではなくファイルの拡張属性に保存しておる。

        user.xdg.tags      カンマ区切りのタグ名。階層タグは "/" 区切り
                           例: "H,H/満,H/ベッド"
        user.baloo.rating  0〜10 の整数。星数 x 2
        user.xdg.comment   任意のコメント文字列

    Baloo は拡張属性の変更を inotify で検知して自動的に再インデックスするため、
    ここで書き込めば Dolphin の情報パネルや tags:/ 検索にそのまま反映される。
    (Baloo の索引対象フォルダに入っている場合のみ tags:/ に出る)

    本モジュールは xattr の読み書きだけを担当し、GazoTools 側の
    ハッシュキー方式のタグ辞書とは疎結合に保つ。
'''
import errno
import os
import re

from lib.GazoToolsLogger import get_logger

logger = get_logger(__name__)

# Dolphin / freedesktop.org が使う属性名
XATTR_TAGS = "user.xdg.tags"
XATTR_RATING = "user.baloo.rating"
XATTR_COMMENT = "user.xdg.comment"

# Dolphin 側の区切り文字。GazoTools 側は "; " で結合するが、
# parse_tag_text が [;,]+ で分割するため相互に読める。
DOLPHIN_SEPARATOR = ","

# 星数の上限（GazoTools 側の評価と揃える）
MAX_STARS = 5

# xattr 非対応のファイルシステム上で毎回ログを出さないための記録
_unsupported_roots = set()

# 「拡張属性そのものが使えない環境か」の判定結果キャッシュ
_platform_supported = hasattr(os, "setxattr") and hasattr(os, "getxattr")

# ファイルシステムが対応していないことを示す errno
_UNSUPPORTED_ERRNOS = {
    errno.ENOTSUP,
    getattr(errno, "EOPNOTSUPP", errno.ENOTSUP),
    errno.EPERM,
    errno.EACCES,
    errno.EROFS,
}


def is_available():
    """この環境で拡張属性が扱えるかどうかを返す。"""
    return _platform_supported


def _mark_unsupported(path, exc):
    """非対応の場所を記録し、同じ場所で何度も警告を出さないようにする。"""
    root = os.path.dirname(os.path.abspath(path))
    if root in _unsupported_roots:
        return
    _unsupported_roots.add(root)
    logger.info(f"拡張属性が使えないためDolphin連携をスキップします: {root} ({exc})")


def _is_unsupported_error(exc):
    return isinstance(exc, OSError) and exc.errno in _UNSUPPORTED_ERRNOS


# タグ名に含められない文字。GazoTools 側の区切り文字と、
# Dolphin 側の区切り文字 "," をまとめて置き換える。
_SEPARATOR_CHARS = ",;:；：、"

# 読み取り時に区切りとみなす文字。Dolphin が書くのは "," だけだが、
# 1つのタグの中で ":" を区切り代わりに使っている場合も割って取り込む。
_READ_SEPARATORS = re.compile(r"[,;:；：、]+")


def normalize_tag(tag):
    """Dolphin に書ける形にタグ名を整える。区切り文字は含められない。"""
    cleaned = str(tag or "").strip()
    if not cleaned:
        return ""
    for char in _SEPARATOR_CHARS:
        cleaned = cleaned.replace(char, "／")
    return cleaned.strip()


def normalize_tags(tags):
    """タグ列を正規化し、順序を保ったまま重複を除く。"""
    result = []
    seen = set()
    for tag in tags or []:
        normalized = normalize_tag(tag)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


def stars_to_baloo(stars):
    """GazoTools の星数 (0〜5) を Baloo の評価値 (0〜10) に変換する。"""
    try:
        value = int(stars)
    except (TypeError, ValueError):
        return 0
    value = max(0, min(MAX_STARS, value))
    return value * 2


def baloo_to_stars(value):
    """Baloo の評価値 (0〜10) を GazoTools の星数 (0〜5) に変換する。"""
    try:
        raw = int(value)
    except (TypeError, ValueError):
        return 0
    # 奇数値は切り上げて星数に丸める
    stars = (raw + 1) // 2
    return max(0, min(MAX_STARS, stars))


def canonical_value(tags):
    """write_tags が実際に書き込む文字列を返す。

    保存されている文字列がこの形と違えば、Dolphin から見て区切られていない
    ということなので、書き直す必要がある。
    """
    return DOLPHIN_SEPARATOR.join(normalize_tags(tags))


def read_tags_with_raw(path):
    """タグ一覧と、拡張属性に入っている生の文字列を返す。

    生の文字列は「すでに Dolphin の区切り "," になっているか」を
    判定するために使う。未設定なら ([], None)。
    """
    if not _platform_supported or not path:
        return ([], None)
    try:
        raw = os.getxattr(path, XATTR_TAGS)
    except OSError as exc:
        if exc.errno in (errno.ENODATA, errno.ENOENT):
            return ([], None)
        if _is_unsupported_error(exc):
            _mark_unsupported(path, exc)
            return ([], None)
        logger.debug(f"タグ属性の読み込みに失敗: {path} ({exc})")
        return ([], None)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        logger.debug(f"タグ属性の文字コードが不正: {path}")
        return ([], None)
    # 先に区切ってから正規化する。順番を逆にすると、区切り文字が
    # 置換されてしまい 1 つの長いタグ名になってしまう。
    return (normalize_tags(_READ_SEPARATORS.split(text)), text)


def read_tags(path):
    """ファイルに付いた Dolphin のタグをリストで返す。無ければ空リスト。"""
    return read_tags_with_raw(path)[0]


def write_tags(path, tags):
    """Dolphin 互換のタグをファイルに書き込む。成功したら True。"""
    if not _platform_supported or not path:
        return False
    normalized = normalize_tags(tags)
    try:
        if not normalized:
            # タグが空になった場合は属性ごと削除する（Dolphin と同じ挙動）
            try:
                os.removexattr(path, XATTR_TAGS)
            except OSError as exc:
                if exc.errno not in (errno.ENODATA, errno.ENOENT):
                    raise
            return True
        payload = DOLPHIN_SEPARATOR.join(normalized).encode("utf-8")
        os.setxattr(path, XATTR_TAGS, payload)
        return True
    except OSError as exc:
        if _is_unsupported_error(exc):
            _mark_unsupported(path, exc)
            return False
        logger.debug(f"タグ属性の書き込みに失敗: {path} ({exc})")
        return False


def read_rating(path):
    """Dolphin の評価を星数 (0〜5) で返す。未設定なら None。"""
    if not _platform_supported or not path:
        return None
    try:
        raw = os.getxattr(path, XATTR_RATING)
    except OSError as exc:
        if exc.errno in (errno.ENODATA, errno.ENOENT):
            return None
        if _is_unsupported_error(exc):
            _mark_unsupported(path, exc)
            return None
        logger.debug(f"評価属性の読み込みに失敗: {path} ({exc})")
        return None
    try:
        return baloo_to_stars(raw.decode("utf-8").strip())
    except (UnicodeDecodeError, ValueError):
        return None


def write_rating(path, stars):
    """星数 (0〜5) を Baloo の評価値として書き込む。成功したら True。"""
    if not _platform_supported or not path:
        return False
    try:
        if stars is None:
            try:
                os.removexattr(path, XATTR_RATING)
            except OSError as exc:
                if exc.errno not in (errno.ENODATA, errno.ENOENT):
                    raise
            return True
        value = stars_to_baloo(stars)
        if value <= 0:
            try:
                os.removexattr(path, XATTR_RATING)
            except OSError as exc:
                if exc.errno not in (errno.ENODATA, errno.ENOENT):
                    raise
            return True
        os.setxattr(path, XATTR_RATING, str(value).encode("utf-8"))
        return True
    except OSError as exc:
        if _is_unsupported_error(exc):
            _mark_unsupported(path, exc)
            return False
        logger.debug(f"評価属性の書き込みに失敗: {path} ({exc})")
        return False


def read_all(path):
    """タグと評価をまとめて読み出す。"""
    return {"tags": read_tags(path), "stars": read_rating(path)}
