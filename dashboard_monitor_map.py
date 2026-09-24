"""Map-selectable 3x3 WELL-FLOW monitor for five wellness tourism sites."""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="WELL-FLOW Monitor · Map",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "output" / "five_sites_by_designation"
PERIODS = ["P1", "P2", "P3", "P4"]
PERIOD_SHORT = {"P1": "지정 2년 전", "P2": "지정 직전", "P3": "지정 1년차", "P4": "지정 2년차"}

SITES = pd.DataFrame(
    [
        ("전남장성", "장성군", "국립장성숲체원", "북이면", 2020, 126.751410, 35.444047, "방문·소비 회복", "체류·장기숙박 전환"),
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
    "지정 직후 P2→P3": ("P2", "P3", "g23_pct", "delta23_pctp", "지정직후_판정_3pct", "P2→P3"),
    "2년차 P3→P4": ("P3", "P4", "g34_pct", "delta34_pctp", "2년차_판정_3pct", "P3→P4"),
}
STATUS = {
    "UP": ("개선", "#138A72", "↑"),
    "FLAT": ("유지", "#B17817", "→"),
    "DOWN": ("하락", "#D9534F", "↓"),
    "NA": ("측정불충분", "#7B8794", "·"),
}

DATA_NEEDS = {
    "전남장성": [
        ("1", "시설 직접 이용", "입장·예약·프로그램 이용자 수"),
        ("2", "북이면 소비", "업종별 카드 매출과 숙박소비"),
        ("3", "전환 원인", "숙박 가격·예약전환·후기"),
    ],
    "전북무주": [
        ("1", "시설 직접 이용", "태권도원 방문·예약·체험 인원"),
        ("2", "설천면 소비", "업종별 카드 매출과 숙박소비"),
        ("3", "체류 원인", "당일·연박 목적과 이동 동선"),
    ],
    "전남완도": [
        ("1", "시설 직접 이용", "센터 예약·프로그램·재방문"),
        ("2", "소비 이동", "신지면 밖 읍면별 업종 소비"),
        ("3", "전환 원인", "체류 중 활동·결제 경로"),
    ],
    "전북순창": [
        ("1", "시설 직접 이용", "검색 이후 예약·실방문 전환"),
        ("2", "인계면 소비", "세부 업종·시간대별 소비"),
        ("3", "이탈 원인", "가격·후기·예약 단계 데이터"),
    ],
    "전북완주": [
        ("1", "시설 직접 이용", "아원고택 예약·방문·숙박 구분"),
        ("2", "소양면 소비", "업종별 카드 매출과 숙박소비"),
        ("3", "숙박 원인", "방문객 숙박지·예약·이동 동선"),
    ],
}

FOCUS_METRIC = {
    "전남장성": "평균체류시간_분",
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
    .map-guide { margin-top:.65rem; color:#667382; font-size:.65rem; }
    div[data-testid="stVerticalBlockBorderWrapper"] { border-color:#DCE4EB; border-radius:14px; background:#FFFFFF; box-shadow:0 1px 2px rgba(16,24,35,.025); }
    div[data-testid="stVerticalBlockBorderWrapper"] > div { padding:.82rem .95rem .9rem; }
    .panel-title { font-size:1rem; font-weight:780; color:#172438; margin:0; }
    .panel-sub { color:#667382; font-size:.73rem; margin:.12rem 0 .7rem; }
    .site-head { background:#F5F8FB; border:1px solid #E0E7EE; border-radius:9px; padding:.58rem .7rem; margin-bottom:.65rem; }
    .site-head strong { font-size:.94rem; }
    .site-head span { color:#667382; font-size:.72rem; margin-left:.35rem; }
    .metric-grid { display:grid; grid-template-columns:repeat(6,1fr); gap:7px; }
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
    .stPlotlyChart { margin:-.2rem 0; }
    [data-testid="stPlotlyChart"] > div { border:0 !important; }
    section[data-testid="stSidebar"] [data-baseweb="select"] > div { min-height:2.55rem; border-color:#D5DFE8; border-radius:9px; font-size:.72rem; }
    @media(max-width:1100px) { .metric-grid { grid-template-columns:repeat(3,1fr); } }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    files = {
        "kpi": DATA_DIR / "kpi_by_period.csv",
        "growth": DATA_DIR / "growth_bottleneck.csv",
        "monthly": DATA_DIR / "monthly_input.csv",
        "mobile": DATA_DIR / "spatial_mobility_only.csv",
        "origin": DATA_DIR / "mobility_origin_by_period.csv",
        "spatial": DATA_DIR / "spatial_concentration_available_sites.csv",
        "spatial_relative": DATA_DIR / "spatial_relative_growth_available_sites.csv",
        "market": DATA_DIR / "market_alignment_conditional_available_sites.csv",
        "market_legacy": DATA_DIR / "market_alignment_legacy_wanju_from_previous_p_extract.csv",
        "availability": DATA_DIR / "data_availability.csv",
        "periods": DATA_DIR / "period_definitions.csv",
        "its": DATA_DIR / "its_designation_hac3.csv",
        "its_robustness": DATA_DIR / "its_robustness.csv",
        "poi": ROOT / "output" / "geo_tourism_density.csv",
        "nearest": ROOT / "output" / "geo_nearest_lodging.csv",
        "rooms": ROOT / "output" / "geo_room_capacity.csv",
    }
    return {name: csv(path) for name, path in files.items()}


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


def local_share(region_key: str, period: str) -> tuple[float, str]:
    mobile = DATA["mobile"].loc[
        DATA["mobile"]["지역키"].eq(region_key) & DATA["mobile"]["기간"].eq(period)
    ]
    if not mobile.empty:
        return pd.to_numeric(mobile.iloc[0]["시설동_점유율_pct"], errors="coerce"), "이동통신 방문"
    spatial = DATA["spatial"].loc[
        DATA["spatial"]["지역키"].eq(region_key)
        & DATA["spatial"]["기간"].eq(period)
        & DATA["spatial"]["영역"].eq("방문")
    ]
    if not spatial.empty:
        return pd.to_numeric(spatial.iloc[0]["시설동_점유율_pct"], errors="coerce"), "읍면동 방문"
    return np.nan, "미확보"


def local_change(region_key: str, before: str, after: str) -> float:
    b, _ = local_share(region_key, before)
    a, _ = local_share(region_key, after)
    return a - b if pd.notna(a) and pd.notna(b) else np.nan


def local_detail(region_key: str, after_period: str, interval: str) -> tuple[float, float, float, str]:
    mobile = DATA["mobile"].loc[
        DATA["mobile"]["지역키"].eq(region_key) & DATA["mobile"]["기간"].eq(after_period)
    ]
    if not mobile.empty:
        row = mobile.iloc[0]
        return (
            pd.to_numeric(row["시설동_점유율_pct"], errors="coerce"),
            pd.to_numeric(row["시설동_점유율변화_pctp"], errors="coerce"),
            pd.to_numeric(row["상대집중도_RC_pctp"], errors="coerce"),
            "이동통신 방문",
        )
    growth_code = {"P2→P3": "g23", "P3→P4": "g34"}[interval]
    spatial = DATA["spatial_relative"].loc[
        DATA["spatial_relative"]["지역키"].eq(region_key)
        & DATA["spatial_relative"]["영역"].eq("방문")
        & DATA["spatial_relative"]["변화구간"].eq(growth_code)
    ]
    if spatial.empty:
        return np.nan, np.nan, np.nan, "미확보"
    row = spatial.iloc[0]
    return (
        pd.to_numeric(row["시설동_점유율_after_pct"], errors="coerce"),
        pd.to_numeric(row["시설동_점유율변화_pctp"], errors="coerce"),
        pd.to_numeric(row["상대집중도_RC_pctp"], errors="coerce"),
        "읍면동 방문분포",
    )


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
                x=PERIODS, y=index, mode="lines+markers", name=label,
                line={"color": color, "width": 2}, marker={"size": 5}, connectgaps=False,
                hovertemplate=f"{label}<br>%{{x}} · %{{y:.1f}}<extra></extra>",
            )
        )
    fig.add_hline(y=100, line_dash="dot", line_color="#AAB5C0")
    fig.update_layout(
        height=165, margin=dict(l=2, r=3, t=5, b=2), showlegend=True,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        legend=dict(orientation="h", y=1.02, x=0, font={"size": 8}),
        xaxis=dict(showgrid=False, title="", categoryorder="array", categoryarray=PERIODS),
        yaxis=dict(showgrid=True, gridcolor="#E8EDF3", title="P1=100", nticks=4),
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
    custom = points[0].get("customdata", [])
    return custom[0] if custom else None


def selection_map(selected_key: str) -> go.Figure:
    points = SITES.copy()
    points["상태"] = np.where(points["지역키"].eq(selected_key), "선택", "관광지")
    points["마커크기"] = np.where(points["지역키"].eq(selected_key), 22, 14)
    fig = px.scatter_map(
        points,
        lat="위도",
        lon="경도",
        hover_name="시설",
        hover_data={"지역": True, "시설동": True, "선정연도": True, "위도": False, "경도": False, "상태": False, "마커크기": False, "지역키": False},
        color="상태",
        size="마커크기",
        size_max=22,
        custom_data=["지역키"],
        color_discrete_map={"선택": "#E45527", "관광지": "#1287E5"},
        center={"lat": 35.35, "lon": 127.25},
        zoom=6.35,
        map_style="carto-positron",
    )
    fig.update_traces(marker={"opacity": .94}, selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": .72}})
    fig.update_layout(height=285, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, clickmode="event+select")
    return fig


if "monitor_map_site" not in st.session_state:
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
      <div class="top-meta">{escape(site['지역'])} 분석기간 · {analysis_start}–{analysis_end} · P1–P4</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="map-head"><div><b>지도에서 관광지 선택</b></div>'
    '<span>파랑 · 관광지　 주황 · 현재 선택</span></div>',
    unsafe_allow_html=True,
)
map_col, selected_col = st.columns([2.2, 1], gap="medium")
with map_col:
    event = st.plotly_chart(
        selection_map(selected_key),
        width="stretch",
        key="monitor_selection_map",
        on_select="rerun",
        selection_mode="points",
        config={"displayModeBar": False, "scrollZoom": True},
    )
    clicked_key = selected_from_map(event)
    if clicked_key and clicked_key != selected_key:
        st.session_state.monitor_map_site = clicked_key
        st.rerun()
with selected_col:
    with st.container(border=True):
        st.markdown(
            f'<div class="map-selection"><div class="place">SELECTED SITE</div><h2>{escape(site["시설"])}</h2>'
            f'<div class="location">{escape(site["지역"])} · {escape(site["시설동"])} · {int(site["선정연도"])}년 지정</div>'
            f'<div class="diagnosis"><b>분석 가설</b><br>{escape(site["진단"])}<br><br><b>측정 범위</b><br>시설동 방문 · 시군구 전환성과</div>'
            '<div class="map-guide">성과는 시설 소재 읍면동·시군구 자료를 사용합니다.</div></div>',
            unsafe_allow_html=True,
        )

ctl1, ctl2, ctl3 = st.columns([1.1, 1.1, 4])
with ctl1:
    interval_name = st.selectbox("변화 구간", list(INTERVALS), label_visibility="collapsed")
with ctl2:
    display_period = st.selectbox("표시 기간", PERIODS, index=3, format_func=lambda x: f"{x} · {PERIOD_SHORT[x]}", label_visibility="collapsed")
with ctl3:
    period_caption = " · ".join(
        f"{period} {month_text(site_periods.loc[period, '시작월'])}–{month_text(site_periods.loc[period, '종료월'])}"
        for period in PERIODS
    )
    st.caption(period_caption)

before, after, growth_col, point_col, status_col, interval_code = INTERVALS[interval_name]
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
    with st.container(border=True):
        panel_head(1, "성과 한눈에", "현재 수준·변화·핵심 진단")
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
        ls, _ = local_share(selected_key, display_period)
        lc = local_change(selected_key, before, after)
        local_cls = "good" if lc >= 0 else "bad" if pd.notna(lc) else "muted"
        cards.append(
            f'<div class="metric-mini"><small>지역파급</small><b>{ls:.1f}%</b>'
            f'<em class="{local_cls}">{lc:+.1f}%p</em></div>' if pd.notna(ls) and pd.notna(lc)
            else '<div class="metric-mini"><small>지역파급</small><b>자료 없음</b><em class="muted">측정불충분</em></div>'
        )
        st.markdown('<div class="metric-grid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
        st.markdown(f'<div class="headline-diagnosis"><b>한 문장 진단</b><br>{escape(diagnosis_text)}</div>', unsafe_allow_html=True)

with c2:
    with st.container(border=True):
        panel_head(2, "5개 관광지 비교", "같은 상대시점의 병목 방향")
        compare_rows = []
        compare_metrics = FLOW[1:]
        for region in SITES.itertuples():
            cells = []
            for _, metric in compare_metrics:
                code = status(region.지역키, metric, status_col)
                cells.append(f'<td><span class="compare-state" style="color:{STATUS[code][1]}">{STATUS[code][2]}</span></td>')
            _, delta, _, _ = local_detail(region.지역키, after, interval_code)
            local_code = "NA" if pd.isna(delta) else "UP" if delta >= 3 else "DOWN" if delta <= -3 else "FLAT"
            cells.append(f'<td><span class="compare-state" style="color:{STATUS[local_code][1]}">{STATUS[local_code][2]}</span></td>')
            selected_cls = ' class="selected"' if region.지역키 == selected_key else ""
            compare_rows.append(f'<tr{selected_cls}><td>{escape(region.지역.replace("군", ""))}</td>' + "".join(cells) + '</tr>')
        st.markdown(
            '<table class="compare-mini"><thead><tr><th>지역</th>'
            + "".join(f'<th>{stage}</th>' for stage, _ in compare_metrics)
            + '<th>파급</th></tr></thead><tbody>' + "".join(compare_rows) + '</tbody></table>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="measure-note">↑ 개선　→ 유지　↓ 하락　· 측정불충분</div>', unsafe_allow_html=True)

with c3:
    with st.container(border=True):
        panel_head(3, "전환 퍼널", "각 단계의 지정 전후 변화")
        funnel_data = []
        for stage, metric in FLOW:
            funnel_data.append((stage, change(selected_key, metric, growth_col, point_col), metric, status(selected_key, metric, status_col)))
        lc = local_change(selected_key, before, after)
        local_code = "NA" if pd.isna(lc) else "UP" if lc >= 3 else "DOWN" if lc <= -3 else "FLAT"
        funnel_data.append(("지역파급", lc, "local_pct", local_code))
        widths = [100, 91, 82, 73, 64, 55]
        colors = ["#DCEBFA", "#CDEBDD", "#FBE8AC", "#E5D9F6", "#FFD5B5", "#D7E6F5"]
        rows = []
        comparable = []
        for (stage, val, metric, code), width, color in zip(funnel_data, widths, colors):
            text = "측정불충분" if pd.isna(val) else (f"{val:+.1f}%p" if metric in {"숙박자비율_pct", "local_pct"} else f"{val:+.1f}%")
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
    with st.container(border=True):
        panel_head(4, "g0·g1·g2 성장궤적", "P1=100 전환지표 변화")
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
            '<table class="mini-table"><thead><tr><th>지표</th><th>g0</th><th>g1</th><th>g2</th></tr></thead><tbody>'
            + "".join(rows) + '</tbody></table><div class="period-key"><div>g0<br>P1→P2</div><div>g1<br>P2→P3</div><div>g2<br>P3→P4</div><div>점선 없이<br>실측만</div></div>',
            unsafe_allow_html=True,
        )

with c5:
    with st.container(border=True):
        panel_head(5, "시설동 파급", "점유율·점유율 변화·시군구 대비 성장")
        impact_share, impact_delta, impact_rc, impact_source = local_detail(selected_key, after, interval_code)

        def impact_text(value: float, suffix: str, signed: bool = True) -> str:
            if pd.isna(value):
                return "측정불충분"
            return f"{value:+.1f}{suffix}" if signed else f"{value:.1f}{suffix}"

        st.markdown(
            '<div class="impact-grid">'
            f'<div class="impact-card"><small>{escape(site["시설동"])} 방문 비중</small><b>{impact_text(impact_share, "%", False)}</b></div>'
            f'<div class="impact-card"><small>점유율 변화</small><b>{impact_text(impact_delta, "%p")}</b></div>'
            f'<div class="impact-card"><small>시군구 대비 성장</small><b>{impact_text(impact_rc, "%p")}</b></div></div>',
            unsafe_allow_html=True,
        )
        growth_code = {"P2→P3": "g23", "P3→P4": "g34"}[interval_code]
        spend_spatial = DATA["spatial_relative"].loc[
            DATA["spatial_relative"]["지역키"].eq(selected_key)
            & DATA["spatial_relative"]["영역"].eq("소비")
            & DATA["spatial_relative"]["변화구간"].eq(growth_code)
        ]
        if not spend_spatial.empty:
            spend_row = spend_spatial.iloc[0]
            spend_note = f"시설동 소비 점유율 {float(spend_row['시설동_점유율변화_pctp']):+.1f}%p · 시군구 대비 소비성장 {float(spend_row['상대집중도_RC_pctp']):+.1f}%p"
        else:
            spend_note = "시설동 소비파급 측정불충분"
        st.markdown(
            f'<div class="measure-note">{escape(impact_source)} 기준<br>{escape(spend_note)}</div>',
            unsafe_allow_html=True,
        )
        st.caption("시설동 점유율은 시설 직접 방문율이 아닙니다.")

with c6:
    with st.container(border=True):
        panel_head(6, "숙박·체류 구조", "전환·심화·계절 안정성")
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
        st.markdown(f'<div class="measure-note">계절안정=1−월별 방문 변동계수 · 반경 5km POI · {escape(near_text)}<br>시설동 숙박소비는 측정불충분</div>', unsafe_allow_html=True)

# Row 3 ---------------------------------------------------------------------
c7, c8, c9 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c7:
    with st.container(border=True):
        panel_head(7, "병목·구조변화", "기술적 판정과 ITS 근거 분리")
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
    with st.container(border=True):
        panel_head(8, "추가 검증 데이터", "병목 원인을 확인하려면 필요한 자료")
        html = []
        for number, title, reason in DATA_NEEDS[selected_key]:
            html.append(
                f'<div class="policy-row"><span class="policy-num">{number}</span><strong>{escape(title)}</strong><span>{escape(reason)}</span></div>'
            )
        st.markdown("".join(html), unsafe_allow_html=True)
        st.markdown('<div class="measure-note">추가 자료 확보 전에는 원인과 지원방향을 확정하지 않습니다.</div>', unsafe_allow_html=True)

with c9:
    with st.container(border=True):
        panel_head(9, "데이터 신뢰도", "공간단위와 확보 수준")
        has_origin = not DATA["origin"].loc[DATA["origin"]["지역키"].eq(selected_key)].empty
        has_spatial_spend = selected_key in {"전남완도", "전북순창"}
        jangseong_lodging_limit = selected_key == "전남장성"
        reliability = [
            ("시설 직접 성과", "시설", "측정불충분", "missing"),
            ("관심·방문", "시군구", "확보", "ok"),
            ("숙박전환·장기체류", "시군구", "부분확보" if jangseong_lodging_limit else "확보", "partial" if jangseong_lodging_limit else "ok"),
            ("방문당 소비·DSI", "시군구", "확보", "ok"),
            ("시설동 방문파급", "읍면동", "확보", "ok"),
            ("소비 공간파급", "시설동", "확보" if has_spatial_spend else "측정불충분", "ok" if has_spatial_spend else "missing"),
            ("출발지역", "시군구", "확보" if has_origin else "측정불충분", "ok" if has_origin else "missing"),
            ("WSPI·비교시장", "독립 benchmark", "측정불충분", "missing"),
            ("ITS", "시군구 월별", "탐색근거", "partial"),
        ]
        table_rows = "".join(
            f'<tr><td>{escape(metric)}</td><td>{escape(unit)}</td><td><span class="badge {cls}">{state}</span></td></tr>'
            for metric, unit, state, cls in reliability
        )
        st.markdown(
            '<table class="reliability"><thead><tr><th>지표</th><th>공간단위</th><th>확보 수준</th></tr></thead><tbody>'
            + table_rows + '</tbody></table><div class="measure-note"><b>측정불충분도 분석 결과입니다.</b> 없는 자료를 낮은 성과로 처리하지 않습니다.</div>',
            unsafe_allow_html=True,
        )

st.caption("WELL-FLOW · 지정연도 기준 연간 구간(P1–P4) · 시설 성과로 직접 해석할 때는 공간단위를 반드시 확인하세요.")
