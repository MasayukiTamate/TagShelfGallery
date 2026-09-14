'''
機能: GazoToolsAI (CLIP) の動作検証用スクリプトなのじゃ
'''
import os
import sys

# 自身のディレクトリパスを追加してライブラリをインポートできるようにするのじゃ
sys.path.append(os.getcwd())

from lib.GazoToolsAI import VectorEngine

import threading
import time

def run_test_logic(stop_event):
    """実際のAIテストロジックを実行する関数なのじゃ"""
    print("AI機能のテストを開始するのじゃ！")
    
    # マネージャーの初期化（モデルロード）
    # ここが一番時間がかかる可能性があるのじゃ
    ai = VectorEngine.get_instance()
    
    if stop_event.is_set(): return

    # テスト画像の検索
    image_files = [f for f in os.listdir(".") if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    
    if len(image_files) < 2:
        print("テスト用に画像ファイルが少なくとも2つ必要なのじゃ。カレントディレクトリに置いてほしいのじゃ。")
        return

    img1 = image_files[0]
    img2 = image_files[1]
    
    print(f"テスト対象画像: {img1}, {img2}")

    if stop_event.is_set(): return

    # ベクトル取得テスト
    print(f"--- {img1} の解析 ---")
    vec1 = ai.get_image_feature(img1)
    if vec1:
        print(f"ベクトル取得成功！ 次元数: {len(vec1)}")
        print(f"先頭5つの値: {vec1[:5]}")
    else:
        print("ベクトル取得失敗なのじゃ...")

    if stop_event.is_set(): return

    print(f"--- {img2} の解析 ---")
    vec2 = ai.get_image_feature(img2)
    if vec2:
        print("ベクトル取得成功！")

    # 類似度比較テスト
    if vec1 and vec2:
        similarity = ai.compare_features(vec1, vec2)
        print(f"--- 類似度判定 ---")
        print(f"{img1} と {img2} の類似度: {similarity:.4f}")
        
        if similarity > 0.8:
            print("かなり似ている画像のようじゃな！")
        else:
            print("違う画像のようじゃな。")

    print("テスト終了なのじゃ。")

def test_ai():
    stop_event = threading.Event()
    t = threading.Thread(target=run_test_logic, args=(stop_event,))
    t.daemon = True # メインが終了したら強制終了できるようにする
    t.start()
    
    start_time = time.time()
    last_log_time = start_time
    
    while t.is_alive():
        current_time = time.time()
        elapsed = current_time - start_time
        
        # 10分 (600秒) でタイムアウト
        if elapsed > 600:
            print("\n!!! タイムアウトなのじゃ (10分経過) !!!")
            stop_event.set()
            # スレッドは強制停止できないが、daemon=Trueなのでメインが抜ければ終わる
            return

        # 1分 (60秒) ごとに経過表示
        if current_time - last_log_time >= 60:
            print(f"... 処理中なのじゃ ({int(elapsed)}秒経過)")
            last_log_time = current_time
            
        time.sleep(1) # CPU負荷を下げるためのウェイト

if __name__ == "__main__":
    test_ai()
