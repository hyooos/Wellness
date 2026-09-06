"""
웰니스 관광지 지정효과 분석 — 재현 가능한 데이터 로더

data/{이동통신,신용카드,숙박체류시간}/{지역폴더}/**/*.zip (행정동 하위폴더 포함, 재귀)를
읽어 시군구/행정동 단위 월별 tidy DataFrame으로 변환한다.

PROJECT.md 규칙을 그대로 따른다:
  - encoding='utf-8-sig' 고정
  - 신용카드 내국인/외국인 파일은 파일명으로 구분되지 않으므로, 같은 기간에 짝지어
    다운로드된 2개 zip 중 관광총소비 합계가 큰 쪽을 내국인, 작은 쪽을 외국인으로 판별
  - 방문자·소비는 구간 합계, 체류시간·숙박비율·숙박일은 구간 월평균
  - 절대수치가 아닌 증감률로 해석

지역 폴더명(예: "강원영월")은 data/이동통신, data/신용카드, data/숙박체류시간 세 폴더에
동일하게 존재해야 한다.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"

REGION_TO_SITE = {
    "강원영월": "영월(하이힐링원)",
    "강원삼척": "삼척(활기 치유의숲)",
    "경남양산": "양산(숲애서)",
    "경북칠곡": "칠곡(국립칠곡숲체원)",
    "충북제천": "제천(국립제천치유의숲)",
    "전남완도": "완도(해양치유센터)",
    "전북순창": "순창(쉴랜드)",
    "충북영동": "영동(레인보우 힐링센터)",
    "전북완주": "완주(아원고택)",
    "경북영주": "영주(소백산생태탐방원)",
}

COHORT_2023 = ["강원영월", "강원삼척", "경남양산", "경북칠곡", "충북제천"]
COHORT_2024 = ["전남완도", "전북순창", "충북영동", "전북완주", "경북영주"]

# 코호트별 구간 정의 (§3-3). 2024 코호트는 2023 코호트 대비 12개월 shift.
PERIODS = {
    2023: {
        "P1": ("202104", "202203"),
        "P2": ("202204", "202303"),
        "P3": ("202304", "202403"),
        "P4": ("202404", "202503"),
    },
    2024: {
        "P1": ("202204", "202303"),
        "P2": ("202304", "202403"),
        "P3": ("202404", "202503"),
        "P4": ("202504", "202603"),
    },
}


def cohort_of(region: str) -> int:
    if region in COHORT_2023:
        return 2023
    if region in COHORT_2024:
        return 2024
    raise KeyError(f"unknown region: {region}")


def _iter_region_zips(region: str, domain: str):
    """domain in {'이동통신','신용카드','숙박체류시간'}. 하위 폴더(행정동 등) 포함 재귀 탐색."""
    region_dir = DATA_ROOT / domain / region
    if not region_dir.exists():
        raise FileNotFoundError(region_dir)
    yield from sorted(region_dir.rglob("*.zip"))


def _read_csv_from_zip(zip_path: Path, name: str) -> pd.DataFrame:
    with zipfile.ZipFile(zip_path) as z:
        with z.open(name) as f:
            return pd.read_csv(f, encoding="utf-8-sig")


def _zip_csv_map(zip_path: Path) -> dict[str, str]:
    """파일명 접미사(타임스탬프 접두어 제거) -> 실제 zip 내부 파일명"""
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
    out = {}
    for n in names:
        # "20260816005140_방문자수 히트맵.csv" -> "방문자수 히트맵.csv"
        suffix = n.split("_", 1)[1] if "_" in n else n
        out[suffix.strip()] = n
    return out


# --------------------------------------------------------------------------
# 이동통신 (방문자수)
# --------------------------------------------------------------------------

def load_visitor_series(region: str) -> pd.DataFrame:
    """반환: 기준년월, 지역(시군구/행정동), level('시군구'|'행정동'), 방문자구분, 방문자수"""
    rows = []
    for zp in _iter_region_zips(region, "이동통신"):
        fmap = _zip_csv_map(zp)
        target = "방문자 수 추이.csv"
        if target not in fmap:
            continue
        df = _read_csv_from_zip(zp, fmap[target])
        if "기초지자체" in df.columns:
            level = "시군구"
            area_col = "기초지자체"
        elif "행정동명" in df.columns:
            level = "행정동"
            area_col = "행정동명"
        else:
            continue
        tmp = df.rename(columns={area_col: "지역", "방문자 구분": "방문자구분", "방문자 수": "방문자수"})
        tmp["level"] = level
        rows.append(tmp[["기준년월", "지역", "level", "방문자구분", "방문자수"]])
    if not rows:
        return pd.DataFrame(columns=["기준년월", "지역", "level", "방문자구분", "방문자수"])
    out = pd.concat(rows, ignore_index=True)
    out["기준년월"] = out["기준년월"].astype(str)
    return out.drop_duplicates(subset=["기준년월", "지역", "level", "방문자구분"])


# --------------------------------------------------------------------------
# 신용카드 (관광소비, 업종별 지출비중)
# --------------------------------------------------------------------------

def _classify_domestic_foreign(zp_group: list[Path]) -> dict[Path, str]:
    """같은 기간에 다운로드된 zip들을 관광총소비 합계 크기로 내국인/외국인으로 분류."""
    sums = {}
    for zp in zp_group:
        fmap = _zip_csv_map(zp)
        target = "관광소비 추이.csv"
        if target not in fmap:
            sums[zp] = None
            continue
        df = _read_csv_from_zip(zp, fmap[target])
        total_col = "소비액(천원)"
        s = df.loc[df.get("중분류", "관광총소비") == "관광총소비", total_col].sum() if total_col in df.columns else 0
        sums[zp] = s
    valid = {k: v for k, v in sums.items() if v}
    if not valid:
        return {zp: "unknown" for zp in zp_group}
    max_zp = max(valid, key=valid.get)
    result = {}
    for zp in zp_group:
        result[zp] = "내국인" if zp == max_zp else "외국인"
    return result


def load_consumption_series(region: str) -> pd.DataFrame:
    """반환: 기준년월, 지역, level, 통화구분(내국인/외국인), 소비액(천원)"""
    zips = list(_iter_region_zips(region, "신용카드"))

    # (level, period_start_end) 기준으로 짝짓기: 파일명 "{ts}_{시군구}_{YYYYMM-YYYYMM}_데이터랩_다운로드"
    # 에서 기간 문자열(YYYYMM-YYYYMM)은 뒤에서 3번째 토큰.
    def period_key(zp: Path) -> str:
        parts = zp.stem.split("_")
        return parts[-3] if len(parts) >= 3 else zp.stem

    # level(시군구/행정동)은 파일 내용으로 판정해야 하므로 먼저 한번 읽어 태깅
    tagged = []
    for zp in zips:
        fmap = _zip_csv_map(zp)
        target = "관광소비 추이.csv"
        if target not in fmap:
            continue
        df = _read_csv_from_zip(zp, fmap[target])
        if "기초지자체" in df.columns:
            level, area_col = "시군구", "기초지자체"
        elif "행정동명" in df.columns:
            level, area_col = "행정동", "행정동명"
        elif "행정동" in df.columns:
            level, area_col = "행정동", "행정동"
        else:
            continue
        tagged.append((zp, level, area_col, df))

    from collections import defaultdict
    groups = defaultdict(list)
    for zp, level, area_col, df in tagged:
        groups[(level, period_key(zp))].append((zp, area_col, df))

    rows = []
    for (level, _pk), members in groups.items():
        zp_list = [m[0] for m in members]
        cls = _classify_domestic_foreign(zp_list)
        for zp, area_col, df in members:
            tmp = df.rename(columns={area_col: "지역", "소비액(천원)": "소비액(천원)"})
            tmp = tmp[tmp.get("중분류", "관광총소비") == "관광총소비"] if "중분류" in tmp.columns else tmp
            tmp = tmp[["기준년월", "지역", "소비액(천원)"]].copy()
            tmp["level"] = level
            tmp["통화구분"] = cls.get(zp, "unknown")
            rows.append(tmp)
    if not rows:
        return pd.DataFrame(columns=["기준년월", "지역", "level", "통화구분", "소비액(천원)"])
    out = pd.concat(rows, ignore_index=True)
    out["기준년월"] = out["기준년월"].astype(str)
    return out.drop_duplicates(subset=["기준년월", "지역", "level", "통화구분"])


def load_category_share(region: str) -> pd.DataFrame:
    """업종별 지출액 대분류 비중(%) — 내국인 zip만, 기간 그룹별 1행씩.
    반환: period_key, 대분류, 대분류 지출액 비율"""
    zips = list(_iter_region_zips(region, "신용카드"))

    def period_key(zp: Path) -> str:
        parts = zp.stem.split("_")
        return parts[-3] if len(parts) >= 3 else zp.stem

    from collections import defaultdict
    groups = defaultdict(list)
    for zp in zips:
        fmap = _zip_csv_map(zp)
        if "관광소비 추이.csv" not in fmap:
            continue
        df_trend = _read_csv_from_zip(zp, fmap["관광소비 추이.csv"])
        if "기초지자체" not in df_trend.columns:
            continue  # 시군구 레벨만 (업종별 지출액은 행정동 레벨에서 제공 안 됨)
        groups[period_key(zp)].append(zp)

    rows = []
    for pk, zp_list in groups.items():
        cls = _classify_domestic_foreign(zp_list)
        dom_zp = next((zp for zp, c in cls.items() if c == "내국인"), None)
        if dom_zp is None:
            continue
        fmap = _zip_csv_map(dom_zp)
        if "업종별 지출액.csv" not in fmap:
            continue
        cat = _read_csv_from_zip(dom_zp, fmap["업종별 지출액.csv"])
        cat = cat[["대분류", "대분류 지출액 비율"]].drop_duplicates(subset=["대분류"])
        cat["period_key"] = pk
        rows.append(cat)
    if not rows:
        return pd.DataFrame(columns=["period_key", "대분류", "대분류 지출액 비율"])
    return pd.concat(rows, ignore_index=True)


# --------------------------------------------------------------------------
# 숙박체류시간 (체류시간, 숙박방문자비율, 평균숙박일, 숙박목적지검색)
# --------------------------------------------------------------------------

def load_stay_series(region: str) -> pd.DataFrame:
    """반환: 기준연월, 체류시간(분), 숙박방문자비율(%), 평균숙박일수, 숙박목적지검색건수 (시군구 단위, wide)"""
    frames = {}
    for zp in _iter_region_zips(region, "숙박체류시간"):
        fmap = _zip_csv_map(zp)

        if "평균 체류시간 추이.csv" in fmap:
            df = _read_csv_from_zip(zp, fmap["평균 체류시간 추이.csv"])
            df = df[df["지역명"] != "전국 기초지자체별 평균"][["기준연월", "체류시간(분)"]]
            frames.setdefault("stay_min", []).append(df)

        if "숙박방문자 비율 추이 .csv" in fmap or "숙박방문자 비율 추이.csv" in fmap:
            key = "숙박방문자 비율 추이 .csv" if "숙박방문자 비율 추이 .csv" in fmap else "숙박방문자 비율 추이.csv"
            df = _read_csv_from_zip(zp, fmap[key])
            df = df[df["지역명"] != "전국 기초지자체별 평균"][["기준연월", "숙박방문자 비율"]]
            frames.setdefault("lodge_ratio", []).append(df)

        if "평균 숙박일.csv" in fmap:
            df = _read_csv_from_zip(zp, fmap["평균 숙박일.csv"])[["기준연월", "평균 숙박일수"]]
            frames.setdefault("avg_nights", []).append(df)

        if "숙박 목적지 검색건수.csv" in fmap:
            df = _read_csv_from_zip(zp, fmap["숙박 목적지 검색건수.csv"])[["기준연월", "검색건수"]]
            frames.setdefault("search", []).append(df)

    def merged(key):
        if key not in frames:
            return None
        d = pd.concat(frames[key], ignore_index=True)
        d["기준연월"] = d["기준연월"].astype(str)
        return d.drop_duplicates(subset=["기준연월"])

    out = None
    for key in ["stay_min", "lodge_ratio", "avg_nights", "search"]:
        d = merged(key)
        if d is None:
            continue
        out = d if out is None else out.merge(d, on="기준연월", how="outer")
    return out.sort_values("기준연월").reset_index(drop=True) if out is not None else pd.DataFrame()


# --------------------------------------------------------------------------
# 구간 집계
# --------------------------------------------------------------------------

def months_in(start: str, end: str) -> list[str]:
    s, e = int(start), int(end)
    months = []
    y, m = s // 100, s % 100
    ey, em = e // 100, e % 100
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def period_sum(series: pd.DataFrame, value_col: str, start: str, end: str, month_col: str = "기준년월") -> float:
    mset = set(months_in(start, end))
    return series.loc[series[month_col].isin(mset), value_col].sum()


def period_mean(series: pd.DataFrame, value_col: str, start: str, end: str, month_col: str = "기준연월") -> float:
    mset = set(months_in(start, end))
    return series.loc[series[month_col].isin(mset), value_col].mean()


def growth(a: float, b: float) -> float:
    if a in (0, None) or pd.isna(a) or a == 0:
        return float("nan")
    return (b - a) / a * 100.0
