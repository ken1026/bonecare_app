# utils/calculations.py の修正版

import sqlite3
import os

class BoneDensityCalculator:
    def __init__(self):
        """骨密度計算クラスの初期化"""
        self.reference_values = self._load_reference_values()
    
    def _load_reference_values(self):
        """データベースから年齢範囲対応の基準値を読み込み"""
        try:
            db_path = os.path.join('data', 'bone_density.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 新しいテーブル構造から読み込み
            cursor.execute("""
                SELECT site, female_mean_young, female_sd_young, female_mean_adult, female_sd_adult,
                       male_mean_young, male_sd_young, male_mean_adult, male_sd_adult
                FROM reference_values
            """)
            
            reference_data = {}
            for row in cursor.fetchall():
                site, f_mean_y, f_sd_y, f_mean_a, f_sd_a, m_mean_y, m_sd_y, m_mean_a, m_sd_a = row
                reference_data[site] = {
                    'female': {
                        'young': {'mean': f_mean_y, 'sd': f_sd_y},    # 20-29歳
                        'adult': {'mean': f_mean_a, 'sd': f_sd_a}     # 20-44歳
                    },
                    'male': {
                        'young': {'mean': m_mean_y, 'sd': m_sd_y},    # 20-29歳
                        'adult': {'mean': m_mean_a, 'sd': m_sd_a}     # 20-44歳
                    }
                }
            
            conn.close()
            return reference_data
            
        except Exception as e:
            print(f"基準値読み込みエラー: {e}")
            # エラー時は古い形式の基準値を読み込み
            return self._load_old_reference_values()
    
    def _load_old_reference_values(self):
        """旧形式の基準値読み込み（フォールバック）"""
        try:
            db_path = os.path.join('data', 'bone_density.db')
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # 旧テーブル構造から読み込み
            cursor.execute("SELECT site, female_mean, female_sd, male_mean, male_sd FROM reference_values_backup")
            
            reference_data = {}
            for row in cursor.fetchall():
                site, f_mean, f_sd, m_mean, m_sd = row
                reference_data[site] = {
                    'female': {
                        'young': {'mean': f_mean, 'sd': f_sd},
                        'adult': {'mean': f_mean, 'sd': f_sd}
                    },
                    'male': {
                        'young': {'mean': m_mean, 'sd': m_sd},
                        'adult': {'mean': m_mean, 'sd': m_sd}
                    }
                }
            
            conn.close()
            return reference_data
            
        except Exception as e:
            print(f"フォールバック基準値読み込みエラー: {e}")
            return self._get_default_reference_values()
    
    def _get_default_reference_values(self):
        """デフォルト基準値（最終フォールバック）"""
        return {
            'femur_neck': {
                'female': {
                    'young': {'mean': 0.864, 'sd': 0.12},    # 20-29歳基準
                    'adult': {'mean': 0.864, 'sd': 0.12}     # 大腿骨は若い基準のみ
                },
                'male': {
                    'young': {'mean': 1.028, 'sd': 0.146},
                    'adult': {'mean': 1.028, 'sd': 0.146}
                }
            },
            'lumbar': {
                'female': {
                    'young': {'mean': 1.120, 'sd': 0.134},   # 20-29歳基準（推定）
                    'adult': {'mean': 1.056, 'sd': 0.134}    # 20-44歳基準
                },
                'male': {
                    'young': {'mean': 1.200, 'sd': 0.155},
                    'adult': {'mean': 1.140, 'sd': 0.155}
                }
            }
        }
    
    def calculate_yam(self, bmd_value, site, gender):
        """医学的に正しいYAM計算（年齢範囲対応）"""
        try:
            if site not in self.reference_values:
                return None
            
            # 部位別の正しい基準年齢を使用
            if site == 'femur_neck':
                # 大腿骨: 20-29歳基準を使用
                reference = self.reference_values[site][gender]['young']
            elif site == 'lumbar':
                # 腰椎: 20-44歳基準を使用
                reference = self.reference_values[site][gender]['adult']
            else:
                # その他: 20-44歳基準を使用
                reference = self.reference_values[site][gender]['adult']
            
            # YAM計算
            yam_percentage = (bmd_value / reference['mean']) * 100
            return round(yam_percentage, 1)
            
        except Exception as e:
            print(f"YAM計算エラー: {e}")
            return None
    
    def calculate_tscore(self, bmd_value, site, gender):
        """T-score計算（YAMと同じ基準を使用）"""
        try:
            if site not in self.reference_values:
                return None
            
            # YAMと同じ基準年齢を使用
            if site == 'femur_neck':
                # 大腿骨: 20-29歳基準を使用
                reference = self.reference_values[site][gender]['young']
            elif site == 'lumbar':
                # 腰椎: 20-44歳基準を使用
                reference = self.reference_values[site][gender]['adult']
            else:
                # その他: 20-44歳基準を使用
                reference = self.reference_values[site][gender]['adult']
            
            # T-score計算
            tscore = (bmd_value - reference['mean']) / reference['sd']
            return round(tscore, 1)
            
        except Exception as e:
            print(f"T-score計算エラー: {e}")
            return None
    
    def get_diagnosis(self, yam_percentage):
        """YAM値による診断判定"""
        if yam_percentage is None:
            return "測定不可"
        elif yam_percentage < 70:
            return "骨粗鬆症"
        elif yam_percentage < 80:
            return "骨量減少"
        else:
            return "正常"
    
    def _get_overall_diagnosis(self, results):
        """総合診断の決定"""
        diagnoses = []
        
        if 'femur_diagnosis' in results:
            diagnoses.append(results['femur_diagnosis'])
        if 'lumbar_diagnosis' in results:
            diagnoses.append(results['lumbar_diagnosis'])
        
        if not diagnoses:
            return "測定不可"
        
        # 最も重篤な診断を採用
        if "骨粗鬆症" in diagnoses:
            return "骨粗鬆症"
        elif "骨量減少" in diagnoses:
            return "骨量減少"
        else:
            return "正常"
    
    def calculate_all_metrics(self, femur_bmd, lumbar_bmd, gender):
        """全指標の計算（修正版）"""
        results = {}
        
        # 性別を英語に変換
        gender_en = 'female' if gender == '女性' else 'male'
        
        # 大腿骨の計算
        if femur_bmd and femur_bmd > 0:
            results['femur_yam'] = self.calculate_yam(femur_bmd, 'femur_neck', gender_en)
            results['femur_tscore'] = self.calculate_tscore(femur_bmd, 'femur_neck', gender_en)
            results['femur_diagnosis'] = self.get_diagnosis(results['femur_yam'])
        
        # 腰椎の計算
        if lumbar_bmd and lumbar_bmd > 0:
            results['lumbar_yam'] = self.calculate_yam(lumbar_bmd, 'lumbar', gender_en)
            results['lumbar_tscore'] = self.calculate_tscore(lumbar_bmd, 'lumbar', gender_en)
            results['lumbar_diagnosis'] = self.get_diagnosis(results['lumbar_yam'])
        
        # 総合診断
        results['overall_diagnosis'] = self._get_overall_diagnosis(results)
        
        return results