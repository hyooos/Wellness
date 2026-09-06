"""
전국 숙박업 인허가 원자료(data/문화_숙박업.csv)를 이용한 두 가지 분석:

  A) 88개소 전체 — 20선 잔류 여부와 소재 시군구 숙박업 밀도의 상관관계
  B) 10개 핵심 분석 대상 — 숙박업 유형 구성(호텔/콘도 vs 여관/여인숙/생활숙박)
     및 P1~P4 구간별 신규개업·폐업·순증(§8-4)

실행:
    venv/bin/python3 scripts/lodging_supply_analysis.py

주의: `문화_숙박업.csv`는 2026년 기준 행정구역 개편을 반영한다
(전남+광주 → "전남광주통합특별시", 인천 중구/동구 → 제물포구·영종구·
서해구 등으로 재편). wellness_88.csv의 구 명칭과 매칭되지 않는 3개소
("인천 중구" 소재)는 결측 처리했다.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from scipy.stats import mannwhitneyu

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
OUT.mkdir(exist_ok=True)

SIDO_MAP = {
    "서울": "서울특별시", "부산": "부산광역시", "대구": "대구광역시", "인천": "인천광역시",
    "광주": "전남광주통합특별시", "대전": "대전광역시", "울산": "울산광역시",
    "세종": "세종특별자치시", "경기": "경기도", "강원": "강원특별자치도",
    "충북": "충청북도", "충남": "충청남도", "전북": "전북특별자치도",
    "전남": "전남광주통합특별시", "경북": "경상북도", "경남": "경상남도",
    "제주": "제주특별자치도",
}

SITE10 = {
    "강원영월": ("강원특별자치도", "영월군", 2023),
    "강원삼척": ("강원특별자치도", "삼척시", 2023),
    "경남양산": ("경상남도", "양산시", 2023),
    "경북칠곡": ("경상북도", "칠곡군", 2023),
    "충북제천": ("충청북도", "제천시", 2023),
    "전남완도": ("전남광주통합특별시", "완도군", 2024),
    "전북순창": ("전북특별자치도", "순창군", 2024),
    "충북영동": ("충청북도", "영동군", 2024),
    "전북완주": ("전북특별자치도", "완주군", 2024),
    "경북영주": ("경상북도", "영주시", 2024),
}

PERIODS = {
    2023: {"P1": ("2021-04", "2022-03"), "P2": ("2022-04", "2023-03"),
           "P3": ("2023-04", "2024-03"), "P4": ("2024-04", "2025-03")},
    2024: {"P1": ("2022-04", "2023-03"), "P2": ("2023-04", "2024-03"),
           "P3": ("2024-04", "2025-03"), "P4": ("2025-04", "2026-03")},
}


def load_lodging() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "문화_숙박업.csv", encoding="cp949", low_memory=False)
    df["addr"] = df["도로명주소"].fillna("") + " " + df["지번주소"].fillna("")
    df["인허가일자"] = pd.to_datetime(df["인허가일자"], errors="coerce")
    df["폐업일자"] = pd.to_datetime(df["폐업일자"], errors="coerce")
    return df


def region_mask(ldf: pd.DataFrame, sido_short: str, gugun: str) -> pd.Series:
    sido_full = SIDO_MAP.get(sido_short, sido_short)
    return ldf["addr"].str.contains(re.escape(sido_full), na=False) & \
        ldf["addr"].str.contains(rf"{re.escape(gugun)}\b", na=False, regex=True)


def dong_mask(ldf: pd.DataFrame, sido_short: str, gugun: str, dong: str) -> pd.Series:
    return region_mask(ldf, sido_short, gugun) & \
        ldf["addr"].str.contains(rf"{re.escape(dong)}\b", na=False, regex=True)


# §7(md)에서 행정동 단위 재검증이 확인된 2023 코호트 5개소만 신뢰 가능한 행정동명을
# 보유한다. 2024 코호트는 로컬 데이터에 행정동 단위 다운로드가 없어 제외한다.
SITE_DONG = {
    "강원영월": ("강원특별자치도", "영월군", "상동읍", 2023),
    "강원삼척": ("강원특별자치도", "삼척시", "미로면", 2023),
    "경남양산": ("경상남도", "양산시", "서창동", 2023),
    "경북칠곡": ("경상북도", "칠곡군", "석적읍", 2023),
    "충북제천": ("충청북도", "제천시", "청풍면", 2023),
}


def part_a_88sites(ldf: pd.DataFrame) -> pd.DataFrame:
    wdf = pd.read_csv(ROOT / "wellness_88.csv")
    rows = []
    for _, r in wdf.iterrows():
        parts = str(r["시군구"]).split()
        sido, gugun = (parts[0], parts[1]) if len(parts) >= 2 else (None, None)
        if gugun is None or gugun == "(확인필요)":
            rows.append({**r, "lodging_active": None, "제외사유": "시군구 정보 미기재"})
            continue
        mask = region_mask(ldf, sido, gugun)
        if not mask.any():
            rows.append({**r, "lodging_active": None,
                         "제외사유": f"'{sido} {gugun}' 조합이 원자료에 존재하지 않음(행정구역 개편 가능성)"})
            continue
        sub = ldf[mask]
        active = sub[sub["영업상태명"] == "영업/정상"]
        rows.append({**r, "lodging_active": len(active), "lodging_ever": len(sub), "제외사유": None})
    out = pd.DataFrame(rows)
    out["20선"] = out["20선_2026"].fillna("").str.strip() == "O"
    out.to_csv(OUT / "lodging_88sites.csv", index=False, encoding="utf-8-sig")

    valid = out.dropna(subset=["lodging_active"])
    a = valid[valid["20선"]]["lodging_active"]
    b = valid[~valid["20선"]]["lodging_active"]
    u, p = mannwhitneyu(a, b, alternative="greater")
    print(f"[A] 매칭 {len(valid)}/88 | 20선 O 평균 {a.mean():.0f}(중앙값 {a.median():.0f}, n={len(a)}) "
          f"vs 20선 X 평균 {b.mean():.0f}(중앙값 {b.median():.0f}, n={len(b)}) | "
          f"Mann-Whitney U={u:.0f}, p={p:.4f}")
    return out


def part_b_site10(ldf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for region, (sido, gugun, yr) in SITE10.items():
        sub = ldf[region_mask(ldf, sido, gugun)]
        periods = PERIODS[yr]
        row = {"지역": region, "시군구": gugun}
        for pname, (s, e) in periods.items():
            s_ts, e_ts = pd.Timestamp(s + "-01"), pd.Timestamp(e + "-28")
            new_open = sub[(sub["인허가일자"] >= s_ts) & (sub["인허가일자"] <= e_ts)].shape[0]
            closed = sub[(sub["폐업일자"] >= s_ts) & (sub["폐업일자"] <= e_ts)].shape[0]
            row[f"{pname}_신규개업"] = new_open
            row[f"{pname}_폐업"] = closed
            row[f"{pname}_순증"] = new_open - closed
        active = sub[sub["영업상태명"] == "영업/정상"]
        row["현재_영업중_총"] = len(active)
        type_pct = active["업태구분명"].value_counts(normalize=True) * 100
        row["관광호텔+콘도_비중%"] = round(
            type_pct.get("일반호텔", 0) + type_pct.get("관광호텔", 0) + type_pct.get("휴양콘도미니엄업", 0), 1)
        row["여관+여인숙+생활숙박_비중%"] = round(
            type_pct.get("여관업", 0) + type_pct.get("여인숙업", 0) + type_pct.get("숙박업(생활)", 0), 1)
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "lodging_site10_supply.csv", index=False, encoding="utf-8-sig")
    print("[B] output/lodging_site10_supply.csv 저장 완료")
    return out


def part_c_dong5(ldf: pd.DataFrame) -> pd.DataFrame:
    """2023 코호트 5개소 — 시군구 집계가 시설 인근 실태를 왜곡하는지 행정동 단위로
    재검증(§7과 동일한 방법론을 §8-4의 숙박 공급 데이터에도 적용)."""
    rows = []
    for region, (sido, gugun, dong, yr) in SITE_DONG.items():
        sub = ldf[dong_mask(ldf, sido, gugun, dong)]
        periods = PERIODS[yr]
        row = {"지역": region, "행정동": dong, "현재_영업중_행정동": len(sub[sub["영업상태명"] == "영업/정상"])}
        for pname, (s, e) in periods.items():
            s_ts, e_ts = pd.Timestamp(s + "-01"), pd.Timestamp(e + "-28")
            new_open = sub[(sub["인허가일자"] >= s_ts) & (sub["인허가일자"] <= e_ts)].shape[0]
            closed = sub[(sub["폐업일자"] >= s_ts) & (sub["폐업일자"] <= e_ts)].shape[0]
            row[f"{pname}_순증_행정동"] = new_open - closed
        rows.append(row)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "lodging_dong5_supply.csv", index=False, encoding="utf-8-sig")
    print("[C] output/lodging_dong5_supply.csv 저장 완료 (2023 코호트만 — 2024 코호트는 로컬에 행정동 데이터 없음)")
    return out


if __name__ == "__main__":
    ldf = load_lodging()
    print(f"전국 숙박업 원자료: {len(ldf)}건 "
          f"(영업중 {(ldf['영업상태명']=='영업/정상').sum()}, 폐업 {(ldf['영업상태명']=='폐업').sum()})\n")
    dfa = part_a_88sites(ldf)
    print()
    dfb = part_b_site10(ldf)
    print()
    print(dfb.to_string(index=False))
    print()
    dfc = part_c_dong5(ldf)
    print()
    print(dfc.to_string(index=False))
