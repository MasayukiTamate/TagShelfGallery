
import os
import time
import torch
from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info

def test_qwen_cpu_low_load():
    print("--- Qwen2-VL-2B CPU Test Start ---")
    print("PCへの負荷を抑えるため、CPUスレッド数を制限して実行するのじゃ...")
    
    # 1. 負荷軽減設定: スレッド数を制限 (全コアを使わないようにする)
    torch.set_num_threads(2) 
    
    try:
        # 2. モデルのロード (これには少し時間がかかり、メモリも使うのじゃ)
        print("モデルをロード中... (初回はダウンロードを含め数分かかる場合があるのじゃ)")
        start_load = time.time()
        
        # Qwen2-VL-2B-Instruct をロード
        # "Qwen/Qwen2-VL-2B-Instruct" はHugging FaceのモデルID
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            "Qwen/Qwen2-VL-2B-Instruct", 
            torch_dtype=torch.float32, # CPU用標準精度 (float32)
            device_map="cpu",
            low_cpu_mem_usage=True # メモリ効率化
        )
        
        processor = AutoProcessor.from_pretrained("Qwen/Qwen2-VL-2B-Instruct")
        
        load_time = time.time() - start_load
        print(f"モデルロード完了: {load_time:.2f}秒")

        # 3. テストデータの準備 (Web上のサンプル画像を使用)
        print("画像解析を実行中...")
        image_url = "https://qianwen-res.oss-cn-beijing.aliyuncs.com/Qwen-VL/assets/demo.jpeg"
        
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "image": image_url,
                    },
                    {"type": "text", "text": "この画像に写っているものを日本語の単語で、カンマ区切りで5つ挙げてほしいのじゃ。例: 犬, 公園, 木"},
                ],
            }
        ]

        # 4. 推論実行
        start_infe = time.time()
        
        # 入力の準備
        text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        image_inputs, video_inputs = process_vision_info(messages)
        inputs = processor(
            text=[text],
            images=image_inputs,
            videos=video_inputs,
            padding=True,
            return_tensors="pt",
        )
        inputs = inputs.to("cpu")

        # 生成
        generated_ids = model.generate(**inputs, max_new_tokens=128)
        generated_ids_trimmed = [
            out_ids[len(in_ids) :] for in_ids, out_ids in zip(inputs.input_ids, generated_ids)
        ]
        output_text = processor.batch_decode(
            generated_ids_trimmed, skip_special_tokens=True, clean_up_tokenization_spaces=False
        )
        
        infe_time = time.time() - start_infe
        
        print("\n--- 結果 ---")
        print(f"出力タグ: {output_text[0]}")
        print(f"解析時間: {infe_time:.2f}秒")
        print("----------------")
        print("テスト成功なのじゃ！")

    except Exception as e:
        print(f"\nエラーが発生したのじゃ...\n{e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qwen_cpu_low_load()
