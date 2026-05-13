import os
import sqlite3
import pandas as pd
import streamlit as st

DB_NAME = "social.db"
TABLE_NAME = "survey"

SEX_COL = "SEX"
AGE_COL = "AGE_10"
ESG_COL = "Q6_1"

st.set_page_config(page_title="공공데이터 분석 대시보드", layout="wide")
st.title("📊 공공데이터 분석 대시보드")

# -----------------------------
# DB 연결
# -----------------------------
if not os.path.exists(DB_NAME):
    st.error("social.db 파일을 찾을 수 없습니다. app.py와 같은 폴더에 넣어주세요.")
    st.stop()

conn = sqlite3.connect(DB_NAME)

# -----------------------------
# 컬럼 확인
# -----------------------------
cols_df = pd.read_sql(f'PRAGMA table_info("{TABLE_NAME}")', conn)
columns = cols_df["name"].tolist()

required_cols = [SEX_COL, AGE_COL, ESG_COL]
missing = [c for c in required_cols if c not in columns]

if missing:
    st.error(f"다음 컬럼이 DB에 없습니다: {missing}")
    st.write("현재 컬럼 목록:", columns)
    st.stop()

q6_4_cols = [c for c in columns if c.startswith("Q6_4_")]
q6_6_cols = [c for c in columns if c.startswith("Q6_6_")]

st.info("사용 컬럼: SEX=성별, AGE_10=연령대, Q6_1=ESG 인지도")

# -----------------------------
# 1. ESG 인지도 분포
# -----------------------------
st.header("1. 성별·연령대별 ESG 인지도 분포")

sql1 = f"""
SELECT 
    "{SEX_COL}" AS 성별,
    "{AGE_COL}" AS 연령대,
    "{ESG_COL}" AS ESG인지도,
    COUNT(*) AS 응답수
FROM "{TABLE_NAME}"
WHERE "{ESG_COL}" IS NOT NULL
GROUP BY "{SEX_COL}", "{AGE_COL}", "{ESG_COL}"
ORDER BY 성별, 연령대, ESG인지도;
"""

df1 = pd.read_sql(sql1, conn)

if df1.empty:
    st.warning("ESG 인지도 분석에 사용할 데이터가 없습니다.")
else:
    col1, col2 = st.columns(2)

    with col1:
        selected_sex = st.selectbox(
            "성별 선택",
            sorted(df1["성별"].dropna().unique()),
            key="sex_chart1"
        )

    with col2:
        selected_age = st.selectbox(
            "연령대 선택",
            sorted(df1["연령대"].dropna().unique()),
            key="age_chart1"
        )

    pie_df = df1[
        (df1["성별"] == selected_sex) &
        (df1["연령대"] == selected_age)
    ]

    chart_df = pie_df.set_index("ESG인지도")["응답수"]

    st.bar_chart(chart_df)

    st.subheader("사용한 SQL")
    st.code(sql1, language="sql")

    top_label = chart_df.idxmax()
    st.write(
        f"**인사이트:** {selected_sex}, {selected_age} 집단에서는 "
        f"`{top_label}` 응답이 가장 많습니다. "
        "ESG 인지도는 성별과 연령대에 따라 다르게 나타날 수 있습니다."
    )

# -----------------------------
# 2. 성별별 대기업 지속가능경영 중요 이슈
# -----------------------------
st.header("2. 성별별 대기업 지속가능경영 중요 이슈")

if not q6_4_cols:
    st.warning("Q6_4_로 시작하는 컬럼을 찾을 수 없습니다.")
else:
    union_parts = []

    for col in q6_4_cols:
        union_parts.append(
            f"""
            SELECT 
                "{SEX_COL}" AS 성별,
                "{col}" AS 이슈
            FROM "{TABLE_NAME}"
            WHERE "{col}" IS NOT NULL
              AND TRIM(CAST("{col}" AS TEXT)) != ''
            """
        )

    sql2 = f"""
WITH issue_long AS (
    {" UNION ALL ".join(union_parts)}
)
SELECT 
    성별,
    이슈,
    COUNT(*) AS 선택수
FROM issue_long
WHERE 이슈 IS NOT NULL
  AND TRIM(CAST(이슈 AS TEXT)) != ''
GROUP BY 성별, 이슈
ORDER BY 성별, 선택수 DESC;
"""

    df2 = pd.read_sql(sql2, conn)

    if df2.empty:
        st.warning("대기업 지속가능경영 이슈 분석에 사용할 데이터가 없습니다.")
    else:
        selected_sex2 = st.selectbox(
            "이슈 분석 성별 선택",
            sorted(df2["성별"].dropna().unique()),
            key="sex_chart2"
        )

        issue_df = (
            df2[df2["성별"] == selected_sex2]
            .sort_values("선택수", ascending=False)
            .head(10)
            .sort_values("선택수")
        )

        chart_df2 = issue_df.set_index("이슈")["선택수"]

        st.bar_chart(chart_df2)

        st.subheader("사용한 SQL")
        st.code(sql2, language="sql")

        top_issue = (
            df2[df2["성별"] == selected_sex2]
            .sort_values("선택수", ascending=False)
            .iloc[0]["이슈"]
        )

        st.write(
            f"**인사이트:** {selected_sex2} 응답자에게서는 "
            f"`{top_issue}` 항목이 가장 많이 선택되었습니다. "
            "성별에 따라 기업이 중요하게 관리해야 한다고 보는 이슈가 달라질 수 있습니다."
        )

# -----------------------------
# 3. 성별·연령대별 저출생 대응 기업 우선 정책 TOP3
# -----------------------------
st.header("3. 성별·연령대별 저출생 대응 기업 우선 정책 TOP3")

if not q6_6_cols:
    st.warning("Q6_6_로 시작하는 컬럼을 찾을 수 없습니다.")
else:
    union_parts = []

    for col in q6_6_cols:
        union_parts.append(
            f"""
            SELECT 
                "{SEX_COL}" AS 성별,
                "{AGE_COL}" AS 연령대,
                "{col}" AS 정책
            FROM "{TABLE_NAME}"
            WHERE "{col}" IS NOT NULL
              AND TRIM(CAST("{col}" AS TEXT)) != ''
            """
        )

    sql3 = f"""
WITH policy_long AS (
    {" UNION ALL ".join(union_parts)}
)
SELECT 
    성별,
    연령대,
    정책,
    COUNT(*) AS 선택수
FROM policy_long
WHERE 정책 IS NOT NULL
  AND TRIM(CAST(정책 AS TEXT)) != ''
GROUP BY 성별, 연령대, 정책
ORDER BY 성별, 연령대, 선택수 DESC;
"""

    df3 = pd.read_sql(sql3, conn)

    if df3.empty:
        st.warning("저출생 대응 정책 분석에 사용할 데이터가 없습니다.")
    else:
        col1, col2 = st.columns(2)

        with col1:
            selected_sex3 = st.selectbox(
                "정책 분석 성별 선택",
                sorted(df3["성별"].dropna().unique()),
                key="sex_chart3"
            )

        with col2:
            selected_age3 = st.selectbox(
                "정책 분석 연령대 선택",
                sorted(df3["연령대"].dropna().unique()),
                key="age_chart3"
            )

        policy_df = (
            df3[
                (df3["성별"] == selected_sex3) &
                (df3["연령대"] == selected_age3)
            ]
            .sort_values("선택수", ascending=False)
            .head(3)
            .sort_values("선택수")
        )

        if policy_df.empty:
            st.warning("선택한 성별·연령대에 해당하는 정책 응답 데이터가 없습니다.")
        else:
            chart_df3 = policy_df.set_index("정책")["선택수"]

            st.bar_chart(chart_df3)

            st.subheader("사용한 SQL")
            st.code(sql3, language="sql")

            top_policy = (
                policy_df.sort_values("선택수", ascending=False)
                .iloc[0]["정책"]
            )

            st.write(
                f"**인사이트:** {selected_sex3}, {selected_age3} 집단에서는 "
                f"`{top_policy}` 정책이 가장 많이 선택되었습니다. "
                "저출생 대응 정책은 성별과 연령대에 따라 우선순위를 나누어 볼 필요가 있습니다."
            )

conn.close()
