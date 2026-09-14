'''
作成日: 2026年01月02日
作成者: tamate masayuki (Implemented by Antigravity)
機能: AI (MobileNetV3) を使用した軽量な画像ベクトル化ロジックを提供するクラスなのじゃ
'''
from PIL import Image
import os
import threading
import sys
import itertools
from collections import OrderedDict

try:
    import torch
    from torchvision import models, transforms
    TORCH_AVAILABLE = True
except ModuleNotFoundError:
    torch = None
    models = None
    transforms = None
    TORCH_AVAILABLE = False

from .GazoToolsExceptions import AIModelError, ImageLoadError, VectorProcessingError
from .GazoToolsLogger import LoggerManager
import time
from lib.GazoToolsData import load_vectors, save_vectors, calculate_file_hash
from lib.GazoToolsLib import GetGazoFiles
from lib.GazoToolsExceptions import FileHashError


logger = LoggerManager.get_logger(__name__)
if not TORCH_AVAILABLE:
    logger.warning("torch / torchvision が見つからないため、AI機能は無効化されます")

class VectorEngine:
    """MobileNetV3を使用して画像のベクトル化を行うクラスなのじゃ。"""
    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        """インスタンスを取得する（なければ作る）のじゃ。"""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
        return cls._instance

    def __init__(self, debug_mode=False, cache_size=256):
        """モデルを読み込むのじゃ。初回はダウンロードが走るかもしれないのじゃ。
        
        Args:
            debug_mode (bool): デバッグログを出力するか
            cache_size (int): ベクトルキャッシュの最大サイズ（LRU）
        """
        self.debug_mode = debug_mode
        self.cache_size = cache_size
        self.vector_cache = OrderedDict()  # LRUキャッシュ
        self.available = False

        if not TORCH_AVAILABLE:
            logger.warning("AI機能は無効です: torch / torchvision がインストールされていません")
            return

        logger.info("AIモデル(MobileNetV3)の準備手順を開始するのじゃ...")
        
        try:
            if self.debug_mode:
                logger.debug("手順1: モデルウェイトの設定を読み込むのじゃ。")
            
            # 軽量なMobileNetV3 Smallを使用
            self.weights = models.MobileNet_V3_Small_Weights.DEFAULT
            
            if self.debug_mode:
                logger.debug("手順2: MobileNetV3_Smallモデルを構築するのじゃ。")
            self.model = models.mobilenet_v3_small(weights=self.weights)
            
            if self.debug_mode:
                logger.debug("手順3: 特徴抽出用にモデルを改造するのじゃ（1024次元出力用）。")
            # 576次元 -> 1024次元への変換（Linear -> Hardswish -> Dropout）だけを残し、
            # 最後の1000クラス分類層だけを削除するのじゃ
            # MobileNetV3 SmallのClassifierは [Linear(576, 1024), Hardswish, Dropout, Linear(1024, 1000)]
            self.model.classifier = torch.nn.Sequential(
                self.model.classifier[0], # Linear(576, 1024)
                self.model.classifier[1], # Hardswish
                self.model.classifier[2], # Dropout
                torch.nn.Identity()       # 最後のLinearを無効化
            )
            
            if self.debug_mode:
                logger.debug("手順4: 推論モード (eval) に切り替えるのじゃ。")
            self.model.eval() 
            
            # GPU利用可能なら使用
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self.model.to(self.device)
            if self.debug_mode:
                logger.debug(f"使用デバイス: {self.device}")
            
            if self.debug_mode:
                logger.debug("手順5: 前処理用変換(Transforms)を用意するのじゃ。")
            self.preprocess = self.weights.transforms()
            
            # メモリ最適化：勾配計算を無効化
            torch.set_grad_enabled(False)
            
            self.available = True
            logger.info("AIモデルの準備が全て正常に完了したのじゃ！")
        except Exception as e:
            logger.error(f"AIモデルの読み込み手順でエラーが発生したのじゃ: {e}", exc_info=True)
            raise AIModelError(f"Failed to initialize AI model: {e}") from e

    def check_available(self):
        return self.available

    def _get_cache_key(self, image_path):
        """ファイルパスとサイズをキーにする（変更検出用）"""
        try:
            stat_info = os.stat(image_path)
            return f"{os.path.abspath(image_path)}_{stat_info.st_mtime}_{stat_info.st_size}"
        except:
            return os.path.abspath(image_path)

    def _get_from_cache(self, image_path):
        """キャッシュからベクトルを取得"""
        key = self._get_cache_key(image_path)
        if key in self.vector_cache:
            # LRU更新：アクセスした項目を最後に移動
            self.vector_cache.move_to_end(key)
            if self.debug_mode:
                logger.debug(f"キャッシュヒット: {os.path.basename(image_path)}")
            return self.vector_cache[key]
        return None

    def _add_to_cache(self, image_path, vector):
        """ベクトルをキャッシュに追加"""
        key = self._get_cache_key(image_path)
        self.vector_cache[key] = vector
        
        # キャッシュサイズを制限（LRU削除）
        if len(self.vector_cache) > self.cache_size:
            removed_key, removed_val = self.vector_cache.popitem(last=False)
            if self.debug_mode:
                logger.debug(f"キャッシュ削除（LRU）: {len(self.vector_cache)}/{self.cache_size}")

    def clear_cache(self):
        """キャッシュをクリア（メモリ節約時に呼び出し）"""
        self.vector_cache.clear()
        logger.info(f"ベクトルキャッシュをクリアしたのじゃ")

    def get_cache_stats(self):
        """キャッシュ統計情報を返す"""
        return {
            "size": len(self.vector_cache),
            "max_size": self.cache_size
        }

    def get_image_feature(self, image_path):
        """画像パスを受け取って、特徴量ベクトル（リスト）を返すのじゃ。
        
        キャッシュを確認して、必要に応じて推論を実行する。
        """
        if not self.available:
            logger.error("AIモデルが利用可能ではありません")
            raise AIModelError("AI model is not available")

        # キャッシュから取得を試みる
        cached_vec = self._get_from_cache(image_path)
        if cached_vec is not None:
            return cached_vec

        try:
            if self.debug_mode:
                logger.debug(f"画像ファイルを開くのじゃ: {os.path.basename(image_path)}")
            
            image = Image.open(image_path).convert("RGB")
            
            if self.debug_mode:
                logger.debug(f"画像の前処理を行うのじゃ: {image.size}")
            
            input_tensor = self.preprocess(image)
            input_batch = input_tensor.unsqueeze(0).to(self.device)

            if self.debug_mode:
                logger.debug("AIモデルで推論を実行するのじゃ。")
            
            with torch.no_grad():
                output = self.model(input_batch)
            
            feature_vector = output[0]
            
            if self.debug_mode:
                logger.debug("ベクトルの正規化 (L2 norm) を行うのじゃ。")
            
            norm = feature_vector.norm(p=2)
            if norm > 0:
                feature_vector = feature_vector / norm
            
            vec_list = feature_vector.tolist()
            
            # キャッシュに保存
            self._add_to_cache(image_path, vec_list)
            
            if self.debug_mode:
                logger.debug(f"画像処理完了: {len(vec_list)}次元のベクトルを取得")
            return vec_list
            
        except FileNotFoundError as e:
            logger.error(f"画像ファイルが見つかりません: {image_path}", exc_info=True)
            raise ImageLoadError(f"Image file not found: {image_path}") from e
        except IOError as e:
            logger.error(f"画像ファイル読み込みエラー: {image_path}", exc_info=True)
            raise ImageLoadError(f"Cannot read image file: {image_path}") from e
        except Exception as e:
            logger.error(f"ベクトル化処理中に予期しないエラー: {os.path.basename(image_path)}", exc_info=True)
            raise VectorProcessingError(f"Failed to vectorize image: {e}") from e

    def get_image_features_batch(self, image_paths):
        """複数の画像パスを受け取って、ベクトルのリストを返すのじゃ。
        
        バッチ処理により、単一処理より高速に複数画像を処理できるのじゃ。
        
        Args:
            image_paths (list): 画像ファイルパスのリスト
            
        Returns:
            list: (画像パス, ベクトル) のタプルリスト
        """
        if not self.available:
            logger.error("AIモデルが利用可能ではありません")
            raise AIModelError("AI model is not available")
        
        if not image_paths:
            logger.warning("バッチ処理：画像パスリストが空です")
            return []
        
        results = []
        batch_size = 8  # GPU/CPU負荷を考慮したバッチサイズ
        
        try:
            logger.info(f"バッチ処理開始: {len(image_paths)}個の画像を{batch_size}個ずつ処理するのじゃ")
            
            # 画像をバッチで処理
            for batch_start in range(0, len(image_paths), batch_size):
                batch_end = min(batch_start + batch_size, len(image_paths))
                batch_paths = image_paths[batch_start:batch_end]
                
                if self.debug_mode:
                    logger.debug(f"バッチ {batch_start//batch_size + 1}: {len(batch_paths)}個の画像を処理中")
                
                # バッチ内の画像を読み込む
                images = []
                valid_paths = []
                
                for path in batch_paths:
                    try:
                        image = Image.open(path).convert("RGB")
                        images.append(image)
                        valid_paths.append(path)
                    except Exception as e:
                        logger.warning(f"画像読み込み失敗（スキップ）: {path} - {e}")
                        continue
                
                if not images:
                    continue
                
                # 前処理（画像をテンソルに変換）
                input_tensors = [self.preprocess(img) for img in images]
                input_batch = torch.stack(input_tensors).to(self.device)
                
                # バッチ推論
                with torch.no_grad():
                    outputs = self.model(input_batch)
                
                # L2正規化と結果の収集
                for i, (path, output) in enumerate(zip(valid_paths, outputs)):
                    feature_vector = output
                    norm = feature_vector.norm(p=2)
                    if norm > 0:
                        feature_vector = feature_vector / norm
                    
                    vec_list = feature_vector.tolist()
                    results.append((path, vec_list))
                    
                    if self.debug_mode:
                        logger.debug(f"処理完了: {os.path.basename(path)} ({len(vec_list)}次元)")
            
            logger.info(f"バッチ処理完了: {len(results)}個の画像ベクトルを生成したのじゃ")
            return results
            
        except Exception as e:
            logger.error(f"バッチ処理中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to batch process images: {e}") from e

    def compare_features(self, vec1, vec2):
        """2つのベクトルのコサイン類似度（0.0〜1.0）を計算するのじゃ。"""
        try:
            if not TORCH_AVAILABLE or torch is None:
                raise AIModelError("AI model is not available because torch is not installed")
            if not vec1 or not vec2:
                logger.warning("比較するベクトルが空です")
                raise VectorProcessingError("Cannot compare empty vectors")
            
            # torcで計算するのじゃ
            t1 = torch.tensor(vec1)
            t2 = torch.tensor(vec2)
            score = torch.nn.functional.cosine_similarity(t1.unsqueeze(0), t2.unsqueeze(0)).item()
            
            if self.debug_mode:
                logger.debug(f"ベクトル比較完了: 類似度スコア = {score:.4f}")
            return score
        except (VectorProcessingError, AIModelError):
            raise
        except Exception as e:
            logger.error(f"ベクトル比較中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to compare features: {e}") from e

    def compare_features_batch(self, query_vec, candidate_vecs, threshold=0.5):
        """クエリベクトルと複数の候補ベクトルを比較し、閾値以上のスコアを返すのじゃ。
        
        バッチ比較により、大量の類似度計算を高速に処理できるのじゃ。
        
        Args:
            query_vec (list): クエリベクトル（特徴量）
            candidate_vecs (list): 候補ベクトルのリスト
            threshold (float): スコア閾値（0.0-1.0）。この以上のマッチを返す。
            
        Returns:
            list: (インデックス, スコア) のタプルリスト。スコア順（降順）に返す。
        """
        try:
            if not TORCH_AVAILABLE or torch is None:
                raise AIModelError("AI model is not available because torch is not installed")
            if not query_vec or not candidate_vecs:
                logger.warning("比較用ベクトルが不足しています")
                return []
            
            t_query = torch.tensor(query_vec)
            t_candidates = torch.stack([torch.tensor(v) for v in candidate_vecs])
            
            # バッチコサイン類似度計算
            scores = torch.nn.functional.cosine_similarity(
                t_query.unsqueeze(0),
                t_candidates
            )
            
            # 閾値以上のマッチを抽出＆ソート
            matches = []
            for idx, score in enumerate(scores):
                score_val = score.item()
                if score_val >= threshold:
                    matches.append((idx, score_val))
            
            # スコア降順でソート
            matches.sort(key=lambda x: x[1], reverse=True)
            
            if self.debug_mode:
                logger.debug(f"バッチ比較完了: {len(candidate_vecs)}個中{len(matches)}個がマッチ（閾値={threshold}）")
            
            return matches
            
        except AIModelError:
            raise
        except Exception as e:
            logger.error(f"バッチ比較処理中にエラー: {e}", exc_info=True)
            raise VectorProcessingError(f"Failed to batch compare features: {e}") from e

class VectorBatchProcessor(threading.Thread):
    """バックグラウンドでベクトル化を行うスレッドクラスなのじゃ。"""
    def __init__(self, folder_path, callback_progress=None, callback_finish=None):
        super().__init__()
        self.folder_path = folder_path
        self.callback_progress = callback_progress
        self.callback_finish = callback_finish
        self.daemon = True # メイン終了時に一緒に終わるようにするのじゃ
        self.running = True

    def run(self):
        try:
            engine = VectorEngine.get_instance()
            if not engine.check_available():
                logger.error("AIモデルが利用できません")
                if self.callback_finish: 
                    self.callback_finish("AIモデルが利用できないのじゃ")
                return

            all_items = os.listdir(self.folder_path)
            files = GetGazoFiles(all_items, self.folder_path)
            total = len(files)
            
            try:
                vectors = load_vectors()
            except VectorProcessingError as e:
                logger.warning(f"既存ベクトルデータの読み込み失敗、新規作成します: {e}")
                vectors = {}
            
            updated_count = 0
            failed_count = 0
            
            logger.info(f"ベクトル更新開始: {total}ファイルをチェック")
            
            start_time = time.time()
            last_log_time = start_time
            
            for i, filename in enumerate(files):
                if not self.running: 
                    logger.info("ベクトル化処理が中止されました")
                    break
                
                # タイムアウトチェック (10分)
                current_time = time.time()
                elapsed = current_time - start_time
                if elapsed > 600:
                    logger.warning(f"ベクトル化処理がタイムアウト (10分経過)")
                    if self.callback_finish:
                        self.callback_finish("タイムアウトにより停止したのじゃ")
                    break

                # 経過表示 (1分ごと)
                if current_time - last_log_time >= 60:
                    logger.info(f"ベクトル化処理中... {i}/{total} ({int(elapsed)}秒経過)")
                    last_log_time = current_time

                full_path = os.path.join(self.folder_path, filename)
                
                try:
                    file_hash = calculate_file_hash(full_path)
                except FileHashError as e:
                    logger.warning(f"ハッシュ計算失敗: {filename}")
                    failed_count += 1
                    continue
                
                # まだベクトルがない、あるいはハッシュが変わった場合のみ計算
                if file_hash and file_hash not in vectors:
                    try:
                        vec = engine.get_image_feature(full_path)
                        if vec:
                            vectors[file_hash] = vec
                            updated_count += 1
                    except Exception as e:
                        logger.warning(f"ベクトル化失敗: {filename} - {e}")
                        failed_count += 1
                
                if self.callback_progress:
                    self.callback_progress(i + 1, total, filename)
                
                # 少し休みを入れてCPUを占有しすぎないようにするのじゃ
                time.sleep(0.01)

            # ベクトルを保存
            try:
                if updated_count > 0:
                    save_vectors(vectors)
            except VectorProcessingError as e:
                logger.error(f"ベクトルデータ保存失敗: {e}")
                if self.callback_finish:
                    self.callback_finish(f"ベクトル保存エラー: {e}")
                return
                
            if self.callback_finish:
                message = f"完了！ {updated_count}件のベクトルを新規追加したのじゃ。"
                if failed_count > 0:
                    message += f"({failed_count}件失敗)"
                self.callback_finish(message)
            
            logger.info(f"ベクトル更新完了: 追加{updated_count}件、失敗{failed_count}件")
            
        except Exception as e:
            logger.error(f"ベクトル化スレッド処理中に予期しないエラー: {e}", exc_info=True)
            if self.callback_finish:
                self.callback_finish(f"予期しないエラーが発生したのじゃ: {e}")

    def stop(self):
        logger.info("ベクトル化処理停止要求")
        self.running = False

if __name__ == "__main__":
    # メイン実行ブロックなのじゃ
    print("=== GazoToolsAI 単体実行モードを開始するのじゃ ===")

    if not TORCH_AVAILABLE:
        print("AI機能は無効です: torch / torchvision がインストールされていません")
        sys.exit(0)

    # シングルトンインスタンスを取得するのじゃ
    print("メイン: VectorEngineのインスタンスを取得しに行くのじゃ。")
    engine = VectorEngine.get_instance()

    if not engine.check_available():
        print("メイン: エンジンの初期化に失敗したため、終了するのじゃ...")
        sys.exit(1)

    print("メイン: 引数のチェックを行うのじゃ。")
    # 引数があれば画像パスとして処理、なければ対話モード
    if len(sys.argv) > 1:
        img_paths = sys.argv[1:]
        print(f"メイン: コマンドライン引数から {len(img_paths)} 個の画像パスを受け取ったのじゃ。")
        vectors = []
        for i, path in enumerate(img_paths):
            print(f"\n--- 画像 {i+1} / {len(img_paths)} の処理 ---")
            # パスの前後の引用符を削除（Windowsのコピペ対策）
            clean_path = path.strip().strip('"')
            if os.path.exists(clean_path):
                print(f"パス確認OK: '{os.path.basename(clean_path)}'")
                vec = engine.get_image_feature(clean_path)
                if vec:
                    print("  -> ベクトル化成功なのじゃ。リストに追加するのじゃ。")
                    vectors.append((clean_path, vec))
                else:
                    print("  -> ベクトル化失敗なのじゃ。スキップするのじゃ。")
            else:
                print(f"ファイルが見つからないのじゃ: {clean_path}")
        
        # 2つ以上あれば総当たりで比較
        if len(vectors) >= 2:
            print("\n==============================")
            print("総当たり類似度比較を開始するのじゃ:")
            for (p1, v1), (p2, v2) in itertools.combinations(vectors, 2):
                print(f"\n[{os.path.basename(p1)}] vs [{os.path.basename(p2)}]")
                score = engine.compare_features(v1, v2)
                print(f"結果: 類似度 {score:.4f}")
            print("==============================")
        else:
             print("比較対象が2つ以上揃わなかったため、比較はスキップするのじゃ。")

    else:
        print("メイン: 画像パスが引数に指定されていないのじゃ。対話モードでテストを開始するのじゃ。")
        while True:
            print("\n--- 新しい比較ラウンド ---")
            path1 = input("1枚目の画像パスを入力するのじゃ (終了ならq): ").strip().strip('"')
            if path1.lower() == 'q' or not path1:
                print("対話モードを終了するのじゃ。")
                break
            
            print(f"入力されたパス(1): {path1}")
            if not os.path.exists(path1):
                print("ファイルが存在しないのじゃ。もう一度頼むのじゃ。")
                continue

            print("画像1の処理を呼び出すのじゃ...")
            vec1 = engine.get_image_feature(path1)
            if not vec1:
                print("画像1のベクトル化に失敗したのじゃ。やり直すのじゃ。")
                continue
                
            path2 = input("比較対象の画像パスを入力するのじゃ (なければEnterでスキップ): ").strip().strip('"')
            if not path2:
                print("比較対象がないため、このラウンドは終了なのじゃ。")
                continue
            
            print(f"入力されたパス(2): {path2}")
            if not os.path.exists(path2):
                print("比較ファイルが存在しないのじゃ。")
                continue

            print("画像2の処理を呼び出すのじゃ...")
            vec2 = engine.get_image_feature(path2)
            if vec2:
                print("2つのベクトルが揃ったので比較するのじゃ...")
                sim = engine.compare_features(vec1, vec2)
                print(f"★ 最終結果判定: 類似度は {sim:.4f} なのじゃ！")

    print("\n=== GazoToolsAI 単体実行モードを終了するのじゃ ===")
