#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースセットアップ
"""

import sqlite3
import os
from datetime import datetime, timedelta

def create_database():
    """データベースの作成・初期化"""
    db_path = os.path.join('data', 'bone_density.db')
    
    # データディレクトリ作成
    os.makedirs('data', exist_ok=True)
    
    if os.path.exists(db_path):
        print("✅ データベースファイルが既に存在します")
        return True
    
    try:
        # データベース接続・作成
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 基本テーブル作成
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS patients (
                patient_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_kanji TEXT NOT NULL,
                name_kana TEXT NOT NULL,
                birth_date DATE NOT NULL,
                gender TEXT NOT NULL,
                phone TEXT,
                address TEXT,
                insurance_number TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS measurements (
                measurement_id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER NOT NULL,
                measurement_date DATE NOT NULL,
                lumbar_bmd REAL,
                lumbar_yam REAL,
                lumbar_tscore REAL,
                femur_bmd REAL,
                femur_yam REAL,
                femur_tscore REAL,
                diagnosis TEXT,
                notes TEXT,
                device_name TEXT DEFAULT 'DXA-Pro',
                FOREIGN KEY (patient_id) REFERENCES patients(patient_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vertebral_measurements (
                vertebral_id INTEGER PRIMARY KEY AUTOINCREMENT,
                measurement_id INTEGER NOT NULL,
                l1_bmd REAL, l1_yam REAL, l1_tscore REAL,
                l2_bmd REAL, l2_yam REAL, l2_tscore REAL,
                l3_bmd REAL, l3_yam REAL, l3_tscore REAL,
                l4_bmd REAL, l4_yam REAL, l4_tscore REAL,
                FOREIGN KEY (measurement_id) REFERENCES measurements(measurement_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
        print("✅ データベースを作成しました")
        return True
        
    except Exception as e:
        print(f"❌ データベース作成エラー: {e}")
        return False

def setup_database():
    """データベースの初期化（既存関数）"""
    return create_database()

if __name__ == "__main__":
    create_database()
