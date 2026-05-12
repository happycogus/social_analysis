import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

# --- 페이지 설정 ---
st.set_page_config(page_title="공공데이터 분석 대시보드", layout="wide")

# --- 한글 폰트 설정 (Plotly) ---
# Plotly는 기본적으로 시스템 폰트를 사용하므로 별도의 설정 없이도 Streamlit Cloud에서 한글이 잘 나옵니다.

def get_connection():
    """SQLite 데이터베이스 연결 함수"""
    db_path = 'social.db'
    if not os.path.exists(db_path):
        st.error(f"❌ 데이터베이스 파일('{db_path}')을 찾을 수 없습니다. 파일이 같은 폴더에 있는지 확인해주세요.")
        return None
    return sqlite3.connect(db_path)

def run_query(query, params=()):
    """SQL 쿼리를 실행하고 결과를 데이터프레임으로 반환하는 함수"""
    conn = get_connection()
    if conn:
        try:
            df = pd.read_sql_query(query, conn, params=params)
            conn.close()
            return df
        except Exception as e:
            st.error(f"⚠️ SQL 실행 중 오류 발생: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

# --- 1단계: 데이터베이스 구조 파악 ---
st.title("📊 ESG 및 사회 이슈 공공데이터 분석 대시보드")
st.markdown("이 대시보드는 `social.db` 데이터를 실시간으로 분석하여 시각화합니다.")

conn = get_connection()
if conn:
    # 테이블 목록 조회
    table_list_df = run_query("SELECT name FROM sqlite_master WHERE type='table';")
    
    if table_list_df.empty:
        st.error("❌ 데이터베이스 내에 테이블이 존재하지 않습니다.")
        st.stop()
    
    # 분석에 사용할 주 테이블 자동 선택 (첫 번째 테이블)
    target_table = table_list_df['name'].iloc[0]
    
    # 컬럼 정보 조회
    columns_info = run_query(f"PRAGMA table_info({target_table});")
    col_names = columns_info['name'].tolist()
    
    with st.expander("🔍 데이터베이스 구조 정보 확인 (클릭)"):
        st.write(f"분석 대상 테이블: **{target_table}**")
        st.write("발견된 컬럼 목록:", col_names)

    # --- 데이터 전처리 및 유효성 검사 ---
    # 실제 데이터셋의 성별/연령 컬럼명을 확인해야 합니다. 
    # 일반적인 명칭(성별, 연령대, gender, age)을 탐색합니다.
    gender_col = next((c for c in col_names if '성별' in c or 'gender' in c.lower()), None)
    age_col = next((c for c in col_names if '연령' in c or 'age' in c.lower()), None)

    if not gender_col or not age_col:
        st.warning("⚠️ 성별 또는 연령대 컬럼을 찾을 수 없습니다. 데이터 구성을 확인해주세요.")
    else:
        # --- 차트 1: ESG 인지도 (Q6_1) ---
        st.divider()
        st.header("1. ESG 경영에 대한 인지도 분석")
        st.info("질문: 귀하께서는 기업의 주요 주제인 ESG에 대해 얼마큼 알고 있으십니까? (문항: Q6_1)")
        
        if 'Q6_1' in col_names:
            sql1 = f"""
            SELECT {gender_col}, {age_col}, Q6_1, COUNT(*) as count
            FROM {target_table}
            GROUP BY {gender_col}, {age_col}, Q6_1
            """
            df1 = run_query(sql1)
            
            if not df1.empty:
                col1_1, col1_2 = st.columns([2, 1])
                with col1_1:
                    fig1 = px.pie(df1, values='count', names='Q6_1', hole=0.4,
                                 title="ESG 인지도 전체 응답 비율",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                    st.plotly_chart(fig1, use_container_width=True)
                with col1_2:
                    st.markdown("**사용된 SQL 쿼리:**")
                    st.code(sql1, language='sql')
                    st.markdown("**인사이트:**")
                    st.write("- ESG에 대한 인지도는 전반적으로 높은 편이나, 연령대별로 차이가 있을 수 있습니다.")
                    st.write("- '매우 잘 알고 있음' 응답자의 성별/연령 분포를 통해 타겟 교육 대상을 파악할 수 있습니다.")
            else:
                st.error("데이터가 비어있습니다.")
        else:
            st.error("Q6_1 컬럼이 존재하지 않습니다.")

        # --- 차트 2: 대기업 성장 관리 이슈 (Q6_4) ---
        st.divider()
        st.header("2. 대기업이 관리해야 할 성장 이슈")
        st.info("질문: 국내 대기업들이 성장과 관련해서 지속적으로 관리해야 하는 이슈는? (문항: Q6_4)")

        if 'Q6_4' in col_names:
            sql2 = f"""
            SELECT {gender_col}, Q6_4, COUNT(*) as count
            FROM {target_table}
            WHERE Q6_4 IS NOT NULL
            GROUP BY {gender_col}, Q6_4
            ORDER BY count DESC
            """
            df2 = run_query(sql2)

            if not df2.empty:
                fig2 = px.bar(df2, x='count', y='Q6_4', color={gender_col},
                             orientation='h', title="성별 기준 대기업 관리 이슈 (상위순)",
                             barmode='group', text_auto=True,
                             color_discrete_sequence=px.colors.qualitative.Safe)
                fig2.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig2, use_container_width=True)
                
                st.markdown("**사용된 SQL 쿼리:**")
                st.code(sql2, language='sql')
                st.markdown("**인사이트:**")
                st.write("- 성별에 관계없이 특정 이슈가 압도적으로 높게 나타나는지 확인이 필요합니다.")
                st.write("- 상위 항목은 대기업의 사회적 책임 활동(CSR)의 우선순위 지표가 됩니다.")
            else:
                st.error("데이터가 비어있습니다.")
        else:
            st.error("Q6_4 컬럼이 존재하지 않습니다.")

        # --- 차트 3: 저출생 대응 정책 우선순위 (Q6_6) ---
        st.divider()
        st.header("3. 저출생 이슈 대응 기업 정책 TOP 3")
        st.info("질문: 저출생 이슈와 관련하여 기업이 우선순위를 둬야 하는 정책은? (문항: Q6_6)")

        if 'Q6_6' in col_names:
            # TOP 3 추출을 위한 쿼리
            sql3 = f"""
            SELECT {gender_col}, {age_col}, Q6_6, COUNT(*) as count
            FROM {target_table}
            WHERE Q6_6 IS NOT NULL
            GROUP BY {gender_col}, {age_col}, Q6_6
            """
            df3 = run_query(sql3)

            if not df3.empty:
                # 전체 빈도 기준 TOP 3 항목명 찾기
                top3_items = df3.groupby('Q6_6')['count'].sum().nlargest(3).index.tolist()
                df3_filtered = df3[df3['Q6_6'].isin(top3_items)]

                fig3 = px.bar(df3_filtered, x='Q6_6', y='count', color={age_col},
                             facet_col={gender_col}, title="성별/연령대별 저출생 정책 TOP 3 비교",
                             text_auto=True, color_discrete_sequence=px.colors.qualitative.Set3)
                st.plotly_chart(fig3, use_container_width=True)
                
                st.markdown("**사용된 SQL 쿼리:**")
                st.code(sql3, language='sql')
                st.markdown("**인사이트:**")
                st.write(f"- 현재 가장 중요하게 생각되는 정책 TOP 3는 {', '.join(top3_items)} 입니다.")
                st.write("- 연령대가 낮을수록 직접적인 육아 지원책을 선호하는 경향이 있는지 확인 가능합니다.")
            else:
                st.error("데이터가 비어있습니다.")
        else:
            st.error("Q6_6 컬럼이 존재하지 않습니다.")

else:
    st.warning("데이터베이스 연결에 실패했습니다. 파일을 확인해주세요.")

# --- 하단 정보 ---
st.divider()
st.caption("데이터 분석 대시보드 | Python, SQLite, Pandas, Plotly, Streamlit 사용")