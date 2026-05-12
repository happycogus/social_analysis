import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import os

# --- [설정] ---
DB_NAME = 'social.db'

# --- [DB 관련 함수] ---
def get_connection():
    """SQLite 연결 객체 생성"""
    if not os.path.exists(DB_NAME):
        st.error(f"❌ 데이터베이스 파일을 찾을 수 없습니다: {DB_NAME}")
        return None
    return sqlite3.connect(DB_NAME)

def get_table_name(conn):
    """DB 내의 실제 테이블 명을 가져옴"""
    try:
        query = "SELECT name FROM sqlite_master WHERE type='table';"
        tables = pd.read_sql(query, conn)
        if tables.empty:
            st.error("❌ DB 내에 테이블이 존재하지 않습니다.")
            return None
        return tables['name'].iloc[0]  # 첫 번째 테이블 반환
    except Exception as e:
        st.error(f"SQL 오류 (테이블 확인): {e}")
        return None

def get_columns(conn, table_name):
    """테이블의 실제 컬럼 리스트 확인"""
    try:
        query = f"PRAGMA table_info({table_name});"
        cols = pd.read_sql(query, conn)
        return cols['name'].tolist()
    except Exception as e:
        st.error(f"SQL 오류 (컬럼 확인): {e}")
        return []

# --- [데이터 매핑 정보 (인사이트용)] ---
GENDER_MAP = {1: '남성', 2: '여성'}
AGE_MAP = {1: '19-29세', 2: '30대', 3: '40대', 4: '50대', 5: '60대 이상'}
ESG_MAP = {1: '전혀 모름', 2: '알지 못함', 3: '보통', 4: '어느 정도 알고 있음', 5: '매우 잘 알고 있음'}

# --- [메인 대시보드 함수] ---
def main():
    st.set_page_config(page_title="ESG & 저출생 인식 조사 대시보드", layout="wide")
    st.title("📊 공공데이터 분석 대시보드")
    st.info("SQLite 데이터베이스 구조를 자동 분석하여 시각화를 수행합니다.")

    conn = get_connection()
    if conn is None: return

    table_name = get_table_name(conn)
    if not table_name: return

    columns = get_columns(conn, table_name)
    
    # --- 사이드바 필터 ---
    st.sidebar.header("🔍 데이터 필터")
    
    # 성별/연령대 컬럼 존재 여부 확인
    if 'SQ1' in columns and 'SQ2_1' in columns:
        gender_list = pd.read_sql(f"SELECT DISTINCT SQ1 FROM {table_name}", conn)['SQ1'].tolist()
        age_list = pd.read_sql(f"SELECT DISTINCT SQ2_1 FROM {table_name}", conn)['SQ2_1'].tolist()

        selected_gender = st.sidebar.multiselect("성별 선택 (1:남성, 2:여성)", gender_list, default=gender_list)
        selected_age = st.sidebar.multiselect("연령대 선택", age_list, default=age_list)
        
        filter_query = f"WHERE SQ1 IN ({','.join(map(str, selected_gender))}) AND SQ2_1 IN ({','.join(map(str, selected_age))})"
    else:
        filter_query = ""
        st.sidebar.warning("SQ1 또는 SQ2_1 컬럼을 찾을 수 없어 필터가 제한됩니다.")

    # --- 차트 1: ESG 인지도 (Q6_1) ---
    st.divider()
    st.subheader("1. ESG 인지도 분포 (Q6_1)")
    if 'Q6_1' in columns:
        sql1 = f"SELECT Q6_1, COUNT(*) as count FROM {table_name} {filter_query} GROUP BY Q6_1"
        df1 = pd.read_sql(sql1, conn)
        
        if not df1.empty:
            df1['인지도_라벨'] = df1['Q6_1'].map(ESG_MAP).fillna(df1['Q6_1'])
            fig1 = px.pie(df1, values='count', names='인지도_라벨', hole=0.4, title="ESG 인지도 비율")
            st.plotly_chart(fig1, use_container_width=True)
            
            st.code(sql1, language='sql')
            st.write(f"**💡 인사이트:** 분석 결과 '{df1.loc[df1['count'].idxmax(), '인지도_라벨']}' 응답이 가장 높게 나타났습니다. 필터링된 그룹 내에서 ESG 정책에 대한 인지 정도를 파악할 수 있습니다.")
        else:
            st.warning("데이터가 없습니다.")
    else:
        st.error("Q6_1 컬럼이 존재하지 않습니다.")

    # --- 차트 2: 국내 대기업 성장 관련 관리 이슈 (Q6_4_*) ---
    st.divider()
    st.subheader("2. 대기업 지속가능경영 중요 이슈 (복수응답)")
    q6_4_cols = [c for c in columns if c.startswith('Q6_4_')]
    
    if q6_4_cols:
        # 복수응답 처리: 각 컬럼의 합계(응답 수)를 구함
        sum_query = ", ".join([f"SUM(CASE WHEN {c} = 1 THEN 1 ELSE 0 END) as {c}" for c in q6_4_cols])
        sql2 = f"SELECT {sum_query} FROM {table_name} {filter_query}"
        df2_raw = pd.read_sql(sql2, conn)
        
        if not df2_raw.empty:
            df2 = df2_raw.melt(var_name='항목', value_name='선택수').sort_values(by='선택수', ascending=True)
            fig2 = px.bar(df2, x='선택수', y='항목', orientation='h', title="이슈별 응답 빈도 (TOP 항목 확인)")
            st.plotly_chart(fig2, use_container_width=True)
            
            st.code(sql2, language='sql')
            st.write(f"**💡 인사이트:** {len(q6_4_cols)}개의 세부 항목 중 가장 많이 선택된 이슈는 '{df2.iloc[-1]['항목']}'입니다. 대기업에 대한 요구사항을 보여줍니다.")
        else:
            st.warning("데이터가 없습니다.")
    else:
        st.error("Q6_4_N 패턴의 컬럼을 찾을 수 없습니다.")

    # --- 차트 3: 저출생 이슈 관련 기업 우선 정책 (Q6_6_*) ---
    st.divider()
    st.subheader("3. 저출생 대응 기업 우선 정책 TOP 3")
    q6_6_cols = [c for c in columns if c.startswith('Q6_6_')]
    
    if q6_6_cols:
        sum_query_6 = ", ".join([f"SUM(CASE WHEN {c} = 1 THEN 1 ELSE 0 END) as {c}" for c in q6_6_cols])
        sql3 = f"SELECT {sum_query_6} FROM {table_name} {filter_query}"
        df3_raw = pd.read_sql(sql3, conn)
        
        if not df3_raw.empty:
            df3 = df3_raw.melt(var_name='정책항목', value_name='선택수').sort_values(by='선택수', ascending=False).head(3)
            fig3 = px.bar(df3, x='선택수', y='정책항목', orientation='h', 
                          title="가장 시급한 저출생 대응 정책 TOP 3", color='선택수', color_continuous_scale='Reds')
            fig3.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig3, use_container_width=True)
            
            st.code(sql3, language='sql')
            st.write(f"**💡 인사이트:** 현재 선택된 성별/연령대 그룹에서 가장 선호하는 정책 TOP 3는 위와 같습니다. 정책 수립 시 우선순위로 고려해야 할 지표입니다.")
        else:
            st.warning("데이터가 없습니다.")
    else:
        st.error("Q6_6_N 패턴의 컬럼을 찾을 수 없습니다.")

    conn.close()

if __name__ == "__main__":
    main()