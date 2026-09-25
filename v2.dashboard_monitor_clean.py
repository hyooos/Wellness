"""Readable 3x3 WELL-FLOW monitor for four wellness tourism sites."""

from __future__ import annotations

from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="WELL-FLOW Monitor · Clean",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "output" / "four_sites_by_designation"
PERIODS = ["P1", "P2", "P3", "P4"]
PERIOD_SHORT = {"P1": "지정 2년 전", "P2": "지정 직전", "P3": "지정 1년차", "P4": "지정 2년차"}

SITES = pd.DataFrame(
    [
        ("전북무주", "무주군", "태권도원 상징지구", "설천면", 2022, "유입 성장, 체류 정체", "숙박일수·장기체류 확대"),
        ("전남완도", "완도군", "완도 해양치유센터", "신지면", 2024, "긴 체류, 소비·계절성 약세", "체험소비·지역 확산"),
        ("전북순창", "순창군", "쉴랜드", "인계면", 2024, "관심 대비 전환 약세", "방문·숙박·소비 전환"),
        ("전북완주", "완주군", "아원고택", "소양면", 2024, "방문 대비 숙박 약세", "숙박 연계·체류 콘텐츠"),
    ],
    columns=["지역키", "지역", "시설", "시설동", "선정연도", "진단", "과제"],
)

ALIASES = {"쉴랜드": "쉴(SHIL)랜드"}
FLOW = [
    ("관심", "숙박검색건수"),
    ("방문", "외지인방문자수"),
    ("숙박·체류", "숙박자비율_pct"),
    ("소비", "내국인관광소비_천원"),
]
METRIC_LABEL = {
    "숙박검색건수": "숙박 관심",
    "외지인방문자수": "외지인 방문",
    "숙박자비율_pct": "숙박 비율",
    "평균체류시간_분": "평균 체류",
    "평균숙박일수": "평균 숙박일",
    "내국인관광소비_천원": "관광 소비",
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

POLICIES = {
    "전북무주": [
        ("1", "숙박일수 확대", "태권도·자연 체험을 2일 이상 코스로 구성"),
        ("2", "비수기 체류", "계절별 실내 프로그램으로 체류 편차 완화"),
        ("3", "소비자료 확보", "설천면 카드 매출로 방문의 소비 전환 검증"),
    ],
    "전남완도": [
        ("1", "체험소비 연결", "긴 체류를 치유·식음·쇼핑 소비로 연결"),
        ("2", "지역 확산", "신지면 밖 상권과 연계 코스 구성"),
        ("3", "비수기 상품", "계절 편차를 줄이는 상시 프로그램 강화"),
    ],
    "전북순창": [
        ("1", "방문 전환", "검색 이후 예약·방문 경로를 단순화"),
        ("2", "숙박 패키지", "쉴랜드와 인근 숙박·식음을 묶어 판매"),
        ("3", "반복 측정", "지정 2년차 이후 전환 회복 여부 확인"),
    ],
    "전북완주": [
        ("1", "숙박 연계", "아원고택 방문객을 소양면 숙박으로 연결"),
        ("2", "야간 콘텐츠", "숙박 동기가 되는 저녁 프로그램 보강"),
        ("3", "소비자료 확보", "소양면 카드 매출로 실제 파급 확인"),
    ],
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
    .origin-row { display:grid; grid-template-columns:22px 1fr 42px; gap:7px; align-items:center; margin:.36rem 0; font-size:.7rem; }
    .rank { width:20px; height:20px; border-radius:50%; display:grid; place-items:center; background:#E6EEF8; color:#245B99; font-weight:800; }
    .bar-bg { height:6px; background:#E9EEF4; border-radius:5px; overflow:hidden; margin-top:2px; }
    .bar { height:100%; background:#327ABD; border-radius:5px; }
    .env-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:5px; }
    .env-card { border:1px solid #DEE6EF; border-radius:6px; padding:.38rem; text-align:center; }
    .env-card small { display:block; color:#69798E; font-size:.63rem; }
    .env-card b { font-size:.82rem; }
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
        "market": DATA_DIR / "market_alignment_conditional_available_sites.csv",
        "availability": DATA_DIR / "data_availability.csv",
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
    if metric == "숙박자비율_pct":
        return f"{value:.1f}%"
    if metric == "평균체류시간_분":
        return f"{value / 60:.1f}시간"
    if metric == "평균숙박일수":
        return f"{value:.2f}일"
    if metric == "내국인관광소비_천원":
        return f"{value / 100_000:.1f}억원"
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


def status_class(code: str) -> str:
    return {"UP": "good", "DOWN": "bad", "FLAT": "flat"}.get(code, "muted")


def panel_head(number: int, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="panel-title">{number}. {escape(title)}</div><div class="panel-sub">{escape(subtitle)}</div>',
        unsafe_allow_html=True,
    )


def trend_chart(region_key: str) -> go.Figure:
    frame = DATA["monthly"].loc[DATA["monthly"]["지역키"].eq(region_key)].copy()
    frame["날짜"] = pd.to_datetime(frame["기준년월"].astype(str), format="%Y%m")
    fig = go.Figure()
    colors = {"P1": "#A9B8C8", "P2": "#7395BA", "P3": "#2F77B9", "P4": "#0B4E8A"}
    for period in PERIODS:
        part = frame.loc[frame["기간"].eq(period)].sort_values("날짜")
        fig.add_trace(
            go.Scatter(
                x=part["날짜"], y=part["외지인방문자수"], mode="lines",
                name=period, line={"color": colors[period], "width": 2},
                hovertemplate="%{x|%Y-%m}<br>%{y:,.0f}명<extra></extra>",
            )
        )
    fig.update_layout(
        height=150, margin=dict(l=2, r=3, t=4, b=2), showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        xaxis=dict(showgrid=False, title="", tickformat="%y.%m", nticks=5),
        yaxis=dict(showgrid=True, gridcolor="#E8EDF3", title="", tickformat="~s", nticks=4),
        font=dict(family="Pretendard", size=9, color="#52647A"),
    )
    return fig


with st.sidebar:
    st.markdown('<div class="sidebar-title">시설 선택</div><div class="sidebar-note">4개 웰니스 관광지</div>', unsafe_allow_html=True)
    if "monitor_site" not in st.session_state:
        st.session_state.monitor_site = SITES.iloc[0]["지역키"]
    site_labels = {
        r.지역키: f"{r.지역.replace('군', '')} · {r.시설}" for r in SITES.itertuples()
    }
    selected_key = st.selectbox(
        "관광지",
        SITES["지역키"].tolist(),
        key="monitor_site",
        format_func=lambda value: site_labels[value],
        label_visibility="collapsed",
    )
    site = SITES.loc[SITES["지역키"].eq(selected_key)].iloc[0]
    st.markdown(
        f'<div class="selected-site"><b>{escape(site["시설"])}</b><br>{escape(site["지역"])} · {escape(site["시설동"])}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("분석 기준"):
        st.caption("시설 소재 읍면동·시군구 자료를 사용하며, 없는 값은 측정불충분으로 표시합니다.")

st.markdown(
    f"""
    <div class="topbar">
      <div class="brand"><strong>WELL-FLOW <span>Monitor</span></strong><span>웰니스 관광지 성과 진단</span></div>
      <div class="top-meta">분석기간 · 지정연도 기준 4월~다음 해 3월 · P1–P4</div>
    </div>
    """,
    unsafe_allow_html=True,
)

ctl1, ctl2, ctl3 = st.columns([1.1, 1.1, 4])
with ctl1:
    interval_name = st.selectbox("변화 구간", list(INTERVALS), label_visibility="collapsed")
with ctl2:
    display_period = st.selectbox("표시 기간", PERIODS, index=3, format_func=lambda x: f"{x} · {PERIOD_SHORT[x]}", label_visibility="collapsed")
with ctl3:
    st.caption("P1 지정 2년 전 · P2 지정 직전 · P3 지정 1년차 · P4 지정 2년차")

before, after, growth_col, point_col, status_col, interval_code = INTERVALS[interval_name]
kpi_site = DATA["kpi"].loc[DATA["kpi"]["지역키"].eq(selected_key)].set_index("기간")
latest = kpi_site.loc[display_period]

# Row 1 ---------------------------------------------------------------------
c1, c2, c3 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c1:
    with st.container(border=True):
        panel_head(1, "WELL-FLOW Monitor", "전환성과와 핵심 병목")
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
        stage_codes = [(s, status(selected_key, m, status_col)) for s, m in FLOW]
        downs = [s for s, code in stage_codes if code == "DOWN"]
        summary = " → ".join(downs[:2]) + " 단계 점검" if downs else site["진단"]
        st.markdown(f'<div class="flow-summary"><b>주요 병목</b> · {escape(summary)}</div>', unsafe_allow_html=True)

with c2:
    with st.container(border=True):
        panel_head(2, "3층 성과 진단", "시설 → 소재 읍면동 → 시군구")
        share, share_source = local_share(selected_key, display_period)
        dong_spend = selected_key in {"전남완도", "전북순창"}
        layers = [
            ("시설 수준", "직접 방문·매출 자료 없음", "측정불충분", "missing"),
            (
                f"소재 행정동 · {site['시설동']}",
                f"방문 비중 {share:.1f}% · 소비 {'확보' if dong_spend else '미확보'}" if pd.notna(share) else "방문·소비 미확보",
                "부분확보" if pd.notna(share) else "측정불충분",
                "partial" if pd.notna(share) else "missing",
            ),
            ("시군구 수준", "방문·숙박·소비 지표", "확보", "ok"),
        ]
        for name, detail, badge, cls in layers:
            st.markdown(
                f'<div class="layer"><div><div class="layer-name">{escape(name)}</div><div class="layer-detail">{escape(detail)}</div></div>'
                f'<span class="badge {cls}">{badge}</span></div>', unsafe_allow_html=True,
            )
        st.markdown(
            f'<div class="measure-note">현재 성과 해석의 기준은 <b>{escape(share_source)}</b>과 시군구 지표입니다.</div>',
            unsafe_allow_html=True,
        )

with c3:
    with st.container(border=True):
        panel_head(3, "전환 퍼널", "각 단계의 지정 전후 변화")
        funnel_data = []
        for stage, metric in FLOW:
            funnel_data.append((stage, change(selected_key, metric, growth_col, point_col), metric, status(selected_key, metric, status_col)))
        lc = local_change(selected_key, before, after)
        local_code = "NA" if pd.isna(lc) else "UP" if lc >= 3 else "DOWN" if lc <= -3 else "FLAT"
        funnel_data.append(("지역파급", lc, "local_pct", local_code))
        widths = [100, 88, 76, 64, 52]
        colors = ["#DCEBFA", "#CDEBDD", "#FBE8AC", "#FFD5B5", "#DCD1F3"]
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
        down = [x for x in comparable if x[1] == "DOWN"]
        bottleneck = min(down, key=lambda x: x[2])[0] if down else "뚜렷한 하락 없음"
        st.markdown(
            f'<div class="funnel-note">우선 점검 · <b>{escape(bottleneck)}</b><br>서로 다른 단위이므로 단계 간 전환율로 나누지 않습니다.</div>',
            unsafe_allow_html=True,
        )

# Row 2 ---------------------------------------------------------------------
c4, c5, c6 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c4:
    with st.container(border=True):
        panel_head(4, "g0·g1·g2 성장궤적", "지정 전후 외지인 방문 추세")
        st.plotly_chart(trend_chart(selected_key), width="stretch", config={"displayModeBar": False})
        rows = []
        for metric in ["외지인방문자수", "숙박검색건수", "숙박자비율_pct"]:
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
        panel_head(5, "방문거리·유입시장", "출발지역과 시장 일치도")
        origins = DATA["origin"].loc[
            DATA["origin"]["지역키"].eq(selected_key) & DATA["origin"]["기간"].eq(display_period)
        ].copy()
        if not origins.empty:
            origins["비율(%)"] = pd.to_numeric(origins["비율(%)"], errors="coerce")
            origins = origins.sort_values("비율(%)", ascending=False).head(5)
            maxv = origins["비율(%)"].max()
            html = []
            for i, (_, r) in enumerate(origins.iterrows(), 1):
                place = str(r["거주지(시군구)"])
                province = str(r["거주지(시도)"])
                value = float(r["비율(%)"])
                html.append(
                    f'<div class="origin-row"><span class="rank">{i}</span><div>{escape(province)} {escape(place)}'
                    f'<div class="bar-bg"><div class="bar" style="width:{value / maxv * 100:.0f}%"></div></div></div><b>{value:.1f}%</b></div>'
                )
            st.markdown("".join(html), unsafe_allow_html=True)
            st.markdown('<div class="measure-note">이동통신 거주지 기준 · 거리구간은 원자료 미확보</div>', unsafe_allow_html=True)
        else:
            market = DATA["market"]
            m = market.loc[market["지역키"].eq(selected_key) & market["기간"].eq(display_period)]
            if not m.empty:
                rho = float(m.iloc[0]["조건부_Spearman_rho"])
                jsd = float(m.iloc[0]["조건부_JSD_base2"])
                st.metric("검색·방문 순위 일치", f"{rho:.2f}")
                st.metric("시장 구성 차이", f"{jsd:.3f}")
                st.markdown('<div class="measure-note">조건부 프록시입니다. 출발지역·거리분포는 측정불충분입니다.</div>', unsafe_allow_html=True)
            else:
                st.info("출발지역과 거리분포 자료가 없어 측정불충분입니다.")

with c6:
    with st.container(border=True):
        panel_head(6, "숙박·체류환경", "성과지표와 시설 주변 환경")
        env = []
        for label, metric in [("숙박검색", "숙박검색건수"), ("숙박비율", "숙박자비율_pct"), ("숙박일수", "평균숙박일수")]:
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
        st.markdown(f'<div class="measure-note">반경 5km 관광 POI · {escape(near_text)}<br>시설동 숙박소비는 측정불충분</div>', unsafe_allow_html=True)

# Row 3 ---------------------------------------------------------------------
c7, c8, c9 = st.columns([1.05, 1.05, 1.15], gap="medium")
with c7:
    with st.container(border=True):
        panel_head(7, "병목 진단", "관측된 병목과 원인 후보")
        observed = []
        for stage, metric in FLOW:
            code = status(selected_key, metric, status_col)
            if code == "DOWN":
                observed.append((stage, change(selected_key, metric, growth_col, point_col), metric))
        if observed:
            worst = min(observed, key=lambda x: x[1])
            worst_text = f"{worst[0]} {change_text(worst[1], worst[2])}"
        else:
            worst_text = "뚜렷한 하락 없음"
        reason_map = {
            "전북무주": "당일 방문 비중, 비수기 체류 콘텐츠 부족",
            "전남완도": "체류가 지역 상권 소비로 이어지는 경로 부족",
            "전북순창": "검색 이후 예약·방문 동선의 이탈 가능성",
            "전북완주": "인근 숙박 연결과 야간 콘텐츠 부족 가능성",
        }
        st.markdown(
            f'<div class="diag-box"><div class="alert-box">확인된 병목<b>{escape(worst_text)}</b></div>'
            f'<div class="reason-box"><b>추가 검증할 원인</b><br>• {escape(reason_map[selected_key])}<br>• 가격·후기·예약 전환 자료 필요</div></div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="measure-note">현재 자료는 병목 위치를 보여주며 원인을 인과적으로 확정하지 않습니다.</div>', unsafe_allow_html=True)

with c8:
    with st.container(border=True):
        panel_head(8, "정책 추천", "병목에 맞춘 지원 우선순위")
        html = []
        for number, title, reason in POLICIES[selected_key]:
            html.append(
                f'<div class="policy-row"><span class="policy-num">{number}</span><strong>{escape(title)}</strong><span>{escape(reason)}</span></div>'
            )
        st.markdown("".join(html), unsafe_allow_html=True)
        st.markdown(f'<div class="measure-note">우선 과제 · <b>{escape(site["과제"])}</b></div>', unsafe_allow_html=True)

with c9:
    with st.container(border=True):
        panel_head(9, "데이터 신뢰도", "공간단위와 확보 수준")
        has_origin = not DATA["origin"].loc[DATA["origin"]["지역키"].eq(selected_key)].empty
        has_spatial_spend = selected_key in {"전남완도", "전북순창"}
        reliability = [
            ("시설 직접 성과", "시설", "측정불충분", "missing"),
            ("방문", "시설동/시군구", "확보", "ok"),
            ("숙박·체류", "시군구", "확보", "ok"),
            ("관광소비", "시군구", "확보", "ok"),
            ("소비 공간파급", "시설동", "확보" if has_spatial_spend else "측정불충분", "ok" if has_spatial_spend else "missing"),
            ("출발지역", "시군구", "확보" if has_origin else "측정불충분", "ok" if has_origin else "missing"),
            ("인과효과", "시군구", "측정불충분", "missing"),
        ]
        table_rows = "".join(
            f'<tr><td>{escape(metric)}</td><td>{escape(unit)}</td><td><span class="badge {cls}">{state}</span></td></tr>'
            for metric, unit, state, cls in reliability
        )
        st.markdown(
            '<table class="reliability"><thead><tr><th>지표</th><th>공간단위</th><th>확보 수준</th></tr></thead><tbody>'
            + table_rows + '</tbody></table><div class="measure-note"><b>측정불충분도 정책 결과입니다.</b> 추가 수집 대상을 명확히 보여줍니다.</div>',
            unsafe_allow_html=True,
        )

st.caption("WELL-FLOW · 지정연도 기준 연간 구간(P1–P4) · 시설 성과로 직접 해석할 때는 공간단위를 반드시 확인하세요.")
