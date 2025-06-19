#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベースセットアップ
"""

import sqlite3
import os

def setup_database():
    """データベースの初期化"""
    db_path = os.path.join('data', 'bone_density.db')
    
    if not os.path.exists(db_path):
        print("データベースファイルが見つかりません")
        return False
    
    return True

if __name__ == "__main__":
    setup_database()
