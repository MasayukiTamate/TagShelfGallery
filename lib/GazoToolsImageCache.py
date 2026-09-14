"""
GazoTools 画像キャッシング機構

LRU（最近最少使用）キャッシュで、頻繁にアクセスされる画像をメモリに保持。
タイル表示やスライドショーの描画パフォーマンスを大幅に向上させるのじゃ。
"""

from collections import OrderedDict
import threading
import sys
from pathlib import Path
from PIL import Image
from .GazoToolsLogger import LoggerManager

logger = LoggerManager.get_logger(__name__)


class ImageCache:
    """LRUキャッシュで画像を管理するシングルトンクラスのじゃ。
    
    メモリ効率とパフォーマンスのバランスを取りながら、頻繁にアクセスされる
    画像をメモリに保持し、ディスクI/Oを削減するのじゃ。
    """
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, max_size_mb=256):
        """シングルトンインスタンスを取得するのじゃ。
        
        Args:
            max_size_mb (int): キャッシュの最大メモリサイズ（MB単位）
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(max_size_mb=max_size_mb)
        return cls._instance
    
    def __init__(self, max_size_mb=256):
        """初期化処理。
        
        Args:
            max_size_mb (int): キャッシュの最大メモリサイズ（MB）
        """
        self.max_size_bytes = max_size_mb * 1024 * 1024  # MB → bytes
        self.current_size_bytes = 0
        self.cache = OrderedDict()  # {path: PIL.Image}
        logger.info(f"ImageCache初期化: 最大{max_size_mb}MBのメモリを使用するのじゃ")
    
    def get(self, image_path, target_size=None):
        """キャッシュから画像を取得。未キャッシュならディスクから読み込むのじゃ。
        
        Args:
            image_path (str): 画像ファイルパス
            target_size (tuple): リサイズ先サイズ (width, height) - 省略可
            
        Returns:
            PIL.Image: 画像オブジェクト（キャッシュヒット時は高速）
        """
        try:
            # キャッシュから取得
            if image_path in self.cache:
                # LRU更新：アクセス順を最新に
                self.cache.move_to_end(image_path)
                img = self.cache[image_path]
                
                if target_size and img.size != target_size:
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                
                if logger.level == "DEBUG":
                    logger.debug(f"キャッシュヒット: {Path(image_path).name}")
                
                return img
            
            # ディスクから読み込み
            if logger.level == "DEBUG":
                logger.debug(f"ディスク読み込み: {Path(image_path).name}")
            
            img = Image.open(image_path).convert("RGB")
            
            # リサイズが指定されていればここで実行
            if target_size:
                img = img.resize(target_size, Image.Resampling.LANCZOS)
            
            # キャッシュに追加
            self._add_to_cache(image_path, img)
            
            return img
            
        except FileNotFoundError:
            logger.error(f"画像ファイルが見つかりません: {image_path}")
            raise
        except Exception as e:
            logger.error(f"画像読み込みエラー: {image_path} - {e}")
            raise
    
    def preload(self, image_paths, target_size=None):
        """複数の画像を事前読み込みするのじゃ。
        
        スライドショーやギャラリー表示前に呼び出して、表示遅延を防ぐ。
        
        Args:
            image_paths (list): 画像ファイルパスのリスト
            target_size (tuple): リサイズ先サイズ (width, height)
        """
        loaded = 0
        skipped = 0
        
        for path in image_paths:
            if path in self.cache:
                skipped += 1
                continue
            
            try:
                self.get(path, target_size)
                loaded += 1
            except Exception as e:
                logger.warning(f"プリロード失敗: {Path(path).name}")
                continue
        
        logger.info(f"プリロード完了: {loaded}個読み込み, {skipped}個スキップ")
    
    def _add_to_cache(self, image_path, img):
        """画像をキャッシュに追加するのじゃ。必要に応じてLRU削除。"""
        # 画像サイズ推定（RGBA相当で計算）
        width, height = img.size
        estimated_size = width * height * 4  # RGBA: 4bytes/pixel
        
        # 容量を超えるなら古い項目を削除
        while self.current_size_bytes + estimated_size > self.max_size_bytes:
            if not self.cache:
                break
            
            removed_path, removed_img = self.cache.popitem(last=False)
            removed_size = removed_img.size[0] * removed_img.size[1] * 4
            self.current_size_bytes -= removed_size
            logger.debug(f"キャッシュ削除（LRU）: {Path(removed_path).name}")
        
        # 新規項目を追加
        self.cache[image_path] = img
        self.current_size_bytes += estimated_size
    
    def clear(self):
        """キャッシュを全削除するのじゃ。"""
        self.cache.clear()
        self.current_size_bytes = 0
        logger.info("ImageCacheをクリアしたのじゃ")
    
    def get_stats(self):
        """キャッシュ統計情報を返すのじゃ。
        
        Returns:
            dict: {"count": キャッシュ内の画像数, "size_mb": 使用メモリ}
        """
        size_mb = self.current_size_bytes / (1024 * 1024)
        return {
            "count": len(self.cache),
            "size_mb": size_mb,
            "max_mb": self.max_size_bytes / (1024 * 1024)
        }


class TileImageLoader:
    """タイル表示用の画像ローダー。
    
    複数の画像を同じサイズでタイル状に表示する場合の最適化ローダーのじゃ。
    キャッシュとバッチ処理を組み合わせて高速化するのじゃ。
    """
    
    def __init__(self, tile_size=(200, 200), cache_mb=256):
        """初期化。
        
        Args:
            tile_size (tuple): タイル表示時のリサイズサイズ
            cache_mb (int): キャッシュメモリ上限（MB）
        """
        self.tile_size = tile_size
        self.cache = ImageCache.get_instance(max_size_mb=cache_mb)
        logger.info(f"TileImageLoader初期化: {tile_size[0]}x{tile_size[1]}のタイルサイズで設定")
    
    def load_tiles(self, image_paths, preload=True):
        """複数の画像をタイル用にロードするのじゃ。
        
        Args:
            image_paths (list): 画像ファイルパスのリスト
            preload (bool): 事前読み込みを実行するか
            
        Returns:
            list: (パス, PIL.Image) のタプルリスト
        """
        if preload:
            self.cache.preload(image_paths, target_size=self.tile_size)
        
        results = []
        for path in image_paths:
            try:
                img = self.cache.get(path, target_size=self.tile_size)
                results.append((path, img))
            except Exception as e:
                logger.warning(f"タイル読み込み失敗: {path}")
                continue
        
        return results


class SlideShowImageLoader:
    """スライドショー用の画像ローダー。
    
    連続して表示される画像を事前キャッシュして、表示遅延を防ぐのじゃ。
    """
    
    def __init__(self, cache_mb=512):
        """初期化。
        
        Args:
            cache_mb (int): キャッシュメモリ上限（MB）
        """
        self.cache = ImageCache.get_instance(max_size_mb=cache_mb)
        self.preload_count = 3  # 先読みする画像数
        logger.info("SlideShowImageLoader初期化")
    
    def prepare_sequence(self, image_paths, current_index=0):
        """スライドショーの画像シーケンスを準備するのじゃ。
        
        現在の画像周辺を事前ロードして、スムーズな再生を実現。
        
        Args:
            image_paths (list): すべての画像パスのリスト
            current_index (int): 現在の画像インデックス
        """
        # 先読みするインデックスを計算
        to_preload = []
        for offset in range(1, self.preload_count + 1):
            idx = (current_index + offset) % len(image_paths)
            to_preload.append(image_paths[idx])
        
        # 事前ロード実行
        if to_preload:
            self.cache.preload(to_preload)
            logger.debug(f"スライドショー先読み: {len(to_preload)}個を準備")
    
    def get_current(self, image_paths, current_index):
        """現在の画像を取得するのじゃ。
        
        Args:
            image_paths (list): すべての画像パス
            current_index (int): 現在のインデックス
            
        Returns:
            PIL.Image: 画像オブジェクト
        """
        # 次のシーケンスを準備（バックグラウンド）
        self.prepare_sequence(image_paths, current_index)
        
        # 現在の画像を返す
        return self.cache.get(image_paths[current_index])


if __name__ == "__main__":
    # テスト用メイン処理
    print("ImageCache テストモード")
    
    # キャッシュの取得
    cache = ImageCache.get_instance(max_size_mb=100)
    
    # テストディレクトリ作成＆ダミー画像生成
    import os
    test_dir = Path("test_cache_images")
    test_dir.mkdir(exist_ok=True)
    
    print("テスト画像を生成中...")
    test_images = []
    for i in range(3):
        from PIL import Image as PILImage
        import numpy as np
        
        # ランダムカラー画像
        img_array = np.random.randint(0, 256, (400, 400, 3), dtype=np.uint8)
        img = PILImage.fromarray(img_array)
        
        path = test_dir / f"test_{i}.png"
        img.save(path)
        test_images.append(str(path))
    
    print(f"テスト画像: {test_images}")
    
    # キャッシュテスト
    print("\n--- キャッシュテスト ---")
    for i, path in enumerate(test_images):
        print(f"\n{i+1}回目のアクセス:")
        import time
        
        start = time.time()
        img = cache.get(path)
        elapsed = time.time() - start
        
        stats = cache.get_stats()
        print(f"  読み込み時間: {elapsed*1000:.2f}ms")
        print(f"  キャッシュ状態: {stats['count']}個, {stats['size_mb']:.1f}MB/{stats['max_mb']:.1f}MB")
    
    # キャッシュヒット確認
    print("\n--- キャッシュヒット確認 ---")
    for i, path in enumerate(test_images[:1]):
        start = time.time()
        img = cache.get(path)
        elapsed = time.time() - start
        print(f"  読み込み時間: {elapsed*1000:.3f}ms（キャッシュ済み）")
    
    print("\nテスト完了")
