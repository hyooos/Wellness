"""WELL-FLOW v4: bottleneck-first monitor with prescriptions for wellness tourism sites."""

from __future__ import annotations

from html import escape
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from PIL import Image, ImageOps


st.set_page_config(
    page_title="WELL-FLOW Monitor · v4",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="collapsed",
)

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "output" / "4개_웰니스관광지_성과분석"
BOUNDARY_PATH = ROOT / "assets" / "skorea-provinces-geo.json"
MUNICIPAL_BOUNDARY_PATH = ROOT / "assets" / "jeolla-municipalities-geo.json"
SITE_IMAGE_NAMES = {
    "전북무주": "무주태권도원.jpg",
    "전남완도": "완도해양치유센터.jpg",
    "전북순창": "순창쉴랜드.jpg",
    "전북완주": "완주아원고택.jpg",
}
PERIODS = ["P1", "P2", "P3", "P4"]
PERIOD_SHORT = {"P1": "지정 2년 전", "P2": "지정 직전", "P3": "지정 1년차", "P4": "지정 2년차"}

SITES = pd.DataFrame(
    [
        ("전북완주", "완주군", "아원고택", "소양면", 2024, 127.244624, 35.903470, "Wanju"),
        ("전북순창", "순창군", "쉴랜드", "인계면", 2024, 127.131587, 35.431547, "Sunchang"),
        ("전남완도", "완도군", "완도 해양치유센터", "신지면", 2024, 126.818435, 34.328049, "Wando"),
        ("전북무주", "무주군", "태권도원 상징지구", "설천면", 2022, 127.762090, 36.012521, "Muju"),
    ],
    columns=["지역키", "지역", "시설", "시설동", "선정연도", "경도", "위도", "geo_name"],
)
ALIASES = {"쉴랜드": "쉴(SHIL)랜드"}

# 여섯 칸: (칸 이름, 지표 컬럼, 지표 설명, 원천)
STAGES = [
    ("관심", "숙박검색건수", "숙박 목적지 검색", "티맵"),
    ("방문", "외지인방문자수", "외지인 방문자", "KT"),
    ("숙박", "숙박자비율_pct", "숙박자 비율", "KT"),
    ("체류", "평균체류시간_분", "평균 체류시간", "KT"),
    ("소비", "내국인관광소비_천원", "내국인 관광소비", "신한카드"),
    ("파급", "SPREAD", "시설 읍면 소비 비중", "신한카드 읍면동"),
]
METRIC_LABEL = {
    "숙박검색건수": "숙박 검색",
    "외지인방문자수": "외지인 방문",
    "숙박자비율_pct": "숙박자 비율",
    "평균체류시간_분": "평균 체류시간",
    "평균숙박일수": "평균 숙박일수",
    "숙박자중_3박이상_pct": "숙박객 중 3박+",
    "전체순방문자중_3박이상_pct": "장기체류 비율(WStay)",
    "내국인관광소비_천원": "내국인 관광소비",
    "방문자대비관광소비_천원_proxy": "방문자 대비 소비",
    "DSI": "사계절 수요(DSI)",
}
LOG_METRICS = {"숙박검색건수", "외지인방문자수", "내국인관광소비_천원"}
INTERVALS = {
    "지정 직후 (직전 → 1년차)": ("g23_pct", "delta23_pctp", "지정직후_판정_3pct", "P2", "P3", "g23"),
    "2년차 (1년차 → 2년차)": ("g34_pct", "delta34_pctp", "2년차_판정_3pct", "P3", "P4", "g34"),
}
STATUS = {
    "UP": ("오름", "↑", "up"),
    "FLAT": ("유지", "→", "flat"),
    "DOWN": ("내림", "↓", "down"),
    "NA": ("자료 없음", "·", "na"),
    "INFO": ("참고", "◦", "info"),
}
STRENGTH_CLASS = {"강함": "s-strong", "중간": "s-mid", "약함": "s-weak", "신호 없음": "s-none", "자료 없음": "s-none"}

# 분석 보고서(6~7장)의 지역별 진단과 처방
STORY = {
    "전북완주": {
        "type": "숙박전환 병목형",
        "headline": "사람은 계속 오는데, 자고 가지 않는다",
        "bottleneck": ["숙박"],
        "bottleneck_label": "방문 → 숙박 전환",
        "strength": "강함",
        "evidence": "숙박자 비율이 지정 시점에 원래 흐름보다 0.74%p 한 계단 떨어졌고(q=0.019, 8가지 조건 모두 확인), 2년차에도 돌아오지 않았습니다.",
        "good": "방문은 4년 연속 증가했고, 소비·체류는 지정 이후 회복 흐름입니다.",
        "recommend": [
            ("1박 연계 상품", "숙박 가능한 웰니스 시설과 주변 관광지를 묶은 1박 패키지"),
            ("저녁·야간 웰니스 프로그램", "당일 방문객이 하룻밤 머물 이유 만들기"),
            ("숙박 공급 확인", "데이터랩 숙박업 개폐업·객실 수로 '숙소 부족'인지 '머물 이유 부족'인지 구분"),
        ],
        "avoid": [("방문객 유치 홍보 확대", "방문은 이미 4년 연속 늘고 있어 막힌 칸이 아닙니다")],
        "check_metric": "숙박자비율_pct",
        "actions": [
            ("지금", "다음 해 사업 계획에 1박 연계 상품·야간 프로그램 예산 배정"),
            ("6개월 뒤", "숙박자 비율 월별 추이로 반등이 시작됐는지 확인"),
            ("재지정 심사", "숙박자 비율이 지정 직전 수준으로 돌아왔는지 서면평가 근거로 제출"),
        ],
    },
    "전북순창": {
        "type": "입구 단절형",
        "headline": "찾아보긴 하는데, 오지 않는다",
        "bottleneck": ["방문"],
        "bottleneck_label": "관심 → 방문 (접근성)",
        "strength": "강함",
        "evidence": "검색은 5.0% 늘었지만 방문은 3.9% 줄었고, 소비는 지정 시점에 18.4% 한 계단 내려앉았습니다(q=0.004, 8/8). 줄어든 소비의 대부분이 교통(육상운송 −49.2%)입니다.",
        "good": "외식 소비는 버텼고(일반외식업 +3.0%), 쉴랜드가 있는 인계면의 소비 비중은 올랐습니다.",
        "recommend": [
            ("거점 교통 연계", "광주·전주 등 인근 거점과 쉴랜드를 잇는 셔틀·환승 연계"),
            ("예약 + 이동 결합 상품", "검색한 사람이 바로 올 수 있게 예약과 교통을 한 번에"),
            ("장류·음식 테마 체류 상품", "버티고 있는 외식 소비를 체류로 연결"),
        ],
        "avoid": [("인지도 홍보", "검색(관심)은 이미 늘었습니다. 문제는 발걸음입니다")],
        "check_metric": "내국인관광소비_천원",
        "actions": [
            ("지금", "거점 교통 연계·예약 결합 상품 예산을 우선 배정"),
            ("6개월 뒤", "외지인 방문과 교통(육상운송) 소비가 회복되는지 확인"),
            ("재지정 심사", "검색 출발지와 방문 출발지의 차이(JSD 0.132)가 줄었는지 제출"),
        ],
    },
    "전남완도": {
        "type": "소비전환·시설거점형",
        "headline": "오래 머물지만 지갑은 닫혀 있고, 쓰는 돈은 시설 주변에 머문다",
        "bottleneck": ["소비", "파급"],
        "bottleneck_label": "체류 → 소비, 시설 → 군 전체",
        "strength": "중간",
        "evidence": "방문자 대비 소비가 2년 연속 줄었습니다(−11.1% → −2.5%). 체험·문화 소비(관광유원시설 −48.3%)가 빠졌고, 소비는 센터가 있는 신지면으로만 모였습니다(5.0% → 6.9%).",
        "good": "체류는 가장 깁니다. 방문자 100명 중 3명이 3박 이상 머물러 다른 두 곳의 약 3배입니다.",
        "recommend": [
            ("타 읍면 연계 체험", "해양치유센터 이용객 대상 다른 읍면 체험·소비 프로그램"),
            ("장기체류자 지역 소비 연계", "지역화폐·쿠폰으로 머무는 동안 쓸 거리 만들기"),
            ("군 단위 순환 동선", "신지면에 모인 사람을 군 전체로 흘려보내기"),
        ],
        "avoid": [("체류 기간 연장 프로그램", "체류는 이미 가장 깁니다. 막힌 곳은 소비입니다")],
        "check_metric": "방문자대비관광소비_천원_proxy",
        "actions": [
            ("지금", "센터 이용객 대상 타 읍면 연계 체험·소비 프로그램 예산 배정"),
            ("6개월 뒤", "방문자 대비 소비 반등, 신지면 외 읍면 소비 비중 확인"),
            ("재지정 심사", "방문자 대비 소비 회복과 소비의 군 전체 확산을 함께 제출"),
        ],
    },
    "전북무주": {
        "type": "선행 성장형",
        "headline": "성공처럼 보이지만, 상승은 지정 전에 이미 가장 가팔랐다",
        "bottleneck": ["체류"],
        "bottleneck_label": "체류 길이 (연박 전환)",
        "strength": "약함",
        "evidence": "소비는 지정 전에 이미 44.5% 올랐고, 지정 직후 상승(+11.1%)은 그 4분의 1입니다. 지정 시점의 계단 변화는 어느 칸에도 없고, 체류시간은 2년차에 3.8% 줄었습니다.",
        "good": "관심·방문·숙박 전환·소비가 함께 오른 유일한 지역입니다.",
        "recommend": [
            ("연박 프로그램", "태권도원 체험과 연계한 2박 이상 다일 프로그램"),
            ("장기체류 전환 상품", "숙박객 중 3박 이상 비율(5.7%, 최저)을 끌어올리기"),
        ],
        "avoid": [("무주 방식을 다른 지역에 그대로 이식", "성과의 상당 부분이 지정 전 코로나 회복기 흐름입니다")],
        "check_metric": "평균체류시간_분",
        "actions": [
            ("지금", "유입 확대보다 연박 전환 프로그램 설계에 예산 배정"),
            ("6개월 뒤", "숙박객 중 3박 이상 비율과 체류시간 확인"),
            ("다른 지역 확산 전", "성과 중 지정 전 회복기 몫을 분리하고 옮길 요소만 선별"),
        ],
    },
}


st.markdown(
    """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css');
:root {
  --bg:#F3F7F4; --card:#FFFFFF; --ink:#14261E; --ink2:#3E5249; --muted:#6F8279; --line:#DDE7E1; --soft:#EEF4F0;
  --leaf:#2F8F6B; --leaf2:#5DAE7E; --leaf-soft:#E3F1E8;
  --up:#2E9A6E; --up-bg:#E4F4EC; --flat:#A87B1C; --flat-bg:#FBF1DC; --down:#D2513A; --down-bg:#FCE9E4; --na:#94A39B; --na-bg:#F0F3F1;
  --info:#3F6FA8; --info-bg:#E7EFF8;
}
html, body, [class*="css"] { font-family:'Pretendard Variable', Pretendard, -apple-system, sans-serif; letter-spacing:-.015em; }
.stApp { background:var(--bg); color:var(--ink); }
[data-testid="stHeader"] { background:transparent; height:0; }
.block-container { max-width:1560px; padding:1.2rem 1.6rem 3rem; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-color:var(--line); border-radius:18px; background:var(--card); box-shadow:none; }
[data-testid="stImage"] img { border-radius:14px; }

.topbar { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; padding:.45rem 0 1rem; margin:0 0 .9rem; border-bottom:1px solid var(--line); flex-wrap:wrap; }
.brand { display:flex; align-items:center; gap:18px; }
.brand strong { font-family:Inter, Arial, sans-serif; font-size:1.75rem; line-height:1; font-weight:720; letter-spacing:-.025em; color:var(--ink); }
.brand strong span { font-weight:450; }
.brand > span { color:var(--muted); font-size:.8rem; padding-bottom:.08rem; }
.top-meta { color:var(--muted); font-size:.72rem; }
.map-head { display:flex; align-items:flex-end; justify-content:space-between; gap:1rem; margin:.1rem 0 .6rem; }
.map-head b { color:var(--ink); font-size:.95rem; }
.map-head span { color:var(--muted); font-size:.72rem; }

.sec-head { display:flex; align-items:baseline; gap:.7rem; margin:1.6rem 0 .6rem; flex-wrap:wrap; }
.sec-head h3 { font-size:1.08rem; font-weight:780; margin:0; padding:0; color:var(--ink); }
.sec-head span.sub { color:var(--muted); font-size:.76rem; }

.card-label { font-size:.82rem; font-weight:750; color:var(--ink2); }
.site-name { font-size:1.6rem; font-weight:800; margin:.25rem 0 .1rem; letter-spacing:-.03em; }
.site-loc { color:var(--muted); font-size:.8rem; }
.pill { display:inline-block; border-radius:999px; padding:.22rem .7rem; font-size:.74rem; font-weight:750; }
.pill-type { background:var(--leaf-soft); color:#1C6B4E; }
.pill-bneck { background:var(--down-bg); color:#A63A26; }
.headline { margin:.9rem 0 .7rem; font-size:1rem; font-weight:700; line-height:1.45; color:var(--ink); }
.chips { display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin-top:.6rem; }
.chip { background:var(--soft); border-radius:12px; padding:.6rem .7rem; }
.chip small { display:block; color:var(--muted); font-size:.7rem; }
.chip b { display:block; font-size:.92rem; margin-top:.15rem; color:var(--ink); }

/* 여섯 칸 파이프라인 */
.flow-banner { display:flex; justify-content:space-between; align-items:center; gap:1rem; flex-wrap:wrap; padding:.2rem .1rem .9rem; }
.flow-banner .msg { font-size:1.02rem; font-weight:700; color:var(--ink); }
.flow-banner .msg em { font-style:normal; color:var(--down); }
.legend { display:flex; gap:.8rem; font-size:.72rem; color:var(--muted); flex-wrap:wrap; }
.legend i { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:4px; vertical-align:-1px; }
.pipeline { display:flex; align-items:stretch; gap:0; }
.conn { flex:0 0 26px; display:grid; place-items:center; color:#B5C4BB; font-size:1.1rem; font-weight:700; }
.conn.broken { color:var(--down); }
.stage { position:relative; flex:1 1 0; min-width:0; border-radius:14px; padding:.85rem .8rem .8rem; border:1px solid var(--line); border-top-width:3px; background:#fff; cursor:default; }
.stage:hover { border-color:#B9C8BF; z-index:30; }
.stage.up { border-top-color:var(--up); }
.stage.flat { border-top-color:var(--flat); }
.stage.down { border-top-color:var(--down); }
.stage.na { border-top-color:var(--na); }
.stage.info { border-top-color:var(--info); }
.stage.bneck, .stage.bneck:hover { background:#FDF0EC; border:2.5px solid var(--down); padding-top:0; overflow:visible; }
.stage.bneck { flex:1.75 1 0; }
.stage.bneck .stage-name { font-size:1.2rem; }
.stage.bneck .stage-value { color:var(--down); font-size:1.75rem; margin-top:.4rem; }
.stage.bneck .stage-change { font-size:.95rem; }
.bneck-band { margin:0 -.8rem .6rem; padding:.32rem .8rem; background:var(--down); color:#fff; font-size:.74rem; font-weight:800; border-radius:11px 11px 0 0; letter-spacing:.02em; }
.pipeline.has-b .stage:not(.bneck) { opacity:.62; }
.pipeline.has-b .stage:not(.bneck):hover { opacity:1; }
.conn.broken { font-size:1.35rem; }
.stage-top { display:flex; align-items:center; gap:.4rem; }
.stage-no { font-size:.68rem; font-weight:800; color:var(--muted); }
.stage-name { font-size:1.02rem; font-weight:800; color:var(--ink); }
.bneck-tag { margin-left:auto; background:var(--down); color:#fff; font-size:.64rem; font-weight:800; padding:.14rem .45rem; border-radius:999px; white-space:nowrap; }
.stage-metric { color:var(--muted); font-size:.7rem; margin-top:.15rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.stage-value { font-size:1.22rem; font-weight:800; margin-top:.55rem; color:var(--ink); white-space:nowrap; }
.stage-change { margin-top:.2rem; font-size:.84rem; font-weight:750; white-space:nowrap; }
.stage-change .j { font-size:.68rem; font-weight:750; padding:.08rem .38rem; border-radius:999px; margin-left:.25rem; }
.c-up { color:var(--up); } .c-flat { color:var(--flat); } .c-down { color:var(--down); } .c-na { color:var(--na); } .c-info { color:var(--info); }
.j-up { background:var(--up-bg); color:var(--up); } .j-flat { background:var(--flat-bg); color:var(--flat); } .j-down { background:var(--down-bg); color:var(--down); } .j-na { background:var(--na-bg); color:var(--na); } .j-info { background:var(--info-bg); color:var(--info); }
.stage-sig { margin-top:.5rem; font-size:.66rem; color:var(--muted); }

/* 마우스 오버 설명 */
.tip { position:relative; }
.tipbox { visibility:hidden; opacity:0; position:absolute; left:50%; top:calc(100% + 8px); transform:translateX(-50%); width:270px; background:#14261E; color:#EAF2ED; border-radius:12px; padding:.75rem .8rem; font-size:.72rem; line-height:1.5; z-index:60; box-shadow:0 12px 28px rgba(0,0,0,.22); transition:opacity .12s ease; pointer-events:none; text-align:left; font-weight:500; white-space:normal; }
.tipbox::before { content:""; position:absolute; top:-6px; left:50%; transform:translateX(-50%) rotate(45deg); width:12px; height:12px; background:#14261E; }
.tip:hover .tipbox { visibility:visible; opacity:1; }
.tipbox b { color:#fff; }
.tipbox table { width:100%; border-collapse:collapse; margin:.35rem 0; }
.tipbox td { padding:.12rem 0; border-bottom:1px solid rgba(255,255,255,.1); }
.tipbox td:last-child { text-align:right; }
.tipbox .t-head { font-weight:800; font-size:.78rem; color:#fff; margin-bottom:.2rem; }
.tipbox .t-note { color:#A9BDB2; font-size:.66rem; margin-top:.3rem; }

/* 처방 */
.rx-bneck { background:var(--down-bg); border-radius:14px; padding:.8rem .9rem; }
.rx-bneck small { color:#A63A26; font-weight:800; font-size:.7rem; letter-spacing:.08em; }
.rx-bneck .what { font-size:1.2rem; font-weight:800; color:var(--ink); margin:.2rem 0 .3rem; }
.rx-bneck p { margin:0; font-size:.8rem; color:var(--ink2); line-height:1.55; }
.rx-cols { display:grid; grid-template-columns:1.25fr 1fr; gap:12px; margin-top:.8rem; }
.rx-box { border-radius:14px; padding:.75rem .85rem; border:1px solid var(--line); }
.rx-box h4 { margin:0 0 .45rem; padding:0; font-size:.86rem; font-weight:800; }
.rx-do h4 { color:#1C6B4E; } .rx-dont h4 { color:#A63A26; }
.rx-do { background:#F6FBF8; } .rx-dont { background:#FFF8F6; }
.rx-item { display:flex; gap:.5rem; padding:.38rem 0; border-top:1px dashed var(--line); font-size:.78rem; line-height:1.45; }
.rx-item:first-of-type { border-top:0; }
.rx-item .ic { flex:none; width:20px; height:20px; border-radius:50%; display:grid; place-items:center; font-size:.68rem; font-weight:800; }
.rx-do .ic { background:var(--leaf); color:#fff; } .rx-dont .ic { background:var(--down); color:#fff; }
.rx-item b { display:block; color:var(--ink); }
.rx-item span { color:var(--muted); }
.rx-good { margin-top:.7rem; font-size:.78rem; color:#1C6B4E; background:var(--leaf-soft); border-radius:12px; padding:.55rem .75rem; }

.check { border-radius:14px; background:var(--soft); padding:.8rem .9rem; }
.check .row { display:flex; justify-content:space-between; align-items:baseline; gap:.5rem; }
.check .name { font-weight:800; font-size:.92rem; }
.check .state { font-size:.74rem; font-weight:800; padding:.15rem .55rem; border-radius:999px; }
.bar-track { position:relative; height:10px; border-radius:6px; background:#DCE6E0; margin:.75rem 0 .35rem; }
.bar-fill { position:absolute; left:0; top:0; bottom:0; border-radius:6px; }
.bar-target { position:absolute; top:-5px; bottom:-5px; width:2px; background:var(--ink); }
.bar-labels { display:flex; justify-content:space-between; font-size:.72rem; color:var(--muted); }
.bar-labels b { color:var(--ink); }

.steps { display:flex; flex-direction:column; gap:0; margin-top:.2rem; }
.step { display:grid; grid-template-columns:26px 1fr; gap:.65rem; position:relative; padding-bottom:.85rem; }
.step:not(:last-child)::after { content:""; position:absolute; left:12px; top:26px; bottom:0; width:2px; background:var(--line); }
.step .dot { width:26px; height:26px; border-radius:50%; display:grid; place-items:center; background:var(--leaf-soft); color:#1C6B4E; font-weight:800; font-size:.74rem; }
.step.now .dot { background:var(--leaf); color:#fff; }
.step small { color:var(--leaf); font-weight:800; font-size:.72rem; }
.step div.txt { font-size:.82rem; color:var(--ink2); line-height:1.45; margin-top:.05rem; }

/* 조기 경보 */
.ew { width:100%; border-collapse:separate; border-spacing:0 5px; font-size:.78rem; }
.ew th { color:var(--muted); font-size:.68rem; font-weight:700; text-align:left; padding:0 .45rem; }
.ew td { background:var(--soft); padding:.5rem .45rem; }
.ew td:first-child { border-radius:10px 0 0 10px; font-weight:750; }
.ew td:last-child { border-radius:0 10px 10px 0; }
.sbadge { display:inline-block; border-radius:999px; padding:.12rem .5rem; font-size:.68rem; font-weight:800; }
.s-strong { background:#1F3B30; color:#fff; } .s-mid { background:#5E8474; color:#fff; } .s-weak { background:#DCE7E1; color:#2E4A3E; } .s-none { background:#fff; color:var(--muted); border:1px solid var(--line); }
.verdict-warn { color:var(--down); font-weight:800; } .verdict-ok { color:var(--up); font-weight:800; }
.note { margin-top:.6rem; padding:.55rem .7rem; background:var(--soft); color:var(--muted); font-size:.72rem; border-radius:10px; line-height:1.5; }

/* 지역 비교 매트릭스 */
.mx { width:100%; border-collapse:separate; border-spacing:6px 6px; font-size:.8rem; }
.mx th { color:var(--muted); font-size:.72rem; font-weight:700; text-align:center; }
.mx th:first-child, .mx th:last-child { text-align:left; }
.mx td.reg { font-weight:800; white-space:nowrap; padding-right:.3rem; }
.mx td.reg small { display:block; font-weight:500; color:var(--muted); font-size:.68rem; }
.mx tr.sel td.reg { color:var(--leaf); }
.mx td.cell { border-radius:10px; text-align:center; padding:.5rem .2rem; font-weight:800; }
.mx td.cell small { display:block; font-weight:600; font-size:.66rem; opacity:.85; }
.mx td.cell.bneck { outline:2.5px solid var(--down); outline-offset:-2.5px; }
.mx td.cell.up { background:var(--up-bg); color:var(--up); } .mx td.cell.flat { background:var(--flat-bg); color:var(--flat); } .mx td.cell.down { background:var(--down-bg); color:var(--down); } .mx td.cell.na { background:var(--na-bg); color:var(--na); } .mx td.cell.info { background:var(--info-bg); color:var(--info); }
.mx td.type { font-size:.76rem; font-weight:750; color:var(--ink2); white-space:nowrap; }
.mx .tipbox { width:230px; }

.wl-grid { display:grid; grid-template-columns:repeat(5,1fr); gap:8px; }
.wl { background:var(--soft); border-radius:12px; padding:.65rem .7rem; }
.wl small { display:block; color:var(--muted); font-size:.7rem; }
.wl b { display:block; font-size:1.05rem; margin-top:.15rem; }
.wl em { font-style:normal; font-size:.72rem; font-weight:700; }
.origin-row { display:grid; grid-template-columns:22px 1fr 50px; gap:8px; align-items:center; margin:.4rem 0; font-size:.8rem; }
.rank { width:22px; height:22px; border-radius:50%; display:grid; place-items:center; background:var(--leaf-soft); color:#1C6B4E; font-weight:800; font-size:.72rem; }
.obar-bg { height:7px; background:#E3EBE6; border-radius:5px; overflow:hidden; margin-top:3px; }
.obar { height:100%; background:var(--leaf2); border-radius:5px; }
.poi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:6px; margin-top:.5rem; }
.poi { background:var(--soft); padding:.5rem .3rem; text-align:center; border-radius:10px; font-size:.72rem; color:var(--muted); }
.poi b { display:block; color:var(--ink); font-size:.95rem; }
.rel { width:100%; border-collapse:collapse; font-size:.78rem; }
.rel th { text-align:left; color:var(--muted); font-size:.7rem; border-bottom:1px solid var(--line); padding:.35rem .3rem; }
.rel td { border-bottom:1px solid var(--line); padding:.45rem .3rem; }

div[data-testid="stSegmentedControl"] button { font-size:.8rem; }
@media (max-width:1100px) {
  .pipeline { flex-wrap:wrap; gap:8px; }
  .conn { display:none; }
  .stage { flex:1 1 30%; }
  .stage.bneck { flex:1 1 100%; }
  .rx-cols, .chips { grid-template-columns:1fr; }
  .wl-grid { grid-template-columns:repeat(2,1fr); }
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def csv(path: Path, modified_ns: int) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8-sig")


@st.cache_data
def geojson(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def load_data() -> dict[str, pd.DataFrame]:
    files = {
        "kpi": DATA_DIR / "kpi_by_period.csv",
        "growth": DATA_DIR / "growth_bottleneck.csv",
        "monthly": DATA_DIR / "monthly_input.csv",
        "origin": DATA_DIR / "mobility_origin_by_period.csv",
        "periods": DATA_DIR / "period_definitions.csv",
        "its": DATA_DIR / "its_designation_hac3.csv",
        "its_robustness": DATA_DIR / "its_robustness.csv",
        "spread": DATA_DIR / "spatial_relative_growth_available_sites.csv",
        "site_catalog": ROOT / "wellness_88_geocoded.csv",
        "poi": ROOT / "output" / "대시보드_보조데이터" / "geo_tourism_density.csv",
        "nearest": ROOT / "output" / "대시보드_보조데이터" / "geo_nearest_lodging.csv",
    }
    return {name: csv(path, path.stat().st_mtime_ns) for name, path in files.items()}


DATA = load_data()


# ---------------------------------------------------------------------------
# 값 계산
# ---------------------------------------------------------------------------
def num(value: object) -> float:
    return pd.to_numeric(value, errors="coerce")


def growth_row(region: str, metric: str) -> pd.Series | None:
    g = DATA["growth"]
    rows = g.loc[g["지역키"].eq(region) & g["지표"].eq(metric)]
    return None if rows.empty else rows.iloc[0]


def kpi_value(region: str, period: str, metric: str) -> float:
    k = DATA["kpi"]
    rows = k.loc[k["지역키"].eq(region) & k["기간"].eq(period), metric]
    return num(rows.iloc[0]) if not rows.empty else np.nan


def fmt_level(value: float, metric: str) -> str:
    if pd.isna(value):
        return "자료 없음"
    if metric.endswith("_pct"):
        return f"{value:.2f}%" if value < 10 else f"{value:.1f}%"
    if metric == "평균체류시간_분":
        return f"{value / 60:.1f}시간"
    if metric == "평균숙박일수":
        return f"{value:.2f}일"
    if metric == "내국인관광소비_천원":
        return f"{value / 100_000:,.0f}억 원"
    if metric == "방문자대비관광소비_천원_proxy":
        return f"{value:.2f}천 원"
    if metric == "외지인방문자수":
        return f"{value / 10_000:,.0f}만 명"
    if metric == "숙박검색건수":
        return f"{value:,.0f}건"
    if metric == "DSI":
        return f"{value:.3f}"
    return f"{value:,.0f}"


def fmt_change(value: float, metric: str) -> str:
    if pd.isna(value):
        return "–"
    return f"{value:+.2f}%p" if metric.endswith("_pct") else f"{value:+.1f}%"


def stage_change(region: str, metric: str, interval: str) -> tuple[float, str]:
    gcol, pcol, scol, *_ = INTERVALS[interval]
    row = growth_row(region, metric)
    if row is None:
        return np.nan, "NA"
    value = num(row.get(pcol if metric.endswith("_pct") else gcol))
    code = str(row.get(scol)) if pd.notna(row.get(scol)) else "NA"
    return value, code if code in STATUS else "NA"


def spread_info(region: str, interval: str) -> dict | None:
    key = INTERVALS[interval][5]
    s = DATA["spread"]
    rows = s.loc[s["지역키"].eq(region) & s["영역"].eq("소비") & s["변화구간"].eq(key)]
    return None if rows.empty else rows.iloc[0].to_dict()


def its_strength(region: str, metric: str, effect: str) -> dict:
    """Confidence label for an ITS coefficient (report 5-5 rule)."""
    its = DATA["its"]
    rows = its.loc[its["지역키"].eq(region) & its["지표"].eq(metric)]
    if rows.empty:
        return {"label": "자료 없음", "beta": np.nan, "p": np.nan, "q": np.nan, "n": 0, "pct": np.nan}
    row = rows.iloc[0]
    if effect == "즉시수준변화":
        beta, p, q, pct = row["즉시수준변화_beta"], row["즉시수준변화_p"], row["즉시수준변화_q_BH"], row["즉시변화_환산_pct"]
    else:
        beta, p, q, pct = row["지정후_기울기변화_beta"], row["지정후_기울기변화_p"], row["지정후_기울기변화_q_BH"], row["기울기변화_월환산_pct"]
    rob = DATA["its_robustness"]
    rob = rob.loc[rob["지역키"].eq(region) & rob["지표"].eq(metric) & rob["계수"].eq(effect)]
    n_ok = int(pd.to_numeric(rob["p05_유의_lag수"], errors="coerce").fillna(0).sum())
    if pd.notna(q) and q < .05 and n_ok >= 8:
        label = "강함"
    elif n_ok >= 6:
        label = "중간"
    elif pd.notna(p) and p < .10:
        label = "약함"
    else:
        label = "신호 없음"
    return {"label": label, "beta": num(beta), "p": num(p), "q": num(q), "n": n_ok, "pct": num(pct)}


def its_effect_text(metric: str, info: dict, effect: str) -> str:
    if pd.isna(info["beta"]):
        return "자료 없음"
    if metric in LOG_METRICS:
        size = info["pct"] if pd.notna(info["pct"]) else (np.exp(info["beta"]) - 1) * 100
        text = f"{size:+.1f}%" + ("/월" if effect != "즉시수준변화" else "")
    elif metric.endswith("_pct"):
        text = f"{info['beta']:+.2f}%p" + ("/월" if effect != "즉시수준변화" else "")
    elif metric == "평균체류시간_분":
        text = f"{info['beta']:+.1f}분" + ("/월" if effect != "즉시수준변화" else "")
    else:
        text = f"{info['beta']:+.3f}" + ("/월" if effect != "즉시수준변화" else "")
    return text


def month_text(value: object) -> str:
    text = str(int(value)) if pd.notna(value) else ""
    return f"{text[:4]}.{text[4:]}" if len(text) == 6 else text


def site_image(region: str) -> Image.Image | None:
    for folder in (ROOT / "웰니스관광지_사진", ROOT, ROOT / "assets"):
        path = folder / SITE_IMAGE_NAMES[region]
        if path.exists():
            with Image.open(path) as source:
                return ImageOps.fit(source.convert("RGB"), (720, 480), method=Image.Resampling.LANCZOS)
    return None


# ---------------------------------------------------------------------------
# HTML 조각
# ---------------------------------------------------------------------------
DATA_NEEDS = {
    "전북완주": [
        ("시설 직접 이용", "아원고택 예약·방문·숙박 구분 실적"),
        ("숙박 공급", "데이터랩 숙박업 개폐업·객실 수로 숙소 부족인지 확인"),
        ("숙박 원인", "방문객 숙박지·예약·이동 동선"),
    ],
    "전북순창": [
        ("시설 직접 이용", "검색 이후 예약·실방문 전환 실적"),
        ("접근성", "거점 도시별 대중교통·셔틀 이용 자료"),
        ("이탈 원인", "가격·후기·예약 단계 이탈 자료"),
    ],
    "전남완도": [
        ("시설 직접 이용", "해양치유센터 예약·프로그램·재방문 실적"),
        ("이용 전환", "군 방문객 중 센터 실제 이용 비율"),
        ("소비 경로", "체류 중 활동·결제 경로와 타 읍면 이동"),
    ],
    "전북무주": [
        ("시설 직접 이용", "태권도원 방문·예약·체험 인원"),
        ("방문 목적", "웰니스 목적 방문 여부와 만족도"),
        ("체류 원인", "당일·연박 목적과 이동 동선"),
    ],
}
TABLE_METRICS = [
    "숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "평균숙박일수", "내국인관광소비_천원",
    "방문자대비관광소비_천원_proxy", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI",
]


def period_table_html(region: str) -> str:
    story_stages = {m: s for s, m, *_ in STAGES}
    bneck_metrics = {m for s, m, *_ in STAGES if s in STORY[region]["bottleneck"]}
    head = "".join(f"<th>{PERIOD_SHORT[p]}</th>" for p in PERIODS) + "<th>지정 전</th><th>지정 직후</th><th>2년차</th>"
    rows = []
    for metric in TABLE_METRICS:
        r = growth_row(region, metric)
        levels = "".join(f"<td>{fmt_level(kpi_value(region, p, metric), metric)}</td>" for p in PERIODS)
        changes = ""
        for gcol, pcol, scol in [("g12_pct", "delta12_pctp", None), ("g23_pct", "delta23_pctp", "지정직후_판정_3pct"), ("g34_pct", "delta34_pctp", "2년차_판정_3pct")]:
            value = num(r.get(pcol if metric.endswith("_pct") else gcol)) if r is not None else np.nan
            if scol and r is not None and str(r.get(scol)) in STATUS:
                cls = STATUS[str(r.get(scol))][2]
            elif r is not None and pd.notna(num(r.get(gcol))):
                rel = num(r.get(gcol))  # 판정은 %p가 아니라 상대 증감률 ±3% 기준
                cls = "up" if rel > 3 else ("down" if rel < -3 else "flat")
            else:
                cls = "na"
            changes += f'<td class="c-{cls}" style="font-weight:750">{fmt_change(value, metric)}</td>'
        stage = story_stages.get(metric)
        label = f'{METRIC_LABEL[metric]}' + (f' <small style="color:var(--muted)">· {stage}</small>' if stage else "")
        style = ' style="background:var(--down-bg)"' if metric in bneck_metrics else ""
        rows.append(f"<tr{style}><td><b>{label}</b></td>{levels}{changes}</tr>")
    return (
        f'<table class="rel"><thead><tr><th>지표</th>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table>'
        '<div style="font-size:.72rem;color:var(--muted);margin-top:.35rem">붉은 배경 = 막힌 칸 지표</div>'
    )


def sec_head(number: int, title: str, sub: str) -> None:
    st.markdown(
        f'<div class="sec-head"><h3>{number}. {escape(title)}</h3><span class="sub">{escape(sub)}</span></div>',
        unsafe_allow_html=True,
    )


def stage_tooltip(region: str, stage: str, metric: str, desc: str, source: str) -> str:
    if metric == "SPREAD":
        parts = [f'<div class="t-head">{stage} · {desc}</div>']
        rows = []
        for interval in INTERVALS:
            info = spread_info(region, interval)
            if info:
                rows.append(
                    f'<tr><td>{interval.split(" (")[0]}</td><td>{info["시설동_점유율_before_pct"]:.1f}% → {info["시설동_점유율_after_pct"]:.1f}%</td></tr>'
                    f'<tr><td>&nbsp;시설 읍면 / 군 전체 성장</td><td>{info["시설동_성장률_pct"]:+.1f}% / {info["시군구_성장률_pct"]:+.1f}%</td></tr>'
                )
        if rows:
            parts.append("<table>" + "".join(rows) + "</table>")
            parts.append('<div class="t-note">읍면 소비 비중은 소수점 한 자리로 공개되어 방향만 참고합니다.</div>')
        else:
            parts.append('<div class="t-note">지정 전후 구간과 맞는 읍면동 자료가 없어 판정하지 않았습니다.</div>')
        return '<div class="tipbox">' + "".join(parts) + "</div>"

    values = "".join(
        f"<tr><td>{PERIOD_SHORT[p]}</td><td>{fmt_level(kpi_value(region, p, metric), metric)}</td></tr>" for p in PERIODS
    )
    level = its_strength(region, metric, "즉시수준변화")
    slope = its_strength(region, metric, "지정후기울기변화")
    its_rows = ""
    if level["label"] != "자료 없음":
        its_rows = (
            f'<tr><td>지정 시점 계단</td><td>{its_effect_text(metric, level, "즉시수준변화")} · {level["label"]}</td></tr>'
            f'<tr><td>지정 후 속도 변화</td><td>{its_effect_text(metric, slope, "기울기")} · {slope["label"]}</td></tr>'
        )
    extra = ""
    if metric == "내국인관광소비_천원":
        extra = "".join(
            f"<tr><td>방문자 대비 · {PERIOD_SHORT[p]}</td><td>{fmt_level(kpi_value(region, p, '방문자대비관광소비_천원_proxy'), '방문자대비관광소비_천원_proxy')}</td></tr>"
            for p in ("P2", "P3", "P4")
        )
    return (
        f'<div class="tipbox"><div class="t-head">{stage} · {desc} <span style="color:#A9BDB2">({source})</span></div>'
        f"<table>{values}{extra}</table>"
        + (f"<b>지정 시점 확인 (ITS)</b><table>{its_rows}</table>" if its_rows else "")
        + '<div class="t-note">±3% 기준 방향 판정 · 확인 강도는 8가지 조건(보정 1·3·6·12개월 × 시작월 2개) 기준</div></div>'
    )


def pipeline_html(region: str, interval: str) -> str:
    story = STORY[region]
    after = INTERVALS[interval][4]
    cards = []
    for idx, (stage, metric, desc, source) in enumerate(STAGES, 1):
        is_bneck = stage in story["bottleneck"]
        if metric == "SPREAD":
            info = spread_info(region, interval)
            if info:
                value_text = f'{info["시설동_점유율_after_pct"]:.1f}%'
                change_val = info["시설동_점유율변화_pctp"]
                code = "INFO"
                change_html = f'<span class="c-info">{change_val:+.1f}%p</span><span class="j j-info">{"시설지 집중" if change_val > 0 else "분산"}</span>'
            else:
                value_text, code = "자료 없음", "NA"
                change_html = '<span class="c-na">–</span><span class="j j-na">판정 안 함</span>'
            sig = "읍면동 비중"
        else:
            value = kpi_value(region, after, metric)
            change_val, code = stage_change(region, metric, interval)
            label, arrow, cls = STATUS[code]
            value_text = fmt_level(value, metric)
            change_html = f'<span class="c-{cls}">{arrow} {fmt_change(change_val, metric)}</span><span class="j j-{cls}">{label}</span>'
            level = its_strength(region, metric, "즉시수준변화")
            sig = f'ITS 계단 {level["label"]}' if level["label"] != "자료 없음" else "ITS 대상 아님"
        cls = STATUS[code][2]
        tag = ""
        band = '<div class="bneck-band">막힌 칸</div>' if is_bneck else ""
        cards.append(
            f'<div class="stage tip {cls}{" bneck" if is_bneck else ""}">{band}'
            f'<div class="stage-top"><span class="stage-no">{idx}</span><span class="stage-name">{stage}</span>{tag}</div>'
            f'<div class="stage-metric">{desc}</div>'
            f'<div class="stage-value">{value_text}</div>'
            f'<div class="stage-change">{change_html}</div>'
            f'<div class="stage-sig">{sig}</div>'
            f"{stage_tooltip(region, stage, metric, desc, source)}</div>"
        )
    parts = []
    for idx, card in enumerate(cards):
        if idx:
            broken = STAGES[idx][0] in story["bottleneck"]
            parts.append(f'<div class="conn{" broken" if broken else ""}">{"✕" if broken else "›"}</div>')
        parts.append(card)
    return f'<div class="pipeline{" has-b" if story["bottleneck"] else ""}">' + "".join(parts) + "</div>"


def check_panel(region: str) -> str:
    metric = STORY[region]["check_metric"]
    target = kpi_value(region, "P2", metric)
    current = kpi_value(region, "P4", metric)
    low = min(kpi_value(region, p, metric) for p in PERIODS if pd.notna(kpi_value(region, p, metric)))
    high = max(target, current)
    span = (high - low) or 1
    lo = low - span * .35
    hi = high + span * .15
    pos = lambda v: max(0, min(100, (v - lo) / (hi - lo) * 100))  # noqa: E731
    recovered = current >= target * .97
    gap = (current / target - 1) * 100
    gap_text = f"{current - target:+.2f}%p" if metric.endswith("_pct") else f"{gap:+.1f}%"
    state = (
        '<span class="state" style="background:var(--up-bg);color:var(--up)">회복</span>'
        if recovered else '<span class="state" style="background:var(--down-bg);color:var(--down)">아직 미회복</span>'
    )
    color = "var(--up)" if recovered else "var(--down)"
    return (
        f'<div class="check tip"><div class="row"><span class="name">{METRIC_LABEL[metric]}</span>{state}</div>'
        f'<div style="font-size:.76rem;color:var(--muted);margin-top:.2rem">목표: 지정 직전 수준 회복 · 지금 목표 대비 <b style="color:{color}">{gap_text}</b></div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pos(current):.0f}%;background:{color}"></div>'
        f'<div class="bar-target" style="left:{pos(target):.0f}%"></div></div>'
        f'<div class="bar-labels"><span>지금(2년차) <b>{fmt_level(current, metric)}</b></span><span>목표(지정 직전) <b>{fmt_level(target, metric)}</b></span></div>'
        f'<div class="tipbox"><div class="t-head">{METRIC_LABEL[metric]} 네 구간</div><table>'
        + "".join(f"<tr><td>{PERIOD_SHORT[p]}</td><td>{fmt_level(kpi_value(region, p, metric), metric)}</td></tr>" for p in PERIODS)
        + '</table><div class="t-note">검은 세로선이 목표(지정 직전 값)입니다.</div></div></div>'
    )


def early_warning_rows(region: str) -> list[dict]:
    rows = []
    for stage, metric, _, _ in STAGES[:5]:
        r = growth_row(region, metric)
        if r is None or str(r.get("지정직후_판정_3pct")) != "DOWN":
            continue
        p2, p4 = num(r["P2"]), num(r["P4"])
        cum = (p4 / p2 - 1) * 100
        signals = [its_strength(region, metric, eff) for eff in ("즉시수준변화", "지정후기울기변화")]
        negative = [s for s in signals if pd.notna(s["beta"]) and s["beta"] < 0 and s["label"] != "신호 없음"]
        order = ["강함", "중간", "약함"]
        signal = min((s["label"] for s in negative), key=order.index) if negative else "신호 없음"
        rows.append({
            "stage": stage, "metric": metric, "y1": num(r["g23_pct"]), "cum": cum,
            "recovered": cum >= -3, "signal": signal,
        })
    return rows


def its_chart(region: str, metric: str) -> go.Figure:
    m = DATA["monthly"].loc[DATA["monthly"]["지역키"].eq(region)].copy().sort_values("기준년월")
    m["날짜"] = pd.to_datetime(m["기준년월"].astype(str), format="%Y%m")
    if metric == "방문자대비관광소비_천원_proxy":
        y = num(m["내국인관광소비_천원"]) / num(m["외지인방문자수"])
    else:
        y = num(m[metric])
    its = DATA["its"].loc[DATA["its"]["지역키"].eq(region)]
    start = int(its["개입시작월"].iloc[0]) if not its.empty else int(SITES.loc[SITES["지역키"].eq(region), "선정연도"].iloc[0]) * 100 + 4
    start_date = pd.to_datetime(str(start), format="%Y%m")
    fig = go.Figure()
    valid = y.notna().to_numpy()
    if valid.sum() >= 24:
        use_log = metric in LOG_METRICS
        yt = np.log1p(y) if use_log else y
        t = np.arange(len(m), dtype=float)
        post = (m["날짜"] >= start_date).to_numpy().astype(float)
        t0 = t[post.argmax()] if post.any() else len(t)
        post_trend = (t - t0) * post
        months = pd.get_dummies(m["날짜"].dt.month, drop_first=True).to_numpy(dtype=float)
        x = np.column_stack([np.ones_like(t), t, post, post_trend, months])
        beta, *_ = np.linalg.lstsq(x[valid], yt.to_numpy()[valid], rcond=None)
        x_cf = x.copy()
        x_cf[:, 2:4] = 0
        fitted, counter = x @ beta, x_cf @ beta
        if use_log:
            fitted, counter = np.expm1(fitted), np.expm1(counter)
        fig.add_trace(go.Scatter(x=m["날짜"], y=fitted, mode="lines", name="계절 반영 추정선",
                                 line={"color": "#2F8F6B", "width": 2.4},
                                 hovertemplate="%{x|%Y.%m} 추정 %{y:,.2f}<extra></extra>"))
        mask = post.astype(bool)
        fig.add_trace(go.Scatter(x=m["날짜"][mask], y=counter[mask], mode="lines", name="지정 전 흐름이 이어졌다면",
                                 line={"color": "#D2513A", "width": 2, "dash": "dash"},
                                 hovertemplate="%{x|%Y.%m} 지정 전 흐름 %{y:,.2f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=m["날짜"], y=y, mode="markers", name="실제 값",
                             marker={"color": "#8FA39A", "size": 6},
                             hovertemplate="%{x|%Y.%m} 실제 %{y:,.2f}<extra></extra>"))
    fig.add_vline(x=start_date, line_dash="dot", line_color="#14261E")
    fig.add_annotation(x=start_date, y=1, yref="paper", text="지정", showarrow=False, xanchor="left", font={"size": 11, "color": "#14261E"})
    fig.update_layout(
        height=340, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        legend=dict(orientation="h", y=1.12, x=0, font={"size": 11}), hovermode="x unified",
        xaxis=dict(showgrid=False, tickformat="%y.%m"), yaxis=dict(gridcolor="#E6EDE9", title=METRIC_LABEL.get(metric, metric)),
        font=dict(family="Pretendard", size=11, color="#3E5249"),
    )
    return fig


def index_chart(region: str) -> go.Figure:
    story = STORY[region]
    palette = {"관심": "#8FA39A", "방문": "#3F6FA8", "숙박": "#C8932B", "체류": "#2F8F6B", "소비": "#8C5BB5"}
    fig = go.Figure()
    for stage, metric, desc, _ in STAGES[:5]:
        values = [kpi_value(region, p, metric) for p in PERIODS]
        base = next((v for v in values if pd.notna(v) and v), np.nan)
        idx = [v / base * 100 if pd.notna(v) and pd.notna(base) else None for v in values]
        is_b = stage in story["bottleneck"]
        fig.add_trace(go.Scatter(
            x=[PERIOD_SHORT[p] for p in PERIODS], y=idx, mode="lines+markers", name=f"{stage} ({desc})",
            line={"color": "#D2513A" if is_b else palette[stage], "width": 4.5 if is_b else 2},
            marker={"size": 9 if is_b else 6}, opacity=1 if is_b else .75,
            customdata=[fmt_level(v, metric) for v in values],
            hovertemplate=f"<b>{stage}</b> %{{x}}<br>지수 %{{y:.1f}} · 실제 %{{customdata}}<extra></extra>",
        ))
    fig.add_vrect(x0=1.5, x1=3.5, fillcolor="#2F8F6B", opacity=.06, line_width=0)
    fig.add_annotation(x=2.5, y=1.06, yref="paper", text="지정 이후", showarrow=False, font={"size": 11, "color": "#2F8F6B"})
    fig.add_hline(y=100, line_dash="dot", line_color="#B5C4BB")
    fig.update_layout(
        height=340, margin=dict(l=8, r=8, t=30, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="white",
        legend=dict(orientation="h", y=-.15, x=0, font={"size": 11}),
        yaxis=dict(gridcolor="#E6EDE9", title="첫 구간 = 100"), xaxis=dict(showgrid=False),
        font=dict(family="Pretendard", size=11, color="#3E5249"),
    )
    return fig


def selection_map(selected: str) -> go.Figure:
    municipal = geojson(MUNICIPAL_BOUNDARY_PATH)
    names = [f["properties"]["NAME_2"] for f in municipal["features"]]
    site_geo = dict(zip(SITES["geo_name"], SITES["지역키"]))
    selected_geo = SITES.loc[SITES["지역키"].eq(selected), "geo_name"].iloc[0]
    z = [2 if n == selected_geo else (1 if n in site_geo else 0) for n in names]
    muni = go.Choropleth(
        geojson=municipal, locations=names, z=z, featureidkey="properties.NAME_2",
        colorscale=[[0, "#E6F0E9"], [.33, "#E6F0E9"], [.34, "#C9E3D2"], [.66, "#C9E3D2"], [.67, "#86C29E"], [1, "#86C29E"]],
        zmin=0, zmax=2, marker_line_color="#FFFFFF", marker_line_width=1.1, showscale=False, hoverinfo="skip",
    )
    provinces = geojson(BOUNDARY_PATH)
    pnames = [f["properties"]["NAME_1"] for f in provinces["features"]]
    prov = go.Choropleth(
        geojson=provinces, locations=pnames, z=[1] * len(pnames), featureidkey="properties.NAME_1",
        colorscale=[[0, "rgba(0,0,0,0)"], [1, "rgba(0,0,0,0)"]], marker_line_color="#6FA58A", marker_line_width=2,
        showscale=False, hoverinfo="skip",
    )
    pts = SITES.copy()
    pts["sel"] = pts["지역키"].eq(selected)
    pts["유형"] = pts["지역키"].map(lambda k: STORY[k]["type"])
    pts["막힌칸"] = pts["지역키"].map(lambda k: STORY[k]["bottleneck_label"])
    custom = pts[["지역키", "시설", "유형", "막힌칸", "지역"]]
    hover = "<b>%{customdata[1]}</b> · %{customdata[4]}<br>진단: %{customdata[2]}<br>막힌 칸: %{customdata[3]}<br><i>클릭해서 선택</i><extra></extra>"
    halo = go.Scattergeo(
        lon=pts["경도"], lat=pts["위도"], mode="markers", customdata=custom, hovertemplate=hover,
        marker={"size": np.where(pts["sel"], 50, 38), "color": np.where(pts["sel"], "rgba(47,143,107,.30)", "rgba(255,255,255,.85)"),
                "line": {"color": np.where(pts["sel"], "#2F8F6B", "#9CC9AE").tolist(), "width": np.where(pts["sel"], 2.5, 1.5).tolist()}},
        selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": 1}},
    )
    # 잎 이모지 위에 투명 마커를 겹쳐야 클릭 선택이 잡힌다
    leaf = go.Scattergeo(
        lon=pts["경도"], lat=pts["위도"], mode="markers+text", text=["🌿"] * len(pts), customdata=custom, hovertemplate=hover,
        textfont={"size": np.where(pts["sel"], 28, 20).tolist()}, textposition="middle center",
        marker={"size": np.where(pts["sel"], 50, 38), "color": "rgba(0,0,0,0)"},
        selected={"marker": {"opacity": 1}}, unselected={"marker": {"opacity": 1}},
    )
    # 완주·무주가 가까워 라벨 방향을 나눈다
    positions = {"전북완주": "middle left", "전북무주": "bottom center", "전북순창": "bottom center", "전남완도": "bottom center"}
    pad = {"middle left": "{}   ", "middle right": "   {}", "bottom center": "<br><br>{}"}
    label = go.Scattergeo(
        lon=pts["경도"], lat=pts["위도"], mode="text",
        text=[pad[positions[k]].format(f"<b>{r}</b>" if s else r) for k, r, s in zip(pts["지역키"], pts["지역"], pts["sel"])],
        textposition=[positions[k] for k in pts["지역키"]],
        textfont={"size": 13, "color": np.where(pts["sel"], "#14261E", "#4E6359").tolist(), "family": "Pretendard"},
        hoverinfo="skip",
    )
    fig = go.Figure([muni, prov, halo, leaf, label])
    fig.update_layout(
        height=430, margin=dict(l=0, r=0, t=0, b=0), showlegend=False, clickmode="event+select", dragmode=False,
        paper_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#14261E", font_color="#EAF2ED", font_family="Pretendard", bordercolor="#14261E"),
        geo=dict(bgcolor="rgba(0,0,0,0)", showland=False, showcountries=False, showcoastlines=False, showframe=False,
                 projection={"type": "mercator", "scale": 1.2}, center={"lat": 35.2, "lon": 127.1},
                 lonaxis={"range": [125.95, 128.25]}, lataxis={"range": [33.95, 36.35]}),
    )
    return fig


def selected_from_map(event: object) -> str | None:
    try:
        points = event.selection.points
    except AttributeError:
        try:
            points = event["selection"]["points"]
        except (KeyError, TypeError):
            return None
    # 시군구 면도 선택 이벤트에 섞여 오므로 관광지 키가 있는 점을 찾는다
    for point in points or []:
        custom = (point or {}).get("customdata")
        key = custom.get("0") if isinstance(custom, dict) else (custom[0] if isinstance(custom, (list, tuple)) and custom else None)
        if key in STORY:
            return key
    return None


# ---------------------------------------------------------------------------
# 화면
# ---------------------------------------------------------------------------
if st.session_state.get("v4_site") not in set(SITES["지역키"]):
    st.session_state.v4_site = SITES.iloc[0]["지역키"]
selected = st.session_state.v4_site
site = SITES.loc[SITES["지역키"].eq(selected)].iloc[0]
story = STORY[selected]
periods = DATA["periods"].loc[DATA["periods"]["지역키"].eq(selected)].set_index("기간")
announce = str(periods["공식발표일"].iloc[0])

st.markdown(
    f'<div class="topbar"><div class="brand"><strong>WELL-FLOW <span>Monitor</span></strong><span>웰니스 관광지 성과 진단</span></div>'
    f'<div class="top-meta">{escape(site["지역"])} 분석기간 · {month_text(periods.loc["P1", "시작월"])}–{month_text(periods.loc["P4", "종료월"])} · 선정월 기준</div></div>'
    '<div class="map-head"><b>전라도 웰니스 관광지 위치</b><span>잎을 클릭해 선택 · 진한 초록 · 현재 선택</span></div>',
    unsafe_allow_html=True,
)

# 지도 + 진단 카드 ----------------------------------------------------------
map_col, card_col = st.columns([1, 1.15], gap="medium")
with map_col:
    with st.container(border=True, height="stretch"):
        event = st.plotly_chart(
            selection_map(selected), width="stretch", key="v4_map", on_select="rerun", selection_mode="points",
            config={"displayModeBar": False, "scrollZoom": False, "doubleClick": False},
        )
        clicked = selected_from_map(event)
        if clicked and clicked != selected:
            st.session_state.v4_site = clicked
            st.rerun()
with card_col:
    with st.container(border=True, height="stretch"):
        photo_col, info_col = st.columns([.8, 1.2], gap="medium")
        with photo_col:
            photo = site_image(selected)
            if photo is not None:
                st.image(photo, width="stretch")
        with info_col:
            catalog = DATA["site_catalog"].loc[DATA["site_catalog"]["시설명"].eq(ALIASES.get(site["시설"], site["시설"]))]
            theme = str(catalog.iloc[0]["테마"]) if not catalog.empty and "테마" in catalog else "웰니스"
            st.markdown(
                f'<div class="card-label">선택 관광지</div><div class="site-name">{escape(site["시설"])}</div>'
                f'<div class="site-loc">{escape(site["지역"])} {escape(site["시설동"])} · {int(site["선정연도"])}년 지정 · {escape(theme)} 테마</div>'
                f'<div style="margin-top:.6rem;display:flex;gap:6px;flex-wrap:wrap"><span class="pill pill-type">{escape(story["type"])}</span>'
                f'<span class="pill pill-bneck">막힌 칸 · {escape(story["bottleneck_label"])}</span></div>',
                unsafe_allow_html=True,
            )
        check_metric = story["check_metric"]
        st.markdown(
            f'<div class="headline">{escape(story["headline"])}</div>'
            f'<div class="chips">'
            f'<div class="chip"><small>막힌 칸</small><b>{escape(story["bottleneck_label"])}</b></div>'
            f'<div class="chip"><small>확인 강도</small><b><span class="sbadge {STRENGTH_CLASS[story["strength"]]}">{escape(story["strength"])}</span></b></div>'
            f'<div class="chip"><small>다음 점검 지표</small><b>{escape(METRIC_LABEL[check_metric])}</b></div></div>',
            unsafe_allow_html=True,
        )

# 1. 여섯 칸 ---------------------------------------------------------------
sec_head(1, "병목 진단", "지정 전후 여섯 단계의 변화 · 카드에 마우스를 올리면 네 구간 값과 통계 근거")
with st.container(border=True):
    interval = st.segmented_control("비교 구간", list(INTERVALS), default=list(INTERVALS)[0], label_visibility="collapsed", key="v4_interval")
    interval = interval or list(INTERVALS)[0]
    downs = [s for s, m, *_ in STAGES[:5] if stage_change(selected, m, interval)[1] == "DOWN"]
    down_text = "·".join(downs) if downs else "없음"
    st.markdown(
        f'<div class="flow-banner"><div class="msg">막힌 칸은 <em>{escape(story["bottleneck_label"])}</em>입니다 · 이 구간 내림 칸: {escape(down_text)}</div>'
        '<div class="legend"><span><i style="background:var(--up)"></i>오름 (+3% 초과)</span><span><i style="background:var(--flat)"></i>유지</span>'
        '<span><i style="background:var(--down)"></i>내림 (−3% 미만)</span><span><i style="background:var(--na)"></i>자료 없음</span>'
        '<span><i style="background:#fff;border:2px solid var(--down)"></i>막힌 칸</span></div></div>',
        unsafe_allow_html=True,
    )
    st.markdown(pipeline_html(selected, interval), unsafe_allow_html=True)
    st.markdown(f'<div class="note"><b>왜 여기가 막혔나</b> · {escape(story["evidence"])}</div>', unsafe_allow_html=True)

# 2. 처방 ----------------------------------------------------------------
sec_head(2, "처방", "막힌 칸에 맞춘 권장·지양 사업과 다음 점검 지표")
rx_col, plan_col = st.columns([1.5, 1], gap="medium")
with rx_col:
    with st.container(border=True, height="stretch"):
        do_items = "".join(
            f'<div class="rx-item"><span class="ic">{i}</span><div><b>{escape(t)}</b><span>{escape(d)}</span></div></div>'
            for i, (t, d) in enumerate(story["recommend"], 1)
        )
        dont_items = "".join(
            f'<div class="rx-item"><span class="ic">✕</span><div><b>{escape(t)}</b><span>{escape(d)}</span></div></div>'
            for t, d in story["avoid"]
        )
        st.markdown(
            f'<div class="rx-bneck"><small>막힌 칸 · 확인 강도 {escape(story["strength"])}</small><div class="what">{escape(story["bottleneck_label"])}</div>'
            f'<p>{escape(story["headline"])}</p></div>'
            f'<div class="rx-cols"><div class="rx-box rx-do"><h4>권장 사업</h4>{do_items}</div>'
            f'<div class="rx-box rx-dont"><h4>지양 사업</h4>{dont_items}</div></div>'
            f'<div class="rx-good"><b>이미 괜찮은 칸</b> · {escape(story["good"])}</div>',
            unsafe_allow_html=True,
        )
with plan_col:
    with st.container(border=True, height="stretch"):
        st.markdown('<div class="card-label">다음 점검 지표</div>', unsafe_allow_html=True)
        st.markdown(check_panel(selected), unsafe_allow_html=True)
        steps = "".join(
            f'<div class="step{" now" if i == 0 else ""}"><span class="dot">{i + 1}</span><div><small>{escape(when)}</small><div class="txt">{escape(what)}</div></div></div>'
            for i, (when, what) in enumerate(story["actions"])
        )
        st.markdown(f'<div class="card-label" style="margin-top:1rem">정책 단계 추천</div><div class="steps" style="margin-top:.6rem">{steps}</div>', unsafe_allow_html=True)

# 3. 조기 경보 + 지역 비교 -------------------------------------------------
sec_head(3, "조기 경보 · 지역 비교", "1년차에 강하게 확인된 하락은 2년차에도 남는 경향")
ew_col, mx_col = st.columns([1, 1.35], gap="medium")
with ew_col:
    with st.container(border=True, height="stretch"):
        st.markdown('<div class="card-label">1년차에 내려간 칸의 2년차 회복 여부</div>', unsafe_allow_html=True)
        rows = early_warning_rows(selected)
        if rows:
            body = "".join(
                f'<tr><td>{r["stage"]}<br><small style="color:var(--muted);font-weight:500">{METRIC_LABEL[r["metric"]]}</small></td>'
                f'<td class="c-down">{r["y1"]:+.1f}%</td><td>{r["cum"]:+.1f}%</td>'
                f'<td><span class="sbadge {STRENGTH_CLASS[r["signal"]]}">{r["signal"]}</span></td>'
                f'<td>{"<span class=verdict-ok>회복</span>" if r["recovered"] else "<span class=verdict-warn>미회복</span>"}</td></tr>'
                for r in rows
            )
            st.markdown(
                '<table class="ew"><thead><tr><th>칸</th><th>1년차</th><th>2년차 누적</th><th>1년차 신호</th><th>2년차</th></tr></thead>'
                f"<tbody>{body}</tbody></table>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="note">지정 1년차에 내려간 칸이 없습니다.</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="note"><b>읽는 법</b> · 1년차 신호가 <span class="sbadge s-strong">강함</span>이면 다음 해 사업을 배정하고, '
            '<span class="sbadge s-none">신호 없음</span>인 하락은 한 해 더 지켜봅니다. 2년차 누적은 지정 직전 대비이며 −3% 이내면 회복으로 봅니다.</div>',
            unsafe_allow_html=True,
        )
with mx_col:
    with st.container(border=True, height="stretch"):
        st.markdown('<div class="card-label">4개 지역 비교</div>', unsafe_allow_html=True)
        head = "".join(f"<th>{s}</th>" for s, *_ in STAGES)
        body = []
        for reg in SITES.itertuples():
            cells = []
            for stage, metric, desc, _ in STAGES:
                is_b = stage in STORY[reg.지역키]["bottleneck"]
                if metric == "SPREAD":
                    info = spread_info(reg.지역키, interval)
                    if info:
                        cls, arrow, val = "info", "◦", f'{info["시설동_점유율변화_pctp"]:+.1f}%p'
                        tip = f'{desc}: {info["시설동_점유율_before_pct"]:.1f}% → {info["시설동_점유율_after_pct"]:.1f}%'
                    else:
                        cls, arrow, val, tip = "na", "·", "자료 없음", "읍면동 구간 자료 없음"
                else:
                    change_val, code = stage_change(reg.지역키, metric, interval)
                    label, arrow, cls = STATUS[code]
                    val = fmt_change(change_val, metric)
                    a, b = INTERVALS[interval][3], INTERVALS[interval][4]
                    tip = f"{desc}: {fmt_level(kpi_value(reg.지역키, a, metric), metric)} → {fmt_level(kpi_value(reg.지역키, b, metric), metric)} ({label})"
                body_tip = f'<div class="tipbox"><div class="t-head">{escape(reg.지역)} · {stage}{" · 막힌 칸" if is_b else ""}</div>{escape(tip)}</div>'
                cells.append(f'<td class="cell tip {cls}{" bneck" if is_b else ""}">{arrow}<small>{val}</small>{body_tip}</td>')
            sel = ' class="sel"' if reg.지역키 == selected else ""
            body.append(
                f'<tr{sel}><td class="reg">{escape(reg.지역)}<small>{escape(reg.시설)}</small></td>' + "".join(cells)
                + f'<td class="type">{escape(STORY[reg.지역키]["type"])}</td></tr>'
            )
        st.markdown(
            f'<table class="mx"><thead><tr><th>지역</th>{head}<th>진단 유형</th></tr></thead><tbody>{"".join(body)}</tbody></table>'
            f'<div class="note">위 구간 선택({escape(interval.split(" (")[0])})을 따릅니다. 방문 칸만 보면 완주·완도는 "유지"라 문제가 보이지 않습니다. '
            '네 지역 모두 같은 12개월 기준으로 비교합니다.</div>',
            unsafe_allow_html=True,
        )

# 4. 근거 ----------------------------------------------------------------
sec_head(4, "상세 근거", "")
with st.container(border=True):
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "흐름 추이", "지정 시점 확인 (ITS)", "웰니스 지표", "방문 출발지 · 주변 환경", "네 구간 값 표", "데이터 신뢰도 · 추가 필요 자료",
    ])
    with tab1:
        st.caption("다섯 칸을 첫 구간 = 100으로 맞춘 추이입니다. 굵은 빨간 선이 막힌 칸입니다.")
        st.plotly_chart(index_chart(selected), width="stretch", config={"displayModeBar": False})
    with tab2:
        options = ["숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "내국인관광소비_천원", "방문자대비관광소비_천원_proxy"]
        default = check_metric if check_metric in options else "내국인관광소비_천원"
        metric = st.selectbox("지표", options, index=options.index(default), format_func=lambda x: METRIC_LABEL[x], key="v4_its_metric")
        st.plotly_chart(its_chart(selected, metric), width="stretch", config={"displayModeBar": False})
        if metric in set(DATA["its"].loc[DATA["its"]["지역키"].eq(selected), "지표"]):
            lv, sl = its_strength(selected, metric, "즉시수준변화"), its_strength(selected, metric, "지정후기울기변화")
            st.markdown(
                f'<div class="note">지정 시점 계단 <b>{its_effect_text(metric, lv, "즉시수준변화")}</b> (p={lv["p"]:.3f}, q={lv["q"]:.3f}, {lv["n"]}/8 조건) '
                f'<span class="sbadge {STRENGTH_CLASS[lv["label"]]}">{lv["label"]}</span> · '
                f'지정 후 속도 변화 <b>{its_effect_text(metric, sl, "기울기")}</b> (p={sl["p"]:.3f}, {sl["n"]}/8 조건) '
                f'<span class="sbadge {STRENGTH_CLASS[sl["label"]]}">{sl["label"]}</span><br>'
                '빨간 점선보다 실제 값이 아래에 머물면, 계절과 원래 흐름을 빼도 지정 이후 한 계단 내려앉았다는 뜻입니다. 비교 지역이 없어 인과효과가 아니라 구조변화로 읽습니다.</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown('<div class="note">이 지표는 ITS 표에 없어 추정선만 참고로 그렸습니다.</div>', unsafe_allow_html=True)
    with tab3:
        tiles = []
        for metric in ["숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "DSI", "방문자대비관광소비_천원_proxy"]:
            p2, p3 = kpi_value(selected, "P2", metric), kpi_value(selected, "P3", metric)
            diff = (p3 - p2) if metric.endswith("_pct") else ((p3 / p2 - 1) * 100 if pd.notna(p2) and p2 else np.nan)
            cls = "c-up" if diff > 0 else "c-down"
            diff_text = f"{diff:+.2f}%p" if metric.endswith("_pct") else f"{diff:+.1f}%"
            tiles.append(f'<div class="wl tip"><small>{METRIC_LABEL[metric]}</small><b>{fmt_level(p3, metric)}</b><em class="{cls}">지정 직전 대비 {diff_text}</em>'
                         f'<div class="tipbox">지정 직전 {fmt_level(p2, metric)} → 1년차 {fmt_level(p3, metric)}</div></div>')
        st.markdown('<div class="wl-grid">' + "".join(tiles) + "</div>", unsafe_allow_html=True)
        st.markdown(
            '<div class="note">지정 1년차 기준입니다. WStay = 숙박자 비율 × 숙박객 중 3박 이상 비율(전체 방문자 중 3박 이상 추정 비율). '
            'DSI = 1 − 월별 방문 변동계수(1에 가까울수록 사계절 수요가 고름). 웰니스 지표는 막힌 칸과 별개의 질문입니다.</div>',
            unsafe_allow_html=True,
        )
    with tab4:
        o_col, p_col = st.columns(2, gap="large")
        with o_col:
            origin = DATA["origin"].loc[DATA["origin"]["지역키"].eq(selected) & DATA["origin"]["기간"].eq("P4")].copy()
            st.markdown('<div class="card-label">방문자 출발지 상위 5 · 지정 2년차</div>', unsafe_allow_html=True)
            if origin.empty:
                st.markdown('<div class="note">출발지 자료가 없습니다.</div>', unsafe_allow_html=True)
            else:
                top = origin.nlargest(5, "비율(%)")
                peak = max(float(top["비율(%)"].max()), 1)
                st.markdown("".join(
                    f'<div class="origin-row"><span class="rank">{i}</span><div>{escape(str(r["거주지(시도)"]))} {escape(str(r["거주지(시군구)"]))}'
                    f'<div class="obar-bg"><div class="obar" style="width:{float(r["비율(%)"]) / peak * 100:.0f}%"></div></div></div><b>{float(r["비율(%)"]):.1f}%</b></div>'
                    for i, (_, r) in enumerate(top.iterrows(), 1)
                ), unsafe_allow_html=True)
        with p_col:
            name = ALIASES.get(site["시설"], site["시설"])
            poi = DATA["poi"].loc[DATA["poi"]["시설명"].eq(name)]
            poi_map = poi.set_index("구분")["totalCount"].to_dict() if not poi.empty else {}
            nearest = DATA["nearest"].loc[DATA["nearest"]["시설명"].eq(name)]
            near = f'최근접 숙박 {float(nearest.iloc[0]["최근접_거리_km"]):.2f}km · {nearest.iloc[0]["최근접_업체명"]}' if not nearest.empty else "최근접 숙박 자료 없음"
            st.markdown('<div class="card-label">시설 반경 5km 주변 환경</div>', unsafe_allow_html=True)
            st.markdown('<div class="poi-grid">' + "".join(
                f'<div class="poi">{k}<b>{int(poi_map.get(k, 0))}</b></div>' for k in ["숙박", "음식점", "관광지", "문화시설"]
            ) + f'</div><div class="note">{escape(near)} · 숙박 공급은 막힌 칸이 "숙소 부족"인지 "머물 이유 부족"인지 가르는 참고 정보입니다.</div>', unsafe_allow_html=True)
    with tab5:
        st.markdown(period_table_html(selected), unsafe_allow_html=True)
        st.markdown(
            '<div class="note">합계 지표(검색·방문·소비)는 12개월 합계, 비율·시간 지표는 방문객 수(숙박일수·3박+는 숙박객 수)로 가중평균했습니다. '
            '변화 칸 색은 ±3% 기준 판정이며, 비율 지표는 %p로 표시합니다. 한 달이라도 빠진 구간은 계산하지 않았습니다.</div>',
            unsafe_allow_html=True,
        )
    with tab6:
        rel_col, need_col = st.columns([1.1, 1], gap="large")
        with rel_col:
            st.markdown('<div class="card-label">지표별 공간 단위와 확보 수준</div>', unsafe_allow_html=True)
            has_origin = not DATA["origin"].loc[DATA["origin"]["지역키"].eq(selected)].empty
            has_spread = not DATA["spread"].loc[DATA["spread"]["지역키"].eq(selected)].empty
            reliability = [
                ("관심 · 방문", "시군구 월별", "확보", "ok", "티맵 숙박 검색, KT 외지인 방문(내국인만, 외국인 이중계산 제거)"),
                ("숙박 전환 · 체류", "시군구 월별", "확보", "ok", "KT 숙박자 비율·체류시간, 방문객 수 가중평균"),
                ("소비", "시군구 월별", "확보", "ok", "신한카드 내국인 관광소비, 업종별 포함"),
                ("방문자 대비 소비", "시군구", "대리지표", "partial", "카드 이용자와 방문자가 달라 1인당 소비가 아님"),
                ("지역 파급", "읍면동", "확보" if has_spread else "자료 없음", "ok" if has_spread else "missing",
                 "읍면 소비 비중이 소수점 한 자리로 공개되어 방향만 참고" if has_spread else "지정 전후 구간과 맞는 읍면동 자료 없음"),
                ("방문 출발지", "시군구", "확보" if has_origin else "자료 없음", "ok" if has_origin else "missing", "검색 출발지는 광역별 조건부 분포라 광역마다 따로 비교"),
                ("지정 시점 확인(ITS)", "시군구 월별 48개월", "구조변화 근거", "partial", "비교 지역이 없어 인과효과가 아닌 지정 전후 구조변화"),
                ("시설 자체 성과", "시설", "추후 과제", "missing", "데이터랩은 시군구 단위라 시설 이용 실적은 따로 확보 필요"),
            ]
            badge = {"ok": "background:var(--up-bg);color:var(--up)", "partial": "background:var(--flat-bg);color:var(--flat)", "missing": "background:var(--na-bg);color:var(--na)"}
            st.markdown(
                '<table class="rel"><thead><tr><th>지표</th><th>공간 단위</th><th>확보 수준</th><th>주의할 점</th></tr></thead><tbody>'
                + "".join(
                    f'<tr><td><b>{escape(m)}</b></td><td>{escape(u)}</td><td><span class="sbadge" style="{badge[c]}">{escape(s)}</span></td>'
                    f'<td style="color:var(--muted);font-size:.74rem">{escape(n)}</td></tr>'
                    for m, u, s, c, n in reliability
                )
                + "</tbody></table>",
                unsafe_allow_html=True,
            )
        with need_col:
            st.markdown('<div class="card-label">막힌 칸의 원인을 확정하려면 필요한 자료</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="steps" style="margin-top:.6rem">' + "".join(
                    f'<div class="step"><span class="dot">{i}</span><div><small>{escape(title)}</small><div class="txt">{escape(reason)}</div></div></div>'
                    for i, (title, reason) in enumerate(DATA_NEEDS[selected], 1)
                ) + "</div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div class="note">추가 자료를 확보하기 전에는 막힌 칸의 <b>위치</b>까지만 말하고 <b>원인</b>은 확정하지 않습니다. '
                '지자체 사업 예산(사업명·겨냥한 칸·금액·집행 시작월)을 더하면 칸별 투입 대비 효과까지 볼 수 있습니다.</div>',
                unsafe_allow_html=True,
            )

st.markdown(
    '<div class="note" style="margin-top:1.2rem">WELL-FLOW · 한국관광 데이터랩(KT·신한카드·티맵) 공개 자료 · 점검 단위는 시설 소재 시군구 관광시장 · '
    '±3%는 실무용 방향 판정, 확인 강도는 구간 시계열 회귀(월 고정효과, Newey-West, Benjamini-Hochberg) 기준 · 지정의 순효과가 아니라 지정 전후 구조변화입니다.</div>',
    unsafe_allow_html=True,
)
