"""Map-first WELL-FLOW dashboard for five wellness tourism sites."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(page_title="WELL-FLOW Map", page_icon="🌿", layout="wide")

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output" / "five_sites_by_designation"
PERIODS = ["P1", "P2", "P3", "P4"]

SITES = pd.DataFrame(
    [
        ("전남장성", "장성", "국립장성숲체원", "북이면", 2020, 126.751410, 35.444047, "방문·소비 회복", "체류·장기숙박 전환"),
        ("전북무주", "무주", "태권도원 상징지구", "설천면", 2022, 127.762090, 36.012521, "유입 성장, 체류 정체", "숙박일수·장기체류 확대"),
        ("전남완도", "완도", "완도 해양치유센터", "신지면", 2024, 126.818435, 34.328049, "긴 체류, 소비·계절성 약세", "체험소비·지역 확산"),
        ("전북순창", "순창", "쉴랜드", "인계면", 2024, 127.131587, 35.431547, "관심 대비 전환 약세", "방문·숙박·소비 전환"),
        ("전북완주", "완주", "아원고택", "소양면", 2024, 127.244624, 35.903470, "방문 대비 숙박 약세", "숙박 연계·체류 콘텐츠"),
    ],
    columns=["지역키", "지역", "시설", "시설동", "선정연도", "경도", "위도", "진단", "과제"],
)

FLOW = [
    ("관심", "숙박검색건수"),
    ("방문", "외지인방문자수"),
    ("숙박", "숙박자비율_pct"),
    ("체류", "평균체류시간_분"),
    ("소비", "내국인관광소비_천원"),
]
METRIC_LABELS = dict(FLOW)
METRIC_LABELS = {metric: label for label, metric in FLOW}
STATUS = {"UP": ("↑", "개선", "#0F766E"), "FLAT": ("→", "유지", "#A16207"), "DOWN": ("↓", "악화", "#B64646"), "NA": ("·", "제한", "#8A929E")}
INTERVALS = {
    "지정 직후 · P2→P3": ("g23_pct", "delta23_pctp", "지정직후_판정_3pct", "P3"),
    "2년차 · P3→P4": ("g34_pct", "delta34_pctp", "2년차_판정_3pct", "P4"),
}


st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');
    html, body, [class*="css"] { font-family:'Pretendard Variable', Pretendard, sans-serif; letter-spacing:-.018em; }
    .stApp { background:#F6F7F6; color:#171C1A; }
    [data-testid="stHeader"] { background:rgba(246,247,246,.9); }
    .block-container { max-width:1400px; padding-top:1.1rem; padding-bottom:2.5rem; }
    .map-title { padding:.2rem 0 1rem; }
    .map-title small { color:#0F766E; font-size:.72rem; font-weight:700; letter-spacing:.09em; }
    .map-title h1 { margin:.25rem 0 .2rem; font-size:2rem; letter-spacing:-.04em; }
    .map-title p { margin:0; color:#6B7470; font-size:.9rem; }
    .summary { background:white; border:1px solid #E1E5E3; border-radius:14px; padding:1.25rem; }
    .summary .place { color:#0F766E; font-size:.76rem; font-weight:700; }
    .summary h2 { margin:.25rem 0 .15rem; font-size:1.45rem; }
    .summary .facility { color:#717A76; margin-bottom:1rem; }
    .summary .diagnosis { font-size:1.05rem; font-weight:700; margin-bottom:.3rem; }
    .summary .action { color:#59635F; font-size:.88rem; }
    .status-row { display:flex; justify-content:space-between; border-top:1px solid #EEF0EF; padding:.48rem 0; }
    [data-testid="stMetric"] { background:white; border:1px solid #E1E5E3; border-radius:12px; padding:.85rem; }
    .stPlotlyChart { background:white; border:1px solid #E5E8E6; border-radius:12px; padding:.2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    files = {
        "kpi": "kpi_by_period.csv",
        "growth": "growth_bottleneck.csv",
        "mobile": "spatial_mobility_only.csv",
        "origin": "mobility_origin_by_period.csv",
        "spatial": "spatial_concentration_available_sites.csv",
    }
    return {key: pd.read_csv(OUT / name, encoding="utf-8-sig") for key, name in files.items()}


DATA = load()


def row_for(region_key: str, metric: str) -> pd.Series | None:
    rows = DATA["growth"].loc[DATA["growth"]["지역키"].eq(region_key) & DATA["growth"]["지표"].eq(metric)]
    return None if rows.empty else rows.iloc[0]


def status_for(region_key: str, metric: str, status_col: str) -> str:
    row = row_for(region_key, metric)
    value = str(row.get(status_col)) if row is not None and pd.notna(row.get(status_col)) else "NA"
    return value if value in STATUS else "NA"


def change_for(region_key: str, metric: str, growth_col: str, point_col: str) -> str:
    row = row_for(region_key, metric)
    if row is None:
        return "자료 없음"
    col = point_col if metric.endswith("_pct") else growth_col
    value = pd.to_numeric(row.get(col), errors="coerce")
    if pd.isna(value):
        return "자료 없음"
    return f"{value:+.1f}%p" if metric.endswith("_pct") else f"{value:+.1f}%"


def selected_from_map(event: object) -> str | None:
    try:
        points = event.selection.points
    except AttributeError:
        try:
            points = event["selection"]["points"]
        except (KeyError, TypeError):
            return None
    if not points:
        return None
    custom = points[0].get("customdata", [])
    return custom[0] if custom else None


def map_figure(selected_key: str) -> go.Figure:
    points = SITES.copy()
    points["선택"] = np.where(points["지역키"].eq(selected_key), "선택", "지역")
    points["크기"] = np.where(points["지역키"].eq(selected_key), 24, 15)
    fig = px.scatter_map(
        points,
        lat="위도",
        lon="경도",
        hover_name="시설",
        hover_data={"지역": True, "선정연도": True, "위도": False, "경도": False, "선택": False, "크기": False, "지역키": False},
        color="선택",
        size="크기",
        size_max=24,
        custom_data=["지역키"],
        color_discrete_map={"선택": "#E56B4A", "지역": "#0F766E"},
        center={"lat": 35.35, "lon": 127.25},
        zoom=6.5,
        map_style="carto-positron",
    )
    fig.update_traces(marker={"opacity": .95}, selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": .75}})
    fig.update_layout(height=520, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, clickmode="event+select")
    return fig


def trend_figure(region_key: str) -> go.Figure:
    metrics = [metric for _, metric in FLOW]
    frame = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(region_key), ["기간", *metrics]].copy()
    long = frame.melt("기간", var_name="지표", value_name="값")
    pieces = []
    for metric, part in long.groupby("지표", sort=False):
        part = part.set_index("기간").reindex(PERIODS).reset_index()
        available = part["값"].dropna()
        baseline = available.iloc[0] if not available.empty else np.nan
        part["지수"] = part["값"] / baseline * 100
        part["표시명"] = METRIC_LABELS[metric]
        pieces.append(part)
    chart = pd.concat(pieces, ignore_index=True)
    fig = px.line(
        chart,
        x="기간",
        y="지수",
        color="표시명",
        markers=True,
        category_orders={"기간": PERIODS},
        color_discrete_sequence=["#596F7A", "#0F766E", "#C38A36", "#7C63A8", "#B64646"],
    )
    fig.update_traces(line={"width": 3}, marker={"size": 8}, connectgaps=False)
    fig.add_hline(y=100, line_dash="dot", line_color="#AAB5B0")
    fig.add_vline(x=1.5, line_dash="dash", line_color="#8DA099")
    fig.update_layout(height=420, margin=dict(l=20, r=20, t=35, b=20), legend_title_text="", plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="첫 가용기간=100")
    return fig


def facility_share_figure(region_key: str) -> go.Figure | None:
    mobile = DATA["mobile"].loc[DATA["mobile"]["지역키"].eq(region_key)].copy()
    if not mobile.empty:
        frame = mobile
        subtitle = "이동통신 방문자료"
    else:
        frame = DATA["spatial"].loc[
            DATA["spatial"]["지역키"].eq(region_key) & DATA["spatial"]["영역"].eq("방문")
        ].copy()
        subtitle = "읍면동 방문분포"
    if frame.empty:
        return None
    fig = px.line(frame, x="기간", y="시설동_점유율_pct", markers=True, category_orders={"기간": PERIODS})
    fig.update_traces(line={"width": 3, "color": "#0F766E"}, marker={"size": 8}, fill="tozeroy", fillcolor="rgba(15,118,110,.10)")
    fig.update_layout(height=315, margin=dict(l=20, r=20, t=35, b=20), title=subtitle, plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)")
    fig.update_xaxes(title="")
    fig.update_yaxes(title="시설 읍면동 비중", ticksuffix="%")
    return fig


if "map_region" not in st.session_state:
    st.session_state.map_region = "전남완도"

st.markdown(
    """<div class="map-title"><small>WELL-FLOW MAP</small><h1>지도에서 보는 웰니스 관광</h1>
    <p>시설을 선택하면 지정 전후 성과가 바뀝니다.</p></div>""",
    unsafe_allow_html=True,
)

interval_name = st.segmented_control("비교 구간", list(INTERVALS), default=list(INTERVALS)[0], label_visibility="collapsed")
growth_col, point_col, status_col, latest_period = INTERVALS[interval_name or list(INTERVALS)[0]]

map_col, summary_col = st.columns([1.65, 1], gap="large")
with map_col:
    event = st.plotly_chart(
        map_figure(st.session_state.map_region),
        width="stretch",
        key="wellness_map",
        on_select="rerun",
        selection_mode="points",
        config={"displayModeBar": False, "scrollZoom": True},
    )
    clicked = selected_from_map(event)
    if clicked in set(SITES["지역키"]) and clicked != st.session_state.map_region:
        st.session_state.map_region = clicked
        st.rerun()

with summary_col:
    fallback = st.selectbox(
        "지역 선택",
        SITES["지역키"].tolist(),
        index=SITES["지역키"].tolist().index(st.session_state.map_region),
        format_func=lambda key: SITES.loc[SITES["지역키"].eq(key), "지역"].iloc[0],
        key="map_fallback",
    )
    if fallback != st.session_state.map_region:
        st.session_state.map_region = fallback
        st.rerun()
    selected = SITES.loc[SITES["지역키"].eq(st.session_state.map_region)].iloc[0]
    rows = []
    for label, metric in FLOW:
        status = status_for(selected["지역키"], metric, status_col)
        symbol, text, color = STATUS[status]
        rows.append(f'<div class="status-row"><span>{label}</span><b style="color:{color}">{symbol} {text}</b></div>')
    st.markdown(
        f"""<div class="summary"><div class="place">{selected['지역']} · {selected['선정연도']}년 선정</div>
        <h2>{selected['시설']}</h2><div class="facility">{selected['시설동']}</div>
        <div class="diagnosis">{selected['진단']}</div><div class="action">우선 과제 · {selected['과제']}</div>
        <div style="margin-top:1rem">{''.join(rows)}</div></div>""",
        unsafe_allow_html=True,
    )

selected_key = st.session_state.map_region
st.markdown("### 선택 지역 성과")
metric_cols = st.columns(5)
for col, (label, metric) in zip(metric_cols, FLOW):
    status = status_for(selected_key, metric, status_col)
    symbol, text, _ = STATUS[status]
    with col:
        st.metric(label, change_for(selected_key, metric, growth_col, point_col), f"{symbol} {text}", delta_color="off")

trend_col, local_col = st.columns([1.55, 1], gap="large")
with trend_col:
    st.markdown("### P1–P4 흐름")
    st.plotly_chart(trend_figure(selected_key), width="stretch", key="map_trend", config={"displayModeBar": False})
    if DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(selected_key), [metric for _, metric in FLOW]].isna().any().any():
        st.caption("자료가 없는 기간은 선을 연결하지 않습니다.")

with local_col:
    st.markdown("### 시설지역 방문")
    local_fig = facility_share_figure(selected_key)
    if local_fig is None:
        st.info("시설 읍면동 방문자료 없음")
    else:
        st.plotly_chart(local_fig, width="stretch", key="map_local", config={"displayModeBar": False})
        if selected_key in set(DATA["mobile"]["지역키"]):
            st.caption("이동통신 방문자료만 사용 · 소비 자료 없음")
        else:
            st.caption("방문 비중 상승은 시설 주변 집중 확대를 뜻합니다.")

st.caption("한국관광 데이터랩 기반 내부 분석 · 대조군 없는 지정 전후 탐색")
