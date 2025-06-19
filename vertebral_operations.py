# database/vertebral_operations.py
# 椎体別データ操作ヘルパー関数

import sqlite3
import os
from typing import List, Dict, Optional, Tuple

class VertebralMeasurementDB:
    def __init__(self):
        self.db_path = os.path.join('data', 'bone_density.db')
    
    def add_vertebral_measurements(self, measurement_id: int, vertebral_data: List[Dict]) -> bool:
        """椎体別測定データを追加"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 既存データの削除（更新の場合）
            cursor.execute("""
                DELETE FROM vertebral_measurements 
                WHERE measurement_id = ?
            """, (measurement_id,))
            
            # 新しいデータの挿入
            for data in vertebral_data:
                cursor.execute("""
                    INSERT INTO vertebral_measurements 
                    (measurement_id, vertebra_level, bmd_value, tscore, yam_percentage, diagnosis, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    measurement_id,
                    data['vertebra_level'],
                    data['bmd_value'],
                    data.get('tscore'),
                    data.get('yam_percentage'),
                    data.get('diagnosis'),
                    data.get('notes', '')
                ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            print(f"椎体別データ追加エラー: {e}")
            return False
    
    def get_vertebral_measurements(self, measurement_id: int) -> List[Dict]:
        """測定IDから椎体別データを取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT vertebral_id, vertebra_level, bmd_value, tscore, 
                       yam_percentage, diagnosis, notes, created_date
                FROM vertebral_measurements 
                WHERE measurement_id = ?
                ORDER BY 
                    CASE vertebra_level 
                        WHEN 'L1' THEN 1 
                        WHEN 'L2' THEN 2 
                        WHEN 'L3' THEN 3 
                        WHEN 'L4' THEN 4 
                    END
            """, (measurement_id,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'vertebral_id': row[0],
                    'vertebra_level': row[1],
                    'bmd_value': row[2],
                    'tscore': row[3],
                    'yam_percentage': row[4],
                    'diagnosis': row[5],
                    'notes': row[6],
                    'created_date': row[7]
                })
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"椎体別データ取得エラー: {e}")
            return []
    
    def get_patient_vertebral_history(self, patient_id: int) -> Dict:
        """患者の椎体別履歴を取得"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT m.measurement_date, vm.vertebra_level, vm.bmd_value, 
                       vm.tscore, vm.yam_percentage, vm.diagnosis
                FROM measurements m
                JOIN vertebral_measurements vm ON m.measurement_id = vm.measurement_id
                WHERE m.patient_id = ?
                ORDER BY m.measurement_date DESC, 
                    CASE vm.vertebra_level 
                        WHEN 'L1' THEN 1 
                        WHEN 'L2' THEN 2 
                        WHEN 'L3' THEN 3 
                        WHEN 'L4' THEN 4 
                    END
            """, (patient_id,))
            
            history = {}
            for row in cursor.fetchall():
                date, level, bmd, tscore, yam, diagnosis = row
                if date not in history:
                    history[date] = {}
                history[date][level] = {
                    'bmd_value': bmd,
                    'tscore': tscore,
                    'yam_percentage': yam,
                    'diagnosis': diagnosis
                }
            
            conn.close()
            return history
            
        except Exception as e:
            print(f"椎体別履歴取得エラー: {e}")
            return {}
    
    def analyze_vertebral_differences(self, measurement_id: int) -> Dict:
        """椎体間の差異分析"""
        try:
            vertebral_data = self.get_vertebral_measurements(measurement_id)
            
            if len(vertebral_data) < 2:
                return {}
            
            bmd_values = [data['bmd_value'] for data in vertebral_data]
            yam_values = [data['yam_percentage'] for data in vertebral_data if data['yam_percentage']]
            
            analysis = {
                'bmd_max': max(bmd_values),
                'bmd_min': min(bmd_values),
                'bmd_range': max(bmd_values) - min(bmd_values),
                'bmd_average': sum(bmd_values) / len(bmd_values),
                'lowest_vertebra': next((data['vertebra_level'] for data in vertebral_data 
                                       if data['bmd_value'] == min(bmd_values)), None)
            }
            
            if yam_values:
                analysis.update({
                    'yam_max': max(yam_values),
                    'yam_min': min(yam_values),
                    'yam_range': max(yam_values) - min(yam_values),
                    'yam_average': sum(yam_values) / len(yam_values)
                })
            
            return analysis
            
        except Exception as e:
            print(f"椎体別分析エラー: {e}")
            return {}