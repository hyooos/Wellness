"""Map-selectable 3x3 WELL-FLOW monitor for four wellness tourism sites."""

from __future__ import annotations

from contextlib import contextmanager
from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageOps


st.set_page_config(
    page_title="WELL-FLOW Monitor · Map",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "output" / "4개_웰니스관광지_성과분석"
BOUNDARY_PATH = ROOT / "assets" / "skorea-provinces-geo.json"
MUNICIPAL_BOUNDARY_PATH = ROOT / "assets" / "jeolla-municipalities-geo.json"
SITE_IMAGES = {
    "전북무주": ROOT / "웰니스관광지_사진" / "무주태권도원.jpg",
    "전남완도": ROOT / "웰니스관광지_사진" / "완도해양치유센터.jpg",
    "전북순창": ROOT / "웰니스관광지_사진" / "순창쉴랜드.jpg",
    "전북완주": ROOT / "웰니스관광지_사진" / "완주아원고택.jpg",
}
PERIODS = ["P1", "P2", "P3", "P4"]
PERIOD_SHORT = {"P1": "선정 2년 전", "P2": "선정 직전 1년", "P3": "선정 후 1년", "P4": "선정 후 2년"}

SITES = pd.DataFrame(
    [
        ("전북무주", "무주군", "태권도원 상징지구", "설천면", 2022, 127.762090, 36.012521, "유입 성장, 체류 정체", "숙박일수·장기체류 확대"),
        ("전남완도", "완도군", "완도 해양치유센터", "신지면", 2024, 126.818435, 34.328049, "긴 체류, 소비·계절성 약세", "체험소비·지역 확산"),
        ("전북순창", "순창군", "쉴랜드", "인계면", 2024, 127.131587, 35.431547, "관심 대비 전환 약세", "방문·숙박·소비 전환"),
        ("전북완주", "완주군", "아원고택", "소양면", 2024, 127.244624, 35.903470, "방문 대비 숙박 약세", "숙박 연계·체류 콘텐츠"),
    ],
    columns=["지역키", "지역", "시설", "시설동", "선정연도", "경도", "위도", "진단", "과제"],
)

ALIASES = {"쉴랜드": "쉴(SHIL)랜드"}
FLOW = [
    ("관심", "숙박검색건수"),
    ("방문", "외지인방문자수"),
    ("숙박", "숙박자비율_pct"),
    ("체류", "평균체류시간_분"),
    ("소비", "방문자대비관광소비_천원_proxy"),
]
METRIC_LABEL = {
    "숙박검색건수": "숙박 관심",
    "외지인방문자수": "외지인 방문",
    "숙박자비율_pct": "숙박 비율",
    "평균체류시간_분": "평균 체류",
    "평균숙박일수": "평균 숙박일",
    "숙박자중_3박이상_pct": "숙박객 3박+",
    "전체순방문자중_3박이상_pct": "전체 장기체류",
    "내국인관광소비_천원": "관광 소비",
    "방문자대비관광소비_천원_proxy": "방문당 소비",
    "DSI": "계절 안정성",
}
INTERVALS = {
    "선정 직전과 첫해 비교": ("g23_pct", "delta23_pctp", "지정직후_판정_3pct"),
    "첫해와 둘째해 비교": ("g34_pct", "delta34_pctp", "2년차_판정_3pct"),
}
STATUS = {
    "UP": ("개선", "#138A72", "↑"),
    "FLAT": ("유지", "#B17817", "→"),
    "DOWN": ("하락", "#D9534F", "↓"),
    "NA": ("측정불충분", "#7B8794", "·"),
}

DATA_NEEDS = {
    "전북무주": [
        ("1", "시설 직접 이용", "태권도원 방문·예약·체험 인원"),
        ("2", "방문 목적", "웰니스 목적 방문 여부와 만족도"),
        ("3", "체류 원인", "당일·연박 목적과 이동 동선"),
    ],
    "전남완도": [
        ("1", "시설 직접 이용", "센터 예약·프로그램·재방문"),
        ("2", "이용 전환", "지역 방문 중 센터 실제 이용 여부"),
        ("3", "전환 원인", "체류 중 활동·결제 경로"),
    ],
    "전북순창": [
        ("1", "시설 직접 이용", "검색 이후 예약·실방문 전환"),
        ("2", "이용 전환", "지역 방문 중 쉴랜드 실제 이용 여부"),
        ("3", "이탈 원인", "가격·후기·예약 단계 데이터"),
    ],
    "전북완주": [
        ("1", "시설 직접 이용", "아원고택 예약·방문·숙박 구분"),
        ("2", "이용 전환", "지역 방문 중 아원고택 실제 이용 여부"),
        ("3", "숙박 원인", "방문객 숙박지·예약·이동 동선"),
    ],
}

FOCUS_METRIC = {
    "전북무주": "평균숙박일수",
    "전남완도": "내국인관광소비_천원",
    "전북순창": "내국인관광소비_천원",
    "전북완주": "숙박자비율_pct",
}


st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');
    html, body, [class*="css"] { font-family:'Pretendard Variable', Pretendard, -apple-system, sans-serif; letter-spacing:-.018em; }
    .stApp { background:#F5F8FB; color:#101823; }
    [data-testid="stHeader"] { background:transparent; height:0; }
    .block-container { max-width:1740px; padding:1.1rem 1.45rem 2.5rem; }
    section[data-testid="stSidebar"] { width:255px!important; min-width:255px!important; background:rgba(255,255,255,.9); border-right:1px solid #DCE4EB; }
    section[data-testid="stSidebar"] .block-container { padding:1.25rem .85rem; }
    .topbar { background:transparent; color:#101823; padding:.45rem 0 1rem; margin:0 0 .6rem; border-bottom:1px solid #DCE4EB; display:flex; align-items:flex-end; justify-content:space-between; }
    .brand { display:flex; align-items:center; gap:18px; }
    .brand strong { font-family:Inter, Arial, sans-serif; font-size:1.75rem; line-height:1; font-weight:720; letter-spacing:-.025em; }
    .brand strong span { font-weight:450; color:#101823; }
    .brand > span { color:#667382; font-size:.8rem; padding-bottom:.08rem; }
    .top-meta { color:#667382; font-size:.69rem; }
    .sidebar-title { font-weight:800; font-size:.92rem; margin:.15rem 0 .08rem; color:#101823; }
    .sidebar-note { color:#667382; font-size:.68rem; margin-bottom:.65rem; }
    .selected-site { margin-top:.45rem; padding:.5rem .58rem; border-radius:9px; background:#F3F7FA; color:#536276; font-size:.65rem; line-height:1.45; }
    .selected-site b { color:#172438; font-size:.72rem; }
    .map-head { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:.25rem 0 .6rem; }
    .map-head b { display:block; color:#172438; font-size:.94rem; }
    .map-head span { color:#667382; font-size:.7rem; }
    .map-selection { padding:.2rem 0; }
    .map-selection .place { color:#1287E5; font-size:.65rem; font-weight:800; letter-spacing:.08em; }
    .map-selection h2 { color:#101823; font-size:1.45rem; margin:.28rem 0 .15rem; letter-spacing:-.035em; }
    .map-selection .location { color:#667382; font-size:.72rem; }
    .map-selection .diagnosis { margin-top:.85rem; padding:.7rem .75rem; border-radius:10px; background:#F3F7FA; color:#536276; font-size:.71rem; line-height:1.55; }
    .map-selection .diagnosis b { color:#172438; }
    .map-selection .description { margin-top:.65rem; color:#43536A; font-size:.72rem; line-height:1.55; }
    .map-selection .address { margin-top:.55rem; padding:.55rem .62rem; border-radius:8px; background:#F3F7FA; color:#536276; font-size:.68rem; line-height:1.45; }
    .map-selection .address b { color:#172438; }
    [data-testid="stImage"] img { border-radius:11px; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color:#DCE4EB; border-radius:14px; background:#FFFFFF; box-shadow:0 1px 2px rgba(16,24,35,.025); }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding:.82rem .95rem .9rem; }
    .panel-title { font-size:1rem; font-weight:780; color:#172438; margin:0; }
    .panel-sub { color:#667382; font-size:.73rem; margin:.12rem 0 .7rem; }
    .site-head { background:#F5F8FB; border:1px solid #E0E7EE; border-radius:9px; padding:.58rem .7rem; margin-bottom:.65rem; }
    .site-head strong { font-size:.94rem; }
    .site-head span { color:#667382; font-size:.72rem; margin-left:.35rem; }
    .metric-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:7px; }
    .metric-mini { text-align:center; border-right:1px solid #E3E9F0; padding:.22rem .12rem; }
    .metric-mini:last-child { border-right:0; }
    .metric-mini b { display:block; color:#101823; font-size:.88rem; white-space:nowrap; margin-top:.05rem; }
    .metric-mini small { color:#667382; font-size:.66rem; }
    .metric-mini em { display:block; font-style:normal; font-weight:750; font-size:.69rem; margin-top:.14rem; }
    .good { color:#11856E; } .bad { color:#D34A4A; } .flat { color:#A26D16; } .muted { color:#7D8997; }
    .flow-summary { margin-top:.65rem; background:#F5F8FB; border-radius:9px; padding:.55rem .65rem; font-size:.75rem; color:#43536A; }
    .flow-summary b { color:#D34A4A; }
    .headline-diagnosis { margin:.6rem 0 0; padding:.58rem .68rem; border-left:3px solid #1287E5; background:#F3F7FA; border-radius:3px 9px 9px 3px; color:#31445A; font-size:.72rem; line-height:1.45; }
    .headline-diagnosis b { color:#101823; }
    .layer { border:1px solid #E0E7EE; border-radius:10px; padding:.58rem .65rem; margin:.42rem 0; display:flex; justify-content:space-between; gap:.5rem; align-items:center; }
    .layer-name { font-size:.78rem; font-weight:750; color:#26384D; }
    .layer-detail { font-size:.68rem; color:#6B7A8E; margin-top:.1rem; }
    .badge { flex:none; border-radius:999px; padding:.2rem .5rem; font-size:.64rem; font-weight:750; }
    .ok { background:#E5F5EF; color:#08765E; } .partial { background:#FFF2D8; color:#8B5B08; } .missing { background:#F1F3F6; color:#737E8D; }
    .funnel { display:flex; flex-direction:column; align-items:center; gap:3px; }
    .funnel-row { min-height:37px; padding:.38rem .62rem; display:flex; align-items:center; justify-content:space-between; border-radius:7px; color:#12243D; font-size:.72rem; }
    .funnel-row strong { font-size:.84rem; }
    .funnel-note { margin-top:.5rem; padding:.5rem .62rem; background:#FFF4F1; border:1px solid #F2D1CA; border-radius:9px; color:#9C3431; font-size:.7rem; }
    .period-key { display:grid; grid-template-columns:repeat(4,1fr); gap:3px; margin-top:.15rem; }
    .period-key div { background:#F2F5F8; border-radius:4px; text-align:center; padding:.25rem .1rem; font-size:.6rem; color:#607086; }
    .mini-table { width:100%; border-collapse:collapse; font-size:.68rem; }
    .mini-table th { background:#F2F5F8; color:#52647B; font-weight:700; }
    .mini-table th,.mini-table td { border-bottom:1px solid #E4EAF1; padding:.24rem .28rem; text-align:right; }
    .mini-table th:first-child,.mini-table td:first-child { text-align:left; }
    .compare-mini { width:100%; border-collapse:separate; border-spacing:0 3px; font-size:.63rem; }
    .compare-mini th { color:#6A7889; font-size:.58rem; font-weight:700; text-align:center; padding:.18rem; }
    .compare-mini th:first-child { text-align:left; }
    .compare-mini td { background:#F7F9FB; padding:.34rem .2rem; text-align:center; }
    .compare-mini td:first-child { text-align:left; border-radius:6px 0 0 6px; font-weight:750; padding-left:.45rem; }
    .compare-mini td:last-child { border-radius:0 6px 6px 0; }
    .compare-mini tr.selected td { background:#EAF4FC; }
    .compare-state { font-weight:800; font-size:.7rem; }
    .origin-row { display:grid; grid-template-columns:22px 1fr 42px; gap:7px; align-items:center; margin:.36rem 0; font-size:.7rem; }
    .rank { width:20px; height:20px; border-radius:50%; display:grid; place-items:center; background:#E6EEF8; color:#245B99; font-weight:800; }
    .bar-bg { height:6px; background:#E9EEF4; border-radius:5px; overflow:hidden; margin-top:2px; }
    .bar { height:100%; background:#327ABD; border-radius:5px; }
    .env-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:5px; }
    .env-card { border:1px solid #DEE6EF; border-radius:6px; padding:.38rem; text-align:center; }
    .env-card small { display:block; color:#69798E; font-size:.63rem; }
    .env-card b { font-size:.82rem; }
    .impact-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:.25rem 0 .55rem; }
    .impact-card { background:#F3F7FA; border-radius:9px; padding:.62rem .4rem; text-align:center; }
    .impact-card small { display:block; color:#68788B; font-size:.6rem; }
    .impact-card b { display:block; color:#172438; font-size:.88rem; margin-top:.18rem; }
    .poi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:3px; margin-top:.4rem; }
    .poi { background:#F3F6FA; padding:.35rem .22rem; text-align:center; border-radius:7px; font-size:.63rem; }
    .poi b { display:block; color:#176CA9; font-size:.78rem; }
    .diag-box { display:grid; grid-template-columns:.9fr 1.4fr; gap:7px; }
    .alert-box { background:#FFF4F1; border:1px solid #F3CCC4; border-radius:9px; padding:.7rem; text-align:center; font-size:.7rem; }
    .alert-box b { display:block; color:#CE403C; margin-top:.22rem; font-size:.82rem; }
    .reason-box { background:#F5F7FA; border-radius:9px; padding:.58rem .65rem; font-size:.68rem; color:#536278; line-height:1.55; }
    .policy-row { display:grid; grid-template-columns:26px .8fr 1.3fr; align-items:center; gap:8px; padding:.42rem 0; border-bottom:1px solid #E6EBF1; font-size:.68rem; }
    .policy-num { width:24px; height:24px; border-radius:50%; background:#1287E5; color:white; display:grid; place-items:center; font-weight:800; }
    .policy-row strong { color:#16385F; }
    .policy-row span:last-child { color:#66768A; }
    .reliability { width:100%; border-collapse:collapse; font-size:.64rem; }
    .reliability th { background:#F2F5F8; color:#53657B; }
    .reliability td,.reliability th { border-bottom:1px solid #E1E7EE; padding:.25rem .2rem; text-align:left; }
    .measure-note { margin-top:.5rem; padding:.48rem .58rem; background:#F0F6FB; color:#315A82; font-size:.66rem; border-radius:8px; }
    .detail-button-note { color:#7A8796; font-size:.61rem; margin-top:.35rem; }
    div[data-testid="stButton"] button { min-height:2.05rem; border:1px solid #D6E1EA; border-radius:8px; background:#F8FAFC; color:#315A82; font-size:.67rem; font-weight:700; }
    div[data-testid="stButton"] button:hover { border-color:#1287E5; color:#075C99; background:#F1F8FD; }
    .stPlotlyChart { margin:-.2rem 0; }
    [data-testid="stPlotlyChart"] > div { border:0 !important; }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div { min-height:2.55rem; border-color:#D5DFE8; border-radius:9px; font-size:.72rem; }
    @media(max-width:1100px) { .metric-grid { grid-template-columns:repeat(3,1fr); } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def csv(path: Path, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data
def jeolla_boundary() -> dict:
    with BOUNDARY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@st.cache_data
def jeolla_municipalities() -> dict:
    with MUNICIPAL_BOUNDARY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_data() -> dict[str, pd.DataFrame]:
    files = {
        "kpi": DATA_DIR / "kpi_by_period.csv",
        "site_catalog": ROOT / "wellness_88_geocoded.csv",
        "growth": DATA_DIR / "growth_bottleneck.csv",
        "monthly": DATA_DIR / "monthly_input.csv",
        "origin": DATA_DIR / "mobility_origin_by_period.csv",
        "periods": DATA_DIR / "period_definitions.csv",
        "its": DATA_DIR / "its_designation_hac3.csv",
        "its_robustness": DATA_DIR / "its_robustness.csv",
        "poi": ROOT / "output" / "대시보드_보조데이터" / "geo_tourism_density.csv",
        "nearest": ROOT / "output" / "대시보드_보조데이터" / "geo_nearest_lodging.csv",
    }
    return {name: csv(path, path.stat().st_mtime_ns) for name, path in files.items()}


DATA = load_data()


def growth_row(region_key: str, metric: str) -> pd.Series | None:
    rows = DATA["growth"].loc[DATA["growth"]["지역키"].eq(region_key) & DATA["growth"]["지표"].eq(metric)]
    return None if rows.empty else rows.iloc[0]


def clean_status(value: object) -> str:
    value = str(value) if pd.notna(value) else "NA"
    return value if value in STATUS else "NA"


def change(region_key: str, metric: str, growth_col: str, point_col: str) -> float:
    row = growth_row(region_key, metric)
    if row is None:
        return np.nan
    col = point_col if metric.endswith("_pct") else growth_col
    return pd.to_numeric(row.get(col), errors="coerce")


def status(region_key: str, metric: str, status_col: str) -> str:
    row = growth_row(region_key, metric)
    return "NA" if row is None else clean_status(row.get(status_col))


def change_text(value: float, metric: str) -> str:
    if pd.isna(value):
        return "측정불충분"
    return f"{value:+.1f}%p" if metric.endswith("_pct") else f"{value:+.1f}%"


def level_text(value: float, metric: str) -> str:
    if pd.isna(value):
        return "자료 없음"
    if metric in {"숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct"}:
        return f"{value:.1f}%"
    if metric == "평균체류시간_분":
        return f"{value / 60:.1f}시간"
    if metric == "평균숙박일수":
        return f"{value:.2f}일"
    if metric == "내국인관광소비_천원":
        return f"{value / 100_000:.1f}억원"
    if metric == "방문자대비관광소비_천원_proxy":
        return f"{value:.1f}천원"
    if metric == "DSI":
        return f"{value * 100:.0f}점"
    return f"{value:,.0f}"


def status_class(code: str) -> str:
    return {"UP": "good", "DOWN": "bad", "FLAT": "flat"}.get(code, "muted")


def month_text(value: object) -> str:
    text = str(int(value)) if pd.notna(value) else ""
    return f"{text[:4]}.{text[4:]}" if len(text) == 6 else text


def panel_head(number: int, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="panel-title">{number}. {escape(title)}</div><div class="panel-sub">{escape(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def trend_chart(region_key: str) -> go.Figure:
    metrics = [metric for _, metric in FLOW]
    frame = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(region_key), ["기간", *metrics]].set_index("기간").reindex(PERIODS)
    fig = go.Figure()
    colors = ["#647789", "#1287E5", "#D89900", "#10A17F", "#E45527"]
    for (label, metric), color in zip(FLOW, colors):
        values = pd.to_numeric(frame[metric], errors="coerce")
        baseline = values.loc["P1"]
        index = values / baseline * 100 if pd.notna(baseline) and baseline != 0 else values * np.nan
        fig.add_trace(
            go.Scatter(
                x=[PERIOD_SHORT[p] for p in PERIODS], y=index, mode="lines+markers", name=label,
                line={"color": color, "width": 2}, marker={"size": 5}, connectgaps=False,
                hovertemplate=f"{label}<br>%{{x}} · %{{y:.1f}}<extra></extra>",
            )
        )
    fig.add_hline(y=100, line_dash="dot", line_color="#AAB5C0")
    fig.update_layout(
        height=165, margin=dict(l=2, r=3, t=5, b=2), showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        legend=dict(orientation="h", y=1.02, x=0, font={"size": 8}),
        xaxis=dict(showgrid=False, title="", categoryorder="array", categoryarray=list(PERIOD_SHORT.values())),
        yaxis=dict(showgrid=True, gridcolor="#E8EDF3", title="선정 2년 전=100", nticks=4),
        font=dict(family="Pretendard", size=9, color="#52647A"),
    )
    return fig


def its_evidence(region_key: str, metric: str, effect: str) -> tuple[str, str]:
    rows = DATA["its"].loc[DATA["its"]["지역키"].eq(region_key) & DATA["its"]["지표"].eq(metric)]
    if rows.empty:
        return "측정불충분", "missing"
    row = rows.iloc[0]
    if effect == "즉시수준변화":
        beta, pvalue, qvalue = row["즉시수준변화_beta"], row["즉시수준변화_p"], row["즉시수준변화_q_BH"]
    else:
        beta, pvalue, qvalue = row["지정후_기울기변화_beta"], row["지정후_기울기변화_p"], row["지정후_기울기변화_q_BH"]
    robust = DATA["its_robustness"].loc[
        DATA["its_robustness"]["지역키"].eq(region_key)
        & DATA["its_robustness"]["지표"].eq(metric)
        & DATA["its_robustness"]["계수"].eq(effect)
        & pd.to_numeric(DATA["its_robustness"]["개입시작월"], errors="coerce").eq(pd.to_numeric(row["개입시작월"], errors="coerce"))
    ]
    all_lags = False if robust.empty else str(robust.iloc[0]["모든lag_p05유의"]).lower() == "true"
    direction = "상승" if pd.to_numeric(beta, errors="coerce") > 0 else "하락"
    if pd.notna(qvalue) and qvalue < .05 and all_lags:
        return f"{direction} · 근거 강함", "ok"
    if pd.notna(qvalue) and qvalue < .05:
        return f"{direction} · 근거 보통", "partial"
    if pd.notna(pvalue) and pvalue < .05:
        return f"{direction} · 탐색적 신호", "partial"
    return "명확한 변화 없음", "missing"


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
    point = points[0] or {}
    custom = point.get("customdata", []) if isinstance(point, dict) else []
    if isinstance(custom, dict):
        return custom.get("지역키") or custom.get("0")
    if isinstance(custom, (list, tuple)):
        return custom[0] if custom else None
    return None


def selection_map(selected_key: str) -> go.Figure:
    points = SITES.copy()
    points["상태"] = np.where(points["지역키"].eq(selected_key), "선택", "관광지")
    points["마커크기"] = np.where(points["지역키"].eq(selected_key), 22, 14)
    municipal = jeolla_municipalities()
    selected_municipal = {"전북무주": "Muju", "전남완도": "Wando", "전북순창": "Sunchang", "전북완주": "Wanju"}[selected_key]
    municipal_names = [feature["properties"]["NAME_2"] for feature in municipal["features"]]
    municipal_values = [1 if name == selected_municipal else 0 for name in municipal_names]
    municipal_trace = go.Choropleth(
        geojson=municipal,
        locations=municipal_names,
        z=municipal_values,
        featureidkey="properties.NAME_2",
        colorscale=[[0, "#D9EAF7"], [0.49, "#D9EAF7"], [0.5, "#71B1DE"], [1, "#2386C5"]],
        marker_line_color="#FFFFFF",
        marker_line_width=1.15,
        marker_opacity=0.88,
        showscale=False,
        hoverinfo="skip",
        name="시군구 경계",
    )
    boundary = jeolla_boundary()
    boundary_names = [feature["properties"]["NAME_1"] for feature in boundary["features"]]
    province_trace = go.Choropleth(
        geojson=boundary,
        locations=boundary_names,
        z=[1] * len(boundary_names),
        featureidkey="properties.NAME_1",
        colorscale=[[0, "rgba(34, 117, 151, 0.01)"], [1, "rgba(34, 117, 151, 0.01)"]],
        marker_line_color="#227597",
        marker_line_width=2.5,
        marker_opacity=0.02,
        showscale=False,
        hoverinfo="skip",
        name="전라도 경계",
    )
    scatter_trace = go.Scattergeo(
        lon=points["경도"],
        lat=points["위도"],
        mode="markers+text",
        text=points["지역"].str.replace("군", "", regex=False),
        textposition="top center",
        textfont={"size": 12, "color": "#172438"},
        customdata=points[["지역키", "시설", "시설동", "선정연도"]],
        hovertemplate="%{text}<br>%{customdata[1]} · %{customdata[2]}<br>%{customdata[3]}년 선정<extra></extra>",
        marker={"size": points["마커크기"], "color": points["상태"].map({"선택": "#E45527", "관광지": "#1287E5"}), "line": {"color": "white", "width": 2}, "opacity": .98},
        selected={"marker": {"opacity": 1}},
        unselected={"marker": {"opacity": .82}},
        name="관광지",
    )
    fig = go.Figure([municipal_trace, province_trace, scatter_trace])
    fig.update_layout(
        height=360,
        margin=dict(l=0, r=0, t=0, b=0),
        showlegend=False,
        clickmode="event+select",
        dragmode=False,
        geo=dict(
            bgcolor="#F8FAFC",
            showland=False,
            showcountries=False,
            showcoastlines=False,
            showframe=False,
            projection={"type": "mercator", "scale": 1.18},
            center={"lat": 35.15, "lon": 127.05},
            lonaxis={"range": [125.95, 128.20]},
            lataxis={"range": [33.85, 36.45]},
        ),
    )
    return fig


def metric_monthly(region_key: str, metric: str) -> pd.DataFrame:
    frame = DATA["monthly"].loc[DATA["monthly"]["지역키"].eq(region_key)].copy()
    frame["날짜"] = pd.to_datetime(frame["기준년월"].astype(str), format="%Y%m")
    if metric == "방문자대비관광소비_천원_proxy":
        frame["값"] = pd.to_numeric(frame["내국인관광소비_천원"], errors="coerce") / pd.to_numeric(frame["외지인방문자수"], errors="coerce")
    else:
        frame["값"] = pd.to_numeric(frame[metric], errors="coerce")
    return frame.sort_values("날짜")


def monthly_chart(region_key: str, metric: str) -> go.Figure:
    frame = metric_monthly(region_key, metric)
    fig = px.line(frame, x="날짜", y="값", markers=True)
    fig.update_traces(line={"color": "#1287E5", "width": 2.4}, marker={"size": 4},
                      hovertemplate="%{x|%Y-%m}<br>%{y:,.2f}<extra></extra>")
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), showlegend=False,
                      paper_bgcolor="white", plot_bgcolor="white",
                      xaxis=dict(title="", showgrid=False, tickformat="%y.%m"),
                      yaxis=dict(title="", gridcolor="#E8EDF3"))
    return fig


def period_value_table(region_key: str, metrics: list[str]) -> pd.DataFrame:
    frame = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(region_key)].set_index("기간").reindex(PERIODS)
    rows = []
    for metric in metrics:
        row = {"지표": METRIC_LABEL.get(metric, metric)}
        for period in PERIODS:
            row[PERIOD_SHORT[period]] = level_text(pd.to_numeric(frame.loc[period, metric], errors="coerce"), metric)
        rows.append(row)
    return pd.DataFrame(rows)


PANEL_TITLES = {
    1: "성과 한눈에", 2: "4개 관광지 비교", 3: "전환 흐름", 4: "선정 전후 성장 흐름",
    5: "방문 유입", 6: "숙박·체류 구조", 7: "병목·구조변화",
}


@st.dialog("상세 분석", width="large")
def show_panel_detail(panel: int, region_key: str, interval_name: str, display_period: str) -> None:
    site_row = SITES.loc[SITES["지역키"].eq(region_key)].iloc[0]
    growth_col, point_col, status_col = INTERVALS[interval_name]
    st.subheader(f"{panel}. {PANEL_TITLES[panel]}")
    st.caption(f"{site_row['시설']} · {site_row['지역']} · {interval_name}")

    if panel == 1:
        fig = trend_chart(region_key)
        fig.update_layout(height=350)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.dataframe(period_value_table(region_key, [m for _, m in FLOW]), hide_index=True, width="stretch")

    elif panel == 2:
        metric = st.selectbox("비교 지표", [m for _, m in FLOW], format_func=lambda x: METRIC_LABEL[x], key="detail_compare_metric")
        rows = []
        for region in SITES.itertuples():
            value = change(region.지역키, metric, growth_col, point_col)
            code = status(region.지역키, metric, status_col)
            current = DATA["kpi"].loc[(DATA["kpi"]["지역키"].eq(region.지역키)) & (DATA["kpi"]["기간"].eq(display_period)), metric]
            current_value = pd.to_numeric(current.iloc[0], errors="coerce") if not current.empty else np.nan
            rows.append({"지역": region.지역, "관광지": region.시설, "현재 수준": level_text(current_value, metric), "변화": value, "판정": STATUS[code][0]})
        detail = pd.DataFrame(rows)
        chart = px.bar(detail, x="지역", y="변화", color="판정", text_auto=".1f",
                       color_discrete_map={"개선": "#138A72", "유지": "#B17817", "하락": "#D9534F", "측정불충분": "#7B8794"})
        chart.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="%p" if metric.endswith("_pct") else "%", xaxis_title="", legend_title="")
        st.plotly_chart(chart, width="stretch", config={"displayModeBar": False})
        detail["변화"] = detail["변화"].map(lambda x: change_text(x, metric))
        st.dataframe(detail, hide_index=True, width="stretch")

    elif panel == 3:
        metric = st.selectbox("상세 단계", [m for _, m in FLOW], format_func=lambda x: METRIC_LABEL[x], key="detail_funnel_metric")
        st.plotly_chart(monthly_chart(region_key, metric), width="stretch", config={"displayModeBar": False})
        current = DATA["kpi"].loc[(DATA["kpi"]["지역키"].eq(region_key)) & (DATA["kpi"]["기간"].eq(display_period))].iloc[0]
        rows = []
        for stage, stage_metric in FLOW:
            code = status(region_key, stage_metric, status_col)
            rows.append({"단계": stage, "현재 수준": level_text(pd.to_numeric(current.get(stage_metric), errors="coerce"), stage_metric),
                         "기간 변화": change_text(change(region_key, stage_metric, growth_col, point_col), stage_metric), "판정": STATUS[code][0]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    elif panel == 4:
        fig = trend_chart(region_key)
        fig.update_layout(height=380)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        rows = []
        for _, metric in FLOW:
            r = growth_row(region_key, metric)
            vals = []
            for gcol, pcol in [("g12_pct", "delta12_pctp"), ("g23_pct", "delta23_pctp"), ("g34_pct", "delta34_pctp")]:
                value = pd.to_numeric(r.get(pcol if metric.endswith("_pct") else gcol), errors="coerce") if r is not None else np.nan
                vals.append(change_text(value, metric))
            rows.append({"지표": METRIC_LABEL[metric], "선정 2년 전→직전": vals[0], "직전→선정 후 1년": vals[1], "선정 후 1년→2년": vals[2]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    elif panel == 5:
        st.plotly_chart(monthly_chart(region_key, "외지인방문자수"), width="stretch", config={"displayModeBar": False})
        origin = DATA["origin"].loc[(DATA["origin"]["지역키"].eq(region_key)) & (DATA["origin"]["기간"].eq(display_period))].copy()
        if origin.empty:
            st.info("이 기간의 출발지역 자료는 아직 확보되지 않았습니다.")
        else:
            origin["출발지역"] = origin["거주지(시도)"].astype(str) + " " + origin["거주지(시군구)"].astype(str)
            origin = origin.nlargest(12, "비율(%)")
            fig = px.bar(origin.sort_values("비율(%)"), x="비율(%)", y="출발지역", orientation="h", text_auto=".1f")
            fig.update_traces(marker_color="#327ABD")
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="방문자 비중(%)", yaxis_title="")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.dataframe(origin[["거주지(시도)", "거주지(시군구)", "비율(%)"]], hide_index=True, width="stretch")

    elif panel == 6:
        quality = ["숙박자비율_pct", "평균숙박일수", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI"]
        metric = st.selectbox("상세 지표", quality, format_func=lambda x: METRIC_LABEL[x], key="detail_stay_metric")
        annual = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(region_key)].set_index("기간").reindex(PERIODS)
        fig = px.line(x=[PERIOD_SHORT[p] for p in PERIODS], y=pd.to_numeric(annual[metric], errors="coerce"), markers=True)
        fig.update_traces(line={"color": "#10A17F", "width": 3}, marker={"size": 8})
        fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="", yaxis_title="")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
        st.dataframe(period_value_table(region_key, quality), hide_index=True, width="stretch")

    elif panel == 7:
        rows = []
        for stage, metric in FLOW:
            immediate, _ = its_evidence(region_key, metric, "즉시수준변화")
            slope, _ = its_evidence(region_key, metric, "지정후기울기변화")
            rows.append({"단계": stage, "선정 직후 변화": immediate, "선정 후 흐름": slope,
                         "기간 판정": STATUS[status(region_key, metric, status_col)][0]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        focus = st.selectbox("월별 확인 지표", [m for _, m in FLOW], format_func=lambda x: METRIC_LABEL[x], key="detail_its_metric")
        st.plotly_chart(monthly_chart(region_key, focus), width="stretch", config={"displayModeBar": False})
        st.caption("구조변화 분석은 대조군 없는 탐색 결과이며 선정의 인과효과를 뜻하지 않습니다.")

def detail_button(panel: int, region_key: str, interval_name: str, display_period: str) -> None:
    if st.button("상세 그래프·표 보기", key=f"panel_detail_{panel}", width="stretch"):
        show_panel_detail(panel, region_key, interval_name, display_period)


@contextmanager
def detail_panel(number: int, title: str, subtitle: str, region_key: str, interval_name: str, display_period: str):
    with st.container(border=True, height="stretch", vertical_alignment="distribute"):
        with st.container(gap="small"):
            panel_head(number, title, subtitle)
            yield
        detail_button(number, region_key, interval_name, display_period)


if "monitor_map_site" not in st.session_state or st.session_state.monitor_map_site not in set(SITES["지역키"]):
    st.session_state.monitor_map_site = SITES.iloc[0]["지역키"]
selected_key = st.session_state.monitor_map_site
site = SITES.loc[SITES["지역키"].eq(selected_key)].iloc[0]
site_periods = DATA["periods"].loc[DATA["periods"]["지역키"].eq(selected_key)].set_index("기간").reindex(PERIODS)
analysis_start = month_text(site_periods.loc["P1", "시작월"])
analysis_end = month_text(site_periods.loc["P4", "종료월"])

st.markdown(
    f"""
    <div class="topbar">
      <div class="brand"><strong>WELL-FLOW <span>Monitor</span></strong><span>웰니스 관광지 성과 진단</span></div>
      <div class="top-meta">{escape(site['지역'])} 분석기간 · {analysis_start}–{analysis_end} · 선정월 기준</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="map-head"><div><b>전라도 웰니스 관광지 위치</b></div>'
    '<span>마커 클릭으로 선택　 주황 · 현재 선택</span></div>',
    unsafe_allow_html=True,
)
map_col, selected_col = st.columns([.82, 1.18], gap="medium")
with map_col:
    with st.container(border=True, height="stretch"):
        event = st.plotly_chart(
            selection_map(selected_key),
            width="stretch",
            key="monitor_selection_map",
            on_select="rerun",
            selection_mode="points",
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        )
    clicked_key = selected_from_map(event)
    if clicked_key and clicked_key != selected_key:
        st.session_state.monitor_map_site = clicked_key
        st.rerun()
with selected_col:
    with st.container(border=True, height="stretch", vertical_alignment="center"):
        catalog_name = ALIASES.get(site["시설"], site["시설"])
        catalog_rows = DATA["site_catalog"].loc[DATA["site_catalog"]["시설명"].eq(catalog_name)]
        catalog = catalog_rows.iloc[0] if not catalog_rows.empty else pd.Series(dtype=object)
        theme = str(catalog.get("테마", "웰니스 관광지")) if not catalog.empty else "웰니스 관광지"
        address = catalog.get("tour_api_addr", "주소 정보 없음") if not catalog.empty else "주소 정보 없음"
        address = str(address) if pd.notna(address) and str(address).strip() else "주소 정보 없음"
        photo_col, info_col = st.columns([.92, 1.08], gap="medium", vertical_alignment="center")
        with photo_col:
            with Image.open(SITE_IMAGES[selected_key]) as source_image:
                site_photo = ImageOps.fit(source_image.convert("RGB"), (800, 560), method=Image.Resampling.LANCZOS)
            st.image(site_photo, width="stretch")
        with info_col:
            st.markdown(
                f'<div class="map-selection"><div class="place">SELECTED SITE</div><h2>{escape(site["시설"])}</h2>'
                f'<div class="location">{escape(site["지역"])} · {escape(site["시설동"])} · {int(site["선정연도"])}년 지정</div>'
                f'<div class="description">{escape(theme)} 테마의 웰니스 관광지</div>'
                f'<div class="address"><b>주소</b><br>{escape(address)}</div>'
                f'<div class="diagnosis"><b>현재 관찰</b><br>{escape(site["진단"])}<br><br><b>분석 단위</b><br>{escape(site["지역"])} 관광시장</div></div>',
                unsafe_allow_html=True,
            )

ctl1, ctl2, ctl3 = st.columns([1.1, 1.1, 4])
with ctl1:
    interval_name = st.selectbox("변화 구간", list(INTERVALS), label_visibility="collapsed")
with ctl2:
    display_period = st.selectbox("표시 기간", PERIODS, index=3, format_func=lambda x: PERIOD_SHORT[x], label_visibility="collapsed")
with ctl3:
    period_caption = " · ".join(
        f"{PERIOD_SHORT[period]} {month_text(site_periods.loc[period, '시작월'])}–{month_text(site_periods.loc[period, '종료월'])}"
        for period in PERIODS
    )
    st.caption(period_caption)

growth_col, point_col, status_col = INTERVALS[interval_name]
kpi_site = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(selected_key)].set_index("기간")
latest = kpi_site.loc[display_period]
flow_signals = [
    (stage, metric, status(selected_key, metric, status_col), change(selected_key, metric, growth_col, point_col))
    for stage, metric in FLOW
]
up_stages = [stage for stage, _, code, _ in flow_signals if code == "UP"]
down_stages = [stage for stage, _, code, _ in flow_signals if code == "DOWN"]
na_stages = [stage for stage, _, code, _ in flow_signals if code == "NA"]
if down_stages and up_stages:
    diagnosis_text = f"{'·'.join(up_stages[:2])}은 개선됐지만 {'·'.join(down_stages[:3])}에서 하락 신호가 확인됩니다."
elif down_stages:
    diagnosis_text = f"{'·'.join(down_stages[:3])} 단계에서 하락 신호가 확인됩니다."
elif up_stages:
    diagnosis_text = f"{'·'.join(up_stages[:3])} 단계가 개선됐고 뚜렷한 하락 단계는 없습니다."
else:
    diagnosis_text = "현재 구간에서 뚜렷한 방향 변화가 확인되지 않습니다."
if na_stages:
    diagnosis_text += f" {'·'.join(na_stages)}은 측정불충분입니다."
focus_metric = FOCUS_METRIC[selected_key]
instant_evidence, instant_evidence_cls = its_evidence(selected_key, focus_metric, "즉시수준변화")
slope_evidence, slope_evidence_cls = its_evidence(selected_key, focus_metric, "지정후기울기변화")

# Row 1 ---------------------------------------------------------------------
c1, c2, c3 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c1:
    with detail_panel(1, "성과 한눈에", "현재 수준·변화·핵심 진단", selected_key, interval_name, display_period):
        st.markdown(
            f'<div class="site-head"><strong>{escape(site["시설"])}</strong><span>{escape(site["지역"])} {escape(site["시설동"])}</span></div>',
            unsafe_allow_html=True,
        )
        cards = []
        for stage, metric in FLOW:
            val = pd.to_numeric(latest.get(metric), errors="coerce")
            ch = change(selected_key, metric, growth_col, point_col)
            code = status(selected_key, metric, status_col)
            cards.append(
                f'<div class="metric-mini"><small>{stage}</small><b>{level_text(val, metric)}</b>'
                f'<em class="{status_class(code)}">{change_text(ch, metric)}</em></div>'
            )
        st.markdown('<div class="metric-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="headline-diagnosis"><b>한 문장 진단</b><br>{escape(diagnosis_text)}</div>', unsafe_allow_html=True)

with c2:
    with detail_panel(2, "4개 관광지 비교", "같은 상대시점의 병목 방향", selected_key, interval_name, display_period):
        compare_rows = []
        compare_metrics = FLOW
        for region in SITES.itertuples():
            cells = []
            for _, metric in compare_metrics:
                code = status(region.지역키, metric, status_col)
                cells.append(f'<td><span class="compare-state" style="color:{STATUS[code][1]}">{STATUS[code][2]}</span></td>')
            selected_cls = ' class="selected"' if region.지역키 == selected_key else ""
            compare_rows.append(f'<tr{selected_cls}><td>{escape(region.지역.replace("군", ""))}</td>' + "".join(cells) + '</tr>')
        st.markdown(
            '<table class="compare-mini"><thead><tr><th>지역</th>'
            + "".join(f'<th>{stage}</th>' for stage, _ in compare_metrics)
            + '</tr></thead><tbody>' + "".join(compare_rows) + '</tbody></table>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="measure-note">↑ 개선　→ 유지　↓ 하락　· 측정불충분</div>', unsafe_allow_html=True)

with c3:
    with detail_panel(3, "전환 퍼널", "각 단계의 지정 전후 변화", selected_key, interval_name, display_period):
        funnel_data = []
        for stage, metric in FLOW:
            funnel_data.append((stage, change(selected_key, metric, growth_col, point_col), metric, status(selected_key, metric, status_col)))
        widths = [100, 90, 80, 70, 60]
        colors = ["#DCEBFA", "#CDEBDD", "#FBE8AC", "#E5D9F6", "#FFD5B5"]
        rows = []
        comparable = []
        for (stage, val, metric, code), width, color in zip(funnel_data, widths, colors):
            text = "측정불충분" if pd.isna(val) else (f"{val:+.1f}%p" if metric == "숙박자비율_pct" else f"{val:+.1f}%")
            rows.append(
                f'<div class="funnel-row" style="width:{width}%;background:{color}"><span>{stage}</span>'
                f'<strong class="{status_class(code)}">{text}</strong></div>'
            )
            if pd.notna(val):
                comparable.append((stage, code, val))
        st.markdown('<div class="funnel">' + "".join(rows) + "</div>", unsafe_allow_html=True)
        down = [x[0] for x in comparable if x[1] == "DOWN"]
        bottleneck = "·".join(down) if down else "뚜렷한 하락 없음"
        st.markdown(
            f'<div class="funnel-note">하락 신호 · <b>{escape(bottleneck)}</b><br>±3% 기준 기술적 판정이며 단계 간 수치를 직접 비교하지 않습니다.</div>',
            unsafe_allow_html=True,
        )

# Row 2 ---------------------------------------------------------------------
c4, c5, c6 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c4:
    with detail_panel(4, "선정 전후 성장 흐름", "선정 2년 전=100 · 단계별 변화", selected_key, interval_name, display_period):
        st.plotly_chart(trend_chart(selected_key), width="stretch", config={"displayModeBar": False})
        rows = []
        for metric in ["외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "방문자대비관광소비_천원_proxy"]:
            r = growth_row(selected_key, metric)
            vals = []
            for gcol, pcol in [("g12_pct", "delta12_pctp"), ("g23_pct", "delta23_pctp"), ("g34_pct", "delta34_pctp")]:
                v = pd.to_numeric(r.get(pcol if metric.endswith("_pct") else gcol), errors="coerce") if r is not None else np.nan
                vals.append(change_text(v, metric))
            rows.append(f'<tr><td>{METRIC_LABEL[metric]}</td><td>{vals[0]}</td><td>{vals[1]}</td><td>{vals[2]}</td></tr>')
        st.markdown(
            '<table class="mini-table"><thead><tr><th>지표</th><th>선정 전</th><th>선정 첫해</th><th>선정 둘째해</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table><div class="period-key"><div>2년 전→직전</div><div>직전→첫해</div><div>첫해→둘째해</div><div>실제 관측값</div></div>',
            unsafe_allow_html=True,
        )

with c5:
    with detail_panel(5, "방문 유입", "외지인 방문 규모와 주요 출발지역", selected_key, interval_name, display_period):
        visitor_value = pd.to_numeric(latest.get("외지인방문자수"), errors="coerce")
        visitor_change = change(selected_key, "외지인방문자수", growth_col, point_col)
        origin = DATA["origin"].loc[(DATA["origin"]["지역키"].eq(selected_key)) & (DATA["origin"]["기간"].eq(display_period))].copy()
        st.markdown(
            '<div class="impact-grid">'
            f'<div class="impact-card"><small>외지인 방문</small><b>{level_text(visitor_value, "외지인방문자수")}</b></div>'
            f'<div class="impact-card"><small>{escape(interval_name)}</small><b>{change_text(visitor_change, "외지인방문자수")}</b></div>'
            f'<div class="impact-card"><small>확인된 출발지역</small><b>{origin.shape[0]:,}개</b></div></div>',
            unsafe_allow_html=True,
        )
        if origin.empty:
            st.markdown('<div class="measure-note">이 기간의 출발지역 자료는 측정불충분입니다.</div>', unsafe_allow_html=True)
        else:
            origin["출발지역"] = origin["거주지(시도)"].astype(str) + " " + origin["거주지(시군구)"].astype(str)
            top_origin = origin.nlargest(3, "비율(%)")
            origin_rows = []
            max_share = max(float(top_origin["비율(%)"].max()), 1)
            for rank, (_, row) in enumerate(top_origin.iterrows(), 1):
                share = float(row["비율(%)"])
                origin_rows.append(f'<div class="origin-row"><span class="rank">{rank}</span><div>{escape(str(row["출발지역"]))}<div class="bar-bg"><div class="bar" style="width:{share / max_share * 100:.0f}%"></div></div></div><b>{share:.1f}%</b></div>')
            st.markdown("".join(origin_rows), unsafe_allow_html=True)

with c6:
    with detail_panel(6, "숙박·체류 구조", "전환·심화·계절 안정성", selected_key, interval_name, display_period):
        env = []
        for label, metric in [
            ("숙박전환", "숙박자비율_pct"),
            ("평균숙박", "평균숙박일수"),
            ("숙박객 3박+", "숙박자중_3박이상_pct"),
            ("계절안정", "DSI"),
        ]:
            v = pd.to_numeric(latest.get(metric), errors="coerce")
            env.append(f'<div class="env-card"><small>{label}</small><b>{level_text(v, metric)}</b></div>')
        st.markdown('<div class="env-grid">' + "".join(env) + "</div>", unsafe_allow_html=True)
        facility_lookup = ALIASES.get(site["시설"], site["시설"])
        poi = DATA["poi"].loc[DATA["poi"]["시설명"].eq(facility_lookup)].copy()
        poi_order = ["숙박", "음식점", "관광지", "문화시설", "레포츠"]
        poi_map = poi.set_index("구분")["totalCount"].to_dict() if not poi.empty else {}
        nearest = DATA["nearest"].loc[DATA["nearest"]["시설명"].eq(facility_lookup)]
        near_text = "측정불충분"
        if not nearest.empty:
            nr = nearest.iloc[0]
            near_text = f"최근접 숙박 {float(nr['최근접_거리_km']):.2f}km · {nr['최근접_업체명']}"
        st.markdown('<div class="poi-grid">' + "".join(
            f'<div class="poi">{escape(kind)}<b>{int(poi_map.get(kind, 0))}</b></div>' for kind in poi_order[:4]
        ) + '</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="measure-note">계절안정=1−월별 방문 변동계수 · 반경 5km POI · {escape(near_text)}<br>주변 시설 수는 숙박환경을 설명하는 참고 정보입니다.</div>', unsafe_allow_html=True)

# Row 3 ---------------------------------------------------------------------
c7, c8, c9 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c7:
    with detail_panel(7, "병목·구조변화", "기술적 판정과 ITS 근거 분리", selected_key, interval_name, display_period):
        observed = []
        for stage, metric in FLOW:
            code = status(selected_key, metric, status_col)
            if code == "DOWN":
                observed.append((stage, change(selected_key, metric, growth_col, point_col), metric))
        observed_text = " · ".join(x[0] for x in observed) if observed else "뚜렷한 하락 없음"
        focus_metric = FOCUS_METRIC[selected_key]
        instant, instant_cls = its_evidence(selected_key, focus_metric, "즉시수준변화")
        slope, slope_cls = its_evidence(selected_key, focus_metric, "지정후기울기변화")
        st.markdown(
            f'<div class="diag-box"><div class="alert-box">±3% 하락 단계<b>{escape(observed_text)}</b></div>'
            f'<div class="reason-box"><b>ITS · {escape(METRIC_LABEL.get(focus_metric, focus_metric))}</b><br>'
            f'지정 직후 <span class="badge {instant_cls}">{escape(instant)}</span><br>'
            f'그 이후 흐름 <span class="badge {slope_cls}">{escape(slope)}</span></div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="measure-note">±3%는 방향 판정, ITS는 구조변화 탐색입니다. 대조군이 없어 지정의 인과효과로 해석하지 않습니다.</div>', unsafe_allow_html=True)

with c8:
    with st.container(border=True, height="stretch"):
        panel_head(8, "추가 검증 데이터", "병목 원인을 확인하려면 필요한 자료")
        html = []
        for number, title, reason in DATA_NEEDS[selected_key]:
            html.append(
                f'<div class="policy-row"><span class="policy-num">{number}</span><strong>{escape(title)}</strong><span>{escape(reason)}</span></div>'
            )
        st.markdown("".join(html), unsafe_allow_html=True)
        st.markdown('<div class="measure-note">추가 자료 확보 전에는 변화의 원인을 확정하지 않습니다.</div>', unsafe_allow_html=True)

with c9:
    with st.container(border=True, height="stretch"):
        panel_head(9, "데이터 신뢰도", "공간단위와 확보 수준")
        has_origin = not DATA["origin"].loc[DATA["origin"]["지역키"].eq(selected_key)].empty
        reliability = [
            ("시설 직접 성과", "시설", "추후 과제", "partial"),
            ("관심·방문", "시군구", "확보", "ok"),
            ("숙박전환·장기체류", "시군구", "확보", "ok"),
            ("방문당 소비·DSI", "시군구", "확보", "ok"),
            ("방문 출발지역", "시군구", "확보" if has_origin else "측정불충분", "ok" if has_origin else "missing"),
            ("ITS", "시군구 월별", "탐색근거", "partial"),
        ]
        table_rows = "".join(
            f'<tr><td>{escape(metric)}</td><td>{escape(unit)}</td><td><span class="badge {cls}">{state}</span></td></tr>'
            for metric, unit, state, cls in reliability
        )
        st.markdown(
            '<table class="reliability"><thead><tr><th>지표</th><th>공간단위</th><th>확보 수준</th></tr></thead><tbody>'
            + table_rows + '</tbody></table>',
            unsafe_allow_html=True,
        )

st.caption("WELL-FLOW · 관광지 선정월 기준 네 개 연간 구간 · 시설 직접 성과는 추후 과제로 남깁니다.")
