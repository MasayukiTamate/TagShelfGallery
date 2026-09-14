#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GazoTools AI最適化のベンチマークスクリプト

単一処理 vs バッチ処理 vs キャッシュ付きバッチ処理のパフォーマンス比較を実施します。
"""

import time
import os
import sys
from pathlib import Path
from lib.GazoToolsAI import VectorEngine
from lib.GazoToolsLogger import LoggerManager

logger = LoggerManager.get_logger(__name__)


def create_sample_images(num_images=10):
    """テスト用のダミー画像ファイルを作成"""
    try:
        from PIL import Image
        import numpy as np
        
        test_dir = Path("test_images")
        test_dir.mkdir(exist_ok=True)
        
        image_paths = []
        for i in range(num_images):
            # ランダムなRGB画像を生成
            img_array = np.random.randint(0, 256, (224, 224, 3), dtype=np.uint8)
            img = Image.fromarray(img_array)
            
            img_path = test_dir / f"test_image_{i:03d}.png"
            img.save(img_path)
            image_paths.append(str(img_path))
            
        logger.info(f"テスト画像を作成しました: {num_images}個")
        return image_paths
    except Exception as e:
        logger.error(f"テスト画像作成エラー: {e}")
        return []


def benchmark_single_processing(engine, image_paths):
    """単一処理（従来の方法）のベンチマーク
    
    Returns:
        float: 実行時間（秒）
    """
    print("\n" + "="*70)
    print("【ベンチマーク1】単一処理（従来の方法）")
    print("="*70)
    
    start_time = time.time()
    vectors = []
    
    for i, path in enumerate(image_paths):
        try:
            vec = engine.get_image_feature(path)
            vectors.append((path, vec))
            print(f"  進捗: {i+1}/{len(image_paths)} - {os.path.basename(path)}")
        except Exception as e:
            logger.error(f"エラー: {path} - {e}")
    
    elapsed = time.time() - start_time
    
    print(f"\n✓ 実行時間: {elapsed:.2f}秒")
    print(f"✓ 処理枚数: {len(vectors)}枚")
    print(f"✓ 1枚あたり: {elapsed/len(vectors):.3f}秒")
    
    return elapsed


def benchmark_batch_processing(engine, image_paths):
    """バッチ処理（最適化版）のベンチマーク
    
    Returns:
        float: 実行時間（秒）
    """
    print("\n" + "="*70)
    print("【ベンチマーク2】バッチ処理（最適化版）")
    print("="*70)
    
    # キャッシュをクリアして公平な比較を実現
    engine.clear_cache()
    
    start_time = time.time()
    
    try:
        results = engine.get_image_features_batch(image_paths)
        elapsed = time.time() - start_time
        
        print(f"\n✓ 実行時間: {elapsed:.2f}秒")
        print(f"✓ 処理枚数: {len(results)}枚")
        print(f"✓ 1枚あたり: {elapsed/len(results):.3f}秒")
        
        return elapsed
    except Exception as e:
        logger.error(f"バッチ処理エラー: {e}")
        return float('inf')


def benchmark_batch_with_cache(engine, image_paths, num_iterations=2):
    """バッチ処理 + キャッシュのベンチマーク（複数回実行）
    
    Returns:
        tuple: (初回実行時間, 2回目以降の平均時間)
    """
    print("\n" + "="*70)
    print("【ベンチマーク3】バッチ処理 + キャッシュ（複数回実行）")
    print("="*70)
    
    times = []
    
    for iteration in range(num_iterations):
        print(f"\n▶ 実行 {iteration+1}/{num_iterations}")
        
        if iteration == 1:
            # 2回目以降はキャッシュが効いているはず
            print("  (キャッシュが有効な状態)")
        
        start_time = time.time()
        
        try:
            results = engine.get_image_features_batch(image_paths)
            elapsed = time.time() - start_time
            times.append(elapsed)
            
            stats = engine.get_cache_stats()
            print(f"  実行時間: {elapsed:.2f}秒")
            print(f"  キャッシュサイズ: {stats['size']}/{stats['max_size']}")
            
        except Exception as e:
            logger.error(f"バッチ処理エラー: {e}")
            times.append(float('inf'))
    
    print(f"\n✓ 初回実行: {times[0]:.2f}秒")
    if len(times) > 1:
        avg_cached = sum(times[1:]) / len(times[1:])
        print(f"✓ キャッシュ後: {avg_cached:.2f}秒（平均）")
        speedup = times[0] / avg_cached if avg_cached > 0 else 1.0
        print(f"✓ 高速化率: {speedup:.1f}倍")
        return times[0], avg_cached
    
    return times[0], times[0]


def benchmark_similarity_batch(engine):
    """バッチ比較のベンチマーク
    
    1つのクエリベクトルを100個の候補ベクトルと比較
    """
    print("\n" + "="*70)
    print("【ベンチマーク4】バッチ比較処理")
    print("="*70)
    
    # テスト用ベクトル（実際の特徴量の代わり）
    print("▶ テストベクトルを生成中...")
    query_vec = [0.1] * 1024  # クエリベクトル（1024次元）
    candidate_vecs = [[0.1 + i*0.001] * 1024 for i in range(100)]  # 100個の候補
    
    # バッチ比較を実行
    print(f"▶ {len(candidate_vecs)}個の候補ベクトルと比較中...")
    
    start_time = time.time()
    matches = engine.compare_features_batch(query_vec, candidate_vecs, threshold=0.5)
    elapsed = time.time() - start_time
    
    print(f"\n✓ 実行時間: {elapsed*1000:.2f}ms")
    print(f"✓ マッチ数: {len(matches)}/{len(candidate_vecs)}")
    print(f"✓ 1比較あたり: {elapsed/len(candidate_vecs)*1000:.3f}ms")
    
    return elapsed


def main():
    """メインベンチマーク実行"""
    print("\n" + "="*70)
    print("GazoTools AI最適化ベンチマーク")
    print("="*70)
    
    # VectorEngineの初期化
    print("\n▶ VectorEngineを初期化中...")
    try:
        engine = VectorEngine.get_instance()
        print("✓ VectorEngineの初期化完了")
    except Exception as e:
        print(f"✗ VectorEngine初期化エラー: {e}")
        return
    
    # テスト画像の作成
    print("\n▶ テスト画像を生成中...")
    image_paths = create_sample_images(num_images=5)
    
    if not image_paths:
        print("✗ テスト画像の作成に失敗しました")
        return
    
    # ベンチマーク実行
    results = {}
    
    try:
        # 1. 単一処理
        results['single'] = benchmark_single_processing(engine, image_paths)
        
        # 2. バッチ処理
        results['batch'] = benchmark_batch_processing(engine, image_paths)
        
        # 3. バッチ + キャッシュ
        initial_time, cached_time = benchmark_batch_with_cache(engine, image_paths, num_iterations=2)
        results['batch_cached_initial'] = initial_time
        results['batch_cached_avg'] = cached_time
        
        # 4. バッチ比較
        results['batch_similarity'] = benchmark_similarity_batch(engine)
        
    except Exception as e:
        logger.error(f"ベンチマーク実行エラー: {e}", exc_info=True)
        return
    
    # 結果の要約
    print("\n" + "="*70)
    print("ベンチマーク結果サマリー")
    print("="*70)
    
    print(f"\n【処理モード別の実行時間】")
    print(f"  単一処理:           {results['single']:.3f}秒")
    print(f"  バッチ処理:         {results['batch']:.3f}秒")
    print(f"  バッチ+キャッシュ:  {results['batch_cached_initial']:.3f}秒 → {results['batch_cached_avg']:.3f}秒")
    
    # 高速化率の計算
    if results['batch'] > 0:
        speedup_batch = results['single'] / results['batch']
        print(f"\n【高速化率】")
        print(f"  バッチ処理による高速化: {speedup_batch:.1f}倍")
    
    if results['batch_cached_avg'] > 0:
        speedup_cache = results['batch'] / results['batch_cached_avg']
        print(f"  キャッシュによる高速化: {speedup_cache:.1f}倍")
    
    print(f"\n【バッチ比較処理】")
    print(f"  実行時間: {results['batch_similarity']*1000:.2f}ms")
    
    print("\n" + "="*70)
    print("ベンチマーク完了")
    print("="*70)


if __name__ == "__main__":
    main()
