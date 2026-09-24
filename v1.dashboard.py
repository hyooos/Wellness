"""WELL-FLOW: five-site wellness tourism performance dashboard."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="WELL-FLOW | 웰니스 관광 성과",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "output" / "five_sites_by_designation"

PERIODS = ["P1", "P2", "P3", "P4"]
PERIOD_LABELS = {
    "P1": "지정 2년 전",
    "P2": "지정 직전",
    "P3": "지정 1년차",
    "P4": "지정 2년차",
}
INTERVALS = {
    "지정 직후 · P2→P3": {
        "before": "P2",
        "after": "P3",
        "growth": "g23_pct",
        "point": "delta23_pctp",
        "status": "지정직후_판정_3pct",
        "category": "P2→P3",
        "spatial": "P2→P3",
        "relative": "g23",
    },
    "2년차 변화 · P3→P4": {
        "before": "P3",
        "after": "P4",
        "growth": "g34_pct",
        "point": "delta34_pctp",
        "status": "2년차_판정_3pct",
        "category": "P3→P4",
        "spatial": "P3→P4",
        "relative": "g34",
    },
}

FLOW_METRICS = [
    ("관심", "숙박검색건수"),
    ("방문", "외지인방문자수"),
    ("숙박", "숙박자비율_pct"),
    ("체류", "평균체류시간_분"),
    ("소비", "내국인관광소비_천원"),
]
METRIC_NAMES = {
    "숙박검색건수": "숙박 관심",
    "외지인방문자수": "외지인 방문",
    "전체방문자수": "전체 방문",
    "숙박자비율_pct": "숙박 전환",
    "평균체류시간_분": "평균 체류시간",
    "평균숙박일수": "평균 숙박일수",
    "내국인관광소비_천원": "관광소비",
    "숙박자중_3박이상_pct": "숙박객 장기체류",
    "전체순방문자중_3박이상_pct": "전체 장기체류",
    "방문자대비관광소비_천원_proxy": "방문 대비 소비",
    "DSI": "계절 안정성",
}
STATUS_LABEL = {"UP": "개선", "FLAT": "유지", "DOWN": "악화", "NA": "자료 제한"}
STATUS_SYMBOL = {"UP": "↑", "FLAT": "→", "DOWN": "↓", "NA": "·"}
STATUS_COLOR = {"UP": "#0F766E", "FLAT": "#A16207", "DOWN": "#B64646", "NA": "#8A929E"}
STATUS_SCORE = {"DOWN": -1, "FLAT": 0, "UP": 1, "NA": np.nan}

POLICY_FOCUS = {
    "전북무주": ("유입 성장, 체류 정체", "숙박일수·장기체류 확대"),
    "전남완도": ("긴 체류, 소비·계절성 약세", "체험소비·지역 확산"),
    "전북순창": ("관심 대비 전환 약세", "방문·숙박·소비 전환"),
    "전북완주": ("방문 대비 숙박 약세", "숙박 연계·체류 콘텐츠"),
}


st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');
    html, body, [class*="css"] {
        font-family: 'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, sans-serif;
        letter-spacing: -0.018em;
    }
    .stApp { background: #F6F7F6; color: #171C1A; }
    [data-testid="stHeader"] { background: rgba(246,247,246,.9); }
    .block-container { max-width: 1380px; padding-top: 1.1rem; padding-bottom: 2.5rem; }
    .hero {
        padding: 1.7rem 1.8rem; border-radius: 14px;
        background: #FFFFFF; color: #151A18;
        border: 1px solid #E1E5E3; margin-bottom: .8rem;
    }
    .hero-kicker { color:#0F766E; font-weight:700; letter-spacing:.09em; font-size:.7rem; }
    .hero h1 { margin:.28rem 0 .25rem; font-size:2rem; line-height:1.16; letter-spacing:-.04em; }
    .hero p { margin:0; color:#67706C; font-size:.92rem; }
    .region-card, .insight-card {
        background:#FFFFFF; border:1px solid #E1E5E3; border-radius:12px;
        padding:.95rem 1rem; min-height:170px;
    }
    .region-name { font-size:1rem; font-weight:750; color:#171C1A; }
    .facility { color:#7A837F; font-size:.75rem; margin:.15rem 0 .65rem; min-height:2.1em; }
    .stage-row { display:flex; justify-content:space-between; padding:.2rem 0; border-bottom:1px solid #F0F2F1; font-size:.88rem; }
    .diagnosis { margin-top:.62rem; color:#4A5550; font-size:.78rem; line-height:1.4; }
    .eyebrow { color:#727B77; font-size:.72rem; font-weight:650; letter-spacing:.02em; }
    .big-number { font-size:1.6rem; font-weight:750; color:#171C1A; margin:.12rem 0; }
    .soft-note { color:#707975; font-size:.8rem; line-height:1.45; }
    .callout { background:#EEF3F1; border-left:3px solid #0F766E; padding:.85rem 1rem; border-radius:4px 10px 10px 4px; }
    .evidence-strong { color:#0F766E; font-weight:650; }
    .evidence-mid { color:#A16207; font-weight:650; }
    .evidence-weak { color:#747C79; font-weight:650; }
    [data-testid="stMetric"] { background:white; border:1px solid #E1E5E3; padding:.9rem; border-radius:12px; }
    [data-testid="stMetricLabel"] { color:#626B67; }
    [data-testid="stTabs"] button { font-weight:650; }
    .stPlotlyChart { background:white; border-radius:12px; padding:.25rem; border:1px solid #E5E8E6; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, encoding="utf-8-sig")


@st.cache_data
def load_data() -> dict[str, pd.DataFrame]:
    names = [
        "growth_bottleneck.csv",
        "kpi_by_period.csv",
        "its_designation_hac3.csv",
        "its_robustness.csv",
        "category_change.csv",
        "data_availability.csv",
        "not_computable_status.csv",
        "period_definitions.csv",
        "market_alignment_conditional_available_sites.csv",
        "market_alignment_legacy_wanju_from_previous_p_extract.csv",
        "spatial_concentration_available_sites.csv",
        "spatial_change_available_sites.csv",
        "spatial_relative_growth_available_sites.csv",
        "spatial_legacy_wanju_from_previous_p_extract.csv",
        "spatial_mobility_only.csv",
        "mobility_origin_by_period.csv",
    ]
    return {name.removesuffix(".csv"): load_csv(name) for name in names}


DATA = load_data()
GROWTH = DATA["growth_bottleneck"]
KPI = DATA["kpi_by_period"]
INCLUDED_REGION_KEYS = ["전북무주", "전남완도", "전북순창", "전북완주"]
REGIONS = (
    KPI.loc[KPI["지역키"].isin(INCLUDED_REGION_KEYS), ["지역키", "지역", "시설", "최초선정연도"]]
    .drop_duplicates()
    .sort_values(["최초선정연도", "지역"])
    .reset_index(drop=True)
)
REGION_KEYS = REGIONS["지역키"].tolist()
REGION_LABEL = {
    row.지역키: f"{row.지역.replace('군', '')} · {row.시설}" for row in REGIONS.itertuples()
}


def region_meta(region_key: str) -> pd.Series:
    return REGIONS.loc[REGIONS["지역키"].eq(region_key)].iloc[0]


def clean_status(value: object) -> str:
    value = str(value) if pd.notna(value) else "NA"
    return value if value in STATUS_LABEL else "NA"


def growth_row(region_key: str, metric: str) -> pd.Series | None:
    rows = GROWTH.loc[GROWTH["지역키"].eq(region_key) & GROWTH["지표"].eq(metric)]
    return None if rows.empty else rows.iloc[0]


def change_value(row: pd.Series | None, interval: dict[str, str], metric: str) -> float:
    if row is None:
        return np.nan
    column = interval["point"] if metric.endswith("_pct") else interval["growth"]
    return pd.to_numeric(row.get(column), errors="coerce")


def format_change(value: float, metric: str) -> str:
    if pd.isna(value):
        return "자료 제한"
    suffix = "%p" if metric.endswith("_pct") else "%"
    return f"{value:+,.1f}{suffix}"


def format_level(value: float, metric: str) -> str:
    if pd.isna(value):
        return "자료 없음"
    if metric in {"숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct"}:
        return f"{value:,.1f}%"
    if metric == "평균체류시간_분":
        return f"{value / 60:,.1f}시간"
    if metric == "평균숙박일수":
        return f"{value:,.2f}일"
    if metric == "내국인관광소비_천원":
        return f"{value / 100_000:,.1f}억원"
    if metric == "DSI":
        return f"{value:.3f}"
    return f"{value:,.0f}"


def status_for(region_key: str, metric: str, interval: dict[str, str]) -> str:
    row = growth_row(region_key, metric)
    return "NA" if row is None else clean_status(row.get(interval["status"]))


def stage_sentence(region_key: str, interval: dict[str, str]) -> str:
    parts = []
    for stage, metric in FLOW_METRICS:
        status = status_for(region_key, metric, interval)
        if status != "NA":
            parts.append((stage, status))
    down = [stage for stage, status in parts if status == "DOWN"]
    up = [stage for stage, status in parts if status == "UP"]
    if down:
        subject = "·".join(down[:2])
        return f"{subject} 점검"
    if up:
        return f"{'·'.join(up[:2])} 개선"
    return "큰 변화 없음"


def chart_layout(fig: go.Figure, height: int = 400) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=50, b=25),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="#FFFFFF",
        font=dict(family="Pretendard Variable, Pretendard, sans-serif", color="#303835"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    return fig


def flow_matrix(interval: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores, labels = [], []
    for region_key in REGION_KEYS:
        score_row, label_row = [], []
        for stage, metric in FLOW_METRICS:
            status = status_for(region_key, metric, interval)
            score_row.append(STATUS_SCORE[status])
            label_row.append(f"{STATUS_SYMBOL[status]} {STATUS_LABEL[status]}")
        scores.append(score_row)
        labels.append(label_row)
    index = [region_meta(key)["지역"].replace("군", "") for key in REGION_KEYS]
    columns = [stage for stage, _ in FLOW_METRICS]
    return pd.DataFrame(scores, index=index, columns=columns), pd.DataFrame(labels, index=index, columns=columns)


def heatmap_figure(interval: dict[str, str]) -> go.Figure:
    score, label = flow_matrix(interval)
    fig = go.Figure(
        go.Heatmap(
            z=score.values,
            x=score.columns,
            y=score.index,
            text=label.values,
            texttemplate="%{text}",
            textfont={"size": 13},
            zmin=-1,
            zmax=1,
            colorscale=[[0, "#E6A09B"], [0.49, "#F1D9A8"], [0.5, "#F1D9A8"], [1, "#8CC5AD"]],
            showscale=False,
            hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>",
            xgap=5,
            ygap=5,
        )
    )
    fig.update_yaxes(autorange="reversed")
    return chart_layout(fig, 390)


def trend_data(region_key: str, metrics: list[str]) -> pd.DataFrame:
    subset = KPI.loc[KPI["지역키"].eq(region_key), ["기간", *metrics]].copy()
    long = subset.melt("기간", var_name="지표", value_name="값")
    long["기간"] = pd.Categorical(long["기간"], PERIODS, ordered=True)
    long["기준값"] = long.groupby("지표", observed=False)["값"].transform(
        lambda series: series.loc[long.loc[series.index, "기간"].eq("P1")].iloc[0]
        if series.loc[long.loc[series.index, "기간"].eq("P1")].notna().any()
        else series.dropna().iloc[0] if series.notna().any() else np.nan
    )
    long["지수"] = long["값"] / long["기준값"] * 100
    long["표시명"] = long["지표"].map(METRIC_NAMES)
    return long.sort_values("기간")


def trend_figure(region_key: str, metrics: list[str], height: int = 430) -> go.Figure:
    long = trend_data(region_key, metrics).dropna(subset=["지수"])
    fig = px.line(
        long,
        x="기간",
        y="지수",
        color="표시명",
        markers=True,
        color_discrete_sequence=["#335C67", "#D58B39", "#4C956C", "#BC4749", "#7A5195"],
        custom_data=["값", "지표"],
    )
    fig.add_vrect(x0=1.5, x1=2.5, fillcolor="#D9EAD3", opacity=0.28, line_width=0)
    fig.add_vline(x=1.5, line_dash="dash", line_color="#5B7F70")
    fig.add_annotation(x=1.5, y=1.08, yref="paper", text="지정", showarrow=False, font=dict(color="#406B5A"))
    fig.add_hline(y=100, line_dash="dot", line_color="#A8B5AF")
    fig.update_traces(line=dict(width=3), marker=dict(size=8), hovertemplate="%{fullData.name}<br>%{x}: 지수 %{y:.1f}<extra></extra>")
    fig.update_yaxes(title="P1=100 변화지수", ticksuffix="")
    fig.update_xaxes(title="")
    return chart_layout(fig, height)


def evidence_level(q_value: object, p_value: object, robust: bool | None) -> tuple[str, str]:
    q = pd.to_numeric(q_value, errors="coerce")
    p = pd.to_numeric(p_value, errors="coerce")
    if pd.notna(q) and q < 0.05 and robust:
        return "근거 강함", "evidence-strong"
    if pd.notna(q) and q < 0.05:
        return "근거 보통", "evidence-mid"
    if pd.notna(p) and p < 0.05:
        return "탐색적 신호", "evidence-mid"
    return "명확한 변화 없음", "evidence-weak"


def robustness(region_key: str, metric: str, intervention: object, coefficient: str) -> bool | None:
    robust = DATA["its_robustness"]
    rows = robust.loc[
        robust["지역키"].eq(region_key)
        & robust["지표"].eq(metric)
        & robust["개입시작월"].eq(intervention)
        & robust["계수"].eq(coefficient)
    ]
    if rows.empty or pd.isna(rows.iloc[0].get("모든lag_p05유의")):
        return None
    return str(rows.iloc[0]["모든lag_p05유의"]).lower() == "true"


def its_card(region_key: str, metric: str, kind: str) -> None:
    its = DATA["its_designation_hac3"]
    rows = its.loc[its["지역키"].eq(region_key) & its["지표"].eq(metric)]
    if rows.empty:
        st.info("이 지표는 월별 시계열 분석 자료가 없습니다.")
        return
    row = rows.iloc[0]
    if kind == "instant":
        title, coef, pct, p_col, q_col, coef_name = (
            "지정 직후",
            "즉시수준변화_beta",
            "즉시변화_환산_pct",
            "즉시수준변화_p",
            "즉시수준변화_q_BH",
            "즉시수준변화",
        )
    else:
        title, coef, pct, p_col, q_col, coef_name = (
            "그 이후 흐름",
            "지정후_기울기변화_beta",
            "기울기변화_월환산_pct",
            "지정후_기울기변화_p",
            "지정후_기울기변화_q_BH",
            "지정후기울기변화",
        )
    raw_value = pd.to_numeric(row[pct], errors="coerce")
    beta = pd.to_numeric(row[coef], errors="coerce")
    if pd.notna(raw_value):
        display = f"{raw_value:+.1f}%" if kind == "instant" else f"월 {raw_value:+.2f}%"
    elif pd.notna(beta):
        display = f"{beta:+.2f}%p" if metric.endswith("_pct") else f"{beta:+.2f}"
    else:
        display = "자료 제한"
    direction = "개선 방향" if (raw_value if pd.notna(raw_value) else beta) > 0 else "감소 방향"
    robust = robustness(region_key, metric, row["개입시작월"], coef_name)
    evidence, css_class = evidence_level(row[q_col], row[p_col], robust)
    st.markdown(
        f"""<div class="insight-card"><div class="eyebrow">{title}</div>
        <div class="big-number">{display}</div><div>{direction}</div>
        <div class="{css_class}" style="margin-top:.65rem">{evidence}</div></div>""",
        unsafe_allow_html=True,
    )
    with st.expander("통계 상세"):
        st.caption(
            f"FDR 보정 q={pd.to_numeric(row[q_col], errors='coerce'):.4f}, "
            f"원 p={pd.to_numeric(row[p_col], errors='coerce'):.4f}, "
            f"HAC lag 1·3·6·12 전체 유의: {'예' if robust else '아니오/확인 불가'}"
        )


def region_cards(interval: dict[str, str]) -> None:
    columns = st.columns(len(REGION_KEYS))
    for column, region_key in zip(columns, REGION_KEYS):
        meta = region_meta(region_key)
        rows = []
        for stage, metric in FLOW_METRICS:
            status = status_for(region_key, metric, interval)
            rows.append(
                f'<div class="stage-row"><span>{stage}</span><b style="color:{STATUS_COLOR[status]}">'
                f'{STATUS_SYMBOL[status]} {STATUS_LABEL[status]}</b></div>'
            )
        with column:
            st.markdown(
                f"""<div class="region-card"><div class="region-name">{meta['지역'].replace('군', '')}</div>
                <div class="facility">{meta['시설']} · {int(meta['최초선정연도'])}년</div>
                {''.join(rows)}<div class="diagnosis">{stage_sentence(region_key, interval)}</div></div>""",
                unsafe_allow_html=True,
            )


def coverage_badge(region_key: str, item: str) -> str:
    status = DATA["not_computable_status"]
    rows = status.loc[status["지역키"].eq(region_key) & status["항목"].eq(item)]
    if rows.empty:
        return "확인 필요"
    value = rows.iloc[0]["상태"]
    return "이전 산출물" if value == "LEGACY_AVAILABLE" else "계산 불가"


st.markdown(
    """<section class="hero"><div class="hero-kicker">WELL-FLOW</div>
    <h1>웰니스 관광 성과</h1>
    <p>4개 지역의 지정 전후 흐름</p></section>""",
    unsafe_allow_html=True,
)

control_left, control_right = st.columns([2.3, 1])
with control_left:
    interval_name = st.segmented_control(
        "비교 구간",
        options=list(INTERVALS),
        default=list(INTERVALS)[0],
        label_visibility="collapsed",
    )
with control_right:
    st.caption("↑ 개선  → 유지  ↓ 악화 · ±3% 기준")
interval = INTERVALS[interval_name or list(INTERVALS)[0]]

overview_tab, region_tab, why_tab, compare_tab = st.tabs(
    ["요약", "지역", "원인", "비교"]
)

with overview_tab:
    st.subheader("지역별 흐름")
    st.caption("선택 구간의 변화 방향")
    region_cards(interval)

    st.markdown("### 단계별 변화")
    left, right = st.columns([1.65, 1])
    with left:
        st.plotly_chart(
            heatmap_figure(interval),
            width="stretch",
            key="overview_heatmap",
            config={"displayModeBar": False},
        )
    with right:
        st.markdown("#### 보는 법")
        st.markdown(
            """<div class="callout">왼쪽부터 흐름을 따라 보세요.<br>
            앞 단계와 방향이 갈리는 지점이 병목입니다.</div>""",
            unsafe_allow_html=True,
        )
        st.markdown("#### 우선 과제")
        for region_key in REGION_KEYS:
            meta = region_meta(region_key)
            st.markdown(f"**{meta['지역'].replace('군', '')}** · {POLICY_FOCUS[region_key][1]}")

    st.markdown("### P1–P4 흐름")
    selected_overview = st.selectbox(
        "흐름을 볼 지역",
        REGION_KEYS,
        format_func=lambda key: REGION_LABEL[key],
        key="overview_region",
    )
    st.plotly_chart(
        trend_figure(selected_overview, [metric for _, metric in FLOW_METRICS]),
        width="stretch",
        key="overview_trend",
        config={"displayModeBar": False},
    )

with region_tab:
    selected_region = st.selectbox(
        "지역 선택",
        REGION_KEYS,
        format_func=lambda key: REGION_LABEL[key],
        key="detail_region",
    )
    meta = region_meta(selected_region)
    diagnosis, action = POLICY_FOCUS[selected_region]
    st.markdown(f"## {meta['지역']} · {meta['시설']}")
    st.markdown(
        f"<div class='callout'><b>{diagnosis}</b><br><span class='soft-note'>{action}</span></div>",
        unsafe_allow_html=True,
    )

    metric_columns = st.columns(5)
    for column, (stage, metric) in zip(metric_columns, FLOW_METRICS):
        row = growth_row(selected_region, metric)
        value = change_value(row, interval, metric)
        status = status_for(selected_region, metric, interval)
        with column:
            st.metric(
                stage,
                format_change(value, metric),
                f"{STATUS_SYMBOL[status]} {STATUS_LABEL[status]}",
                delta_color="normal" if status == "UP" else "inverse" if status == "DOWN" else "off",
                help=METRIC_NAMES[metric],
            )

    trend_col, its_col = st.columns([1.55, 1])
    with trend_col:
        st.markdown("### P1–P4 변화")
        st.plotly_chart(
            trend_figure(selected_region, [metric for _, metric in FLOW_METRICS]),
            width="stretch",
            key="detail_trend",
            config={"displayModeBar": False},
        )
    with its_col:
        st.markdown("### 변화 근거")
        its_metric = st.selectbox(
            "확인할 지표",
            [metric for _, metric in FLOW_METRICS],
            format_func=lambda metric: METRIC_NAMES[metric],
            key="its_metric",
        )
        c1, c2 = st.columns(2)
        with c1:
            its_card(selected_region, its_metric, "instant")
        with c2:
            its_card(selected_region, its_metric, "trend")
        st.caption("대조군 없는 탐색 결과입니다.")

    st.markdown("### 체류와 안정성")
    latest = KPI.loc[KPI["지역키"].eq(selected_region) & KPI["기간"].eq(interval["after"])]
    latest = latest.iloc[0] if not latest.empty else pd.Series(dtype=float)
    wellness_metrics = [
        ("숙박 전환", "숙박자비율_pct", "방문자 중 숙박으로 이어진 비율"),
        ("전체 장기체류", "전체순방문자중_3박이상_pct", "전체 순방문자 중 3박 이상 체류 비율"),
        ("계절 안정성", "DSI", "1에 가까울수록 월별 방문이 고르게 분포"),
        ("평균 숙박일수", "평균숙박일수", "숙박객이 평균적으로 머문 일수"),
    ]
    wellness_cols = st.columns(4)
    for column, (label, metric, help_text) in zip(wellness_cols, wellness_metrics):
        row = growth_row(selected_region, metric)
        with column:
            st.metric(
                label,
                format_level(pd.to_numeric(latest.get(metric), errors="coerce"), metric),
                format_change(change_value(row, interval, metric), metric),
                help=help_text,
            )

with why_tab:
    why_region = st.selectbox(
        "원인을 볼 지역",
        REGION_KEYS,
        format_func=lambda key: REGION_LABEL[key],
        key="why_region",
    )
    st.markdown("## 변화의 배경")
    st.caption("시장 · 공간 · 소비 업종")

    market_current = DATA["market_alignment_conditional_available_sites"].copy()
    market_legacy = DATA["market_alignment_legacy_wanju_from_previous_p_extract"].copy()
    market = pd.concat([market_current, market_legacy], ignore_index=True, sort=False)
    market_region = market.loc[market["지역키"].eq(why_region)].copy()
    market_col, spatial_col = st.columns(2)
    with market_col:
        st.markdown("### 관심과 방문 시장")
        if market_region.empty:
            st.info(f"시장 분석 {coverage_badge(why_region, '조건부 시장정합도')}")
            origin = DATA["mobility_origin_by_period"]
            origin_region = origin.loc[origin["지역키"].eq(why_region)].copy()
            if not origin_region.empty:
                origin_period = st.selectbox(
                    "방문 출발지 기간",
                    ["P2", "P3", "P4"],
                    index=1,
                    key="mobility_origin_period",
                )
                origin_view = origin_region.loc[origin_region["기간"].eq(origin_period)].copy()
                origin_view["출발지"] = origin_view["거주지(시도)"].astype(str) + " " + origin_view["거주지(시군구)"].astype(str)
                origin_view["비율(%)"] = pd.to_numeric(origin_view["비율(%)"], errors="coerce")
                origin_view = origin_view.nlargest(8, "비율(%)").sort_values("비율(%)")
                fig = px.bar(
                    origin_view,
                    x="비율(%)",
                    y="출발지",
                    orientation="h",
                    text=origin_view["비율(%)"].map(lambda value: f"{value:.1f}%"),
                    color_discrete_sequence=["#5B7280"],
                )
                fig.update_traces(textposition="outside", cliponaxis=False)
                fig.update_xaxes(title="방문 비중", ticksuffix="%")
                fig.update_yaxes(title="")
                st.plotly_chart(
                    chart_layout(fig, 350),
                    width="stretch",
                    key="mobility_origins",
                    config={"displayModeBar": False},
                )
                st.caption("시설 읍면동 방문자의 출발지 상위 8곳")
        else:
            market_long = market_region.melt(
                id_vars="기간",
                value_vars=["조건부_Spearman_rho", "조건부_JSD_base2"],
                var_name="지표",
                value_name="값",
            )
            market_long["표시명"] = market_long["지표"].map(
                {"조건부_Spearman_rho": "시장 순위 일치도", "조건부_JSD_base2": "관심–방문 시장 간격"}
            )
            fig = px.line(
                market_long,
                x="기간",
                y="값",
                color="표시명",
                markers=True,
                color_discrete_map={"시장 순위 일치도": "#2F7663", "관심–방문 시장 간격": "#D47A45"},
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8))
            fig.update_yaxes(title="0~1", range=[0, 1])
            fig.update_xaxes(title="")
            st.plotly_chart(
                chart_layout(fig, 350),
                width="stretch",
                key="market_alignment",
                config={"displayModeBar": False},
            )
            st.caption("일치도는 높을수록, 간격은 낮을수록 유사합니다.")
            if why_region == "전북완주":
                st.warning("완주: 이전 P구간 산출물")

    spatial_current = DATA["spatial_concentration_available_sites"].copy()
    legacy = DATA["spatial_legacy_wanju_from_previous_p_extract"].copy()
    if "원표" in legacy:
        legacy = legacy.loc[legacy["원표"].eq("spatial_concentration.csv")]
    spatial = pd.concat([spatial_current, legacy[spatial_current.columns]], ignore_index=True, sort=False)
    spatial_region = spatial.loc[spatial["지역키"].eq(why_region)].copy()
    mobile = DATA["spatial_mobility_only"].copy()
    mobile_region = mobile.loc[mobile["지역키"].eq(why_region)].copy()
    with spatial_col:
        st.markdown("### 시설지역 비중")
        if not mobile_region.empty:
            st.caption("이동통신 방문자료 · 소비 자료 없음")
            fig = px.line(
                mobile_region,
                x="기간",
                y="시설동_점유율_pct",
                markers=True,
                color_discrete_sequence=["#0F766E"],
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8), fill="tozeroy", fillcolor="rgba(15,118,110,.10)")
            fig.update_yaxes(title="시설 읍면동 방문 비중", ticksuffix="%")
            fig.update_xaxes(title="")
            st.plotly_chart(
                chart_layout(fig, 350),
                width="stretch",
                key="mobility_share",
                config={"displayModeBar": False},
            )
            st.caption("군 전체 방문자 대비 시설 읍면동 방문자 비중")
        elif spatial_region.empty:
            st.info(f"공간 분석 {coverage_badge(why_region, '읍면동 공간파급')}")
        else:
            selected_domain = st.radio("영역", ["방문", "소비"], horizontal=True, key="spatial_domain")
            spatial_view = spatial_region.loc[spatial_region["영역"].eq(selected_domain)].copy()
            fig = px.line(
                spatial_view,
                x="기간",
                y="시설동_점유율_pct",
                markers=True,
                color_discrete_sequence=["#2F7663"],
            )
            fig.update_traces(line=dict(width=4), marker=dict(size=9), fill="tozeroy", fillcolor="rgba(47,118,99,.12)")
            fig.update_yaxes(title="시설 소재 읍면동 비중", ticksuffix="%")
            fig.update_xaxes(title="")
            st.plotly_chart(
                chart_layout(fig, 350),
                width="stretch",
                key="spatial_share",
                config={"displayModeBar": False},
            )
            place = spatial_view["시설소재_읍면동"].dropna().iloc[0]
            st.caption(f"{place} 비중 · 상승 시 시설 주변 집중 확대")
            if why_region == "전북완주":
                st.warning("완주: 이전 P구간 산출물")

    st.markdown("### 소비 업종")
    category = DATA["category_change"]
    category_view = category.loc[
        category["지역키"].eq(why_region) & category["변화구간"].eq(interval["category"])
    ].copy()
    category_view["성장률_pct"] = pd.to_numeric(category_view["성장률_pct"], errors="coerce")
    category_view = category_view.dropna(subset=["성장률_pct"])
    if category_view.empty:
        st.info("업종 자료 없음")
    else:
        extremes = pd.concat(
            [category_view.nsmallest(6, "성장률_pct"), category_view.nlargest(6, "성장률_pct")]
        ).drop_duplicates().sort_values("성장률_pct")
        extremes["방향"] = np.where(extremes["성장률_pct"] >= 0, "증가", "감소")
        fig = px.bar(
            extremes,
            x="성장률_pct",
            y="중분류",
            orientation="h",
            color="방향",
            color_discrete_map={"증가": "#2F8A70", "감소": "#C85B52"},
            text=extremes["성장률_pct"].map(lambda value: f"{value:+.1f}%"),
        )
        fig.add_vline(x=0, line_color="#5E6D68", line_width=1)
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_xaxes(title=f"{interval['category']} 소비 변화", ticksuffix="%")
        fig.update_yaxes(title="")
        st.plotly_chart(
            chart_layout(fig, 470),
            width="stretch",
            key="category_change",
            config={"displayModeBar": False},
        )
        st.caption("증감 폭 상위 업종")

with compare_tab:
    st.markdown("## 4개 지역 비교")
    st.caption("각 지역의 지정 전후 방향 비교")
    st.plotly_chart(
        heatmap_figure(interval),
        width="stretch",
        key="compare_heatmap",
        config={"displayModeBar": False},
    )

    compare_metric = st.selectbox(
        "P1~P4 흐름 비교 지표",
        [metric for _, metric in FLOW_METRICS] + ["전체순방문자중_3박이상_pct", "DSI"],
        format_func=lambda metric: METRIC_NAMES[metric],
        key="compare_metric",
    )
    rows = []
    for region_key in REGION_KEYS:
        subset = KPI.loc[KPI["지역키"].eq(region_key), ["기간", compare_metric]].copy()
        subset["지역"] = region_meta(region_key)["지역"].replace("군", "")
        subset["기간"] = pd.Categorical(subset["기간"], PERIODS, ordered=True)
        baseline = subset.loc[subset["기간"].eq("P1"), compare_metric]
        baseline_value = baseline.iloc[0] if not baseline.empty and pd.notna(baseline.iloc[0]) else subset[compare_metric].dropna().iloc[0]
        subset["지수"] = subset[compare_metric] / baseline_value * 100
        rows.append(subset)
    # Keep missing P1~P4 rows so Plotly leaves a visible gap instead of
    # connecting the first and last available observations directly.
    comparison = pd.concat(rows, ignore_index=True)
    fig = px.line(
        comparison,
        x="기간",
        y="지수",
        facet_col="지역",
        facet_col_wrap=3,
        markers=True,
        color="지역",
        color_discrete_sequence=px.colors.qualitative.Safe,
        category_orders={"기간": PERIODS},
    )
    fig.add_hline(y=100, line_dash="dot", line_color="#AAB5B0")
    fig.update_traces(line=dict(width=3), marker=dict(size=7), connectgaps=False, showlegend=False)
    fig.for_each_annotation(lambda annotation: annotation.update(text=annotation.text.split("=")[-1]))
    fig.update_yaxes(title="P1=100")
    fig.update_xaxes(title="")
    st.plotly_chart(
        chart_layout(fig, 560),
        width="stretch",
        key="compare_small_multiples",
        config={"displayModeBar": False},
    )
    if comparison["지수"].isna().any():
        st.caption("자료가 없는 P구간은 선을 연결하지 않고 비워 둡니다.")

    st.markdown("### 진단과 과제")
    decision_rows = []
    for region_key in REGION_KEYS:
        meta = region_meta(region_key)
        diagnosis, action = POLICY_FOCUS[region_key]
        decision_rows.append(
            {
                "지역": meta["지역"],
                "시설": meta["시설"],
                "진단 유형": diagnosis,
                "우선 대응": action,
                "시장 분석": "가능" if region_key in market["지역키"].unique() else "제한",
                "공간 분석": "가능" if region_key in spatial["지역키"].unique() else "제한",
            }
        )
    st.dataframe(pd.DataFrame(decision_rows), width="stretch", hide_index=True)

with st.expander("지표 기준"):
    st.markdown(
        """
        - **숙박 전환**: 방문자 중 숙박 비율. 변화는 `%p`로 표시
        - **전체 장기체류**: 전체 방문자 중 3박 이상 비율
        - **계절 안정성**: 1에 가까울수록 계절 쏠림이 적음
        - **근거 강함**: FDR q<.05, HAC lag 1·3·6·12 모두 유의

        대조군 없는 탐색 분석으로 인과효과를 뜻하지 않습니다.
        """
    )

st.caption("한국관광 데이터랩 기반 내부 분석")
