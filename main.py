# dashboard
import re
import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# 1. 앱 기본 설정
# ============================================================
st.set_page_config(
    page_title="동네별 인구 피라미드",
    page_icon="🏘️",
    layout="wide",
)

# 따뜻한 색상의 화면 디자인
st.markdown(
    """
    <style>
    .stApp {
        background-color: #FFF9F2;
    }
    h1, h2, h3 {
        color: #75452F;
    }
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #F0DDCC;
        border-radius: 12px;
        padding: 16px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# 2. 데이터 주소 및 나이 라벨 준비
# ============================================================
DATA_URL = (
    "https://raw.githubusercontent.com/first2022-cyber/"
    "contents/main/population_ts_yearly_gender.zip"
)

# 0세부터 100세 이상까지 총 101개 나이 구간
AGES = [f"{age}세" for age in range(101)]
AGES[-1] = "100세 이상"

# 남_0세, 여_0세, ..., 남_100세 이상, 여_100세 이상
MALE_COLS = [f"남_{age}" for age in AGES]
FEMALE_COLS = [f"여_{age}" for age in AGES]
AGE_COLS = MALE_COLS + FEMALE_COLS

LOCATION_COLS = ["시도", "시군구", "동"]
REQUIRED_COLS = ["연도"] + LOCATION_COLS + AGE_COLS


# ============================================================
# 3. CSV 데이터 읽기
# ============================================================
@st.cache_data(show_spinner=False)
def load_data():
    """인터넷에서 ZIP CSV를 읽고 최신 연도 데이터만 반환합니다."""

    # 압축 파일 URL도 pandas가 직접 읽을 수 있습니다.
    df = pd.read_csv(DATA_URL, compression="zip", encoding="utf-8-sig")

    # 혹시 컬럼명 앞뒤에 공백이 있으면 제거합니다.
    df.columns = df.columns.astype(str).str.strip()

    # 필수 컬럼이 실제 데이터에 존재하는지 확인합니다.
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        # 인구 데이터의 컬럼명이 예상과 다르면 원인을 알 수 있게 안내합니다.
        raise ValueError(
            "CSV에서 필요한 컬럼을 찾을 수 없습니다: "
            + ", ".join(missing_cols[:15])
        )

    # 연도를 숫자로 바꿉니다. 변환할 수 없는 행은 제외합니다.
    df["연도"] = pd.to_numeric(df["연도"], errors="coerce")
    df = df.dropna(subset=["연도"]).copy()
    df["연도"] = df["연도"].astype(int)

    if df.empty:
        raise ValueError("CSV에 사용할 수 있는 연도 데이터가 없습니다.")

    # 파일에 포함된 가장 최신 연도를 자동으로 선택합니다.
    latest_year = int(df["연도"].max())
    df = df.loc[df["연도"] == latest_year].copy()

    # 지역명은 문자열로 통일하고 공백을 제거합니다.
    for col in LOCATION_COLS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    # 인구 수를 숫자로 변환합니다.
    # 쉼표가 포함된 문자열이나 빈 값도 안전하게 처리합니다.
    for col in AGE_COLS:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "", regex=False),
            errors="coerce",
        ).fillna(0)

    # 지역명이 없는 행은 선택 목록에서 제외합니다.
    df = df[
        (df["시도"] != "")
        & (df["시군구"] != "")
        & (df["동"] != "")
    ].copy()

    return df, latest_year


# ============================================================
# 4. 앱 제목과 데이터 로딩
# ============================================================
st.title("🏘️ 동네별 인구 피라미드")
st.markdown(
    "우리 동네의 연령대별 인구 구성을 살펴보세요. "
    "남성은 왼쪽, 여성은 오른쪽에 표시됩니다."
)

st.caption("자료: 제공된 전국 읍·면·동 성별·연령별 인구 CSV")

try:
    with st.spinner("최신 인구 데이터를 불러오는 중입니다..."):
        df, latest_year = load_data()
except Exception as e:
    st.error("인구 데이터를 불러오지 못했습니다.")
    st.markdown(
        "인터넷 연결, 데이터 주소, CSV의 컬럼명을 확인해 주세요."
    )
    st.exception(e)
    st.stop()

if df.empty:
    st.warning("최신 연도에 표시할 지역 데이터가 없습니다.")
    st.stop()

st.success(f"현재 표시 중인 데이터 기준 연도: {latest_year}년")


# ============================================================
# 5. 지역 선택: 시도 → 시군구 → 동
# ============================================================
st.subheader("📍 지역 선택")

col1, col2, col3 = st.columns(3)

# 첫 번째 드롭다운: 시도
sido_list = sorted(df["시도"].unique().tolist())

with col1:
    selected_sido = st.selectbox(
        "① 시도",
        options=sido_list,
        key="selected_sido",
    )

# 선택한 시도에 해당하는 시군구만 표시합니다.
df_sido = df.loc[df["시도"] == selected_sido]
sigungu_list = sorted(df_sido["시군구"].unique().tolist())

with col2:
    selected_sigungu = st.selectbox(
        "② 시군구",
        options=sigungu_list,
        key="selected_sigungu",
    )

# 선택한 시도와 시군구에 해당하는 동만 표시합니다.
df_sigungu = df_sido.loc[
    df_sido["시군구"] == selected_sigungu
]
dong_list = sorted(df_sigungu["동"].unique().tolist())

with col3:
    selected_dong = st.selectbox(
        "③ 읍·면·동",
        options=dong_list,
        key="selected_dong",
    )


# ============================================================
# 6. 선택한 지역의 인구 집계
# ============================================================
# 같은 지역에 여러 행이 있더라도 연령별 인구를 합산합니다.
selected_rows = df_sigungu.loc[
    df_sigungu["동"] == selected_dong
]

if selected_rows.empty:
    st.warning("선택한 지역의 인구 데이터가 없습니다.")
    st.stop()

# 연령별 인구를 합산하여 그래프용 배열을 만듭니다.
male_population = (
    selected_rows[MALE_COLS].sum(axis=0).to_numpy(dtype=float)
)
female_population = (
    selected_rows[FEMALE_COLS].sum(axis=0).to_numpy(dtype=float)
)

# 막대그래프에서 남성은 왼쪽으로 향하도록 음수로 변환합니다.
male_negative = -male_population

total_male = int(male_population.sum())
total_female = int(female_population.sum())
total_population = total_male + total_female

location_name = (
    f"{selected_sido} {selected_sigungu} {selected_dong}"
)

st.divider()
st.subheader("📊 인구 피라미드")
st.markdown(f"**{location_name}** · {latest_year}년 기준")


# ============================================================
# 7. 주요 인구 지표
# ============================================================
metric1, metric2, metric3 = st.columns(3)

with metric1:
    st.metric("전체 인구", f"{total_population:,}명")

with metric2:
    st.metric("남성 인구", f"{total_male:,}명")

with metric3:
    st.metric("여성 인구", f"{total_female:,}명")


# ============================================================
# 8. Plotly 가로 막대 인구 피라미드
# ============================================================
fig = go.Figure()

# 남성: 음수이므로 세로축의 왼쪽에 나타납니다.
fig.add_trace(
    go.Bar(
        name="남성",
        y=AGES,
        x=male_negative,
        orientation="h",
        marker_color="#D97757",
        customdata=male_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "남성 인구: %{customdata:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 여성: 양수이므로 세로축의 오른쪽에 나타납니다.
fig.add_trace(
    go.Bar(
        name="여성",
        y=AGES,
        x=female_population,
        orientation="h",
        marker_color="#E8A0A0",
        customdata=female_population,
        hovertemplate=(
            "나이: %{y}<br>"
            "여성 인구: %{customdata:,.0f}명"
            "<extra></extra>"
        ),
    )
)

# 좌우 축 범위를 대칭으로 설정해 성별 분포를 비교하기 쉽게 합니다.
max_population = max(
    float(male_population.max()),
    float(female_population.max()),
    1.0,
)
axis_limit = max_population * 1.12

fig.update_layout(
    title=dict(
        text=f"{location_name} 연령별 성별 인구",
        x=0.5,
        xanchor="center",
        font=dict(size=20, color="#75452F"),
    ),
    barmode="overlay",
    bargap=0.12,
    height=1500,
    paper_bgcolor="#FFF9F2",
    plot_bgcolor="#FFFDF9",
    font=dict(
        family="Arial, sans-serif",
        size=12,
        color="#49372D",
    ),
    margin=dict(l=100, r=40, t=85, b=70),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.01,
        xanchor="center",
        x=0.5,
    ),
    hovermode="y unified",
)

fig.update_xaxes(
    title_text="인구 수 (명)",
    range=[-axis_limit, axis_limit],
    tickmode="array",
    tickvals=np.linspace(-axis_limit, axis_limit, 9),
    ticktext=[
        f"{abs(v):,.0f}" for v in
        np.linspace(-axis_limit, axis_limit, 9)
    ],
    zeroline=True,
    zerolinewidth=2,
    zerolinecolor="#A68A78",
    gridcolor="#EDE1D6",
)

# 중요: 나이 라벨을 직접 지정해 순서를 고정합니다.
# categoryarray의 첫 번째 항목인 0세가 아래쪽에 오도록
# autorange 옵션은 사용하지 않고, 축 범위를 명시합니다.
fig.update_yaxes(
    title_text="나이",
    type="category",
    categoryorder="array",
    categoryarray=AGES,
    tickmode="array",
    tickvals=AGES,
    ticktext=AGES,
    range=[-0.5, len(AGES) - 0.5],
    showgrid=False,
    automargin=True,
)

# 그래프 표시
st.plotly_chart(fig, use_container_width=True)

# 축 순서 확인 안내
st.caption(
    "나이 축 확인: 맨 아래는 0세, 맨 위는 100세 이상입니다. "
    "나이 라벨은 0세부터 100세 이상까지 순서대로 고정되어 있습니다."
)


# ============================================================
# 9. 연령별 인구 표
# ============================================================
with st.expander("📋 연령별 인구 수 표 보기"):
    age_table = pd.DataFrame(
        {
            "나이": AGES,
            "남성 인구": male_population.astype(int),
            "여성 인구": female_population.astype(int),
        }
    )
    age_table["전체 인구"] = (
        age_table["남성 인구"] + age_table["여성 인구"]
    )

    st.dataframe(
        age_table,
        use_container_width=True,
        hide_index=True,
    )

    # 표를 CSV로 내려받을 수 있도록 합니다.
    csv_data = age_table.to_csv(
        index=False,
        encoding="utf-8-sig",
    )
    st.download_button(
        label="연령별 인구 표 CSV 다운로드",
        data=csv_data,
        file_name=f"인구피라미드_{latest_year}.csv",
        mime="text/csv",
    )


# ============================================================
# 10. 데이터 안내
# ============================================================
st.divider()
st.caption(
    "이 앱은 제공된 CSV에서 가장 최신 연도를 자동으로 선택합니다. "
    "지역별 데이터가 여러 행으로 존재하면 연령별 인구를 합산합니다."
)
