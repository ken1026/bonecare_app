# utils/vertebral_calculations.py
# 椎体別計算ロジック

import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.calculations import BoneDensityCalculator
from typing import Dict, List, Optional

class VertebralCalculator:
    def __init__(self):
        """椎体別計算クラスの初期化"""
        self.base_calculator = BoneDensityCalculator()
    
    def calculate_vertebral_metrics(self, vertebral_bmds: Dict[str, float], gender: str) -> Dict:
        """椎体別の全指標を計算
        
        Args:
            vertebral_bmds: {'L1': 0.850, 'L2': 0.920, 'L3': 0.940, 'L4': 0.980}
            gender: '男性' or '女性'
        
        Returns:
            椎体別の計算結果辞書
        """
        try:
            # 性別を英語に変換
            gender_en = 'female' if gender == '女性' else 'male'
            
            vertebral_results = {}
            vertebral_data = []
            
            # 各椎体の計算
            for vertebra, bmd_value in vertebral_bmds.items():
                if bmd_value and bmd_value > 0:
                    # 椎体別計算（腰椎基準を使用）
                    vertebral_result = {
                        'vertebra_level': vertebra,
                        'bmd_value': bmd_value,
                        'yam_percentage': self.base_calculator.calculate_yam(bmd_value, 'lumbar', gender_en),
                        'tscore': self.base_calculator.calculate_tscore(bmd_value, 'lumbar', gender_en),
                    }
                    
                    # 椎体別診断
                    vertebral_result['diagnosis'] = self.base_calculator.get_diagnosis(
                        vertebral_result['yam_percentage']
                    )
                    
                    vertebral_results[vertebra] = vertebral_result
                    vertebral_data.append(vertebral_result)
            
            # 平均値の計算
            if vertebral_data:
                bmd_values = [v['bmd_value'] for v in vertebral_data]
                average_bmd = sum(bmd_values) / len(bmd_values)
                
                # 平均値での公式診断
                average_metrics = {
                    'average_bmd': average_bmd,
                    'average_yam': self.base_calculator.calculate_yam(average_bmd, 'lumbar', gender_en),
                    'average_tscore': self.base_calculator.calculate_tscore(average_bmd, 'lumbar', gender_en),
                }
                average_metrics['average_diagnosis'] = self.base_calculator.get_diagnosis(
                    average_metrics['average_yam']
                )
                
                # 椎体間分析
                analysis = self._analyze_vertebral_differences(vertebral_data)
                
                return {
                    'vertebral_results': vertebral_results,
                    'average_metrics': average_metrics,
                    'analysis': analysis,
                    'vertebral_data': vertebral_data  # データベース保存用
                }
            
            return {}
            
        except Exception as e:
            print(f"椎体別計算エラー: {e}")
            return {}
    
    def _analyze_vertebral_differences(self, vertebral_data: List[Dict]) -> Dict:
        """椎体間の差異分析"""
        try:
            if len(vertebral_data) < 2:
                return {}
            
            bmd_values = [v['bmd_value'] for v in vertebral_data]
            yam_values = [v['yam_percentage'] for v in vertebral_data if v['yam_percentage']]
            tscore_values = [v['tscore'] for v in vertebral_data if v['tscore']]
            
            analysis = {
                # BMD分析
                'bmd_max': max(bmd_values),
                'bmd_min': min(bmd_values),
                'bmd_range': max(bmd_values) - min(bmd_values),
                'bmd_average': sum(bmd_values) / len(bmd_values),
                
                # 最低値・最高値の椎体
                'lowest_vertebra': next((v['vertebra_level'] for v in vertebral_data 
                                       if v['bmd_value'] == min(bmd_values)), None),
                'highest_vertebra': next((v['vertebra_level'] for v in vertebral_data 
                                        if v['bmd_value'] == max(bmd_values)), None),
            }
            
            # YAM分析
            if yam_values:
                analysis.update({
                    'yam_max': max(yam_values),
                    'yam_min': min(yam_values),
                    'yam_range': max(yam_values) - min(yam_values),
                    'yam_average': sum(yam_values) / len(yam_values),
                    'lowest_yam_vertebra': next((v['vertebra_level'] for v in vertebral_data 
                                               if v['yam_percentage'] == min(yam_values)), None)
                })
            
            # T-score分析
            if tscore_values:
                analysis.update({
                    'tscore_max': max(tscore_values),
                    'tscore_min': min(tscore_values),
                    'tscore_range': max(tscore_values) - min(tscore_values),
                    'tscore_average': sum(tscore_values) / len(tscore_values),
                    'lowest_tscore_vertebra': next((v['vertebra_level'] for v in vertebral_data 
                                                  if v['tscore'] == min(tscore_values)), None)
                })
            
            # リスク評価
            analysis['risk_assessment'] = self._assess_vertebral_risk(vertebral_data, analysis)
            
            return analysis
            
        except Exception as e:
            print(f"椎体間分析エラー: {e}")
            return {}
    
    def _assess_vertebral_risk(self, vertebral_data: List[Dict], analysis: Dict) -> Dict:
        """椎体別リスク評価"""
        try:
            risk_assessment = {
                'high_risk_vertebrae': [],
                'moderate_risk_vertebrae': [],
                'attention_points': []
            }
            
            # 各椎体のリスク評価
            for vertebra in vertebral_data:
                yam = vertebra.get('yam_percentage', 0)
                vertebra_level = vertebra['vertebra_level']
                
                if yam < 70:
                    risk_assessment['high_risk_vertebrae'].append({
                        'vertebra': vertebra_level,
                        'yam': yam,
                        'reason': '骨粗鬆症レベル'
                    })
                elif yam < 80:
                    risk_assessment['moderate_risk_vertebrae'].append({
                        'vertebra': vertebra_level,
                        'yam': yam,
                        'reason': '骨量減少'
                    })
            
            # 椎体間の差異チェック
            if analysis.get('yam_range', 0) > 15:
                risk_assessment['attention_points'].append(
                    f"椎体間のYAM差が大きい ({analysis['yam_range']:.1f}%)"
                )
            
            if analysis.get('bmd_range', 0) > 0.1:
                risk_assessment['attention_points'].append(
                    f"椎体間のBMD差が大きい ({analysis['bmd_range']:.3f} g/cm²)"
                )
            
            # 最低値椎体の特定
            if analysis.get('lowest_yam_vertebra'):
                lowest_vertebra = analysis['lowest_yam_vertebra']
                lowest_yam = analysis.get('yam_min', 0)
                risk_assessment['attention_points'].append(
                    f"{lowest_vertebra}椎体が最も脆弱 (YAM: {lowest_yam:.1f}%)"
                )
            
            return risk_assessment
            
        except Exception as e:
            print(f"リスク評価エラー: {e}")
            return {}
    
    def calculate_vertebral_progression(self, current_data: List[Dict], previous_data: List[Dict]) -> Dict:
        """椎体別経過比較"""
        try:
            progression = {}
            
            # 現在のデータを辞書に変換
            current_dict = {v['vertebra_level']: v for v in current_data}
            previous_dict = {v['vertebra_level']: v for v in previous_data}
            
            for vertebra in ['L1', 'L2', 'L3', 'L4']:
                if vertebra in current_dict and vertebra in previous_dict:
                    current = current_dict[vertebra]
                    previous = previous_dict[vertebra]
                    
                    progression[vertebra] = {
                        'bmd_change': current['bmd_value'] - previous['bmd_value'],
                        'yam_change': current.get('yam_percentage', 0) - previous.get('yam_percentage', 0),
                        'tscore_change': current.get('tscore', 0) - previous.get('tscore', 0),
                        'current_bmd': current['bmd_value'],
                        'previous_bmd': previous['bmd_value'],
                        'trend': self._determine_trend(
                            current['bmd_value'], previous['bmd_value']
                        )
                    }
            
            return progression
            
        except Exception as e:
            print(f"経過比較エラー: {e}")
            return {}
    
    def _determine_trend(self, current_value: float, previous_value: float) -> str:
        """変化傾向の判定"""
        change = current_value - previous_value
        change_percent = (change / previous_value) * 100 if previous_value > 0 else 0
        
        if change_percent > 2:
            return "改善"
        elif change_percent < -2:
            return "悪化"
        else:
            return "安定"
    
    def format_vertebral_results(self, results: Dict) -> Dict:
        """結果の表示用フォーマット"""
        try:
            if not results:
                return {}
            
            vertebral_results = results.get('vertebral_results', {})
            average_metrics = results.get('average_metrics', {})
            analysis = results.get('analysis', {})
            
            formatted = {
                'summary': {
                    'average_bmd': f"{average_metrics.get('average_bmd', 0):.3f} g/cm²",
                    'average_yam': f"{average_metrics.get('average_yam', 0):.1f}%",
                    'average_tscore': f"{average_metrics.get('average_tscore', 0):.1f}",
                    'diagnosis': average_metrics.get('average_diagnosis', '不明')
                },
                'vertebral_details': {},
                'analysis_summary': {
                    'range_info': f"BMD範囲: {analysis.get('bmd_min', 0):.3f} - {analysis.get('bmd_max', 0):.3f} g/cm²",
                    'lowest_vertebra': analysis.get('lowest_vertebra', '不明'),
                    'highest_vertebra': analysis.get('highest_vertebra', '不明'),
                    'risk_points': analysis.get('risk_assessment', {}).get('attention_points', [])
                }
            }
            
            # 椎体別詳細
            for vertebra, data in vertebral_results.items():
                formatted['vertebral_details'][vertebra] = {
                    'bmd': f"{data['bmd_value']:.3f} g/cm²",
                    'yam': f"{data['yam_percentage']:.1f}%",
                    'tscore': f"{data['tscore']:.1f}",
                    'diagnosis': data['diagnosis']
                }
            
            return formatted
            
        except Exception as e:
            print(f"フォーマットエラー: {e}")
            return {}