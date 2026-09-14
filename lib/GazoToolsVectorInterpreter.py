'''
作成日: 2026年01月04日
作成者: tamate masayuki
機能: GazoTools ベクトル解釈機能
説明: MobileNetV3が生成した1024次元ベクトルを解釈して、
      ユーザーが理解しやすいセマンティック情報に変換するモジュール
'''

import math
from typing import Dict, List, Optional
from lib.GazoToolsLogger import get_logger

logger = get_logger(__name__)


class VectorInterpreter:
    """ベクトルの各次元に意味を紐づけるクラス
    
    MobileNetV3が生成する1024次元の特徴ベクトルを、ユーザーが理解しやすい
    セマンティック情報に変換します。3つの解釈モード（ラベリング、SHAP、カスタム）と、
    特徴カテゴリ別の表示制御を提供します。
    """
    
    # MobileNetV3の1024次元ベクトルを5つのセマンティックカテゴリにマッピング
    FEATURE_MAPPING = {
        "color": {
            "range": (0, 251),
            "description": "色彩情報",
            "sub_features": [
                "赤色成分", "緑色成分", "青色成分", "黄色成分", "シアン色",
                "マゼンタ色", "明るさ", "彩度", "色相"
            ]
        },
        "edge": {
            "range": (251, 451),
            "description": "エッジ・線特徴",
            "sub_features": [
                "水平線", "垂直線", "対角線（左下→右上）", "対角線（左上→右下）",
                "複雑なエッジ", "角度", "曲線"
            ]
        },
        "texture": {
            "range": (451, 751),
            "description": "テクスチャ・パターン特徴",
            "sub_features": [
                "滑らか", "ざらざら", "規則的パターン", "不規則パターン",
                "リピートパターン", "グラデーション", "反復性"
            ]
        },
        "shape": {
            "range": (751, 921),
            "description": "形状特徴",
            "sub_features": [
                "円形", "四角形", "三角形", "多角形", "複雑な形状",
                "対称性", "アスペクト比"
            ]
        },
        "semantic": {
            "range": (921, 1024),
            "description": "セマンティック特徴",
            "sub_features": [
                "動物", "植物", "風景", "建造物", "人物",
                "乗り物", "食べ物", "テキスト", "物体"
            ]
        }
    }
    
    def __init__(self, config: Optional[Dict] = None):
        """VectorInterpreterの初期化
        
        Args:
            config (Dict, optional): 設定辞書。vector_display キーを含める。
                                    Noneの場合はデフォルト設定を使用。
        """
        self.config = config or self._get_default_config()
        logger.debug(f"VectorInterpreter initialized with mode: {self._get_mode()}")
    
    @staticmethod
    def _get_default_config() -> Dict:
        """デフォルト設定を取得
        
        Returns:
            Dict: デフォルト設定辞書
        """
        return {
            "vector_display": {
                "enabled": True,
                "interpretation_mode": "labels",
                "show_color_features": True,
                "show_edge_features": True,
                "show_texture_features": True,
                "show_shape_features": True,
                "show_semantic_features": True,
                "max_dimensions_to_show": 10,
                "similarity_threshold": 0.05,
            }
        }
    
    def _get_mode(self) -> str:
        """現在の解釈モードを取得
        
        Returns:
            str: 解釈モード ("labels", "shap", "custom")
        """
        return self.config.get("vector_display", {}).get("interpretation_mode", "labels")
    
    def _should_show_category(self, category: str) -> bool:
        """指定されたカテゴリを表示すべきか判定
        
        Args:
            category (str): カテゴリ名 ("color", "edge", "texture", "shape", "semantic")
            
        Returns:
            bool: 表示する場合 True、表示しない場合 False
        """
        vd = self.config.get("vector_display", {})
        flag_name = f"show_{category}_features"
        return vd.get(flag_name, True)
    
    def _get_feature_category(self, dimension_index: int) -> str:
        """次元インデックスから特徴カテゴリを取得
        
        Args:
            dimension_index (int): ベクトルの次元インデックス (0-1023)
            
        Returns:
            str: カテゴリ名 ("color", "edge", "texture", "shape", "semantic")
        """
        for category, mapping in self.FEATURE_MAPPING.items():
            start, end = mapping["range"]
            if start <= dimension_index < end:
                return category
        return "unknown"
    
    def _get_feature_name(self, dimension_index: int) -> str:
        """次元インデックスから特徴名を取得
        
        Args:
            dimension_index (int): ベクトルの次元インデックス (0-1023)
            
        Returns:
            str: 特徴の説明的な名前
        """
        category = self._get_feature_category(dimension_index)
        
        if category == "unknown":
            return f"特徴_{dimension_index}"
        
        mapping = self.FEATURE_MAPPING[category]
        start, end = mapping["range"]
        range_size = end - start
        
        # 各次元がサブ特徴のどれに対応しているか計算
        if range_size > 0:
            sub_idx = int((dimension_index - start) / range_size * len(mapping["sub_features"]))
            sub_idx = min(sub_idx, len(mapping["sub_features"]) - 1)
            return mapping["sub_features"][sub_idx]
        
        return mapping["description"]
    
    def interpret_vector(
        self,
        vector: List[float],
        threshold: Optional[float] = None
    ) -> Dict:
        """ベクトルを解釈する（設定されたモードで）
        
        Args:
            vector (List[float]): 1024次元のベクトル
            threshold (float, optional): 表示する最小スコア。
                                        Noneの場合は設定から取得。
        
        Returns:
            Dict: 解釈結果
        """
        # 入力検証とデバッグログ
        if not isinstance(vector, (list, tuple)):
            logger.error(f"不正なベクトル型: {type(vector)}")
            raise TypeError(f"Vector must be a list or tuple, got {type(vector)}")
            
        if len(vector) != 1024:
            logger.warning(f"ベクトルの次元数が想定(1024)と異なります: {len(vector)}")
            # エラーにはせず、継続を試みるが、マッピングは1024次元前提なので注意
            
        if not self.config.get("vector_display", {}).get("enabled", True):
            return {"mode": "disabled", "dimensions": [], "summary": ""}
        
        if threshold is None:
            threshold = self.config.get("vector_display", {}).get("similarity_threshold", 0.05)
        
        mode = self._get_mode()
        
        if mode == "shap":
            return self._interpret_shap(vector, threshold)
        elif mode == "custom":
            return self._interpret_custom(vector, threshold)
        else:  # "labels" がデフォルト
            return self._interpret_labels(vector, threshold)
    
    def _interpret_labels(
        self,
        vector: List[float],
        threshold: float
    ) -> Dict:
        """ラベリングモードでベクトルを解釈
        
        トップNの次元を取り出し、各次元のセマンティック情報を表示
        
        Args:
            vector (List[float]): 1024次元ベクトル
            threshold (float): 最小スコア
            
        Returns:
            Dict: 解釈結果
        """
        # スコアを計算（絶対値の正規化）
        vector_norm = math.sqrt(sum(x**2 for x in vector)) + 1e-8
        scores = [abs(v) / vector_norm for v in vector]
        
        # スコアでソート
        indexed_scores = [(idx, score) for idx, score in enumerate(scores)]
        indexed_scores.sort(key=lambda x: x[1], reverse=True)
        
        # 表示数の上限を取得
        max_dims = self.config.get("vector_display", {}).get("max_dimensions_to_show", 10)
        
        # フィルタリング
        dimensions = []
        for idx, score in indexed_scores:
            if score < threshold or len(dimensions) >= max_dims:
                break
            
            category = self._get_feature_category(idx)
            if not self._should_show_category(category):
                continue
            
            dimensions.append({
                "index": idx,
                "value": score,
                "category": category,
                "name": self._get_feature_name(idx)
            })
        
        return {
            "mode": "labels",
            "dimensions": dimensions,
            "summary": f"トップ{len(dimensions)}の特徴"
        }
    
    def _interpret_shap(
        self,
        vector: List[float],
        threshold: float
    ) -> Dict:
        """SHAP風モードでベクトルを解釈
        
        各次元の寄与度をスコアとして計算して表示
        
        Args:
            vector (List[float]): 1024次元ベクトル
            threshold (float): 最小スコア
            
        Returns:
            Dict: 解釈結果
        """
        # ベクトルノルムで正規化した寄与度を計算
        vector_norm = math.sqrt(sum(x**2 for x in vector)) + 1e-8
        
        # 各次元の寄与度を計算（二乗の比率）
        contributions = [(idx, (v**2) / (vector_norm**2)) for idx, v in enumerate(vector)]
        contributions.sort(key=lambda x: x[1], reverse=True)
        
        max_dims = self.config.get("vector_display", {}).get("max_dimensions_to_show", 10)
        
        dimensions = []
        for idx, contrib in contributions:
            if contrib < threshold or len(dimensions) >= max_dims:
                break
            
            category = self._get_feature_category(idx)
            if not self._should_show_category(category):
                continue
            
            dimensions.append({
                "index": idx,
                "value": contrib,
                "category": category,
                "name": self._get_feature_name(idx)
            })
        
        return {
            "mode": "shap",
            "dimensions": dimensions,
            "summary": f"寄与度トップ{len(dimensions)}"
        }
    
    def _interpret_custom(
        self,
        vector: List[float],
        threshold: float
    ) -> Dict:
        """カスタムモードでベクトルを解釈
        
        将来的に拡張可能な解釈方法。現在はラベリングモードと同じ。
        
        Args:
            vector (List[float]): 1024次元ベクトル
            threshold (float): 最小スコア
            
        Returns:
            Dict: 解釈結果
        """
        # 現在はラベリングモードと同じ実装
        # 将来は独自のアルゴリズムを実装可能
        result = self._interpret_labels(vector, threshold)
        result["mode"] = "custom"
        return result
    
    def format_interpretation_text(self, interpretation: Dict) -> str:
        """解釈結果をテキスト形式にフォーマット
        
        Args:
            interpretation (Dict): interpret_vector() の戻り値
            
        Returns:
            str: フォーマットされたテキスト
        """
        if not interpretation.get("dimensions"):
            return "利用可能な特徴情報がありません"
        
        mode = interpretation.get("mode", "unknown")
        dimensions = interpretation.get("dimensions", [])
        
        lines = [f"[{mode.upper()}モード]"]
        
        show_values = False
        try:
            vd = self.config.get("vector_display", {})
            if isinstance(vd, dict):
                show_values = vd.get("show_internal_values", False)
        except Exception:
            pass # デフォルトOFF

        for i, dim in enumerate(dimensions, 1):
            idx = dim["index"]
            value = dim["value"]
            name = dim["name"]
            
            # 数値表示の切り替え
            if show_values:
                # パーセンテージ表示
                if mode == "shap":
                    pct = value * 100
                    lines.append(f"  {i}. {name} (寄与度: {pct:.1f}%)")
                else:
                    score = value * 100
                    lines.append(f"  {i}. {name} (スコア: {score:.1f}%)")
            else:
                lines.append(f"  {i}. {name}")
        
        return "\n".join(lines)
    
    def update_config(self, new_config: Dict) -> None:
        """実行時に設定を更新
        
        Args:
            new_config (Dict): 新しい設定。
                              get_default_config() と同じ構造を想定。
        """
        self.config = new_config
        logger.debug(f"VectorInterpreter config updated. New mode: {self._get_mode()}")


# グローバルシングルトンインスタンス
_interpreter_instance: Optional[VectorInterpreter] = None


def get_interpreter(config: Optional[Dict] = None) -> VectorInterpreter:
    """VectorInterpreterのシングルトンインスタンスを取得
    
    Args:
        config (Dict, optional): 設定辞書。初回呼び出し時のみ使用される。
        
    Returns:
        VectorInterpreter: インスタンス
    """
    global _interpreter_instance
    
    if _interpreter_instance is None:
        _interpreter_instance = VectorInterpreter(config)
    elif config is not None:
        # 設定が更新されている場合は反映
        _interpreter_instance.update_config(config)
    
    return _interpreter_instance


def reset_interpreter() -> None:
    """テスト用：インスタンスをリセット"""
    global _interpreter_instance
    _interpreter_instance = None


# ===========================
# テスト・デモコード
# ===========================
if __name__ == "__main__":
    import random
    
    print("=" * 60)
    print("VectorInterpreter デモンストレーション")
    print("=" * 60)
    
    # ダミーベクトルを生成
    test_vector = [random.gauss(0, 0.3) for _ in range(1024)]
    
    # ラベリングモード
    print("\n【ラベリングモード】")
    config_labels = {
        "vector_display": {
            "enabled": True,
            "interpretation_mode": "labels",
            "show_color_features": True,
            "show_edge_features": True,
            "show_texture_features": True,
            "show_shape_features": True,
            "show_semantic_features": True,
            "max_dimensions_to_show": 5,
            "similarity_threshold": 0.05,
        }
    }
    
    interpreter = VectorInterpreter(config_labels)
    result = interpreter.interpret_vector(test_vector)
    print(interpreter.format_interpretation_text(result))
    
    # SHAPモード
    print("\n【SHAPモード】")
    config_shap = {
        "vector_display": {
            "enabled": True,
            "interpretation_mode": "shap",
            "show_color_features": True,
            "show_edge_features": True,
            "show_texture_features": True,
            "show_shape_features": True,
            "show_semantic_features": True,
            "max_dimensions_to_show": 5,
            "similarity_threshold": 0.05,
        }
    }
    
    interpreter.update_config(config_shap)
    result = interpreter.interpret_vector(test_vector)
    print(interpreter.format_interpretation_text(result))
    
    # 色彩特徴OFFの設定
    print("\n【ラベリングモード（色彩特徴OFF）】")
    config_no_color = {
        "vector_display": {
            "enabled": True,
            "interpretation_mode": "labels",
            "show_color_features": False,
            "show_edge_features": True,
            "show_texture_features": True,
            "show_shape_features": True,
            "show_semantic_features": True,
            "max_dimensions_to_show": 5,
            "similarity_threshold": 0.05,
        }
    }
    
    interpreter.update_config(config_no_color)
    result = interpreter.interpret_vector(test_vector)
    print(interpreter.format_interpretation_text(result))
    
    print("\n" + "=" * 60)
    print("デモ完了")
    print("=" * 60)
