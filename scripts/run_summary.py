"""
웰니스 관광지 지정효과 분석 — 핵심 지표 재현 스크립트

10개소(2023 코호트 5 + 2024 코호트 5)에 대해 시군구 단위 P1~P4 구간
지표(외지인 방문자수 합계, 관광소비 합계, 체류시간/숙박방문자비율 월평균,
숙박업 지출비중)와 g0/g1/g2 증감률을 계산해 CSV로 저장한다.

실행:
    /home/leafnode55/tour/venv/bin/python3 scripts/run_summary.py

출력:
    output/이전_분석결과/summary_visitors.csv        - 외지인 방문자수 P1~P4, g0/g1/g2
    output/이전_분석결과/summary_stay.csv            - 체류시간·숙박방문자비율 P1~P4, g0/g1/g2
    output/이전_분석결과/summary_consumption.csv     - 관광소비(내국인) P1~P4, g0/g1/g2
    output/이전_분석결과/summary_lodging_category.csv- 숙박업 지출비중 1년차/2년차 증감

주의: 데이터랩 원자료는 다운로드 시점에 따라 기준연월 경계가 조금씩
다르게 잘려 있을 수 있어(§3-3), months_in()으로 정의한 P1~P4 월 목록에
없는 달은 자동으로 제외된다. 표본 크기(zip 개수)가 사이트마다 다를 수
있으므로 결과를 보고서 수치와 대조할 때는 완전 일치가 아니라 "같은
방향·비슷한 크기"인지를 재현성 검증 기준으로 삼는다.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wellness_pipeline import (  # noqa: E402
    COHORT_2023, COHORT_2024, PERIODS, REGION_TO_SITE,
    cohort_of, growth, load_category_share, load_consumption_series,
    load_stay_series, load_visitor_series, period_mean, period_sum,
)

OUT = Path(__file__).resolve().parent.parent / "output" / "이전_분석결과"
OUT.mkdir(parents=True, exist_ok=True)

ALL_REGIONS = COHORT_2023 + COHORT_2024


def summarize_visitors():
    rows = []
    for region in ALL_REGIONS:
        yr = cohort_of(region)
        periods = PERIODS[yr]
        v = load_visitor_series(region)
        v = v[(v["level"] == "시군구") & (v["방문자구분"] == "외지인방문자(b)")]
        vals = {}
        for pname, (s, e) in periods.items():
            vals[pname] = period_sum(v, "방문자수", s, e)
        g0 = growth(vals["P1"], vals["P2"])
        g1 = growth(vals["P2"], vals["P3"])
        g2 = growth(vals["P3"], vals["P4"])
        rows.append({
            "지역": region, "시설": REGION_TO_SITE[region], "코호트": yr,
            "P1": vals["P1"], "P2": vals["P2"], "P3": vals["P3"], "P4": vals["P4"],
            "g0(%)": round(g0, 1), "g1(%)": round(g1, 1), "g2(%)": round(g2, 1),
            "패턴일치(g1>0,g2<g1)": bool(g1 > 0 and g2 < g1),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "summary_visitors.csv", index=False, encoding="utf-8-sig")
    return df


def summarize_stay():
    rows = []
    for region in ALL_REGIONS:
        yr = cohort_of(region)
        periods = PERIODS[yr]
        s = load_stay_series(region)
        vals_stay, vals_ratio = {}, {}
        for pname, (a, b) in periods.items():
            vals_stay[pname] = period_mean(s, "체류시간(분)", a, b)
            vals_ratio[pname] = period_mean(s, "숙박방문자 비율", a, b)
        g1_stay = growth(vals_stay["P2"], vals_stay["P3"])
        g2_stay = growth(vals_stay["P3"], vals_stay["P4"])
        g1_ratio = growth(vals_ratio["P2"], vals_ratio["P3"])
        g2_ratio = growth(vals_ratio["P3"], vals_ratio["P4"])
        rows.append({
            "지역": region, "시설": REGION_TO_SITE[region], "코호트": yr,
            "체류시간_P2": round(vals_stay["P2"], 0), "체류시간_P3": round(vals_stay["P3"], 0),
            "체류시간_P4": round(vals_stay["P4"], 0),
            "체류시간_g1(%)": round(g1_stay, 1), "체류시간_g2(%)": round(g2_stay, 1),
            "숙박비율_P2": round(vals_ratio["P2"], 1), "숙박비율_P3": round(vals_ratio["P3"], 1),
            "숙박비율_P4": round(vals_ratio["P4"], 1),
            "숙박비율_g1(%)": round(g1_ratio, 1), "숙박비율_g2(%)": round(g2_ratio, 1),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "summary_stay.csv", index=False, encoding="utf-8-sig")
    return df


def summarize_consumption():
    rows = []
    for region in ALL_REGIONS:
        yr = cohort_of(region)
        periods = PERIODS[yr]
        c = load_consumption_series(region)
        c = c[(c["level"] == "시군구") & (c["통화구분"] == "내국인")]
        vals = {}
        for pname, (a, b) in periods.items():
            vals[pname] = period_sum(c, "소비액(천원)", a, b)
        g1 = growth(vals["P2"], vals["P3"])
        g2 = growth(vals["P3"], vals["P4"])
        rows.append({
            "지역": region, "시설": REGION_TO_SITE[region], "코호트": yr,
            "관광소비_P2(천원)": vals["P2"], "관광소비_P3(천원)": vals["P3"], "관광소비_P4(천원)": vals["P4"],
            "g1(%)": round(g1, 1), "g2(%)": round(g2, 1),
        })
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "summary_consumption.csv", index=False, encoding="utf-8-sig")
    return df


def summarize_lodging_category():
    """업종별 지출비중(%) x 관광소비 총액으로 추정한 대분류별 절대지출, 1/2년차 증감률.
    §6(업종별 소비 분해)의 숙박업 −15.6%(2023 코호트 2년차) 등을 재현하기 위한 함수."""
    rows = []
    for region in ALL_REGIONS:
        yr = cohort_of(region)
        periods = PERIODS[yr]
        cat = load_category_share(region)
        cons = load_consumption_series(region)
        cons = cons[(cons["level"] == "시군구") & (cons["통화구분"] == "내국인")]
        if cat.empty or cons.empty:
            continue

        def est_spend(period_name: str, category: str) -> float:
            s, e = periods[period_name]
            pk = f"{s}-{e}"
            sub = cat[(cat["period_key"] == pk) & (cat["대분류"] == category)]
            if sub.empty:
                return float("nan")
            share = sub["대분류 지출액 비율"].mean()
            total = period_sum(cons, "소비액(천원)", s, e)
            return total * share / 100.0

        row = {"지역": region, "시설": REGION_TO_SITE[region], "코호트": yr}
        for category in ["숙박업", "식음료업", "쇼핑업", "여가서비스업"]:
            p2, p3, p4 = est_spend("P2", category), est_spend("P3", category), est_spend("P4", category)
            row[f"{category}_g1(%)"] = round(growth(p2, p3), 1) if pd.notna(growth(p2, p3)) else None
            row[f"{category}_g2(%)"] = round(growth(p3, p4), 1) if pd.notna(growth(p3, p4)) else None
        rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "summary_lodging_category.csv", index=False, encoding="utf-8-sig")
    return df


if __name__ == "__main__":
    print("=== 외지인 방문자수 P1~P4 (시군구 합계) ===")
    dfv = summarize_visitors()
    print(dfv.to_string(index=False))

    print("\n=== 체류시간·숙박방문자비율 (시군구 월평균) ===")
    dfs = summarize_stay()
    print(dfs.to_string(index=False))

    print("\n=== 관광소비(내국인, 시군구 합계) ===")
    dfc = summarize_consumption()
    print(dfc.to_string(index=False))

    print("\n=== 업종별 추정 지출 증감률 (2023 코호트 숙박업 2년차 -15.6% 재현 검증) ===")
    dfl = summarize_lodging_category()
    print(dfl.to_string(index=False))
    print("\n2023 코호트 숙박업 g2 평균:", round(dfl[dfl["코호트"] == 2023]["숙박업_g2(%)"].mean(), 2), "(보고서: -15.6%)")

    print(f"\nCSV 저장 완료: {OUT}")
