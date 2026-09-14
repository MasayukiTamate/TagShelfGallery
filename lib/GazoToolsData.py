'''
作成日: 2026年01月05日
作成者: tamate masayuki (Refactored by Antigravity)
機能: GazoTools データアクセス層 (Config, Tags, Ratings, Vectors)
'''
import os
import json
import csv
import hashlib
from lib.GazoToolsExceptions import (
    ConfigError, ImageLoadError, FileHashError, TagManagementError,
    VectorProcessingError, FileOperationError
)
from lib.GazoToolsLogger import LoggerManager
from lib.config_defaults import (
    get_default_config, MOVE_DESTINATION_SLOTS,
    TAG_CSV_FILE, VECTOR_DATA_FILE, RATING_DATA_FILE, CONFIG_FILE
)

logger = LoggerManager.get_logger(__name__)

def load_config():
    """設定ファイルを読み込むのじゃ。のじゃ。
    
    config_defaults.py のデフォルト値を使用して、ファイルから設定を読み込みます。
    ファイルが存在しない場合はデフォルト値を返します。
    
    Returns:
        dict: 設定辞書
        
    Raises:
        ConfigError: 設定ファイルの読み込み失敗時
    """
    config = get_default_config()
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                config["last_folder"] = data.get("last_folder", os.getcwd())
                config["geometries"] = data.get("geometries", {})
                saved_settings = data.get("settings", {})
                config["settings"].update(saved_settings)
                
                # move_dest_list の長さを MOVE_DESTINATION_SLOTS に強制するのじゃ（IndexError対策）
                cur_list = config["settings"].get("move_dest_list", [])
                if len(cur_list) < MOVE_DESTINATION_SLOTS:
                    config["settings"]["move_dest_list"] = (cur_list + [""] * MOVE_DESTINATION_SLOTS)[:MOVE_DESTINATION_SLOTS]

                if not os.path.exists(config["last_folder"]):
                    config["last_folder"] = os.getcwd()
        except json.JSONDecodeError as e:
            logger.error(f"設定ファイルのJSON解析に失敗: {CONFIG_FILE}", exc_info=True)
            raise ConfigError(f"Invalid JSON in config file: {e}") from e
        except IOError as e:
            logger.error(f"設定ファイルの読み込み失敗: {CONFIG_FILE}", exc_info=True)
            raise ConfigError(f"Cannot read config file: {e}") from e
        except Exception as e:
            logger.error(f"設定ファイル読み込み中に予期しないエラー: {e}", exc_info=True)
            raise ConfigError(f"Unexpected error loading config: {e}") from e
    return config

def save_config(path, geometries=None, settings=None):
    """設定を保存するのじゃ。のじゃ。"""
    try:
        prev = load_config()
        data = {
            "last_folder": path,
            "geometries": geometries if geometries is not None else prev.get("geometries", {}),
            "settings": settings if settings is not None else prev.get("settings", {})
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        logger.info(f"設定を保存しました: {path}")
    except IOError as e:
        logger.error(f"設定ファイルの書き込み失敗: {CONFIG_FILE}", exc_info=True)
        raise ConfigError(f"Cannot write config file: {e}") from e
    except Exception as e:
        logger.error(f"設定保存中に予期しないエラー: {e}", exc_info=True)
        raise ConfigError(f"Unexpected error saving config: {e}") from e

def calculate_file_hash(filepath):
    """ファイルのMD5ハッシュ値を計算するのじゃ。のじゃ。"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        logger.debug(f"ハッシュ計算完了: {os.path.basename(filepath)}")
        return hash_md5.hexdigest()
    except FileNotFoundError as e:
        logger.error(f"ファイルが見つかりません: {filepath}", exc_info=True)
        raise FileHashError(f"File not found: {filepath}") from e
    except IOError as e:
        logger.error(f"ファイル読み込みエラー: {filepath}", exc_info=True)
        raise FileHashError(f"Cannot read file: {filepath}") from e
    except Exception as e:
        logger.error(f"ハッシュ計算中に予期しないエラー: {filepath}", exc_info=True)
        raise FileHashError(f"Unexpected error calculating hash: {e}") from e

def load_tags():
    """タグデータと評価データを読み込むのじゃ。のじゃ。"""
    tags = {} # key: hash, value: {tag: "...", hint: "...", rating: int or None, assigned_rating: str}
    if os.path.exists(TAG_CSV_FILE):
        try:
            with open(TAG_CSV_FILE, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        h = row[0]
                        t = row[1]
                        hint = row[2] if len(row) > 2 else ""
                        rating = int(row[3]) if len(row) > 3 and row[3] else None
                        assigned_rating = row[4] if len(row) > 4 and row[4] else None
                        tags[h] = {"tag": t, "hint": hint, "rating": rating, "assigned_rating": assigned_rating}
            logger.info(f"タグ・評価データを読み込みました: {len(tags)}件")
        except IOError as e:
            logger.error(f"タグファイル読み込みエラー: {TAG_CSV_FILE}", exc_info=True)
            raise TagManagementError(f"Cannot read tag file: {e}") from e
        except csv.Error as e:
            logger.error(f"CSVファイル解析エラー: {TAG_CSV_FILE}", exc_info=True)
            raise TagManagementError(f"Invalid CSV format in tag file: {e}") from e
        except Exception as e:
            logger.error(f"タグ読み込み中に予期しないエラー: {e}", exc_info=True)
            raise TagManagementError(f"Unexpected error loading tags: {e}") from e
    return tags

def save_tags(tags):
    """タグデータと評価データを保存するのじゃ。のじゃ。"""
    try:
        os.makedirs(os.path.dirname(TAG_CSV_FILE), exist_ok=True)
        with open(TAG_CSV_FILE, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            for h, data in tags.items():
                rating = data.get("rating", "")
                assigned_rating = data.get("assigned_rating", "")
                writer.writerow([h, data["tag"], data["hint"], rating, assigned_rating])
        logger.info(f"タグ・評価データを保存しました: {len(tags)}件")
    except IOError as e:
        logger.error(f"タグファイル書き込みエラー: {TAG_CSV_FILE}", exc_info=True)
        raise TagManagementError(f"Cannot write tag file: {e}") from e

def load_ratings():
    """評価データを読み込むのじゃ。のじゃ。"""
    ratings = {}  # key: rating_id, value: {name: "...", rating: int, linked: bool, custom_rating: int}
    if os.path.exists(RATING_DATA_FILE):
        try:
            with open(RATING_DATA_FILE, "r", encoding="utf-8") as f:
                ratings = json.load(f)
            logger.info(f"評価データを読み込みました: {len(ratings)}件")
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"評価データファイル読み込みエラー: {RATING_DATA_FILE}", exc_info=True)
            raise FileOperationError(f"Cannot read rating file: {e}") from e
    else:
        # 初回起動時はデフォルト評価を作成
        ratings = get_default_ratings()
        save_ratings(ratings)
    return ratings

def get_default_ratings():
    """デフォルトの評価データを返すのじゃ。のじゃ。"""
    return {
        "普通": {
            "name": "普通",
            "rating": 3,
            "linked": True,
            "custom_rating": 3
        },
        "どうでもいい": {
            "name": "どうでもいい",
            "rating": 1,
            "linked": True,
            "custom_rating": 1
        },
        "最高": {
            "name": "最高",
            "rating": 5,
            "linked": True,
            "custom_rating": 5
        },
        "excellent": {
            "name": "excellent",
            "rating": 6,
            "linked": True,
            "custom_rating": 6
        }
    }

def save_ratings(ratings):
    """評価データを保存するのじゃ。のじゃ。"""
    try:
        os.makedirs(os.path.dirname(RATING_DATA_FILE), exist_ok=True)
        with open(RATING_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(ratings, f, ensure_ascii=False, indent=2)
        logger.info(f"評価データを保存しました: {len(ratings)}件")
    except IOError as e:
        logger.error(f"評価データファイル書き込みエラー: {RATING_DATA_FILE}", exc_info=True)
        raise FileOperationError(f"Cannot write rating file: {e}") from e
    except Exception as e:
        logger.error(f"タグ保存中に予期しないエラー: {e}", exc_info=True)
        raise TagManagementError(f"Unexpected error saving tags: {e}") from e

def load_vectors():
    """ベクトルデータを読み込むのじゃ。のじゃ。"""
    if os.path.exists(VECTOR_DATA_FILE):
        try:
            with open(VECTOR_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            logger.info(f"ベクトルデータを読み込みました: {len(data)}件")
            return data
        except json.JSONDecodeError as e:
            logger.error(f"ベクトルファイルのJSON解析エラー: {VECTOR_DATA_FILE}", exc_info=True)
            raise VectorProcessingError(f"Invalid JSON in vector file: {e}") from e
        except IOError as e:
            logger.error(f"ベクトルファイル読み込みエラー: {VECTOR_DATA_FILE}", exc_info=True)
            raise VectorProcessingError(f"Cannot read vector file: {e}") from e
        except Exception as e:
            logger.error(f"ベクトル読み込み中に予期しないエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Unexpected error loading vectors: {e}") from e
    return {}

def save_vectors(vectors):
    """ベクトルデータを保存するのじゃ。のじゃ。"""
    try:
        os.makedirs(os.path.dirname(VECTOR_DATA_FILE), exist_ok=True)
        with open(VECTOR_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(vectors, f)
        logger.info(f"ベクトルデータを保存しました: {len(vectors)}件")
    except IOError as e:
        logger.error(f"ベクトルファイル書き込みエラー: {VECTOR_DATA_FILE}", exc_info=True)
        raise VectorProcessingError(f"Cannot write vector file: {e}") from e
    except Exception as e:
        logger.error(f"ベクトル保存中に予期しないエラー: {e}", exc_info=True)

# -------------------------------------------------------------------
# Additional Imports for HakoData
import random
from lib.GazoToolsLib import GetKoFolder, GetGazoFiles
# from lib.GazoToolsAI import VectorEngine # Circular import fix: Moved to local scope

class HakoData():
    """画像データ保持クラスなのじゃ。のじゃ。"""
    def __init__(self, def_folder):
        self.StartFolder = def_folder
        self.GazoFiles = []
        self.vectors_cache = {}
        self.ai_playlist = []     # AI再生用のキュー
        self.visited_files = set() # 表示済みファイル（AIモード用）

    def SetGazoFiles(self, GazoFiles, folder_path, include_subfolders=False):
        """画像ファイルリストを設定するのじゃ。のじゃ。
        
        Args:
            GazoFiles: 現在のフォルダの画像ファイルリスト
            folder_path: フォルダパス
            include_subfolders: 子フォルダを含めるかどうか
        """
        self.StartFolder = folder_path
        self.GazoFiles = GazoFiles
        
        # 子フォルダを含める場合は再帰的に収集
        if include_subfolders:
            self.GazoFiles = self._collect_all_images(folder_path)
        
        # フォルダが変わったらキャッシュと状態をリセット
        self.vectors_cache = load_vectors()
        self.ai_playlist = []
        self.visited_files = set()

    def _collect_all_images(self, base_folder):
        """ベースフォルダとその子フォルダから全ての画像を収集するのじゃ。のじゃ。
        
        Args:
            base_folder: 基準となるフォルダパス
            
        Returns:
            list: ベースフォルダからの相対パスのリスト
        """
        all_images = []
        
        def collect_recursive(current_folder, base_path):
            """再帰的に画像を収集する内部関数なのじゃ。"""
            try:
                items = os.listdir(current_folder)
                folders = GetKoFolder(items, current_folder)
                files = GetGazoFiles(items, current_folder)
                
                # 現在のフォルダの画像を追加（ベースフォルダからの相対パス）
                for f in files:
                    full_path = os.path.join(current_folder, f)
                    relative_path = os.path.relpath(full_path, base_path)
                    all_images.append(relative_path)
                
                # サブフォルダを再帰的に処理
                for folder in folders:
                    subfolder_path = os.path.join(current_folder, folder)
                    collect_recursive(subfolder_path, base_path)
            except PermissionError:
                logger.warning(f"アクセス権限がありません: {current_folder}")
            except Exception as e:
                logger.warning(f"フォルダ読み込みエラー: {current_folder} - {e}")
        
        collect_recursive(base_folder, base_folder)
        logger.info(f"子フォルダを含めて{len(all_images)}件の画像を収集しました")
        return all_images

    def RandamGazoSet(self):
        """ランダム、またはAI順序で画像を返すのじゃ。のじゃ。"""
        if not self.GazoFiles:
            return None
        return random.choice(self.GazoFiles)

    def GetNextAIImage(self, threshold):
        """AI類似度順で次の画像を取得するのじゃ。のじゃ。"""
        if not self.GazoFiles:
            return None
            
        # プレイリストに残りがあればそれを返す
        if self.ai_playlist:
            next_img = self.ai_playlist.pop(0)
            self.visited_files.add(next_img)
            return next_img
            
        # プレイリストが空の場合、新しい「シード」を探す
        # 未訪問のファイルの中から最初のものをシードにするのじゃ
        seed_cand = [f for f in self.GazoFiles if f not in self.visited_files]
        
        if not seed_cand:
            # 全て訪問済みの場合はリセットして最初から
            self.visited_files.clear()
            seed_cand = self.GazoFiles
            
        # シード決定（リストの先頭＝フォルダ順の若いもの＝「1番目の画像」）
        seed_file = seed_cand[0]
        
        # シードをプレイリストの先頭に追加
        self.ai_playlist.append(seed_file)
        
        # 類似画像を検索してプレイリストの後ろに繋げる処理
        from lib.GazoToolsAI import VectorEngine
        engine = VectorEngine.get_instance()
        if engine.check_available():
            # 相対パスまたはファイル名からフルパスを構築
            if os.path.isabs(seed_file):
                seed_path = seed_file
            else:
                seed_path = os.path.join(self.StartFolder, seed_file)
            seed_hash = calculate_file_hash(seed_path)
            
            # シードのベクトル取得（キャッシュにあればラッキー）
            seed_vec = self.vectors_cache.get(seed_hash)
            if not seed_vec:
                # 無ければ計算してみる
                seed_vec = engine.get_image_feature(seed_path)
                if seed_vec and seed_hash:
                    self.vectors_cache[seed_hash] = seed_vec

            if seed_vec:
                # 他の画像の類似度を計算して高い順に並べる
                sim_list = []
                for f in seed_cand: # 自分自身も含むが、それは後で除外されるか、最初にpopされるのでOK
                    if f == seed_file: continue
                    
                    # 相対パスまたはファイル名からフルパスを構築
                    if os.path.isabs(f):
                        f_path = f
                    else:
                        f_path = os.path.join(self.StartFolder, f)
                    f_hash = calculate_file_hash(f_path)
                    f_vec = self.vectors_cache.get(f_hash)
                    
                    if not f_vec:
                        # リアルタイム計算は重いので、キャッシュにない場合スキップするか検討。
                        # ここではスキップするのじゃ（高速化のため）
                        continue
                        
                    score = engine.compare_features(seed_vec, f_vec)
                    if score >= threshold:
                        sim_list.append((f, score))
                
                # 類似度が高い順にソート
                sim_list.sort(key=lambda x: x[1], reverse=True)
                
                # プレイリストに追加
                for f, s in sim_list:
                    self.ai_playlist.append(f)
                    
        # 準備できたので1つ返す
        return self.GetNextAIImage(threshold) # 再帰呼び出しでpop(0)へ
