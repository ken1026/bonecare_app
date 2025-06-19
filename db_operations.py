# database/db_operations.py (transfer_from削除修正版)
import sqlite3
import pandas as pd
from datetime import datetime, date, timedelta
import os

class BoneDensityDB:
    def __init__(self):
        # データベースファイルのパスを設定
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        data_dir = os.path.join(project_root, 'data')
        
        # dataディレクトリが存在しない場合は作成
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        
        self.db_path = os.path.join(data_dir, 'bone_density.db')
        print(f"データベース接続成功: {self.db_path}")

    def get_connection(self):
        """データベース接続を取得"""
        return sqlite3.connect(self.db_path)
    
    def execute_query(self, query, params=None):
        """SQLクエリを実行"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if query.strip().upper().startswith('SELECT'):
                return cursor.fetchall()
            else:
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

    def search_patients(self, search_term=""):
        """患者を検索"""
        try:
            if search_term:
                query = '''
                SELECT patient_id, name_kanji, name_kana, patient_code, birth_date, gender
                FROM patients 
                WHERE name_kanji LIKE ? OR name_kana LIKE ? OR patient_code LIKE ?
                ORDER BY created_date DESC
                '''
                search_pattern = f"%{search_term}%"
                results = self.execute_query(query, [search_pattern, search_pattern, search_pattern])
            else:
                query = '''
                SELECT patient_id, name_kanji, name_kana, patient_code, birth_date, gender
                FROM patients 
                ORDER BY created_date DESC
                LIMIT 20
                '''
                results = self.execute_query(query)
            
            if results:
                df = pd.DataFrame(results, columns=['patient_id', 'name_kanji', 'name_kana', 'patient_code', 'birth_date', 'gender'])
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"患者検索エラー: {e}")
            return pd.DataFrame()

    def add_patient(self, patient_data):
        """新規患者を登録"""
        try:
            query = '''
            INSERT INTO patients (name_kanji, name_kana, patient_code, birth_date, gender, phone, address, email, notes, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = [
                patient_data['name_kanji'],
                patient_data['name_kana'], 
                patient_data['patient_code'],
                patient_data['birth_date'],
                patient_data['gender'],
                patient_data.get('phone', ''),
                patient_data.get('address', ''),
                patient_data.get('email', ''),
                patient_data.get('notes', ''),
                datetime.now()
            ]
            return self.execute_query(query, params)
        except Exception as e:
            print(f"患者登録エラー: {e}")
            return None

    def add_measurement(self, measurement_data):
        """測定データを追加（継続受診管理付き）"""
        try:
            # 測定データを保存
            query = '''
            INSERT INTO measurements (patient_id, measurement_date, femur_bmd, lumbar_bmd, 
                                    femur_yam, lumbar_yam, femur_tscore, lumbar_tscore,
                                    femur_diagnosis, lumbar_diagnosis, overall_diagnosis, notes, created_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = [
                measurement_data['patient_id'],
                measurement_data['measurement_date'],
                measurement_data['femur_bmd'],
                measurement_data['lumbar_bmd'],
                measurement_data['femur_yam'],
                measurement_data['lumbar_yam'],
                measurement_data['femur_tscore'],
                measurement_data['lumbar_tscore'],
                measurement_data['femur_diagnosis'],
                measurement_data['lumbar_diagnosis'],
                measurement_data['overall_diagnosis'],
                measurement_data.get('notes', ''),
                datetime.now()
            ]
            
            measurement_id = self.execute_query(query, params)
            
            if measurement_id:
                # 自動で次回予定を作成
                self.create_next_follow_up(measurement_data['patient_id'], measurement_data['measurement_date'])
                
                # 既存の予定を完了に更新
                self.update_completed_schedules(measurement_data['patient_id'], measurement_data['measurement_date'])
            
            return measurement_id
            
        except Exception as e:
            print(f"測定データ追加エラー: {e}")
            return None

    def get_patient_measurements(self, patient_id):
        """患者の測定履歴を取得"""
        try:
            query = '''
            SELECT measurement_id, measurement_date, femur_bmd, lumbar_bmd,
                   femur_yam, lumbar_yam, femur_tscore, lumbar_tscore,
                   femur_diagnosis, lumbar_diagnosis, overall_diagnosis, notes
            FROM measurements 
            WHERE patient_id = ?
            ORDER BY measurement_date DESC
            '''
            results = self.execute_query(query, [patient_id])
            
            if results:
                df = pd.DataFrame(results, columns=[
                    'measurement_id', 'measurement_date', 'femur_bmd', 'lumbar_bmd',
                    'femur_yam', 'lumbar_yam', 'femur_tscore', 'lumbar_tscore',
                    'femur_diagnosis', 'lumbar_diagnosis', 'overall_diagnosis', 'notes'
                ])
                return df
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"測定履歴取得エラー: {e}")
            return pd.DataFrame()

    # ===== 継続受診管理機能 =====
    
    def create_next_follow_up(self, patient_id, measurement_date):
        """次回フォローアップ予定を自動作成"""
        try:
            # 標準フォローアップ間隔を取得（デフォルト6ヶ月）
            months = self.get_system_setting('default_follow_up_months', 6)
            
            # 次回予定日を計算（6ヶ月後）
            if isinstance(measurement_date, str):
                measurement_date = datetime.strptime(measurement_date, '%Y-%m-%d').date()
            elif isinstance(measurement_date, datetime):
                measurement_date = measurement_date.date()
            
            # 6ヶ月後の計算（182日後で近似）
            next_date = measurement_date + timedelta(days=int(months) * 30)
            
            query = '''
            INSERT INTO follow_up_schedule (patient_id, scheduled_date, status, created_date)
            VALUES (?, ?, ?, ?)
            '''
            params = [patient_id, next_date, '予定', datetime.now()]
            
            return self.execute_query(query, params)
            
        except Exception as e:
            print(f"次回予定作成エラー: {e}")
            return None

    def update_completed_schedules(self, patient_id, measurement_date):
        """測定実施時に該当する予定を完了に更新"""
        try:
            # 測定日前後3日以内の予定を完了に更新
            if isinstance(measurement_date, str):
                measurement_date = datetime.strptime(measurement_date, '%Y-%m-%d').date()
            elif isinstance(measurement_date, datetime):
                measurement_date = measurement_date.date()
            
            start_date = measurement_date - timedelta(days=3)
            end_date = measurement_date + timedelta(days=3)
            
            query = '''
            UPDATE follow_up_schedule 
            SET status = '済', completed_date = ?, days_overdue = 0
            WHERE patient_id = ? 
            AND scheduled_date BETWEEN ? AND ?
            AND status = '予定'
            '''
            params = [measurement_date, patient_id, start_date, end_date]
            
            return self.execute_query(query, params)
            
        except Exception as e:
            print(f"予定完了更新エラー: {e}")
            return None

    def get_monthly_schedule(self, year, month):
        """月別の継続受診予定を取得"""
        try:
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
            
            query = '''
            SELECT f.schedule_id, f.patient_id, f.scheduled_date, f.status, 
                   f.completed_date, f.days_overdue, f.contact_needed, f.contact_date,
                   p.name_kanji, p.name_kana, p.birth_date, p.gender
            FROM follow_up_schedule f
            JOIN patients p ON f.patient_id = p.patient_id
            WHERE f.scheduled_date BETWEEN ? AND ?
            ORDER BY f.scheduled_date ASC
            '''
            results = self.execute_query(query, [start_date, end_date])
            
            if results:
                df = pd.DataFrame(results, columns=[
                    'schedule_id', 'patient_id', 'scheduled_date', 'status',
                    'completed_date', 'days_overdue', 'contact_needed', 'contact_date',
                    'name_kanji', 'name_kana', 'birth_date', 'gender'
                ])
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"月別予定取得エラー: {e}")
            return pd.DataFrame()

    def get_overdue_patients(self):
        """未受診患者を優先度別に取得"""
        try:
            today = date.today()
            
            # 設定値を取得
            urgent_days = int(self.get_system_setting('urgent_overdue_days', 14))
            warning_days = int(self.get_system_setting('warning_overdue_days', 7))
            attention_days = int(self.get_system_setting('attention_overdue_days', 3))
            
            query = '''
            SELECT f.schedule_id, f.patient_id, f.scheduled_date, f.status,
                   (julianday(?) - julianday(f.scheduled_date)) as days_overdue,
                   p.name_kanji, p.name_kana, p.birth_date, p.gender
            FROM follow_up_schedule f
            JOIN patients p ON f.patient_id = p.patient_id
            WHERE f.status = '予定' AND f.scheduled_date < ?
            ORDER BY days_overdue DESC
            '''
            results = self.execute_query(query, [today, today])
            
            if results:
                df = pd.DataFrame(results, columns=[
                    'schedule_id', 'patient_id', 'scheduled_date', 'status', 'days_overdue',
                    'name_kanji', 'name_kana', 'birth_date', 'gender'
                ])
                
                # 優先度別に分類
                urgent = df[df['days_overdue'] >= urgent_days]
                warning = df[(df['days_overdue'] >= warning_days) & (df['days_overdue'] < urgent_days)]
                attention = df[(df['days_overdue'] >= attention_days) & (df['days_overdue'] < warning_days)]
                
                return {
                    'urgent': urgent,
                    'warning': warning, 
                    'attention': attention,
                    'all': df
                }
            else:
                return {
                    'urgent': pd.DataFrame(),
                    'warning': pd.DataFrame(),
                    'attention': pd.DataFrame(),
                    'all': pd.DataFrame()
                }
                
        except Exception as e:
            print(f"未受診患者取得エラー: {e}")
            return {
                'urgent': pd.DataFrame(),
                'warning': pd.DataFrame(),
                'attention': pd.DataFrame(),
                'all': pd.DataFrame()
            }

    def check_insurance_eligibility(self, patient_id, planned_date):
        """保険適用の可否をチェック"""
        try:
            # 最新の測定データを取得
            query = '''
            SELECT measurement_date
            FROM measurements
            WHERE patient_id = ?
            ORDER BY measurement_date DESC
            LIMIT 1
            '''
            results = self.execute_query(query, [patient_id])
            
            if not results:
                return True, "初回測定のため保険適用"
            
            last_measurement_date = datetime.strptime(results[0][0], '%Y-%m-%d').date()
            
            if isinstance(planned_date, str):
                planned_date = datetime.strptime(planned_date, '%Y-%m-%d').date()
            elif isinstance(planned_date, datetime):
                planned_date = planned_date.date()
            
            days_since_last = (planned_date - last_measurement_date).days
            min_interval = int(self.get_system_setting('insurance_interval_days', 120))
            
            if days_since_last >= min_interval:
                return True, "保険適用OK"
            else:
                shortage = min_interval - days_since_last
                return False, f"あと{shortage}日で保険適用"
                
        except Exception as e:
            print(f"保険適用チェックエラー: {e}")
            return False, "チェックエラー"

    def record_contact(self, schedule_id, contact_date, method, result, notes=""):
        """患者への連絡を記録"""
        try:
            # follow_up_scheduleを更新
            query = '''
            UPDATE follow_up_schedule 
            SET contact_needed = ?, contact_date = ?, notes = ?
            WHERE schedule_id = ?
            '''
            params = [False, contact_date, f"連絡方法:{method}, 結果:{result}, メモ:{notes}", schedule_id]
            
            return self.execute_query(query, params)
            
        except Exception as e:
            print(f"連絡記録エラー: {e}")
            return None

    def get_system_setting(self, key, default=None):
        """システム設定値を取得"""
        try:
            query = 'SELECT setting_value FROM system_settings WHERE setting_key = ?'
            results = self.execute_query(query, [key])
            
            if results:
                return results[0][0]
            else:
                return default
                
        except Exception as e:
            print(f"システム設定取得エラー: {e}")
            return default

    def update_system_setting(self, key, value, description=""):
        """システム設定を更新"""
        try:
            query = '''
            INSERT OR REPLACE INTO system_settings (setting_key, setting_value, description)
            VALUES (?, ?, ?)
            '''
            params = [key, value, description]
            
            return self.execute_query(query, params)
            
        except Exception as e:
            print(f"システム設定更新エラー: {e}")
            return None

    def get_continuation_rate_stats(self, year):
        """年間継続受診率統計を取得"""
        try:
            start_date = date(year, 1, 1)
            end_date = date(year, 12, 31)
            
            # 予定数と実施数を取得
            query = '''
            SELECT 
                COUNT(*) as total_scheduled,
                SUM(CASE WHEN status = '済' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = '予定' AND scheduled_date < ? THEN 1 ELSE 0 END) as overdue
            FROM follow_up_schedule
            WHERE scheduled_date BETWEEN ? AND ?
            '''
            results = self.execute_query(query, [date.today(), start_date, end_date])
            
            if results and results[0][0] > 0:
                total, completed, overdue = results[0]
                rate = (completed / total) * 100
                
                return {
                    'year': year,
                    'total_scheduled': total,
                    'completed': completed,
                    'overdue': overdue,
                    'continuation_rate': round(rate, 1)
                }
            else:
                return {
                    'year': year,
                    'total_scheduled': 0,
                    'completed': 0,
                    'overdue': 0,
                    'continuation_rate': 0.0
                }
                
        except Exception as e:
            print(f"継続率統計取得エラー: {e}")
            return None

# テスト実行
if __name__ == "__main__":
    db = BoneDensityDB()
    
    print(f"データベースパス: {db.db_path}")
    
    # 基本情報確認
    try:
        tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
        print(f"テーブル一覧: {[t[0] for t in tables]}")
        
        patients = db.execute_query("SELECT COUNT(*) FROM patients")[0][0]
        measurements = db.execute_query("SELECT COUNT(*) FROM measurements")[0][0]
        schedules = db.execute_query("SELECT COUNT(*) FROM follow_up_schedule")[0][0]
        overdue = len(db.get_overdue_patients()['all'])
        
        print(f"患者数: {patients}")
        print(f"測定数: {measurements}")
        print(f"継続受診予定数: {schedules}")
        print(f"未受診患者数: {overdue}")
        
    except Exception as e:
        print(f"テストエラー: {e}")