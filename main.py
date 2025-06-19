# main.py (Phase 2対応版)
import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime, date, timedelta
import calendar
import sys
import os
import time

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from utils.vertebral_calculations import VertebralCalculator
    from database.vertebral_operations import VertebralMeasurementDB
except ImportError as e:
    st.error(f"椎体別機能のインポートエラー: {e}")

try:
    from database.data_importer import DataImporter, DataIntegrator
    from utils.import_engine import ImportEngine, ImportValidator
except ImportError as e:
    st.error(f"他院データ統合機能のインポートエラー: {e}")

# ページ設定
st.set_page_config(
    page_title="骨密度継続管理システム",
    page_icon="🦴",
    layout="wide",
    initial_sidebar_state="expanded"
)

# インポートとエラーハンドリング
try:
    from database.db_setup import create_database
    from database.db_operations import BoneDensityDB
    from utils.calculations import BoneDensityCalculator
except ImportError as e:
    st.error(f"モジュールのインポートエラー: {e}")
    st.stop()

# データベース初期化
@st.cache_resource
def initialize_database():
    if not os.path.exists('data/bone_density.db'):
        create_database()
    return BoneDensityDB(), BoneDensityCalculator()

try:
    db, calc = initialize_database()
except Exception as e:
    st.error(f"データベース初期化エラー: {e}")
    st.stop()

def main():
    st.title("🦴 骨密度継続管理システム")
    st.sidebar.title("メニュー")
    
    # システム起動時のアラート表示
    show_startup_alerts()
    
    # サイドバーでページ選択
    page = st.sidebar.selectbox(
        "機能を選択してください",
        ["患者検索", "新規患者登録", "測定データ入力", "椎体別測定", "他院データ統合", "継続受診管理", "経過確認", "データベース確認"]
    )
    
    try:
        if page == "患者検索":
            patient_search_page()
        elif page == "新規患者登録":
            patient_registration_page()
        elif page == "測定データ入力":
            measurement_input_page()
        elif page == "継続受診管理":
            follow_up_management_page()
        elif page == "他院データ統合":
            data_import_page()
        elif page == "椎体別測定":
            vertebral_measurement_input_page()
        elif page == "経過確認":
            progress_review_page()
        elif page == "データベース確認":
            database_debug_page()
    except Exception as e:
        st.error(f"ページ表示エラー: {e}")

def show_startup_alerts():
    """システム起動時の未受診者アラート表示"""
    try:
        overdue_data = db.get_overdue_patients()
        
        urgent_count = len(overdue_data['urgent'])
        warning_count = len(overdue_data['warning'])
        attention_count = len(overdue_data['attention'])
        total_overdue = len(overdue_data['all'])
        
        if total_overdue > 0:
            # サイドバーにアラート表示
            st.sidebar.markdown("---")
            st.sidebar.error(f"⚠️ 未受診者 {total_overdue}名")
            
            if urgent_count > 0:
                st.sidebar.error(f"🔴 緊急: {urgent_count}名")
            if warning_count > 0:
                st.sidebar.warning(f"🟠 要連絡: {warning_count}名")
            if attention_count > 0:
                st.sidebar.info(f"🟡 注意: {attention_count}名")
            
            if st.sidebar.button("📋 詳細確認"):
                st.session_state.page_override = "継続受診管理"
        else:
            st.sidebar.success("✅ 未受診者なし")
            
    except Exception as e:
        print(f"アラート表示エラー: {e}")

def follow_up_management_page():
    """継続受診管理ページ"""
    st.header("📅 継続受診管理")
    
    # タブ機能
    tab1, tab2, tab3, tab4 = st.tabs(["📊 月別一覧", "📅 カレンダー表示", "⚠️ 未受診者管理", "📈 継続率統計"])
    
    with tab1:
        monthly_schedule_view()
    
    with tab2:
        calendar_view()
    
    with tab3:
        overdue_management()
    
    with tab4:
        continuation_statistics()

def monthly_schedule_view():
    """月別予定一覧表示（保険適用情報統合版）"""
    st.subheader("📊 月別予定一覧")
    
    # 月選択
    col1, col2 = st.columns(2)
    
    with col1:
        selected_year = st.selectbox("年", range(2020, 2030), index=5)
    
    with col2:
        selected_month = st.selectbox("月", range(1, 13), index=datetime.now().month - 1)
    
    try:
        # 月別データ取得
        monthly_df = db.get_monthly_schedule(selected_year, selected_month)
        
        # 統計情報表示
        if not monthly_df.empty:
            # 🔧 保険適用可能な患者数を計算（統合版）
            insurance_eligible_count = 0
            
            for _, schedule in monthly_df.iterrows():
                scheduled_date = pd.to_datetime(schedule['scheduled_date']).date()
                eligible, _ = db.check_insurance_eligibility(schedule['patient_id'], scheduled_date)
                if eligible:
                    insurance_eligible_count += 1
            
            total_scheduled = len(monthly_df)
            completed = len(monthly_df[monthly_df['status'] == '済'])
            pending = len(monthly_df[monthly_df['status'] == '予定'])
            
            # 未受診者（予定日経過）
            today = date.today()
            overdue = len(monthly_df[
                (monthly_df['status'] == '予定') & 
                (pd.to_datetime(monthly_df['scheduled_date']).dt.date < today)
            ])
            
            # 統計メトリクス表示（保険適用情報追加）
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric("📅 総予定数", total_scheduled)
            with col2:
                st.metric("✅ 実施済み", completed)
            with col3:
                st.metric("🔄 予定", pending)
            with col4:
                st.metric("⚠️ 未受診", overdue)
            with col5:
                st.metric("🏥 保険適用可", insurance_eligible_count)
            
            st.markdown("---")
            
            # 🔧 詳細情報表示（保険適用状況統合版）
            if st.checkbox("📋 詳細一覧を表示（保険適用状況付き）"):
                display_schedule_with_insurance(monthly_df)
        
        else:
            st.info(f"{selected_year}年{selected_month}月の予定はありません。")
            
    except Exception as e:
        st.error(f"月別一覧表示エラー: {e}")

def calendar_view():
    """改善版カレンダー形式表示"""
    st.subheader("📅 カレンダー表示")
    
    # 年月選択
    col1, col2 = st.columns(2)
    
    with col1:
        cal_year = st.selectbox("年", range(2020, 2030), index=5, key="cal_year")
    
    with col2:
        cal_month = st.selectbox("月", range(1, 13), index=datetime.now().month - 1, key="cal_month")
    
    try:
        # 月別データ取得
        monthly_df = db.get_monthly_schedule(cal_year, cal_month)
        
        # カレンダー生成
        cal = calendar.monthcalendar(cal_year, cal_month)
        
        st.markdown(f"### {cal_year}年{cal_month}月")
        
        # 凡例を改善
        st.markdown("#### 📋 凡例")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("🟢 **実施済み**")
        with col2:
            st.markdown("🟡 **予定**")
        with col3:
            st.markdown("🔴 **未受診**")
        with col4:
            st.markdown("⚪ **予定なし**")
        
        st.markdown("---")
        
        # 曜日ヘッダー
        weekdays = ["月", "火", "水", "木", "金", "土", "日"]
        header_cols = st.columns(7)
        for i, weekday in enumerate(weekdays):
            with header_cols[i]:
                st.markdown(f"**{weekday}**")
        
        # カレンダー表示（改善版）
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                with cols[i]:
                    if day == 0:
                        st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)
                    else:
                        # その日の予定を取得
                        day_date = date(cal_year, cal_month, day)
                        day_schedules = monthly_df[
                            pd.to_datetime(monthly_df['scheduled_date']).dt.date == day_date
                        ]
                        
                        if not day_schedules.empty:
                            completed = len(day_schedules[day_schedules['status'] == '済'])
                            pending = len(day_schedules[day_schedules['status'] == '予定'])
                            overdue = len(day_schedules[
                                (day_schedules['status'] == '予定') & 
                                (day_date < date.today())
                            ])
                            
                            # カスタムHTMLでセル表示を改善
                            if overdue > 0:
                                # 未受診（赤）
                                patient_names = day_schedules[day_schedules['status'] == '予定']['name_kanji'].tolist()
                                names_text = ", ".join(patient_names[:2])  # 最大2名表示
                                if len(patient_names) > 2:
                                    names_text += f"他{len(patient_names)-2}名"
                                
                                st.markdown(f"""
                                <div style='
                                    background-color: #ffebee; 
                                    border: 2px solid #f44336; 
                                    border-radius: 8px; 
                                    padding: 8px; 
                                    height: 80px; 
                                    font-size: 12px;
                                    overflow: hidden;
                                '>
                                    <div style='font-weight: bold; color: #f44336;'>🔴 {day}</div>
                                    <div style='color: #666; margin-top: 2px;'>未受診: {overdue}</div>
                                    <div style='color: #333; font-size: 10px; margin-top: 2px;'>{names_text}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            elif pending > 0:
                                # 予定（黄）
                                patient_names = day_schedules[day_schedules['status'] == '予定']['name_kanji'].tolist()
                                names_text = ", ".join(patient_names[:2])  # 最大2名表示
                                if len(patient_names) > 2:
                                    names_text += f"他{len(patient_names)-2}名"
                                
                                st.markdown(f"""
                                <div style='
                                    background-color: #fff8e1; 
                                    border: 2px solid #ff9800; 
                                    border-radius: 8px; 
                                    padding: 8px; 
                                    height: 80px; 
                                    font-size: 12px;
                                    overflow: hidden;
                                '>
                                    <div style='font-weight: bold; color: #ff9800;'>🟡 {day}</div>
                                    <div style='color: #666; margin-top: 2px;'>予定: {pending}</div>
                                    <div style='color: #333; font-size: 10px; margin-top: 2px;'>{names_text}</div>
                                </div>
                                """, unsafe_allow_html=True)
                                
                            elif completed > 0:
                                # 実施済み（緑）
                                patient_names = day_schedules[day_schedules['status'] == '済']['name_kanji'].tolist()
                                names_text = ", ".join(patient_names[:2])  # 最大2名表示
                                if len(patient_names) > 2:
                                    names_text += f"他{len(patient_names)-2}名"
                                
                                st.markdown(f"""
                                <div style='
                                    background-color: #e8f5e8; 
                                    border: 2px solid #4caf50; 
                                    border-radius: 8px; 
                                    padding: 8px; 
                                    height: 80px; 
                                    font-size: 12px;
                                    overflow: hidden;
                                '>
                                    <div style='font-weight: bold; color: #4caf50;'>🟢 {day}</div>
                                    <div style='color: #666; margin-top: 2px;'>実施: {completed}</div>
                                    <div style='color: #333; font-size: 10px; margin-top: 2px;'>{names_text}</div>
                                </div>
                                """, unsafe_allow_html=True)
                        else:
                            # 予定なし（グレー）
                            st.markdown(f"""
                            <div style='
                                background-color: #fafafa; 
                                border: 1px solid #e0e0e0; 
                                border-radius: 8px; 
                                padding: 8px; 
                                height: 80px; 
                                font-size: 12px;
                                text-align: center;
                                color: #999;
                            '>
                                <div style='font-weight: bold; margin-top: 20px;'>⚪ {day}</div>
                            </div>
                            """, unsafe_allow_html=True)
        
        # 詳細情報表示
        if not monthly_df.empty:
            st.markdown("---")
            st.subheader("📋 月間詳細情報")
            
            # 日別の詳細情報をexpanderで表示
            dates_with_schedules = monthly_df.groupby('scheduled_date')
            
            for date_str, group in dates_with_schedules:
                schedule_date = pd.to_datetime(date_str).strftime('%m月%d日')
                patient_count = len(group)
                
                with st.expander(f"📅 {schedule_date} ({patient_count}名)"):
                    for _, schedule in group.iterrows():
                        age = calculate_age(schedule['birth_date'])
                        status_emoji = "🟢" if schedule['status'] == '済' else ("🔴" if pd.to_datetime(schedule['scheduled_date']).date() < date.today() else "🟡")
                        
                        col1, col2, col3 = st.columns([2, 1, 1])
                        with col1:
                            st.write(f"{status_emoji} **{schedule['name_kanji']}** ({age}歳{schedule['gender']})")
                        with col2:
                            st.write(f"状況: {schedule['status']}")
                        with col3:
                            if schedule['status'] == '予定':
                                if st.button(f"✅ 完了", key=f"cal_complete_{schedule['schedule_id']}"):
                                    mark_as_completed(schedule['schedule_id'], schedule['name_kanji'])
                            
    except Exception as e:
        st.error(f"カレンダー表示エラー: {e}")

def create_calendar_cell(day, status, patient_names, count):
    """カレンダーセル用のHTMLを生成"""
    if status == "overdue":
        bg_color = "#ffebee"
        border_color = "#f44336"
        emoji = "🔴"
        text_color = "#f44336"
        label = f"未受診: {count}"
    elif status == "pending":
        bg_color = "#fff8e1"
        border_color = "#ff9800"
        emoji = "🟡"
        text_color = "#ff9800"
        label = f"予定: {count}"
    elif status == "completed":
        bg_color = "#e8f5e8"
        border_color = "#4caf50"
        emoji = "🟢"
        text_color = "#4caf50"
        label = f"実施: {count}"
    else:
        bg_color = "#fafafa"
        border_color = "#e0e0e0"
        emoji = "⚪"
        text_color = "#999"
        label = ""
    
    # 患者名を最大2名まで表示
    names_text = ""
    if patient_names:
        names_list = patient_names[:2]
        names_text = ", ".join(names_list)
        if len(patient_names) > 2:
            names_text += f" 他{len(patient_names)-2}名"
    
    return f"""
    <div style='
        background-color: {bg_color}; 
        border: 2px solid {border_color}; 
        border-radius: 8px; 
        padding: 6px; 
        height: 85px; 
        font-size: 11px;
        overflow: hidden;
        position: relative;
    '>
        <div style='font-weight: bold; color: {text_color};'>{emoji} {day}</div>
        {f"<div style='color: #666; margin-top: 2px; font-size: 10px;'>{label}</div>" if label else ""}
        {f"<div style='color: #333; font-size: 9px; margin-top: 2px; line-height: 1.2;'>{names_text}</div>" if names_text else ""}
    </div>
    """

def overdue_management():
    """未受診者管理（視覚的区別版）"""
    st.subheader("⚠️ 未受診者管理")
    
    try:
        overdue_data = db.get_overdue_patients()
        
        urgent_df = overdue_data['urgent']
        warning_df = overdue_data['warning']
        attention_df = overdue_data['attention']
        all_df = overdue_data['all']
        
        # 連絡済み・未連絡で分類
        contacted_count = 0
        uncontacted_count = 0
        
        # データベースから連絡済み情報を取得
        contacted_patients = []
        try:
            contacted_results = db.execute_query("""
                SELECT schedule_id, contact_date 
                FROM follow_up_schedule 
                WHERE contact_needed = 1 AND status = '予定'
            """)
            contacted_dict = {row[0]: row[1] for row in contacted_results} if contacted_results else {}
        except:
            contacted_dict = {}
        
        for _, patient in all_df.iterrows():
            if patient['schedule_id'] in contacted_dict:
                contacted_count += 1
            else:
                uncontacted_count += 1
        
        # 統計表示
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔴 要連絡", uncontacted_count)
        with col2:
            st.metric("📞 連絡済み", contacted_count)
        with col3:
            st.metric("📊 合計", len(all_df))
        with col4:
            completion_rate = round((contacted_count / len(all_df) * 100), 1) if len(all_df) > 0 else 0
            st.metric("連絡率", f"{completion_rate}%")
        
        st.markdown("---")
        
        # 患者一覧（緊急度順で表示）
        if not all_df.empty:
            st.markdown("### 📋 未受診患者一覧")
            st.markdown("**凡例**: 🔴緊急（14日以上） 🟠警告（7-13日） 🟡注意（3-6日）")
            
            # 緊急患者から順に表示
            for _, patient in all_df.iterrows():
                age = calculate_age(patient['birth_date'])
                days = int(patient['days_overdue'])
                schedule_id = patient['schedule_id']
                is_contacted = schedule_id in contacted_dict
                contact_date = contacted_dict.get(schedule_id, '')
                
                # 緊急度による色分け
                if days >= 14:
                    urgency_color = "🔴"
                    urgency_level = "緊急"
                elif days >= 7:
                    urgency_color = "🟠"
                    urgency_level = "警告"
                else:
                    urgency_color = "🟡"
                    urgency_level = "注意"
                
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    if is_contacted:
                        # 連絡済み患者（グレーアウト表示）
                        st.markdown(f"""
                        <div style="
                            opacity: 0.6; 
                            background-color: #f8f9fa; 
                            padding: 12px; 
                            border-radius: 8px; 
                            border-left: 4px solid #28a745;
                            margin-bottom: 8px;
                        ">
                            <span style="font-size: 14px;">
                                ✅ <strong>{patient['name_kanji']}</strong> ({age}歳{patient['gender']}) - 
                                予定日: {patient['scheduled_date']} - {days}日経過 - 
                                <span style="color: #28a745; font-weight: bold;">[連絡済み {contact_date}]</span>
                            </span>
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        # 未連絡患者（通常表示）
                        if days >= 14:
                            st.error(f"{urgency_color} **{patient['name_kanji']}** ({age}歳{patient['gender']}) - 予定日: {patient['scheduled_date']} - **{days}日経過** [{urgency_level}]")
                        elif days >= 7:
                            st.warning(f"{urgency_color} **{patient['name_kanji']}** ({age}歳{patient['gender']}) - 予定日: {patient['scheduled_date']} - **{days}日経過** [{urgency_level}]")
                        else:
                            st.info(f"{urgency_color} **{patient['name_kanji']}** ({age}歳{patient['gender']}) - 予定日: {patient['scheduled_date']} - **{days}日経過** [{urgency_level}]")
                
                with col2:
                    if not is_contacted:
                        if st.button(f"📞 連絡済み", key=f"contact_{schedule_id}", help="連絡済みとしてマーク"):
                            mark_as_contacted(schedule_id, patient['name_kanji'])
                    else:
                        st.markdown('<div style="text-align: center; padding: 8px;"><span style="color: #28a745; font-weight: bold;">✅ 連絡済み</span></div>', unsafe_allow_html=True)
                
                with col3:
                    if st.button(f"✅ 完了", key=f"complete_{schedule_id}", help="受診完了としてマーク"):
                        mark_as_completed(schedule_id, patient['name_kanji'])
                
                # 区切り線
                st.markdown('<hr style="margin: 8px 0; border: 0; border-top: 1px solid #e9ecef;">', unsafe_allow_html=True)
        
        else:
            st.success("🎉 **素晴らしい！未受診者はいません。**")
            
    except Exception as e:
        st.error(f"未受診者管理エラー: {e}")
        import traceback
        traceback.print_exc()

def mark_as_contacted(schedule_id, patient_name):
    """連絡済みにマーク"""
    try:
        # 連絡済みフラグと連絡日を更新
        success = db.execute_query("""
            UPDATE follow_up_schedule 
            SET contact_needed = 1, 
                contact_date = ?, 
                notes = COALESCE(notes, '') || CASE 
                    WHEN notes IS NULL OR notes = '' THEN ?
                    ELSE char(10) || ?
                END
            WHERE schedule_id = ?
        """, [
            date.today().strftime('%Y-%m-%d'), 
            f"連絡済み - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"連絡済み - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            schedule_id
        ])
        
        if success is not None:
            st.success(f"✅ {patient_name}さんを連絡済みとしてマークしました。")
            time.sleep(0.5)  # 短い待機
            st.rerun()
        else:
            st.error("❌ 連絡済み更新に失敗しました。")
            
    except Exception as e:
        st.error(f"連絡済み更新エラー: {e}")

def continuation_statistics():
    """継続率統計（横向きラベル対応版）"""
    st.subheader("📈 継続受診率統計")
    
    try:
        # 年別統計
        current_year = datetime.now().year
        years = range(current_year - 2, current_year + 1)
        
        stats_data = []
        for year in years:
            stats = db.get_continuation_rate_stats(year)
            if stats:
                stats_data.append(stats)
        
        if stats_data:
            stats_df = pd.DataFrame(stats_data)
            
            # メトリクス表示
            col1, col2, col3 = st.columns(3)
            
            current_stats = stats_df[stats_df['year'] == current_year].iloc[0] if len(stats_df[stats_df['year'] == current_year]) > 0 else None
            
            if current_stats is not None:
                with col1:
                    st.metric("今年の継続率", f"{current_stats['continuation_rate']}%")
                with col2:
                    st.metric("総予定数", current_stats['total_scheduled'])
                with col3:
                    st.metric("実施済み", current_stats['completed'])
            
            # 年別グラフ（横向きラベル対応）
            if len(stats_df) > 1:
                st.subheader("📊 年別継続率推移")
                
                # plotlyを使用してカスタムグラフを作成
                import plotly.express as px
                import plotly.graph_objects as go
                
                # データ準備
                chart_data = stats_df.copy()
                chart_data['year_label'] = chart_data['year'].astype(str) + '年'
                
                # Plotlyグラフ作成
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=chart_data['year_label'],
                    y=chart_data['continuation_rate'],
                    mode='lines+markers',
                    name='継続率',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=8, color='#1f77b4')
                ))
                
                # レイアウト設定
                fig.update_layout(
                    title='年別継続受診率推移',
                    xaxis_title='年',
                    yaxis_title='継続率 (%)',
                    xaxis=dict(
                        tickangle=0,  # 横向き表示（0度）
                        tickfont=dict(size=12)
                    ),
                    yaxis=dict(
                        ticksuffix='%',
                        tickfont=dict(size=12)
                    ),
                    height=400,
                    showlegend=False
                )
                
                # Streamlitで表示
                st.plotly_chart(fig, use_container_width=True)
            
            # 詳細テーブル
            st.subheader("📋 年別詳細")
            display_df = stats_df.copy()
            display_df.columns = ['年', '総予定数', '実施済み', '未受診', '継続率(%)']
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("統計データがまだありません。")
            
    except Exception as e:
        st.error(f"統計表示エラー: {e}")

def display_schedule_with_insurance(monthly_df):
    """予定一覧を保険適用情報付きで表示（完全統合版）"""
    try:
        st.subheader("📋 月間予定詳細（保険適用状況付き）")
        
        # データフレーム表示用の準備
        display_data = []
        
        for _, schedule in monthly_df.iterrows():
            scheduled_date = pd.to_datetime(schedule['scheduled_date']).date()
            eligible, message = db.check_insurance_eligibility(schedule['patient_id'], scheduled_date)
            age = calculate_age(schedule['birth_date'])
            
            # 保険適用状況の詳細表示
            if eligible:
                insurance_status = "✅ 適用可"
                insurance_detail = "保険適用OK"
            else:
                insurance_status = f"⏳ 適用外"
                insurance_detail = message
            
            display_data.append({
                '予定日': schedule['scheduled_date'],
                '患者名': schedule['name_kanji'],
                '年齢': f"{age}歳",
                '性別': schedule['gender'],
                '状況': schedule['status'],
                '保険適用': insurance_status,
                '詳細': insurance_detail
            })
        
        # データフレーム表示
        if display_data:
            display_df = pd.DataFrame(display_data)
            st.dataframe(display_df, use_container_width=True)
            
            # 保険適用統計
            eligible_count = len([d for d in display_data if "✅" in d['保険適用']])
            total_count = len(display_data)
            st.info(f"📊 保険適用状況: {eligible_count}/{total_count}名が適用可能 ({round(eligible_count/total_count*100, 1)}%)")
        
    except Exception as e:
        st.error(f"詳細一覧表示エラー: {e}")

def calculate_age(birth_date_str):
    """年齢計算"""
    try:
        birth_date = datetime.strptime(birth_date_str, '%Y-%m-%d').date()
        today = date.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return "不明"

def record_contact(schedule_id, patient_name):
    """連絡記録"""
    st.session_state[f"show_contact_form_{schedule_id}"] = True

def mark_as_completed(schedule_id, patient_name):
    """予定を完了にマーク"""
    try:
        # 予定を完了に更新
        success = db.execute_query(
            "UPDATE follow_up_schedule SET status = '済', completed_date = ? WHERE schedule_id = ?",
            [date.today().strftime('%Y-%m-%d'), schedule_id]
        )
        
        if success is not None:
            st.success(f"✅ {patient_name}さんの予定を完了にしました。")
            time.sleep(0.5)  # 短い待機
            st.rerun()
        else:
            st.error("❌ 更新に失敗しました。")
            
    except Exception as e:
        st.error(f"完了更新エラー: {e}")

# 既存の関数はそのまま保持
def database_debug_page():
    """データベース確認ページ（デバッグ用）"""
    st.header("🔧 データベース確認")
    
    if st.button("データベース情報表示"):
        try:
            # 基本情報表示
            tables = db.execute_query("SELECT name FROM sqlite_master WHERE type='table'")
            st.write("テーブル一覧:", [t[0] for t in tables])
            
            patients_count = db.execute_query("SELECT COUNT(*) FROM patients")[0][0]
            measurements_count = db.execute_query("SELECT COUNT(*) FROM measurements")[0][0]
            schedules_count = db.execute_query("SELECT COUNT(*) FROM follow_up_schedule")[0][0]
            
            st.write(f"患者数: {patients_count}")
            st.write(f"測定数: {measurements_count}")
            st.write(f"継続受診予定数: {schedules_count}")
            
            st.success("データベース情報を表示しました")
        except Exception as e:
            st.error(f"エラー: {e}")
    
    if st.button("データベースリセット"):
        try:
            # データベースファイル削除
            db_path = os.path.join('data', 'bone_density.db')
            if os.path.exists(db_path):
                os.remove(db_path)
            
            # 再作成
            create_database()
            st.success("データベースがリセットされました")
            st.rerun()
        except Exception as e:
            st.error(f"リセットエラー: {e}")

def patient_search_page():
    """患者検索画面（保険適用チェック統合版）"""
    st.header("🔍 患者検索")
    
    # 検索フォーム
    col1, col2 = st.columns([3, 1])
    
    with col1:
        search_term = st.text_input("患者名・患者番号で検索", placeholder="田中太郎 または P001")
    
    with col2:
        search_button = st.button("検索", type="primary")
    
    # 検索実行
    if search_button or search_term:
        try:
            patients_df = db.search_patients(search_term)
            
            if not patients_df.empty:
                st.success(f"検索結果: {len(patients_df)}名")
                
                # 患者一覧表示（保険適用状況付き）
                for idx, patient in patients_df.iterrows():
                    with st.expander(f"{patient['name_kanji']} ({patient['patient_code']})"):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.write(f"**氏名（漢字）:** {patient['name_kanji']}")
                            st.write(f"**氏名（カナ）:** {patient.get('name_kana', 'N/A')}")
                            st.write(f"**患者番号:** {patient['patient_code']}")
                            st.write(f"**性別:** {patient['gender']}")
                        
                        with col2:
                            st.write(f"**生年月日:** {patient['birth_date']}")
                            age = calculate_age(patient['birth_date'])
                            st.write(f"**年齢:** {age}歳")
                            
                            # 🔧 保険適用状況表示（修正版）
                            patient_id = int(patient['patient_id'])
                            show_insurance_status_compact(patient_id)
                        
                        with col3:
                            if st.button(f"📊 測定履歴", key=f"history_{patient_id}"):
                                show_patient_history(patient_id)
            else:
                st.info("該当する患者が見つかりませんでした。")
        except Exception as e:
            st.error(f"検索エラー: {e}")

def show_insurance_status_compact(patient_id):
    """コンパクトな保険適用状況表示（完全統合版）"""
    try:
        today = date.today()
        eligible, message = db.check_insurance_eligibility(patient_id, today)
        
        st.write("**🏥 保険適用状況:**")
        if eligible:
            st.success("✅ 適用可能")
        else:
            # より詳細な情報を表示
            measurements_df = db.get_patient_measurements(patient_id)
            if not measurements_df.empty:
                latest_date = measurements_df.iloc[0]['measurement_date']
                days_since = (today - datetime.strptime(latest_date, '%Y-%m-%d').date()).days
                shortage_days = 120 - days_since
                st.warning(f"⏳ あと{shortage_days}日で適用可能")
                st.caption(f"前回測定: {latest_date} ({days_since}日経過)")
            else:
                st.success("🆕 初回測定 - 適用可能")
            
    except Exception as e:
        st.error(f"保険チェックエラー: {e}")


def patient_registration_page():
    st.header("👤 新規患者登録")
    
    with st.form("patient_registration"):
        col1, col2 = st.columns(2)
        
        with col1:
            name_kanji = st.text_input("氏名（漢字） *", placeholder="田中太郎")
            name_kana = st.text_input("氏名（カタカナ）", placeholder="タナカタロウ")
            patient_code = st.text_input("患者番号 *", placeholder="P001")
        
        with col2:
            birth_date = st.date_input("生年月日", value=date(1960, 1, 1), min_value=date(1915, 1, 1), max_value=date(2025, 12, 31))
            gender = st.selectbox("性別 *", ["女性", "男性"])
        
        submit_button = st.form_submit_button("患者登録", type="primary")
        
        if submit_button:
            if name_kanji and patient_code and gender:
                try:
                    patient_data = {
                        'name_kanji': name_kanji,
                        'name_kana': name_kana or "",
                        'patient_code': patient_code,
                        'birth_date': birth_date.strftime('%Y-%m-%d'),
                        'gender': gender
                    }
                    patient_id = db.add_patient(patient_data)
                    
                    if patient_id:
                        st.success(f"✅ 患者が正常に登録されました！（患者ID: {patient_id}）")
                        st.balloons()
                    else:
                        st.error("❌ 患者番号が重複しています。別の番号を入力してください。")
                except Exception as e:
                    st.error(f"登録エラー: {e}")
            else:
                st.error("❌ 必須項目（*）を全て入力してください。")

def measurement_input_page():
    """測定データ入力画面（保険適用チェック統合版）"""
    st.header("📊 測定データ入力")
    
    try:
        # 患者選択
        patients_df = db.search_patients()
        
        if patients_df.empty:
            st.warning("⚠️ 患者が登録されていません。先に患者登録を行ってください。")
            return
        
        # 患者選択方法を選択
        st.subheader("👤 患者選択")
        
        # 検索機能付き患者選択
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            patient_search = st.text_input("患者検索（名前・患者番号）", placeholder="田中太郎 または P001", key="patient_search_measurement")
        
        with col_search2:
            search_patients_btn = st.button("検索", key="search_patients_measurement")
        
        # 検索結果に基づいて患者リストを更新
        if patient_search or search_patients_btn:
            filtered_patients_df = db.search_patients(patient_search)
        else:
            filtered_patients_df = patients_df
        
        if filtered_patients_df.empty:
            st.warning("⚠️ 検索条件に一致する患者が見つかりません。")
            return
        
        # 患者選択ボックス（検索結果に基づく）
        patient_options = [f"{row['name_kanji']} ({row['patient_code']}) - ID:{row['patient_id']}" 
                          for idx, row in filtered_patients_df.iterrows()]
        
        selected_patient_display = st.selectbox(
            f"患者を選択してください（{len(filtered_patients_df)}名表示）", 
            patient_options, 
            key="patient_select"
        )
        
        if selected_patient_display:
            # 選択された患者のIDを取得
            selected_idx = patient_options.index(selected_patient_display)
            selected_patient = filtered_patients_df.iloc[selected_idx]
            selected_patient_id = int(selected_patient['patient_id'])
            
            # 🔧 保険適用チェック表示（統合版）
            show_insurance_status_detail(selected_patient_id, selected_patient['name_kanji'])
            
            # 前回の測定データ表示
            show_previous_measurement(selected_patient_id)
            
            # 測定データ入力フォーム
            st.markdown("---")
            st.subheader("📊 測定データ入力フォーム")
            
            # フォーム外で入力値を管理
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📅 測定情報")
                measurement_date = st.date_input("測定日", value=date.today(), key="date_input")
                
                # 🔧 測定日変更時の保険適用チェック（統合版）
                if measurement_date:
                    insurance_check_for_date(selected_patient_id, measurement_date, selected_patient['name_kanji'])
                
                st.subheader("🦴 骨密度測定値 (g/cm²)")
                # st.info("💡 数値入力後のEnterキーは無視されます。必ず「測定データ保存」ボタンを押してください。")
                femur_bmd = st.number_input("大腿骨頚部 BMD", min_value=0.0, max_value=2.0, step=0.001, format="%.3f", key="femur_input")
                lumbar_bmd = st.number_input("腰椎 BMD", min_value=0.0, max_value=2.0, step=0.001, format="%.3f", key="lumbar_input")
            
            with col2:
                st.subheader("🧮 自動計算結果")
                
                if femur_bmd > 0 or lumbar_bmd > 0:
                    try:
                        results = calc.calculate_all_metrics(femur_bmd, lumbar_bmd, selected_patient['gender'])
                        
                        if femur_bmd > 0:
                            st.write(f"**🦴 大腿骨頚部**")
                            st.write(f"- YAM: {results.get('femur_yam', 'N/A')}%")
                            st.write(f"- T-score: {results.get('femur_tscore', 'N/A')}")
                            st.write(f"- 診断: {results.get('femur_diagnosis', 'N/A')}")
                        
                        if lumbar_bmd > 0:
                            st.write(f"**🦴 腰椎**")
                            st.write(f"- YAM: {results.get('lumbar_yam', 'N/A')}%")
                            st.write(f"- T-score: {results.get('lumbar_tscore', 'N/A')}")
                            st.write(f"- 診断: {results.get('lumbar_diagnosis', 'N/A')}")
                        
                        # 診断結果の色分け表示
                        diagnosis = results.get('overall_diagnosis', 'N/A')
                        if diagnosis == '正常':
                            st.success(f"**総合診断: {diagnosis}**")
                        elif diagnosis == '骨量減少':
                            st.warning(f"**総合診断: {diagnosis}**")
                        elif diagnosis == '骨粗鬆症':
                            st.error(f"**総合診断: {diagnosis}**")
                        else:
                            st.info(f"**総合診断: {diagnosis}**")
                    except Exception as e:
                        st.error(f"計算エラー: {e}")
            
            # メモ入力
            notes = st.text_area("📝 メモ・所見", placeholder="特記事項があれば記入してください", key="notes_input")
            
            # 保存ボタン
            st.markdown("---")
            col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
            with col_btn2:
                save_button = st.button("🔒 測定データ保存", type="primary", use_container_width=True)
            
            # 保存処理（既存のコード）
            if save_button:
                if femur_bmd > 0 or lumbar_bmd > 0:
                    try:
                        results = calc.calculate_all_metrics(femur_bmd, lumbar_bmd, selected_patient['gender'])
                        
                        measurement_data = {
                            'patient_id': selected_patient_id,
                            'measurement_date': measurement_date.strftime('%Y-%m-%d'),
                            'femur_bmd': femur_bmd if femur_bmd > 0 else None,
                            'lumbar_bmd': lumbar_bmd if lumbar_bmd > 0 else None,
                            'femur_yam': results.get('femur_yam'),
                            'lumbar_yam': results.get('lumbar_yam'),
                            'femur_tscore': results.get('femur_tscore'),
                            'lumbar_tscore': results.get('lumbar_tscore'),
                            'femur_diagnosis': results.get('femur_diagnosis'),
                            'lumbar_diagnosis': results.get('lumbar_diagnosis'),
                            'overall_diagnosis': results.get('overall_diagnosis'),
                            'notes': notes
                        }
                        
                        measurement_id = db.add_measurement(measurement_data)
                        
                        if measurement_id:
                            st.success("✅ 測定データが正常に保存されました！")
                            st.info("🔄 前回データを更新するため、ページを再読み込みします...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("❌ データ保存に失敗しました。")
                    except Exception as e:
                        st.error(f"保存エラー: {e}")
                else:
                    st.error("❌ 少なくとも1つの測定値を入力してください。")
    except Exception as e:
        st.error(f"測定入力ページエラー: {e}")

def show_insurance_status_detail(patient_id, patient_name):
    """詳細な保険適用状況を表示（完全統合版）"""
    try:
        # 今日の日付で保険適用チェック
        today = date.today()
        eligible, message = db.check_insurance_eligibility(patient_id, today)
        
        # 最新測定日を取得
        measurements_df = db.get_patient_measurements(patient_id)
        
        if not measurements_df.empty:
            latest_date = measurements_df.iloc[0]['measurement_date']
            days_since = (today - datetime.strptime(latest_date, '%Y-%m-%d').date()).days
            
            # 保険適用状況を色分けして表示
            st.markdown("### 🏥 保険適用状況")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("前回測定日", latest_date)
            
            with col2:
                st.metric("経過日数", f"{days_since}日")
            
            with col3:
                if eligible:
                    st.success("✅ 保険適用OK")
                else:
                    shortage_days = 120 - days_since
                    st.warning(f"⏳ あと{shortage_days}日")
            
            # 詳細メッセージ
            if eligible:
                st.success(f"🎉 {patient_name}さんは保険適用で測定可能です（前回から{days_since}日経過）")
            else:
                next_eligible_date = datetime.strptime(latest_date, '%Y-%m-%d').date() + timedelta(days=120)
                st.info(f"📅 次回保険適用日: {next_eligible_date.strftime('%Y年%m月%d日')} ({message})")
        else:
            st.success("🆕 初回測定のため保険適用です")
            
    except Exception as e:
        st.error(f"保険適用チェックエラー: {e}")

def insurance_check_for_date(patient_id, measurement_date, patient_name):
    """指定日での保険適用チェック（完全統合版）"""
    try:
        eligible, message = db.check_insurance_eligibility(patient_id, measurement_date)
        
        # より詳細な表示
        st.markdown("#### 📅 選択日での保険適用チェック")
        
        if eligible:
            st.success(f"✅ {measurement_date}は保険適用で測定可能です")
        else:
            st.warning(f"⚠️ {measurement_date}は保険適用外です")
            st.caption(f"詳細: {message}")
            
            # 次回適用日の案内
            measurements_df = db.get_patient_measurements(patient_id)
            if not measurements_df.empty:
                latest_date = measurements_df.iloc[0]['measurement_date']
                next_eligible_date = datetime.strptime(latest_date, '%Y-%m-%d').date() + timedelta(days=120)
                st.info(f"💡 次回保険適用日: {next_eligible_date.strftime('%Y年%m月%d日')}")
            
    except Exception as e:
        st.error(f"日付別保険チェックエラー: {e}")

def show_previous_measurement(patient_id):
    """前回の測定データを表示"""
    try:
        measurements_df = db.get_patient_measurements(patient_id)
        
        if not measurements_df.empty:
            st.subheader("📈 前回の測定結果")
            latest = measurements_df.iloc[0]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("測定日", latest['measurement_date'])
                
            with col2:
                if latest['femur_tscore'] is not None:
                    st.metric("大腿骨 T-score", f"{latest['femur_tscore']}")
                
            with col3:
                if latest['lumbar_tscore'] is not None:
                    st.metric("腰椎 T-score", f"{latest['lumbar_tscore']}")
        else:
            st.info("📝 初回測定です（前回データなし）")
    except Exception as e:
        st.error(f"前回データ取得エラー: {e}")

def show_patient_history(patient_id):
    """患者の測定履歴を表示"""
    try:
        measurements_df = db.get_patient_measurements(patient_id)
        
        if not measurements_df.empty:
            st.subheader("📊 測定履歴")
            
            # 履歴テーブル表示（番号を1から開始）
            display_df = measurements_df[['measurement_date', 'femur_tscore', 'lumbar_tscore', 'overall_diagnosis']].copy()
            display_df.columns = ['測定日', '大腿骨T-score', '腰椎T-score', '総合診断']
            
            # インデックスを1から開始するように設定
            display_df.index = range(1, len(display_df) + 1)
            display_df.index.name = '回数'
            
            st.dataframe(display_df, use_container_width=True)
        else:
            st.info("まだ測定データがありません。")
    except Exception as e:
        st.error(f"履歴表示エラー: {e}")

def progress_review_page():
    st.header("📈 経過確認")
    
    # 簡単な統計表示
    try:
        patients_df = db.search_patients()
        if not patients_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("登録患者数", len(patients_df))
            
            with col2:
                # 全測定回数を計算
                total_measurements = 0
                for _, patient in patients_df.iterrows():
                    patient_id = int(patient['patient_id'])
                    measurements = db.get_patient_measurements(patient_id)
                    total_measurements += len(measurements)
                st.metric("総測定回数", total_measurements)
        else:
            st.metric("登録患者数", 0)
            st.metric("総測定回数", 0)
    except Exception as e:
        st.error(f"統計データの取得に失敗しました: {e}")

def vertebral_measurement_input_page():
    """椎体別測定データ入力ページ"""
    st.header("🦴 椎体別骨密度測定")
    
    try:
        # 患者選択（既存のロジックを再利用）
        patients_df = db.search_patients()
        
        if patients_df.empty:
            st.warning("⚠️ 患者が登録されていません。先に患者登録を行ってください。")
            return
        
        # 患者選択
        st.subheader("👤 患者選択")
        
        col_search1, col_search2 = st.columns([3, 1])
        
        with col_search1:
            patient_search = st.text_input("患者検索（名前・患者番号）", placeholder="田中太郎 または P001", key="vertebral_patient_search")
        
        with col_search2:
            search_patients_btn = st.button("検索", key="vertebral_search_patients")
        
        # 検索結果に基づいて患者リストを更新
        if patient_search or search_patients_btn:
            filtered_patients_df = db.search_patients(patient_search)
        else:
            filtered_patients_df = patients_df
        
        if filtered_patients_df.empty:
            st.warning("⚠️ 検索条件に一致する患者が見つかりません。")
            return
        
        # 患者選択ボックス
        patient_options = [f"{row['name_kanji']} ({row['patient_code']}) - ID:{row['patient_id']}" 
                          for idx, row in filtered_patients_df.iterrows()]
        
        selected_patient_display = st.selectbox(
            f"患者を選択してください（{len(filtered_patients_df)}名表示）", 
            patient_options, 
            key="vertebral_patient_select"
        )
        
        if selected_patient_display:
            # 選択された患者のIDを取得
            selected_idx = patient_options.index(selected_patient_display)
            selected_patient = filtered_patients_df.iloc[selected_idx]
            selected_patient_id = int(selected_patient['patient_id'])
            
            # 保険適用チェック表示
            show_insurance_status_detail(selected_patient_id, selected_patient['name_kanji'])
            
            # 前回の椎体別データ表示
            show_previous_vertebral_measurements(selected_patient_id)
            
            # 椎体別測定データ入力フォーム
            st.markdown("---")
            st.subheader("🦴 椎体別測定データ入力")
            
            # 入力方式の選択
            input_mode = st.radio(
                "入力方式を選択してください",
                ["椎体別入力", "平均値入力"],
                help="椎体別入力: L1-L4を個別に入力、平均値入力: 従来の腰椎BMD平均値を入力"
            )
            
            if input_mode == "椎体別入力":
                vertebral_input_form(selected_patient_id, selected_patient)
            else:
                average_input_form(selected_patient_id, selected_patient)
                
    except Exception as e:
        st.error(f"椎体別測定入力エラー: {e}")

def vertebral_input_form(patient_id, patient_info):
    """椎体別入力フォーム"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📅 測定情報")
        measurement_date = st.date_input("測定日", value=date.today(), key="vertebral_date_input")
        
        # 測定日での保険適用チェック
        if measurement_date:
            insurance_check_for_date(patient_id, measurement_date, patient_info['name_kanji'])
        
        st.subheader("🦴 椎体別骨密度測定値 (g/cm²)")
        st.info("💡 各椎体のBMD値を入力してください。空欄の椎体は計算から除外されます。")
        
        # 椎体別BMD入力
        vertebral_bmds = {}
        for vertebra in ['L1', 'L2', 'L3', 'L4']:
            bmd_value = st.number_input(
                f"{vertebra}椎体 BMD", 
                min_value=0.0, 
                max_value=2.0, 
                step=0.001, 
                format="%.3f",
                key=f"vertebral_{vertebra}_input",
                help=f"{vertebra}椎体の骨密度を入力"
            )
            if bmd_value > 0:
                vertebral_bmds[vertebra] = bmd_value
        
        # 大腿骨BMD（従来通り）
        st.subheader("🦴 大腿骨頚部BMD (g/cm²)")
        femur_bmd = st.number_input("大腿骨頚部 BMD", min_value=0.0, max_value=2.0, step=0.001, format="%.3f", key="vertebral_femur_input")
    
    with col2:
        st.subheader("🧮 リアルタイム計算結果")
        
        if vertebral_bmds:
            try:
                # 椎体別計算の実行
                vertebral_calc = VertebralCalculator()
                vertebral_results = vertebral_calc.calculate_vertebral_metrics(vertebral_bmds, patient_info['gender'])
                
                if vertebral_results:
                    # 椎体別結果表示
                    st.write("**🦴 椎体別結果**")
                    
                    for vertebra in ['L1', 'L2', 'L3', 'L4']:
                        if vertebra in vertebral_results['vertebral_results']:
                            data = vertebral_results['vertebral_results'][vertebra]
                            
                            # 診断による色分け
                            if data['diagnosis'] == '骨粗鬆症':
                                st.error(f"**{vertebra}:** BMD {data['bmd_value']:.3f} | YAM {data['yam_percentage']:.1f}% | T-score {data['tscore']:.1f} | {data['diagnosis']}")
                            elif data['diagnosis'] == '骨量減少':
                                st.warning(f"**{vertebra}:** BMD {data['bmd_value']:.3f} | YAM {data['yam_percentage']:.1f}% | T-score {data['tscore']:.1f} | {data['diagnosis']}")
                            else:
                                st.success(f"**{vertebra}:** BMD {data['bmd_value']:.3f} | YAM {data['yam_percentage']:.1f}% | T-score {data['tscore']:.1f} | {data['diagnosis']}")
                    
                    # 平均値での診断
                    st.write("**📊 腰椎平均値（診断用）**")
                    avg_metrics = vertebral_results['average_metrics']
                    
                    if avg_metrics['average_diagnosis'] == '骨粗鬆症':
                        st.error(f"**総合診断: {avg_metrics['average_diagnosis']}**")
                    elif avg_metrics['average_diagnosis'] == '骨量減少':
                        st.warning(f"**総合診断: {avg_metrics['average_diagnosis']}**")
                    else:
                        st.success(f"**総合診断: {avg_metrics['average_diagnosis']}**")
                    
                    st.write(f"- 平均BMD: {avg_metrics['average_bmd']:.3f} g/cm²")
                    st.write(f"- 平均YAM: {avg_metrics['average_yam']:.1f}%")
                    st.write(f"- 平均T-score: {avg_metrics['average_tscore']:.1f}")
                    
                    # 椎体間分析
                    analysis = vertebral_results['analysis']
                    st.write("**📋 椎体間分析**")
                    st.write(f"- BMD範囲: {analysis['bmd_min']:.3f} - {analysis['bmd_max']:.3f} g/cm²")
                    st.write(f"- 最低値椎体: {analysis['lowest_vertebra']}")
                    st.write(f"- 椎体間差: {analysis['bmd_range']:.3f} g/cm²")
                    
                    # リスク評価
                    risk_assessment = analysis.get('risk_assessment', {})
                    if risk_assessment.get('attention_points'):
                        st.write("**⚠️ 注意事項**")
                        for point in risk_assessment['attention_points']:
                            st.warning(f"- {point}")
                    
                    # セッションに結果を保存（保存ボタン用）
                    st.session_state['vertebral_calculation_results'] = vertebral_results
                
            except Exception as e:
                st.error(f"計算エラー: {e}")
        
        # 大腿骨の計算（従来通り）
        if femur_bmd > 0:
            try:
                femur_results = calc.calculate_all_metrics(femur_bmd, None, patient_info['gender'])
                
                if femur_results.get('femur_yam'):
                    st.write("**🦴 大腿骨頚部**")
                    st.write(f"- YAM: {femur_results['femur_yam']}%")
                    st.write(f"- T-score: {femur_results['femur_tscore']}")
                    st.write(f"- 診断: {femur_results['femur_diagnosis']}")
                    
                    # セッションに大腿骨結果を保存
                    st.session_state['femur_calculation_results'] = femur_results
                    
            except Exception as e:
                st.error(f"大腿骨計算エラー: {e}")
    
    # メモ入力
    notes = st.text_area("📝 メモ・所見", placeholder="特記事項があれば記入してください", key="vertebral_notes_input")
    
    # 保存ボタン
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        save_button = st.button("🔒 椎体別測定データ保存", type="primary", use_container_width=True)
    
    # 保存処理
    if save_button:
        if vertebral_bmds or femur_bmd > 0:
            try:
                save_vertebral_measurement_data(
                    patient_id, 
                    measurement_date, 
                    vertebral_bmds, 
                    femur_bmd, 
                    patient_info['gender'], 
                    notes
                )
                
            except Exception as e:
                st.error(f"保存エラー: {e}")
        else:
            st.error("❌ 少なくとも1つの測定値を入力してください。")

def average_input_form(patient_id, patient_info):
    """平均値入力フォーム（従来の方式）"""
    st.info("💡 従来の腰椎BMD平均値入力方式です。椎体別詳細は記録されません。")
    
    # 従来の measurement_input_page のロジックを再利用
    # ここでは簡略化
    col1, col2 = st.columns(2)
    
    with col1:
        measurement_date = st.date_input("測定日", value=date.today(), key="avg_date_input")
        
        st.subheader("🦴 骨密度測定値 (g/cm²)")
        femur_bmd = st.number_input("大腿骨頚部 BMD", min_value=0.0, max_value=2.0, step=0.001, format="%.3f", key="avg_femur_input")
        lumbar_bmd = st.number_input("腰椎 BMD", min_value=0.0, max_value=2.0, step=0.001, format="%.3f", key="avg_lumbar_input")
    
    with col2:
        st.subheader("🧮 自動計算結果")
        
        if femur_bmd > 0 or lumbar_bmd > 0:
            try:
                results = calc.calculate_all_metrics(femur_bmd, lumbar_bmd, patient_info['gender'])
                
                # 結果表示（従来通り）
                if femur_bmd > 0:
                    st.write(f"**🦴 大腿骨頚部**")
                    st.write(f"- YAM: {results.get('femur_yam', 'N/A')}%")
                    st.write(f"- T-score: {results.get('femur_tscore', 'N/A')}")
                    st.write(f"- 診断: {results.get('femur_diagnosis', 'N/A')}")
                
                if lumbar_bmd > 0:
                    st.write(f"**🦴 腰椎**")
                    st.write(f"- YAM: {results.get('lumbar_yam', 'N/A')}%")
                    st.write(f"- T-score: {results.get('lumbar_tscore', 'N/A')}")
                    st.write(f"- 診断: {results.get('lumbar_diagnosis', 'N/A')}")
                
                # 診断結果の色分け表示
                diagnosis = results.get('overall_diagnosis', 'N/A')
                if diagnosis == '正常':
                    st.success(f"**総合診断: {diagnosis}**")
                elif diagnosis == '骨量減少':
                    st.warning(f"**総合診断: {diagnosis}**")
                elif diagnosis == '骨粗鬆症':
                    st.error(f"**総合診断: {diagnosis}**")
                else:
                    st.info(f"**総合診断: {diagnosis}**")
                    
            except Exception as e:
                st.error(f"計算エラー: {e}")
    
    # メモ・保存ボタン（従来通り）
    notes = st.text_area("📝 メモ・所見", placeholder="特記事項があれば記入してください", key="avg_notes_input")
    
    st.markdown("---")
    col_btn1, col_btn2, col_btn3 = st.columns([1, 2, 1])
    with col_btn2:
        save_button = st.button("🔒 測定データ保存", type="primary", use_container_width=True)
    
    if save_button:
        if femur_bmd > 0 or lumbar_bmd > 0:
            # 従来の保存処理を実行
            save_traditional_measurement_data(patient_id, measurement_date, femur_bmd, lumbar_bmd, patient_info['gender'], notes)
        else:
            st.error("❌ 少なくとも1つの測定値を入力してください。")

def show_previous_vertebral_measurements(patient_id):
    """前回の椎体別測定データを表示"""
    try:
        vertebral_db = VertebralMeasurementDB()
        
        # 患者の測定履歴を取得
        measurements_df = db.get_patient_measurements(patient_id)
        
        if not measurements_df.empty:
            latest_measurement_id = measurements_df.iloc[0]['measurement_id']
            
            # 最新の椎体別データを取得
            vertebral_data = vertebral_db.get_vertebral_measurements(latest_measurement_id)
            
            if vertebral_data:
                st.subheader("📈 前回の椎体別測定結果")
                
                col1, col2, col3, col4 = st.columns(4)
                
                for i, data in enumerate(vertebral_data):
                    with [col1, col2, col3, col4][i]:
                        st.metric(
                            data['vertebra_level'],
                            f"{data['bmd_value']:.3f}",
                            delta=f"YAM: {data['yam_percentage']:.1f}%"
                        )
                
                # 椎体別分析結果
                analysis = vertebral_db.analyze_vertebral_differences(latest_measurement_id)
                if analysis:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.info(f"💡 前回最低値: {analysis['lowest_vertebra']}椎体")
                    with col2:
                        st.info(f"📊 BMD範囲: {analysis['bmd_range']:.3f} g/cm²")
            else:
                # 従来の腰椎BMDを表示
                st.subheader("📈 前回の測定結果（腰椎平均値）")
                latest = measurements_df.iloc[0]
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("測定日", latest['measurement_date'])
                    
                with col2:
                    if latest['lumbar_tscore'] is not None:
                        st.metric("腰椎 T-score", f"{latest['lumbar_tscore']}")
                    
                with col3:
                    if latest['femur_tscore'] is not None:
                        st.metric("大腿骨 T-score", f"{latest['femur_tscore']}")
        else:
            st.info("📝 初回測定です（前回データなし）")
    except Exception as e:
        st.error(f"前回データ取得エラー: {e}")

def save_vertebral_measurement_data(patient_id, measurement_date, vertebral_bmds, femur_bmd, gender, notes):
    """椎体別測定データの保存"""
    try:
        # 椎体別計算の実行
        vertebral_calc = VertebralCalculator()
        vertebral_results = vertebral_calc.calculate_vertebral_metrics(vertebral_bmds, gender)
        
        # 大腿骨の計算
        femur_results = {}
        if femur_bmd > 0:
            femur_results = calc.calculate_all_metrics(femur_bmd, None, gender)
        
        # 腰椎の平均値を計算（従来のmeasurementsテーブル用）
        lumbar_bmd = vertebral_results['average_metrics']['average_bmd'] if vertebral_results else None
        
        # 従来のmeasurementsテーブルにデータを保存
        measurement_data = {
            'patient_id': patient_id,
            'measurement_date': measurement_date.strftime('%Y-%m-%d'),
            'femur_bmd': femur_bmd if femur_bmd > 0 else None,
            'lumbar_bmd': lumbar_bmd,
            'femur_yam': femur_results.get('femur_yam'),
            'lumbar_yam': vertebral_results['average_metrics']['average_yam'] if vertebral_results else None,
            'femur_tscore': femur_results.get('femur_tscore'),
            'lumbar_tscore': vertebral_results['average_metrics']['average_tscore'] if vertebral_results else None,
            'femur_diagnosis': femur_results.get('femur_diagnosis'),
            'lumbar_diagnosis': vertebral_results['average_metrics']['average_diagnosis'] if vertebral_results else None,
            'overall_diagnosis': vertebral_results['average_metrics']['average_diagnosis'] if vertebral_results else femur_results.get('femur_diagnosis', '測定不可'),
            'notes': notes
        }
        
        # メイン測定データを保存
        measurement_id = db.add_measurement(measurement_data)
        
        if measurement_id and vertebral_results:
            # 椎体別データを保存
            vertebral_db = VertebralMeasurementDB()
            vertebral_data_for_db = vertebral_results['vertebral_data']
            
            success = vertebral_db.add_vertebral_measurements(measurement_id, vertebral_data_for_db)
            
            if success:
                st.success("✅ 椎体別測定データが正常に保存されました！")
                st.info("🔄 前回データを更新するため、ページを再読み込みします...")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ 椎体別データの保存に失敗しました。")
        else:
            st.error("❌ メイン測定データの保存に失敗しました。")
            
    except Exception as e:
        st.error(f"保存エラー: {e}")

def save_traditional_measurement_data(patient_id, measurement_date, femur_bmd, lumbar_bmd, gender, notes):
    """従来方式での測定データ保存"""
    try:
        results = calc.calculate_all_metrics(femur_bmd, lumbar_bmd, gender)
        
        measurement_data = {
            'patient_id': patient_id,
            'measurement_date': measurement_date.strftime('%Y-%m-%d'),
            'femur_bmd': femur_bmd if femur_bmd > 0 else None,
            'lumbar_bmd': lumbar_bmd if lumbar_bmd > 0 else None,
            'femur_yam': results.get('femur_yam'),
            'lumbar_yam': results.get('lumbar_yam'),
            'femur_tscore': results.get('femur_tscore'),
            'lumbar_tscore': results.get('lumbar_tscore'),
            'femur_diagnosis': results.get('femur_diagnosis'),
            'lumbar_diagnosis': results.get('lumbar_diagnosis'),
            'overall_diagnosis': results.get('overall_diagnosis'),
            'notes': notes
        }
        
        measurement_id = db.add_measurement(measurement_data)
        
        if measurement_id:
            st.success("✅ 測定データが正常に保存されました！")
            st.info("🔄 前回データを更新するため、ページを再読み込みします...")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ データ保存に失敗しました。")
            
    except Exception as e:
        st.error(f"保存エラー: {e}")

def data_import_page():
    """他院データ統合メインページ"""
    st.header("📂 他院データ統合")
    
    # タブ機能
    tab1, tab2, tab3, tab4 = st.tabs(["📥 データインポート", "📊 インポート履歴", "🏥 データソース管理", "📋 マッピングテンプレート"])
    
    with tab1:
        data_import_interface()
    
    with tab2:
        import_history_view()
    
    with tab3:
        data_source_management()
    
    with tab4:
        mapping_template_management()

def data_import_interface():
    """データインポートインターフェース"""
    st.subheader("📥 他院データのインポート")
    
    try:
        engine = ImportEngine()
        
        # Step 1: ファイルアップロード
        st.markdown("### 🔄 Step 1: ファイルの選択")
        
        uploaded_file = st.file_uploader(
            "CSVまたはExcelファイルを選択してください",
            type=['csv', 'xlsx', 'xls'],
            help="最大ファイルサイズ: 10MB"
        )
        
        if uploaded_file is not None:
            # ファイル情報表示
            file_details = {
                "ファイル名": uploaded_file.name,
                "ファイルサイズ": f"{uploaded_file.size:,} bytes",
                "ファイル形式": uploaded_file.type
            }
            
            col1, col2 = st.columns(2)
            with col1:
                st.info("📄 **ファイル情報**")
                for key, value in file_details.items():
                    st.write(f"- **{key}**: {value}")
            
            # ファイル形式判定
            file_extension = uploaded_file.name.split('.')[-1].lower()
            file_type = 'excel' if file_extension in ['xlsx', 'xls'] else 'csv'
            
            # ファイル内容読み込み
            file_content = uploaded_file.getvalue()
            
            # Step 2: データプレビュー
            st.markdown("### 📋 Step 2: データプレビュー")
            
            preview_result = engine.preview_import_data(file_content, file_type, 10)
            
            if preview_result['success']:
                st.success(f"✅ ファイル解析成功！総行数: {preview_result['total_rows']}行")
                
                # プレビューデータ表示
                preview_df = pd.DataFrame(preview_result['preview_data'])
                st.dataframe(preview_df, use_container_width=True)
                
                # Excel の場合はシート選択機能（将来拡張用）
                if file_type == 'excel':
                    st.info("💡 Excelファイルの場合、複数シート対応は今後のアップデートで実装予定です")
                
                # Step 3: 列マッピング設定
                st.markdown("### 🔄 Step 3: 列マッピング設定")
                
                mapping = configure_column_mapping(
                    preview_result['columns'],
                    preview_result['column_suggestions'],
                    preview_result['sample_data']
                )
                
                # データソース設定
                st.markdown("### 🏥 Step 4: データソース設定")
                
                col1, col2 = st.columns(2)
                with col1:
                    data_source = st.text_input(
                        "データ提供元（他院名など）",
                        placeholder="例: 山田整形外科",
                        help="統計・管理のためのデータソース名"
                    )
                
                with col2:
                    import_notes = st.text_area(
                        "インポートメモ",
                        placeholder="このインポートに関する特記事項があれば記入",
                        height=100
                    )
                
                # Step 5: インポート実行
                st.markdown("### 🚀 Step 5: インポート実行")
                
                # マッピング確認表示
                if mapping:
                    with st.expander("🔍 マッピング設定確認"):
                        mapping_df = pd.DataFrame([
                            {"システム項目": k, "ファイル列名": v} 
                            for k, v in mapping.items() if v
                        ])
                        st.dataframe(mapping_df, use_container_width=True)
                
                # インポートボタン
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🔒 データインポート実行", type="primary", use_container_width=True):
                        execute_data_import(
                            engine, file_content, uploaded_file.name,
                            mapping, data_source, import_notes, file_type
                        )
            else:
                st.error(f"❌ ファイル解析エラー: {preview_result['error']}")
                st.info("💡 ファイル形式やエンコーディングを確認してください")
        
        else:
            # ファイル未選択時のガイド表示
            st.info("📁 CSVまたはExcelファイルを選択してください")
            
            # サンプルフォーマット表示
            with st.expander("📋 推奨ファイル形式"):
                st.markdown("""
                **CSVファイルの推奨形式:**
                ```
                患者番号,氏名,性別,生年月日,測定日,大腿骨BMD,腰椎BMD
                P001,田中太郎,男性,1965-03-15,2025-06-01,0.820,0.910
                P002,山田花子,女性,1970-08-22,2025-06-02,0.750,0.880
                ```
                
                **対応する列名の例:**
                - 患者ID/番号: 患者番号, patient_id, ID
                - 氏名: 氏名, 患者名, name
                - 測定日: 測定日, 検査日, measurement_date
                - BMD値: 大腿骨BMD, 腰椎BMD, femur, lumbar
                """)
                
    except Exception as e:
        st.error(f"データインポート機能エラー: {e}")

def configure_column_mapping(columns: list, suggestions: dict, sample_data: dict) -> dict:
    """列マッピング設定UI"""
    
    # システム項目定義
    system_fields = {
        'patient_code': {'label': '患者番号', 'required': True, 'description': '患者を識別する番号'},
        'name_kanji': {'label': '氏名（漢字）', 'required': False, 'description': '患者の氏名'},
        'name_kana': {'label': '氏名（カナ）', 'required': False, 'description': '患者のフリガナ'},
        'birth_date': {'label': '生年月日', 'required': False, 'description': '患者の生年月日'},
        'gender': {'label': '性別', 'required': False, 'description': '男性/女性'},
        'measurement_date': {'label': '測定日', 'required': True, 'description': '骨密度測定を行った日'},
        'femur_bmd': {'label': '大腿骨BMD', 'required': False, 'description': '大腿骨頚部の骨密度'},
        'lumbar_bmd': {'label': '腰椎BMD', 'required': False, 'description': '腰椎の骨密度'},
        'l1_bmd': {'label': 'L1椎体BMD', 'required': False, 'description': 'L1椎体の骨密度'},
        'l2_bmd': {'label': 'L2椎体BMD', 'required': False, 'description': 'L2椎体の骨密度'},
        'l3_bmd': {'label': 'L3椎体BMD', 'required': False, 'description': 'L3椎体の骨密度'},
        'l4_bmd': {'label': 'L4椎体BMD', 'required': False, 'description': 'L4椎体の骨密度'}
    }
    
    mapping = {}
    
    # 自動推奨の適用
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**列マッピング設定**")
        st.caption("各システム項目に対応するファイル列を選択してください")
    
    with col2:
        if st.button("🔄 自動マッピング適用", help="AIによる推奨マッピングを適用"):
            st.session_state['auto_mapping_applied'] = True
            st.rerun()
    
    # マッピング設定UI
    for field_key, field_info in system_fields.items():
        col1, col2, col3 = st.columns([2, 3, 1])
        
        with col1:
            # 必須マーク表示
            required_mark = " *" if field_info['required'] else ""
            st.write(f"**{field_info['label']}{required_mark}**")
            st.caption(field_info['description'])
        
        with col2:
            # 推奨マッピングの取得
            default_column = None
            if field_key in suggestions and suggestions[field_key]:
                default_column = suggestions[field_key][0]
            elif st.session_state.get('auto_mapping_applied'):
                if field_key in suggestions and suggestions[field_key]:
                    default_column = suggestions[field_key][0]
            
            # デフォルトインデックスの設定
            default_index = 0
            column_options = ['（選択なし）'] + columns
            
            if default_column and default_column in columns:
                default_index = columns.index(default_column) + 1
            
            selected_column = st.selectbox(
                f"列選択_{field_key}",
                column_options,
                index=default_index,
                key=f"mapping_{field_key}",
                label_visibility="collapsed"
            )
            
            if selected_column != '（選択なし）':
                mapping[field_key] = selected_column
        
        with col3:
            # サンプルデータ表示
            if field_key in mapping and mapping[field_key] in sample_data:
                sample_values = sample_data[mapping[field_key]]
                if sample_values:
                    sample_text = "、".join(str(v) for v in sample_values[:2])
                    st.caption(f"例: {sample_text}")
    
    # 必須項目チェック
    missing_required = []
    for field_key, field_info in system_fields.items():
        if field_info['required'] and field_key not in mapping:
            missing_required.append(field_info['label'])
    
    if missing_required:
        st.warning(f"⚠️ 必須項目が未設定です: {', '.join(missing_required)}")
        st.info("💡 患者番号と測定日は必須項目です")
    
    return mapping

def execute_data_import(engine: ImportEngine, file_content: bytes, filename: str,
                       mapping: dict, data_source: str, notes: str, file_type: str):
    """データインポートの実行"""
    
    # 必須項目チェック
    required_fields = ['patient_code', 'measurement_date']
    missing_required = [field for field in required_fields if field not in mapping]
    
    if missing_required:
        st.error(f"❌ 必須項目が不足しています: {', '.join(missing_required)}")
        return
    
    # インポート実行
    with st.spinner("🔄 データインポート中..."):
        try:
            results = engine.execute_import(
                file_content, filename, mapping, data_source, file_type
            )
            
            # 結果表示
            display_import_results(results)
            
        except Exception as e:
            st.error(f"❌ インポートエラー: {str(e)}")

def display_import_results(results: dict):
    """インポート結果の表示"""
    
    if results['success']:
        st.success("🎉 データインポートが完了しました！")
    else:
        st.error("❌ データインポートでエラーが発生しました")
    
    # 統計情報表示
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📊 総レコード数", results['total_records'])
    
    with col2:
        st.metric("✅ 成功", results['success_records'])
    
    with col3:
        st.metric("⚠️ 警告", results['warning_records'])
    
    with col4:
        st.metric("❌ 失敗", results['failed_records'])
    
    # 詳細結果
    if results['created_patients']:
        st.info(f"🆕 新規患者: {len(results['created_patients'])}名を作成しました")
    
    if results['duplicates']:
        with st.expander(f"⚠️ 重複データ ({len(results['duplicates'])}件)"):
            for duplicate in results['duplicates']:
                st.warning(f"行{duplicate['row'] + 1}: 同じ測定日のデータが既に存在")
    
    if results['errors']:
        with st.expander(f"❌ エラー詳細 ({len(results['errors'])}件)"):
            for error in results['errors']:
                st.error(f"{error['type']}: {error['message']}")
    
    if results['warnings']:
        with st.expander(f"⚠️ 警告詳細 ({len(results['warnings'])}件)"):
            for warning in results['warnings']:
                st.warning(f"{warning['type']}: {warning['message']}")
    
    # 再読み込み案内
    if results['success']:
        st.info("🔄 患者データに反映されました。他のページで確認してください。")
        
        if st.button("📊 患者検索ページに移動"):
            st.session_state['page_redirect'] = '患者検索'
            st.rerun()

def import_history_view():
    """インポート履歴表示"""
    st.subheader("📊 インポート履歴")
    
    try:
        engine = ImportEngine()
        history = engine.get_import_history(50)
        
        if history:
            # 履歴統計
            total_imports = len(history)
            successful_imports = len([h for h in history if h['import_status'] == 'completed'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("📥 総インポート数", total_imports)
            with col2:
                st.metric("✅ 成功", successful_imports)
            with col3:
                success_rate = round(successful_imports / total_imports * 100, 1) if total_imports > 0 else 0
                st.metric("成功率", f"{success_rate}%")
            
            # 履歴テーブル
            st.markdown("### 📋 インポート履歴詳細")
            
            history_data = []
            for record in history:
                status_icon = {
                    'completed': '✅',
                    'failed': '❌',
                    'processing': '🔄'
                }.get(record['import_status'], '❓')
                
                history_data.append({
                    '状況': f"{status_icon} {record['import_status']}",
                    'ファイル名': record['original_filename'] or record['filename'],
                    'データソース': record['data_source'] or '-',
                    '総数': record['total_records'],
                    '成功': record['success_records'],
                    '警告': record['warning_records'],
                    '失敗': record['failed_records'],
                    'インポート日': record['import_date'][:16] if record['import_date'] else '-'
                })
            
            history_df = pd.DataFrame(history_data)
            st.dataframe(history_df, use_container_width=True)
            
            # 詳細表示
            st.markdown("### 🔍 詳細確認")
            
            selected_record = st.selectbox(
                "詳細を確認するインポートを選択",
                [f"{h['filename']} ({h['import_date'][:16]})" for h in history]
            )
            
            if selected_record:
                selected_index = [f"{h['filename']} ({h['import_date'][:16]})" for h in history].index(selected_record)
                selected_import = history[selected_index]
                
                display_import_detail(engine, selected_import)
        
        else:
            st.info("📝 インポート履歴がありません")
            
    except Exception as e:
        st.error(f"履歴表示エラー: {e}")

def display_import_detail(engine: ImportEngine, import_record: dict):
    """インポート詳細表示"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📄 基本情報**")
        st.write(f"- **ファイル名**: {import_record['original_filename']}")
        st.write(f"- **データソース**: {import_record['data_source']}")
        st.write(f"- **ファイルサイズ**: {import_record['file_size']:,} bytes")
        st.write(f"- **インポート日**: {import_record['import_date']}")
    
    with col2:
        st.markdown("**📊 統計情報**")
        st.write(f"- **総レコード数**: {import_record['total_records']}")
        st.write(f"- **成功**: {import_record['success_records']}")
        st.write(f"- **警告**: {import_record['warning_records']}")
        st.write(f"- **失敗**: {import_record['failed_records']}")
    
    # エラーログ表示
    if import_record['failed_records'] > 0 or import_record['warning_records'] > 0:
        try:
            errors = engine.get_import_errors(import_record['import_id'])
            
            if errors:
                st.markdown("**📝 エラー・警告詳細**")
                
                error_data = []
                for error in errors:
                    severity_icon = {
                        'error': '❌',
                        'warning': '⚠️',
                        'info': 'ℹ️'
                    }.get(error['error_severity'], '❓')
                    
                    error_data.append({
                        '重要度': f"{severity_icon} {error['error_severity']}",
                        '行番号': error['row_number'],
                        '列名': error['column_name'],
                        '元の値': error['original_value'],
                        'エラー内容': error['error_message']
                    })
                
                error_df = pd.DataFrame(error_data)
                st.dataframe(error_df, use_container_width=True)
        
        except Exception as e:
            st.error(f"エラー詳細取得エラー: {e}")

def data_source_management():
    """データソース管理"""
    st.subheader("🏥 データソース管理")
    
    try:
        engine = ImportEngine()
        sources = engine.get_data_sources()
        
        if sources:
            st.markdown("### 📊 データソース一覧")
            
            source_data = []
            for source in sources:
                source_data.append({
                    'データソース': source['source_name'],
                    '測定データ数': source['measurement_count'],
                    '初回インポート': source['first_import'][:10] if source['first_import'] else '-',
                    '最終インポート': source['last_import'][:10] if source['last_import'] else '-'
                })
            
            source_df = pd.DataFrame(source_data)
            st.dataframe(source_df, use_container_width=True)
            
            # 統計情報
            total_external_measurements = sum(s['measurement_count'] for s in sources)
            st.info(f"📈 他院からの測定データ総数: {total_external_measurements}件")
        
        else:
            st.info("📝 他院からのデータソースがありません")
            
    except Exception as e:
        st.error(f"データソース管理エラー: {e}")

def mapping_template_management():
    """マッピングテンプレート管理"""
    st.subheader("📋 マッピングテンプレート管理")
    
    try:
        importer = DataImporter()
        templates = importer.get_mapping_templates()
        
        if templates:
            st.markdown("### 📄 保存済みテンプレート")
            
            for template in templates:
                with st.expander(f"📋 {template['template_name']} {'⭐' if template['is_default'] else ''}"):
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**説明**: {template['description']}")
                        st.write(f"**対応形式**: {template['source_type']}")
                        st.write(f"**デフォルト**: {'はい' if template['is_default'] else 'いいえ'}")
                    
                    with col2:
                        st.write("**マッピング設定**:")
                        mapping_items = template['column_mappings']
                        for system_field, file_columns in mapping_items.items():
                            if file_columns:
                                st.write(f"- {system_field}: {', '.join(file_columns)}")
        
        else:
            st.info("📝 マッピングテンプレートがありません")
        
        # 新規テンプレート作成（将来実装予定）
        st.markdown("### 🆕 新規テンプレート作成")
        st.info("💡 新規マッピングテンプレートの作成機能は今後のアップデートで実装予定です")
        
    except Exception as e:
        st.error(f"テンプレート管理エラー: {e}")

if __name__ == "__main__":
    main()