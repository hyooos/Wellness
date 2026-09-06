"""2024년 선정 웰니스 관광지 3개소 Tier 1 지표 계산.

대상: 완도 해양치유센터, 순창 쉴랜드, 완주 아원고택
기간: P1=2022.04~2023.03, P2=2023.04~2024.03,
      P3=2024.04~2025.03, P4=2025.04~2026.03

실행:
    ./venv/bin/python scripts/analyze_2024_three_sites.py

원본 ZIP은 풀지 않고 직접 읽는다. 결과는 output/2024_three_sites/에 저장한다.
가이드의 Tier 1 중 현재 원자료로 식별 가능한 지표만 계산하며, 계산 불가능한
WSPI(비교지역 자료 없음)와 전국 단위 시장정합도(검색 유입자료가 광역별 조건부
분포임)는 data_quality.csv에 명시한다.
"""
from __future__ import annotations

import math
import re
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "output" / "2024_three_sites"

PERIODS = {
    "P1": ("202204", "202303"),
    "P2": ("202304", "202403"),
    "P3": ("202404", "202503"),
    "P4": ("202504", "202603"),
}

SITES = {
    "전남완도": {"region": "완도군", "site": "완도 해양치유센터", "dong": "신지면"},
    "전북순창": {"region": "순창군", "site": "쉴랜드", "dong": "인계면"},
    "전북완주": {"region": "완주군", "site": "아원고택", "dong": "소양면"},
}

PERIOD_FROM_FILENAME = re.compile(r"(20\d{4})-(20\d{4})")
SUM_METRICS = {"숙박검색건수", "외지인방문자수", "전체방문자수", "내국인관광소비_천원", "외국인관광소비_천원"}
MAIN_METRICS = ["숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분", "평균숙박일수", "내국인관광소비_천원"]
RATE_METRICS = {"숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct"}
HAC_LAGS = (1, 3, 6, 12)
ITS_STARTS = ("202404", "202405")


def period_key(path: Path) -> str:
    m = PERIOD_FROM_FILENAME.search(path.name)
    if not m:
        raise ValueError(f"파일명에서 기간을 찾을 수 없음: {path}")
    bounds = m.groups()
    for name, value in PERIODS.items():
        if value == bounds:
            return name
    raise ValueError(f"분석 범위 밖 기간: {path}")


def csv_map(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
    result = {}
    for name in names:
        suffix = name.split("_", 1)[1] if "_" in name else name
        result[suffix.strip()] = name
    return result


def read_zip_csv(path: Path, member: str) -> pd.DataFrame:
    with zipfile.ZipFile(path) as zf, zf.open(member) as fh:
        return pd.read_csv(fh, encoding="utf-8-sig")


def find_member(path: Path, suffix: str) -> str | None:
    mapping = csv_map(path)
    if suffix in mapping:
        return mapping[suffix]
    # 원본에 공백이 들어간 "숙박방문자 비율 추이 .csv" 같은 경우 대응
    normalized = suffix.replace(" ", "")
    for key, value in mapping.items():
        if key.replace(" ", "") == normalized:
            return value
    return None


def checked_one(items: list[Path], description: str) -> Path:
    if len(items) != 1:
        raise ValueError(f"{description}: 1개여야 하나 {len(items)}개")
    return items[0]


def weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & weights.notna() & (weights >= 0)
    if not mask.any() or weights[mask].sum() == 0:
        return np.nan
    return float(np.average(values[mask], weights=weights[mask]))


def growth(old: float, new: float) -> float:
    if pd.isna(old) or pd.isna(new) or old == 0:
        return np.nan
    return (new / old - 1.0) * 100.0


def direction(value: float, threshold: float = 3.0) -> str:
    if pd.isna(value):
        return "NA"
    if value > threshold:
        return "UP"
    if value < -threshold:
        return "DOWN"
    return "FLAT"


def gini(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x) & (x >= 0)]
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    return float(np.abs(x[:, None] - x[None, :]).sum() / (2 * len(x) * x.sum()))


def hhi(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x) & (x >= 0)]
    if len(x) == 0 or x.sum() == 0:
        return np.nan
    shares = x / x.sum()
    return float(np.square(shares).sum() * 10_000)


def load_card(site_key: str):
    """월별 총소비/업종소비와 기간별 읍면동 소비점유율을 반환."""
    by_period: dict[str, list[tuple[Path, pd.DataFrame]]] = defaultdict(list)
    folder = DATA / "신용카드" / site_key
    for path in sorted(folder.glob("*.zip")):
        member = find_member(path, "관광소비 추이.csv")
        if member:
            by_period[period_key(path)].append((path, read_zip_csv(path, member)))

    monthly_total, monthly_category, dong_frames, classification = [], [], [], []
    for period in PERIODS:
        members = by_period[period]
        if len(members) != 2:
            raise ValueError(f"{site_key} {period} 카드 ZIP은 내/외국인 2개가 필요")
        sums = {}
        for path, frame in members:
            total = frame.loc[frame["중분류"] == "관광총소비", "소비액(천원)"].sum()
            sums[path] = float(total)
        domestic_path = max(sums, key=sums.get)
        for path, frame in members:
            kind = "내국인" if path == domestic_path else "외국인"
            classification.append({
                "지역키": site_key, "기간": period, "파일": path.name,
                "판별": kind, "관광총소비합_천원": sums[path],
            })
            total = frame[frame["중분류"] == "관광총소비"].copy()
            total = total[["기준년월", "소비액(천원)"]]
            total["기준년월"] = total["기준년월"].astype(str)
            total["구분"] = kind
            monthly_total.append(total)
            if kind == "내국인":
                cat = frame[frame["중분류"] != "관광총소비"][["기준년월", "중분류", "소비액(천원)"]].copy()
                cat["기준년월"] = cat["기준년월"].astype(str)
                cat["기간"] = period
                monthly_category.append(cat)

                spatial_member = find_member(path, "지역별 지출액.csv")
                spatial = read_zip_csv(path, spatial_member)
                dong_col = "행정동명" if "행정동명" in spatial.columns else "지역명"
                spatial = spatial.rename(columns={dong_col: "읍면동", "비율(%)": "점유율_pct"})
                spatial["기간"] = period
                dong_frames.append(spatial[["기간", "읍면동", "점유율_pct"]])

    totals = pd.concat(monthly_total, ignore_index=True)
    if totals.duplicated(["기준년월", "구분"]).any():
        raise ValueError(f"{site_key}: 카드 월/구분 중복")
    pivot = totals.pivot(index="기준년월", columns="구분", values="소비액(천원)").reset_index()
    pivot = pivot.rename(columns={"내국인": "내국인관광소비_천원", "외국인": "외국인관광소비_천원"})
    categories = pd.concat(monthly_category, ignore_index=True)
    dongs = pd.concat(dong_frames, ignore_index=True)
    return pivot, categories, dongs, pd.DataFrame(classification)


def load_mobile(site_key: str):
    """월별 방문자, 기간별 목적지 읍면동 방문량, 실제 방문자 거주지 분포."""
    folder = DATA / "이동통신" / site_key
    general_by_period: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(folder.glob("*.zip")):
        if find_member(path, "방문자 수 추이.csv"):
            general_by_period[period_key(path)].append(path)

    monthly, destination, origins = [], [], []
    for period in PERIODS:
        path = checked_one(general_by_period[period], f"{site_key} {period} 이동통신 일반 ZIP")
        trend = read_zip_csv(path, find_member(path, "방문자 수 추이.csv"))
        trend["기준년월"] = trend["기준년월"].astype(str)
        trend = trend.pivot(index="기준년월", columns="방문자 구분", values="방문자 수").reset_index()
        trend = trend.rename(columns={"외지인방문자(b)": "외지인방문자수", "전체방문자(a+b)": "전체방문자수", "현지인방문자(a)": "현지인방문자수"})
        monthly.append(trend)

        dest = read_zip_csv(path, find_member(path, "지역별 방문자 수.csv"))
        dest = dest.rename(columns={"기초지자체명": "읍면동", "기초지자체 방문자 수": "방문자수", "기초지자체 방문자 비율": "점유율_pct"})
        dest["기간"] = period
        destination.append(dest[["기간", "읍면동", "방문자수", "점유율_pct"]])

        origin = read_zip_csv(path, find_member(path, "방문자 거주지.csv"))
        origin = origin.rename(columns={"거주지(시도)": "광역", "거주지(시군구)": "기초", "비율(%)": "점유율_pct"})
        origin["기간"] = period
        origins.append(origin[["기간", "광역", "기초", "점유율_pct"]])

    result = pd.concat(monthly, ignore_index=True)
    if result.duplicated("기준년월").any():
        raise ValueError(f"{site_key}: 이동통신 월 중복")
    return result, pd.concat(destination, ignore_index=True), pd.concat(origins, ignore_index=True)


def load_stay(site_key: str):
    """월별 숙박·체류 KPI와 검색 유입지역의 광역 내 조건부 분포."""
    folder = DATA / "숙박체류시간" / site_key
    by_period: dict[str, list[Path]] = defaultdict(list)
    for path in sorted(folder.glob("*.zip")):
        by_period[period_key(path)].append(path)

    monthly, search_origins = [], []
    for period in PERIODS:
        path = checked_one(by_period[period], f"{site_key} {period} 숙박체류 ZIP")
        unique = read_zip_csv(path, find_member(path, "순 방문자 수 및 숙박 비율.csv"))
        unique = unique.rename(columns={"기준연월": "기준년월", "순 방문자수": "순방문자수", "숙박자 비율": "숙박자비율_pct"})
        nights = read_zip_csv(path, find_member(path, "평균 숙박일.csv")).rename(columns={"기준연월": "기준년월"})

        stay = read_zip_csv(path, find_member(path, "평균 체류시간 추이.csv"))
        stay = stay[stay["지역명"] != "전국 기초지자체별 평균"].rename(columns={"기준연월": "기준년월", "체류시간(분)": "평균체류시간_분"})
        stay = stay[["기준년월", "평균체류시간_분"]]
        search = read_zip_csv(path, find_member(path, "숙박 목적지 검색건수.csv")).rename(columns={"기준연월": "기준년월", "검색건수": "숙박검색건수"})
        search = search[["기준년월", "숙박검색건수"]]
        types = read_zip_csv(path, find_member(path, "숙박 유형별 방문자 비율.csv")).rename(columns={"기준연월": "기준년월"})
        long_cols = ["3박", "4박", "5박", "6박", "7박이상"]
        types["숙박자중_3박이상_pct"] = types[long_cols].sum(axis=1, min_count=len(long_cols))
        types = types[["기준년월", "숙박자중_3박이상_pct"]]

        frames = [unique, nights, stay, search, types]
        for frame in frames:
            frame["기준년월"] = frame["기준년월"].astype(str)
        merged = frames[0]
        for frame in frames[1:]:
            merged = merged.merge(frame, on="기준년월", how="outer", validate="one_to_one")
        monthly.append(merged)

        origin = read_zip_csv(path, find_member(path, "숙박 목적지 유입 지역 분포.csv"))
        origin = origin.rename(columns={"광역지자체명": "광역", "기초지자체명": "기초", "기초지자체별 거주 방문자 비율": "조건부점유율_pct"})
        origin["기간"] = period
        search_origins.append(origin[["기간", "광역", "기초", "조건부점유율_pct"]])

    result = pd.concat(monthly, ignore_index=True)
    if result.duplicated("기준년월").any():
        raise ValueError(f"{site_key}: 숙박체류 월 중복")
    return result, pd.concat(search_origins, ignore_index=True)


def build_inputs():
    monthly_all, categories, card_dongs, visit_dongs = [], {}, {}, {}
    actual_origins, search_origins, classifications = {}, {}, []
    for site_key, meta in SITES.items():
        card, cat, card_dong, cls = load_card(site_key)
        mobile, visit_dong, actual_origin = load_mobile(site_key)
        stay, search_origin = load_stay(site_key)
        merged = mobile.merge(card, on="기준년월", validate="one_to_one").merge(stay, on="기준년월", validate="one_to_one")
        merged["지역키"] = site_key
        merged["지역"] = meta["region"]
        merged["시설"] = meta["site"]
        merged["기간"] = merged["기준년월"].map(lambda x: next((p for p, (a, b) in PERIODS.items() if a <= x <= b), None))
        merged["숙박방문자추정수"] = merged["순방문자수"] * merged["숙박자비율_pct"] / 100.0
        merged["전체순방문자중_3박이상_pct"] = merged["숙박자비율_pct"] * merged["숙박자중_3박이상_pct"] / 100.0
        monthly_all.append(merged)
        categories[site_key], card_dongs[site_key], visit_dongs[site_key] = cat, card_dong, visit_dong
        actual_origins[site_key], search_origins[site_key] = actual_origin, search_origin
        classifications.append(cls)
    monthly = pd.concat(monthly_all, ignore_index=True).sort_values(["지역키", "기준년월"])
    expected = len(SITES) * 48
    if len(monthly) != expected or monthly.isna().any().any():
        nulls = monthly.columns[monthly.isna().any()].tolist()
        raise ValueError(f"월별 통합자료 불완전: rows={len(monthly)}/{expected}, null columns={nulls}")
    return monthly, categories, card_dongs, visit_dongs, actual_origins, search_origins, pd.concat(classifications, ignore_index=True)


def aggregate_kpis(monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (site_key, period), frame in monthly.groupby(["지역키", "기간"], sort=False):
        if len(frame) != 12:
            raise ValueError(f"{site_key} {period}: 12개월이 아님")
        overnight_weight = frame["숙박방문자추정수"]
        row = {
            "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "기간": period,
            "숙박검색건수": frame["숙박검색건수"].sum(),
            "외지인방문자수": frame["외지인방문자수"].sum(),
            "전체방문자수": frame["전체방문자수"].sum(),
            "숙박자비율_pct": weighted_mean(frame["숙박자비율_pct"], frame["순방문자수"]),
            "평균체류시간_분": weighted_mean(frame["평균체류시간_분"], frame["순방문자수"]),
            "평균숙박일수": weighted_mean(frame["평균 숙박일수"], overnight_weight),
            "내국인관광소비_천원": frame["내국인관광소비_천원"].sum(),
            "외국인관광소비_천원": frame["외국인관광소비_천원"].sum(),
            "숙박자중_3박이상_pct": weighted_mean(frame["숙박자중_3박이상_pct"], overnight_weight),
            "전체순방문자중_3박이상_pct": weighted_mean(frame["전체순방문자중_3박이상_pct"], frame["순방문자수"]),
        }
        # 카드와 통신의 모집단이 다르므로 개인 단위의 엄밀한 1인당 소비가 아니다.
        row["방문자대비관광소비_천원_proxy"] = row["내국인관광소비_천원"] / row["외지인방문자수"]
        mean_v = frame["외지인방문자수"].mean()
        row["방문_CV"] = frame["외지인방문자수"].std(ddof=0) / mean_v
        row["DSI"] = 1.0 - row["방문_CV"]
        row["WSPI"] = np.nan  # 같은 광역시도의 미지정 비교지역 자료가 없음
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["지역키", "기간"])


def growth_table(kpis: pd.DataFrame) -> pd.DataFrame:
    metrics = MAIN_METRICS + ["숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct", "방문자대비관광소비_천원_proxy", "방문_CV", "DSI"]
    rows = []
    for site_key, frame in kpis.groupby("지역키"):
        by_period = frame.set_index("기간")
        for metric in metrics:
            rates = {
                "g12_pct": growth(by_period.at["P1", metric], by_period.at["P2", metric]),
                "g23_pct": growth(by_period.at["P2", metric], by_period.at["P3", metric]),
                "g34_pct": growth(by_period.at["P3", metric], by_period.at["P4", metric]),
            }
            differences = {
                "delta12_abs": by_period.at["P2", metric] - by_period.at["P1", metric],
                "delta23_abs": by_period.at["P3", metric] - by_period.at["P2", metric],
                "delta34_abs": by_period.at["P4", metric] - by_period.at["P3", metric],
            }
            dirs = [direction(rates["g23_pct"], t) for t in (0, 3, 5)]
            rows.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "지표": metric,
                **rates, **differences,
                "delta12_pctp": differences["delta12_abs"] if metric in RATE_METRICS else np.nan,
                "delta23_pctp": differences["delta23_abs"] if metric in RATE_METRICS else np.nan,
                "delta34_pctp": differences["delta34_abs"] if metric in RATE_METRICS else np.nan,
                "지정직후_판정_3pct": direction(rates["g23_pct"], 3),
                "2년차_판정_3pct": direction(rates["g34_pct"], 3),
                "민감도_0pct": dirs[0], "민감도_3pct": dirs[1], "민감도_5pct": dirs[2],
                "민감도신뢰": "HIGH" if len(set(dirs)) == 1 else "LOW",
            })
    return pd.DataFrame(rows)


def newey_west_ols(y: np.ndarray, x: np.ndarray, maxlags: int = 3):
    """OLS와 Newey-West(HAC) 공분산. statsmodels 없이 재현 가능하게 구현."""
    beta = np.linalg.pinv(x.T @ x) @ x.T @ y
    resid = y - x @ beta
    n, k = x.shape
    meat = np.zeros((k, k))
    for t in range(n):
        xt = x[t][:, None]
        meat += resid[t] ** 2 * (xt @ xt.T)
    for lag in range(1, maxlags + 1):
        weight = 1.0 - lag / (maxlags + 1.0)
        gamma = np.zeros((k, k))
        for t in range(lag, n):
            gamma += resid[t] * resid[t - lag] * np.outer(x[t], x[t - lag])
        meat += weight * (gamma + gamma.T)
    bread = np.linalg.pinv(x.T @ x)
    cov = bread @ meat @ bread * (n / (n - k))
    return beta, cov


def benjamini_hochberg(pvalues: pd.Series) -> pd.Series:
    """Benjamini-Hochberg FDR 보정."""
    values = pvalues.to_numpy(dtype=float)
    order = np.argsort(values)
    ranked = values[order]
    adjusted = ranked * len(values) / np.arange(1, len(values) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    out = np.empty_like(adjusted)
    out[order] = np.minimum(adjusted, 1.0)
    return pd.Series(out, index=pvalues.index)


def its_table(monthly: pd.DataFrame, maxlags: int = 3, intervention_start: str = "202404") -> pd.DataFrame:
    specs = {
        "숙박검색건수": ("숙박검색건수", True),
        "외지인방문자수": ("외지인방문자수", True),
        "숙박자비율_pct": ("숙박자비율_pct", False),
        "평균체류시간_분": ("평균체류시간_분", False),
        "평균숙박일수": ("평균 숙박일수", False),
        "내국인관광소비_천원": ("내국인관광소비_천원", True),
    }
    rows = []
    for site_key, frame in monthly.groupby("지역키"):
        frame = frame.sort_values("기준년월").reset_index(drop=True)
        n = len(frame)
        t = np.arange(1, n + 1, dtype=float)
        post = (frame["기준년월"].to_numpy() >= intervention_start).astype(float)
        first_post_positions = np.flatnonzero(post == 1)
        if len(first_post_positions) == 0:
            raise ValueError(f"ITS 개입월이 분석 범위 밖: {intervention_start}")
        first_post_t = t[first_post_positions[0]]
        # 첫 post 월에서 0이 되도록 중심화한다. 그래야 beta[2]가 첫 post 월의
        # 불연속적 수준변화이고 beta[3]가 이후 월별 기울기 변화가 된다.
        post_slope = (t - first_post_t) * post
        month = frame["기준년월"].str[-2:].astype(int)
        month_dummies = pd.get_dummies(month, prefix="month", drop_first=True, dtype=float)
        x = np.column_stack([np.ones(n), t, post, post_slope, month_dummies.to_numpy()])
        for metric, (column, log_transform) in specs.items():
            raw = frame[column].to_numpy(dtype=float)
            y = np.log1p(raw) if log_transform else raw
            beta, cov = newey_west_ols(y, x, maxlags=maxlags)
            se = np.sqrt(np.maximum(np.diag(cov), 0))
            p = 2 * norm.sf(np.abs(beta / np.where(se == 0, np.nan, se)))
            post_slope_beta = beta[1] + beta[3]
            post_slope_var = cov[1, 1] + cov[3, 3] + 2 * cov[1, 3]
            post_slope_se = math.sqrt(max(post_slope_var, 0))
            post_slope_p = 2 * norm.sf(abs(post_slope_beta / post_slope_se)) if post_slope_se else np.nan
            rows.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "지표": metric,
                "변환": "log1p" if log_transform else "level", "관측월수": n,
                "개입시작월": intervention_start, "HAC_maxlags": maxlags,
                "지정전_월추세_beta": beta[1], "지정전_월추세_p": p[1],
                "즉시수준변화_beta": beta[2], "즉시수준변화_p": p[2],
                "지정후_기울기변화_beta": beta[3], "지정후_기울기변화_p": p[3],
                "지정후_월추세_beta": post_slope_beta, "지정후_월추세_p": post_slope_p,
                "즉시변화_환산_pct": (math.exp(beta[2]) - 1) * 100 if log_transform else np.nan,
                "기울기변화_월환산_pct": (math.exp(beta[3]) - 1) * 100 if log_transform else np.nan,
            })
    out = pd.DataFrame(rows)
    # 동일 개입월·lag 안에서 18개 지역×지표 검정에 대한 계수군별 FDR 보정.
    out["즉시수준변화_q_BH"] = benjamini_hochberg(out["즉시수준변화_p"])
    out["지정후_기울기변화_q_BH"] = benjamini_hochberg(out["지정후_기울기변화_p"])
    return out


def its_robustness_table(sensitivity: pd.DataFrame) -> pd.DataFrame:
    """HAC lag에 따른 부호·유의성 유지 여부를 계수별로 요약."""
    rows = []
    for (site_key, metric, start), frame in sensitivity.groupby(["지역키", "지표", "개입시작월"]):
        for label, beta_col, p_col in [
            ("즉시수준변화", "즉시수준변화_beta", "즉시수준변화_p"),
            ("지정후기울기변화", "지정후_기울기변화_beta", "지정후_기울기변화_p"),
        ]:
            signs = np.sign(frame[beta_col].to_numpy())
            rows.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"],
                "지표": metric, "개입시작월": start, "계수": label,
                "lag목록": ",".join(map(str, sorted(frame["HAC_maxlags"].unique()))),
                "부호일관": bool(len(set(signs)) == 1),
                "p05_유의_lag수": int((frame[p_col] < 0.05).sum()),
                "모든lag_p05유의": bool((frame[p_col] < 0.05).all()),
                "beta_min": frame[beta_col].min(), "beta_max": frame[beta_col].max(),
                "p_min": frame[p_col].min(), "p_max": frame[p_col].max(),
            })
    return pd.DataFrame(rows)


def conditional_alignment(actual_all, search_all):
    """광역 내 조건부 분포 기준의 시장정합도 프록시.

    검색 유입 분포는 광역마다 합이 100이어서 전국 점유율이 아니다. 실제 방문자
    분포도 광역별로 재정규화한 후, 광역을 동일 가중해 비교한다.
    """
    rows = []
    for site_key in SITES:
        for period in PERIODS:
            a = actual_all[site_key].query("기간 == @period").copy()
            q = search_all[site_key].query("기간 == @period").copy()
            common_provinces = sorted(set(a["광역"]) & set(q["광역"]))
            pa, pq, top_overlap = [], [], []
            for province in common_provinces:
                aa = a[a["광역"] == province].set_index("기초")["점유율_pct"]
                qq = q[q["광역"] == province].set_index("기초")["조건부점유율_pct"]
                keys = sorted(set(aa.index) | set(qq.index))
                av = aa.reindex(keys, fill_value=0).to_numpy(dtype=float)
                qv = qq.reindex(keys, fill_value=0).to_numpy(dtype=float)
                if av.sum() == 0 or qv.sum() == 0:
                    continue
                av, qv = av / av.sum(), qv / qv.sum()
                # 각 광역에 동일 질량을 부여한 조건부 정합도 프록시
                pa.extend(av / len(common_provinces))
                pq.extend(qv / len(common_provinces))
                n_top = min(5, len(keys))
                atop = set(np.asarray(keys)[np.argsort(av)[-n_top:]])
                qtop = set(np.asarray(keys)[np.argsort(qv)[-n_top:]])
                top_overlap.append(len(atop & qtop) / n_top)
            pa, pq = np.asarray(pa), np.asarray(pq)
            rho, pvalue = spearmanr(pa, pq) if len(pa) >= 3 else (np.nan, np.nan)
            midpoint = (pa + pq) / 2
            def kl(x, m):
                mask = x > 0
                return float(np.sum(x[mask] * np.log2(x[mask] / m[mask])))
            jsd = 0.5 * kl(pa, midpoint) + 0.5 * kl(pq, midpoint) if len(pa) else np.nan
            rows.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "기간": period,
                "비교가능_광역수": len(common_provinces), "비교key수": len(pa),
                "조건부_Spearman_rho": rho, "Spearman_p_참고": pvalue,
                "조건부_JSD_base2": jsd, "광역별_Top5_overlap_평균": np.mean(top_overlap) if top_overlap else np.nan,
                "주의": "광역 동일가중 조건부 프록시; 전국 시장정합도로 해석 금지",
            })
    out = pd.DataFrame(rows)
    out["JSD_전기대비변화"] = out.groupby("지역키")["조건부_JSD_base2"].diff()
    return out


def lq_status_table():
    """자기포함 3개소 평균 LQ를 중단하고 정식 계산에 필요한 상태를 기록."""
    rows = []
    for site_key in SITES:
        for period in PERIODS:
            rows.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "기간": period,
                "LQ": np.nan, "상태": "NOT_COMPUTABLE",
                "필요분모": "전남/전북 일반 관광시장의 출발지역별 방문 점유율",
                "중단사유": "세 처치지역 자기포함 평균은 독립 benchmark가 아니며 LQ가 기계적으로 커질 수 있음",
            })
    return pd.DataFrame(rows)


def spatial_tables(kpis, card_dongs, visit_dongs):
    concentration, relative = [], []
    for site_key, meta in SITES.items():
        city = kpis[kpis["지역키"] == site_key].set_index("기간")
        domain_frames = {
            "소비": card_dongs[site_key].assign(value=lambda d: d.apply(lambda r: city.at[r["기간"], "내국인관광소비_천원"] * r["점유율_pct"] / 100, axis=1)),
            "방문": visit_dongs[site_key].rename(columns={"방문자수": "value"}),
        }
        for domain, data in domain_frames.items():
            for period in PERIODS:
                d = data[data["기간"] == period]
                facility = d.loc[d["읍면동"] == meta["dong"]]
                if len(facility) != 1:
                    raise ValueError(f"{site_key} {period} {domain}: 시설 읍면동 {meta['dong']} 식별 실패")
                concentration.append({
                    "지역키": site_key, "지역": meta["region"], "시설": meta["site"], "영역": domain, "기간": period,
                    "읍면동수": len(d), "HHI": hhi(d["value"].to_numpy()), "Gini": gini(d["value"].to_numpy()),
                    "시설소재_읍면동": meta["dong"], "시설동_점유율_pct": float(facility["value"].iloc[0] / d["value"].sum() * 100),
                    "공간자료기준": "내국인소비 점유율 복원" if domain == "소비" else "전체방문자 읍면동 분포",
                })
            indexed = data.set_index(["기간", "읍면동"])["value"]
            for before, after, label in [("P1", "P2", "g12"), ("P2", "P3", "g23"), ("P3", "P4", "g34")]:
                facility_growth = growth(indexed.get((before, meta["dong"]), np.nan), indexed.get((after, meta["dong"]), np.nan))
                before_data = data[data["기간"] == before]
                after_data = data[data["기간"] == after]
                before_share = indexed.get((before, meta["dong"]), np.nan) / before_data["value"].sum() * 100
                after_share = indexed.get((after, meta["dong"]), np.nan) / after_data["value"].sum() * 100
                if domain == "소비":
                    city_metric = "내국인관광소비_천원"
                    city_growth = growth(city.at[before, city_metric], city.at[after, city_metric])
                else:
                    # 하위 행정구역 합은 상위 값으로 사용하지 않는다.
                    city_growth = growth(city.at[before, "전체방문자수"], city.at[after, "전체방문자수"])
                relative.append({
                    "지역키": site_key, "지역": meta["region"], "시설": meta["site"], "영역": domain, "변화구간": label,
                    "시설소재_읍면동": meta["dong"], "시설동_성장률_pct": facility_growth,
                    "시군구_성장률_pct": city_growth, "상대집중도_RC_pctp": facility_growth - city_growth,
                    "시설동_점유율_before_pct": before_share, "시설동_점유율_after_pct": after_share,
                    "시설동_점유율변화_pctp": after_share - before_share,
                    "시군구방문기준": "해당없음" if domain == "소비" else "전체방문자(메인 KPI 외지인과 다름)",
                })
    concentration = pd.DataFrame(concentration)
    changes = []
    for (site_key, domain), frame in concentration.groupby(["지역키", "영역"]):
        indexed = frame.set_index("기간")
        for before, after, label in [("P1", "P2", "12"), ("P2", "P3", "23"), ("P3", "P4", "34")]:
            changes.append({
                "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "영역": domain,
                "변화구간": f"P{label[0]}→P{label[1]}",
                "delta_HHI": indexed.at[after, "HHI"] - indexed.at[before, "HHI"],
                "delta_Gini": indexed.at[after, "Gini"] - indexed.at[before, "Gini"],
                "delta_시설동점유율_pctp": indexed.at[after, "시설동_점유율_pct"] - indexed.at[before, "시설동_점유율_pct"],
            })
    return concentration, pd.DataFrame(changes), pd.DataFrame(relative)


def shift_share_table(kpis, categories):
    period_totals = {}
    available = {}
    for site_key, data in categories.items():
        grouped = data.groupby(["기간", "중분류"], as_index=False)["소비액(천원)"].sum()
        period_totals[site_key] = grouped.set_index(["기간", "중분류"])["소비액(천원)"]
        available[site_key] = {p: set(grouped.loc[grouped["기간"] == p, "중분류"]) for p in PERIODS}

    rows = []
    kpi_idx = kpis.set_index(["지역키", "기간"])
    for before, after, transition in [("P2", "P3", "P2→P3"), ("P3", "P4", "P3→P4")]:
        # 결측 업종을 0으로 만들지 않기 위해 3지역·양 기간에 모두 관측된 업종만 사용.
        balanced = set.intersection(*(available[s][p] for s in SITES for p in (before, after)))
        start_all = sum(kpi_idx.at[(s, before), "내국인관광소비_천원"] for s in SITES)
        end_all = sum(kpi_idx.at[(s, after), "내국인관광소비_천원"] for s in SITES)
        global_growth = end_all / start_all - 1
        for category in sorted(balanced):
            industry_start = sum(period_totals[s].at[(before, category)] for s in SITES)
            industry_end = sum(period_totals[s].at[(after, category)] for s in SITES)
            industry_growth = industry_end / industry_start - 1
            for site_key in SITES:
                start = period_totals[site_key].at[(before, category)]
                end = period_totals[site_key].at[(after, category)]
                local_growth = end / start - 1
                actual_change = end - start
                ns = start * global_growth
                im = start * (industry_growth - global_growth)
                rs = start * (local_growth - industry_growth)
                rows.append({
                    "지역키": site_key, "지역": SITES[site_key]["region"], "시설": SITES[site_key]["site"], "변화구간": transition, "중분류": category,
                    "기준소비_천원": start, "실제변화_D_천원": actual_change, "NS_천원": ns, "IM_천원": im, "RS_천원": rs,
                    "RS_share_보조": rs / actual_change if abs(actual_change) > 1e-9 else np.nan,
                    "3지역전체성장률_pct": global_growth * 100, "3지역업종성장률_pct": industry_growth * 100,
                    "지역업종성장률_pct": local_growth * 100,
                    "성장률gap_3개지역업종대비_pctp": (local_growth - industry_growth) * 100,
                    "benchmark_정의": "완도·순창·완주 3개 처치지역 합계(일반 비교시장 아님)",
                    "분해오차": actual_change - (ns + im + rs),
                })
    return pd.DataFrame(rows)


def quality_table(classification, kpis, search_origins, categories):
    rows = [
        {"항목": "월별 기간 완전성", "상태": "OK", "내용": "3지역×48개월, 각 P1~P4 12개월; 통합 후 결측 없음"},
        {"항목": "카드 내·외국인 분리", "상태": "OK", "내용": "동일 기간 2개 ZIP의 관광총소비 합계가 큰 파일을 내국인으로 판별; 세부 근거는 card_classification.csv"},
        {"항목": "WSPI", "상태": "NOT_COMPUTABLE", "내용": "전남·전북의 미지정 일반 시군구 방문자/내국인소비 자료가 없어 권장 benchmark를 만들 수 없음; 방문자 대비 관광소비 proxy만 계산"},
        {"항목": "전국 시장정합도", "상태": "NOT_COMPUTABLE", "내용": "숙박검색 유입 비율이 전국합 100%가 아니라 광역별 각각 100%인 조건부 분포; 광역 동일가중 조건부 프록시만 계산"},
        {"항목": "시장정합도 Top-5", "상태": "PROXY", "내용": "전국 Top-5 대신 광역별 Top-5 overlap의 단순평균"},
        {"항목": "LQ benchmark", "상태": "NOT_COMPUTABLE", "내용": "자기포함 3개 처치지역 평균 LQ를 중단함; 전남·전북 일반 관광시장 출발지 분포 필요"},
        {"항목": "ITS 인과해석", "상태": "CAUTION", "내용": "대조군 없는 단절시계열이므로 구조변화이며 지정의 인과효과로 단정 불가"},
        {"항목": "ITS 개입월", "상태": "SENSITIVITY", "내용": "77선 공식 공개가 2024.04.24로 월말이므로 가이드 기준 202404와 완전 노출 첫 달 202405를 모두 계산"},
        {"항목": "ITS 다중검정", "상태": "CAUTION", "내용": "지역×지표 반복검정을 고려해 계수군별 Benjamini-Hochberg q-value를 함께 제공"},
        {"항목": "시설단위 해석", "상태": "CAUTION", "내용": "KPI/ITS는 시설이 아니라 시설 소재 시군구 시장의 변화"},
        {"항목": "공간점유율 반올림", "상태": "CAUTION", "내용": "원본 읍면동 점유율 합이 99.9~100.2%이고 소수점 1자리라 소비 절대금액 복원 오차 가능; 점유율 변화도 함께 제공"},
        {"항목": "공간 방문 기준", "상태": "CAUTION", "내용": "읍면동 방문 분포는 전체방문자 기준이고 메인 방문 KPI는 외지인 기준; 동일 지표로 간주 금지"},
        {"항목": "Shift-Share benchmark", "상태": "CAUTION", "내용": "NS/IM/RS benchmark는 3개 처치지역이며 일반 비교시장 아님; RS는 3개소 평균 대비 상대효과"},
        {"항목": "Shift-Share 결측업종", "상태": "OK", "내용": "결측을 0으로 대체하지 않고 3지역×비교 양 기간에 모두 존재하는 균형 업종만 분해"},
        {"항목": "시설 소재 읍면동", "상태": "OK", "내용": "완도=신지면, 순창=인계면, 완주=소양면"},
        {"항목": "DEA/AHP/k-means/SCM/Monte Carlo", "상태": "EXCLUDED", "내용": "사용자 요청에 따라 Tier 1 외 분석 제외"},
    ]
    # 검색 유입 원자료가 실제로 광역별 약 100인지 자동 점검 결과도 기록한다.
    deviations = []
    for site_key, data in search_origins.items():
        sums = data.groupby(["기간", "광역"])["조건부점유율_pct"].sum()
        deviations.extend((sums - 100).abs().tolist())
    rows.append({"항목": "검색유입 광역별 합 검증", "상태": "OK" if max(deviations) <= 1 else "CHECK", "내용": f"광역별 100%와 최대 절대편차 {max(deviations):.1f}%p"})
    return pd.DataFrame(rows)


def round_numeric(frame: pd.DataFrame, digits: int = 10) -> pd.DataFrame:
    result = frame.copy()
    cols = result.select_dtypes(include=[np.number]).columns
    result[cols] = result[cols].round(digits)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    monthly, categories, card_dongs, visit_dongs, actual_origins, search_origins, classification = build_inputs()
    kpis = aggregate_kpis(monthly)
    growths = growth_table(kpis)
    its_sensitivity = pd.concat(
        [its_table(monthly, lag, start) for start in ITS_STARTS for lag in HAC_LAGS],
        ignore_index=True,
    )
    its = its_sensitivity[(its_sensitivity["개입시작월"] == "202404") & (its_sensitivity["HAC_maxlags"] == 3)].copy()
    its_robustness = its_robustness_table(its_sensitivity)
    alignment = conditional_alignment(actual_origins, search_origins)
    lq_status = lq_status_table()
    concentration, spatial_changes, relative = spatial_tables(kpis, card_dongs, visit_dongs)
    shift_share = shift_share_table(kpis, categories)
    quality = quality_table(classification, kpis, search_origins, categories)

    outputs = {
        "monthly_input.csv": monthly,
        "kpi_by_period.csv": kpis,
        "growth_bottleneck.csv": growths,
        "its_hac.csv": its,
        "its_hac_sensitivity.csv": its_sensitivity,
        "its_robustness.csv": its_robustness,
        "market_alignment_conditional_proxy.csv": alignment,
        "origin_lq_status.csv": lq_status,
        "spatial_concentration.csv": concentration,
        "spatial_change.csv": spatial_changes,
        "spatial_relative_growth.csv": relative,
        "shift_share.csv": shift_share,
        "card_classification.csv": classification,
        "data_quality.csv": quality,
    }
    for name, frame in outputs.items():
        round_numeric(frame).to_csv(OUT / name, index=False, encoding="utf-8-sig")
    # 이전 자기포함 3개소 benchmark LQ는 해석상 취약해 더 이상 배포하지 않는다.
    (OUT / "origin_lq_three_site_proxy.csv").unlink(missing_ok=True)

    print(f"저장 위치: {OUT}")
    print("\n[KPI P2→P3 / P3→P4 성장률(%)]")
    main_growth = growths[growths["지표"].isin(MAIN_METRICS)]
    print(main_growth[["지역", "지표", "g23_pct", "지정직후_판정_3pct", "g34_pct", "2년차_판정_3pct"]].round(2).to_string(index=False))
    print("\n[계산 제약]")
    print(quality[quality["상태"] != "OK"].to_string(index=False))


if __name__ == "__main__":
    main()
