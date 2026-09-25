"""4개 웰니스 관광지를 최초 지정연도 기준 P1~P4로 분석한다.

입력: data/한국관광데이터랩 데이터 통합.zip
출력: output/4개_웰니스관광지_성과분석/

P3는 공식 신규선정 발표월부터 12개월이며, P1·P2·P4도 같은 월 경계로
앞뒤 12개월씩 배치한다. 네 지역 모두 4월부터 다음 해 3월까지가 한 기간이다.

연간 KPI는 12개월이 모두 관측된 경우에만 계산한다.
"""
from __future__ import annotations

import math
import sys
import unicodedata
import zipfile
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(__file__).resolve().parent.parent
INPUT_ZIP = ROOT / "data" / "한국관광데이터랩 데이터 통합.zip"
OUT = ROOT / "output" / "4개_웰니스관광지_성과분석"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_2024_three_sites as base  # noqa: E402


SITES = {
    "전북무주": {"region": "무주군", "site": "태권도원 상징지구", "dong": "설천면", "year": 2022, "month": 4, "announcement": "2022-04-19"},
    "전남완도": {"region": "완도군", "site": "완도 해양치유센터", "dong": "신지면", "year": 2024, "month": 4, "announcement": "2024-04-24"},
    "전북순창": {"region": "순창군", "site": "쉴랜드", "dong": "인계면", "year": 2024, "month": 4, "announcement": "2024-04-24"},
    "전북완주": {"region": "완주군", "site": "아원고택", "dong": "소양면", "year": 2024, "month": 4, "announcement": "2024-04-24"},
}
REGION_TO_KEY = {v["region"]: k for k, v in SITES.items()}
PERIOD_NAMES = ("P1", "P2", "P3", "P4")
SUM_METRICS = (
    "숙박검색건수", "외지인방문자수", "전체방문자수",
    "내국인관광소비_천원", "외국인관광소비_천원",
)
RATE_METRICS = {
    "숙박자비율_pct", "숙박자중_3박이상_pct", "전체순방문자중_3박이상_pct",
}
KPI_METRICS = [
    "숙박검색건수", "외지인방문자수", "숙박자비율_pct", "평균체류시간_분",
    "평균숙박일수", "내국인관광소비_천원", "숙박자중_3박이상_pct",
    "전체순방문자중_3박이상_pct", "방문자대비관광소비_천원_proxy", "방문_CV", "DSI",
]


def ym(year: int, month: int) -> str:
    return f"{year:04d}{month:02d}"


def period_bounds(year: int, month: int = 4) -> dict[str, tuple[str, str]]:
    intervention = pd.Period(f"{year:04d}-{month:02d}", freq="M")
    bounds = {}
    for name, offset in (("P1", -24), ("P2", -12), ("P3", 0), ("P4", 12)):
        start = intervention + offset
        end = start + 11
        bounds[name] = (start.strftime("%Y%m"), end.strftime("%Y%m"))
    return bounds


def decode_member(name: str) -> str:
    try:
        name = name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return unicodedata.normalize("NFC", name)


class IntegratedZip:
    def __init__(self, path: Path):
        self.path = path
        with zipfile.ZipFile(path) as zf:
            self.members = {
                decode_member(i.filename): i.filename
                for i in zf.infolist()
                if i.file_size > 1000 and decode_member(i.filename).endswith(".csv")
                and not decode_member(i.filename).startswith("__MACOSX")
            }

    def read(self, suffix: str) -> pd.DataFrame:
        matches = [raw for decoded, raw in self.members.items() if decoded.endswith(suffix)]
        if len(matches) != 1:
            raise ValueError(f"ZIP member {suffix!r}: {len(matches)}개 발견")
        with zipfile.ZipFile(self.path) as zf:
            return pd.read_csv(BytesIO(zf.read(matches[0])), encoding="utf-8-sig")


def add_identity(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["지역키"] = out["시군구"].map(REGION_TO_KEY)
    out = out[out["지역키"].notna()].copy()
    out["지역"] = out["시군구"]
    out["시설"] = out["지역키"].map(lambda k: SITES[k]["site"])
    out["최초선정연도"] = out["지역키"].map(lambda k: SITES[k]["year"])
    return out


def load_monthly(z: IntegratedZip) -> pd.DataFrame:
    mobile = z.read("이동통신/방문자수추이.csv")
    mobile = add_identity(mobile[mobile["공간단위"].eq("시군구") & mobile["읍면동"].isna()])
    domestic = mobile[mobile["국적구분"].eq("내국인")].pivot(
        index=["지역키", "기준년월"], columns="방문자구분", values="방문자수"
    ).reset_index().rename(columns={
        "외지인방문자(b)": "외지인방문자수", "전체방문자(a+b)": "전체방문자수",
        "현지인방문자(a)": "현지인방문자수",
    })
    foreign = mobile[mobile["국적구분"].eq("외국인")].groupby(
        ["지역키", "기준년월"], as_index=False
    )["방문자수"].sum().rename(columns={"방문자수": "외국인방문자수"})
    monthly = domestic.merge(foreign, on=["지역키", "기준년월"], how="left", validate="one_to_one")

    card = add_identity(z.read("신용카드/관광소비추이.csv"))
    card = card[(card["공간단위"].eq("시군구")) & card["읍면동"].isna() & card["중분류"].eq("관광총소비")]
    card = card.pivot(index=["지역키", "기준년월"], columns="국적구분", values="소비액천원").reset_index()
    card = card.rename(columns={"내국인": "내국인관광소비_천원", "외국인": "외국인관광소비_천원"})
    monthly = monthly.merge(card, on=["지역키", "기준년월"], how="outer", validate="one_to_one")

    unique = add_identity(z.read("숙박체류/순방문자숙박비율.csv"))[
        ["지역키", "기준년월", "순방문자수", "숙박자비율"]
    ].rename(columns={"숙박자비율": "숙박자비율_pct"})
    nights = add_identity(z.read("숙박체류/평균숙박일.csv"))[
        ["지역키", "기준년월", "평균숙박일수"]
    ]
    search = add_identity(z.read("숙박체류/숙박목적지검색.csv"))[
        ["지역키", "기준년월", "검색건수"]
    ].rename(columns={"검색건수": "숙박검색건수"})
    stay = add_identity(z.read("숙박체류/평균체류시간추이.csv"))
    stay = stay[stay["비교지역명"].eq(stay["시군구"])][
        ["지역키", "기준년월", "체류시간분"]
    ].rename(columns={"체류시간분": "평균체류시간_분"})
    types = add_identity(z.read("숙박체류/숙박유형별비율.csv"))
    types["숙박자중_3박이상_pct"] = types[["3박", "4박", "5박", "6박", "7박이상"]].sum(axis=1, min_count=5)
    types = types[["지역키", "기준년월", "숙박자중_3박이상_pct"]]
    for frame in (unique, nights, search, stay, types):
        monthly = monthly.merge(frame, on=["지역키", "기준년월"], how="outer", validate="one_to_one")

    monthly["기준년월"] = monthly["기준년월"].astype(str)
    monthly["기간"] = None
    for key, meta in SITES.items():
        for period, (start, end) in period_bounds(meta["year"], meta["month"]).items():
            mask = monthly["지역키"].eq(key) & monthly["기준년월"].between(start, end)
            monthly.loc[mask, "기간"] = period
    monthly = monthly[monthly["기간"].notna()].copy()
    monthly["지역"] = monthly["지역키"].map(lambda k: SITES[k]["region"])
    monthly["시설"] = monthly["지역키"].map(lambda k: SITES[k]["site"])
    monthly["최초선정연도"] = monthly["지역키"].map(lambda k: SITES[k]["year"])
    monthly["숙박방문자추정수"] = monthly["순방문자수"] * monthly["숙박자비율_pct"] / 100
    monthly["전체순방문자중_3박이상_pct"] = (
        monthly["숙박자비율_pct"] * monthly["숙박자중_3박이상_pct"] / 100
    )
    return monthly.sort_values(["지역키", "기준년월"]).reset_index(drop=True)


def complete_sum(frame: pd.DataFrame, column: str) -> float:
    return float(frame[column].sum()) if frame[column].notna().sum() == 12 else np.nan


def complete_weighted(frame: pd.DataFrame, column: str, weight: str) -> float:
    valid = frame[[column, weight]].dropna()
    if len(valid) != 12 or valid[weight].sum() == 0:
        return np.nan
    return float(np.average(valid[column], weights=valid[weight]))


def aggregate_kpis(monthly: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (key, period), f in monthly.groupby(["지역키", "기간"], sort=False):
        if len(f) != 12:
            raise ValueError(f"{key} {period}: 달력 월 {len(f)}개")
        row = {
            "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
            "최초선정연도": SITES[key]["year"], "기간": period,
            **{m: complete_sum(f, m) for m in SUM_METRICS},
            "숙박자비율_pct": complete_weighted(f, "숙박자비율_pct", "순방문자수"),
            "평균체류시간_분": complete_weighted(f, "평균체류시간_분", "순방문자수"),
            "평균숙박일수": complete_weighted(f, "평균숙박일수", "숙박방문자추정수"),
            "숙박자중_3박이상_pct": complete_weighted(f, "숙박자중_3박이상_pct", "숙박방문자추정수"),
            "전체순방문자중_3박이상_pct": complete_weighted(f, "전체순방문자중_3박이상_pct", "순방문자수"),
        }
        if pd.notna(row["내국인관광소비_천원"]) and pd.notna(row["외지인방문자수"]):
            row["방문자대비관광소비_천원_proxy"] = row["내국인관광소비_천원"] / row["외지인방문자수"]
        else:
            row["방문자대비관광소비_천원_proxy"] = np.nan
        if f["외지인방문자수"].notna().sum() == 12:
            row["방문_CV"] = f["외지인방문자수"].std(ddof=0) / f["외지인방문자수"].mean()
            row["DSI"] = 1 - row["방문_CV"]
        else:
            row["방문_CV"] = row["DSI"] = np.nan
        row["WSPI"] = np.nan
        rows.append(row)
    return pd.DataFrame(rows).sort_values(["최초선정연도", "지역키", "기간"])


def safe_growth(before: float, after: float) -> float:
    if pd.isna(before) or pd.isna(after) or before == 0:
        return np.nan
    return (after / before - 1) * 100


def direction(value: float, threshold: float = 3) -> str:
    if pd.isna(value):
        return "NA"
    if value > threshold:
        return "UP"
    if value < -threshold:
        return "DOWN"
    return "FLAT"


def growth_table(kpis: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for key, f in kpis.groupby("지역키"):
        by = f.set_index("기간")
        for metric in KPI_METRICS:
            vals = {p: by.at[p, metric] for p in PERIOD_NAMES}
            row = {
                "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
                "최초선정연도": SITES[key]["year"], "지표": metric, **vals,
            }
            for before, after, suffix in [("P1", "P2", "12"), ("P2", "P3", "23"), ("P3", "P4", "34")]:
                delta = vals[after] - vals[before] if pd.notna(vals[before]) and pd.notna(vals[after]) else np.nan
                row[f"g{suffix}_pct"] = safe_growth(vals[before], vals[after])
                row[f"delta{suffix}_abs"] = delta
                row[f"delta{suffix}_pctp"] = delta if metric in RATE_METRICS else np.nan
            row["지정직후_판정_3pct"] = direction(row["g23_pct"])
            row["2년차_판정_3pct"] = direction(row["g34_pct"])
            dirs = [direction(row["g23_pct"], t) for t in (0, 3, 5)]
            row["민감도_0pct"], row["민감도_3pct"], row["민감도_5pct"] = dirs
            row["민감도신뢰"] = "NA" if "NA" in dirs else ("HIGH" if len(set(dirs)) == 1 else "LOW")
            rows.append(row)
    return pd.DataFrame(rows)


def availability_table(monthly: pd.DataFrame) -> pd.DataFrame:
    metrics = [
        "외지인방문자수", "전체방문자수", "외국인방문자수", "내국인관광소비_천원",
        "순방문자수", "숙박자비율_pct", "평균숙박일수", "평균체류시간_분",
        "숙박검색건수", "숙박자중_3박이상_pct",
    ]
    rows = []
    for (key, period), f in monthly.groupby(["지역키", "기간"]):
        start, end = period_bounds(SITES[key]["year"], SITES[key]["month"])[period]
        for metric in metrics:
            n = int(f[metric].notna().sum())
            rows.append({
                "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
                "최초선정연도": SITES[key]["year"], "기간": period,
                "시작월": start, "종료월": end, "지표": metric,
                "관측개월수": n, "연간계산가능": n == 12,
            })
    return pd.DataFrame(rows)


def period_table() -> pd.DataFrame:
    rows = []
    meanings = {"P1": "지정 2년 전", "P2": "지정 직전", "P3": "지정 1년차", "P4": "지정 2년차"}
    for key, meta in SITES.items():
        for p, (start, end) in period_bounds(meta["year"], meta["month"]).items():
            rows.append({
                "지역키": key, "지역": meta["region"], "시설": meta["site"],
                "최초선정연도": meta["year"], "공식발표일": meta["announcement"], "기간": p, "기간의미": meanings[p],
                "시작월": start, "종료월": end, "필요개월수": 12,
            })
    return pd.DataFrame(rows)


def its_tables(monthly: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    specs = {
        "숙박검색건수": ("숙박검색건수", True), "외지인방문자수": ("외지인방문자수", True),
        "숙박자비율_pct": ("숙박자비율_pct", False), "평균체류시간_분": ("평균체류시간_분", False),
        "평균숙박일수": ("평균숙박일수", False), "내국인관광소비_천원": ("내국인관광소비_천원", True),
    }
    rows, excluded = [], []
    for key, f in monthly.groupby("지역키"):
        f = f.sort_values("기준년월").reset_index(drop=True)
        for metric, (column, log_transform) in specs.items():
            if f[column].notna().sum() != 48:
                excluded.append({
                    "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
                    "최초선정연도": SITES[key]["year"], "지표": metric,
                    "상태": "NOT_COMPUTABLE", "관측개월수": int(f[column].notna().sum()),
                    "사유": "지정연도 기준 48개월 완전 관측이 아님",
                })
                continue
            for start_month in (SITES[key]["month"], SITES[key]["month"] + 1):
                intervention = ym(SITES[key]["year"], start_month)
                n = len(f); t = np.arange(1, n + 1, dtype=float)
                post = (f["기준년월"].to_numpy() >= intervention).astype(float)
                first_post_t = t[np.flatnonzero(post == 1)[0]]
                post_slope = (t - first_post_t) * post
                month_dummies = pd.get_dummies(f["기준년월"].str[-2:].astype(int), drop_first=True, dtype=float)
                x = np.column_stack([np.ones(n), t, post, post_slope, month_dummies.to_numpy()])
                raw = f[column].to_numpy(dtype=float)
                y = np.log1p(raw) if log_transform else raw
                for lag in (1, 3, 6, 12):
                    beta, cov = base.newey_west_ols(y, x, maxlags=lag)
                    se = np.sqrt(np.maximum(np.diag(cov), 0))
                    p = 2 * norm.sf(np.abs(beta / np.where(se == 0, np.nan, se)))
                    rows.append({
                        "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
                        "최초선정연도": SITES[key]["year"], "지표": metric,
                        "변환": "log1p" if log_transform else "level", "관측월수": n,
                        "개입시작월": intervention, "HAC_maxlags": lag,
                        "지정전_월추세_beta": beta[1], "지정전_월추세_p": p[1],
                        "즉시수준변화_beta": beta[2], "즉시수준변화_p": p[2],
                        "지정후_기울기변화_beta": beta[3], "지정후_기울기변화_p": p[3],
                        "즉시변화_환산_pct": (math.exp(beta[2]) - 1) * 100 if log_transform else np.nan,
                        "기울기변화_월환산_pct": (math.exp(beta[3]) - 1) * 100 if log_transform else np.nan,
                    })
    sensitivity = pd.DataFrame(rows)
    sensitivity["즉시수준변화_q_BH"] = sensitivity.groupby(["개입시작월", "HAC_maxlags"])["즉시수준변화_p"].transform(base.benjamini_hochberg)
    sensitivity["지정후_기울기변화_q_BH"] = sensitivity.groupby(["개입시작월", "HAC_maxlags"])["지정후_기울기변화_p"].transform(base.benjamini_hochberg)
    primary_month = sensitivity["지역키"].map(lambda k: f"{SITES[k]['month']:02d}")
    primary = sensitivity[(sensitivity["개입시작월"].str[-2:].eq(primary_month)) & sensitivity["HAC_maxlags"].eq(3)].copy()
    original_sites = base.SITES
    try:
        base.SITES = SITES
        robustness = base.its_robustness_table(sensitivity)
    finally:
        base.SITES = original_sites
    return primary, sensitivity, pd.concat([robustness, pd.DataFrame(excluded)], ignore_index=True, sort=False)


def category_change(z: IntegratedZip) -> pd.DataFrame:
    d = add_identity(z.read("신용카드/관광소비추이.csv"))
    d = d[d["공간단위"].eq("시군구") & d["읍면동"].isna() & d["국적구분"].eq("내국인") & ~d["중분류"].eq("관광총소비")].copy()
    d["기준년월"] = d["기준년월"].astype(str)
    d["기간"] = None
    for key, meta in SITES.items():
        for p, (start, end) in period_bounds(meta["year"], meta["month"]).items():
            d.loc[d["지역키"].eq(key) & d["기준년월"].between(start, end), "기간"] = p
    d = d[d["기간"].notna()]
    agg = d.groupby(["지역키", "기간", "중분류"], as_index=False)["소비액천원"].sum(min_count=12)
    rows = []
    for key, f in agg.groupby("지역키"):
        by = f.set_index(["기간", "중분류"])["소비액천원"]
        categories = sorted(set(f["중분류"]))
        for before, after in [("P2", "P3"), ("P3", "P4")]:
            for c in categories:
                a, b = by.get((before, c), np.nan), by.get((after, c), np.nan)
                rows.append({
                    "지역키": key, "지역": SITES[key]["region"], "시설": SITES[key]["site"],
                    "최초선정연도": SITES[key]["year"], "변화구간": f"{before}→{after}", "중분류": c,
                    "before_천원": a, "after_천원": b,
                    "실제변화_천원": b - a if pd.notna(a) and pd.notna(b) else np.nan,
                    "성장률_pct": safe_growth(a, b),
                })
    return pd.DataFrame(rows)


def exact_period_auxiliary(z: IntegratedZip, kpis: pd.DataFrame):
    card = add_identity(z.read("신용카드/지역별지출액.csv"))
    visit = add_identity(z.read("이동통신/지역별방문자수.csv"))
    actual = add_identity(z.read("이동통신/방문자거주지및유출지.csv"))
    search = add_identity(z.read("숙박체류/숙박목적지유입.csv"))

    concentration_parts, change_parts, relative_parts, alignment_parts = [], [], [], []
    original_sites, original_periods = base.SITES, base.PERIODS
    try:
        for key, meta in SITES.items():
            bounds = period_bounds(meta["year"], meta["month"])
            exact = {f"{start}-{end}": period for period, (start, end) in bounds.items()}

            site_card = card[
                card["지역키"].eq(key)
                & card["국적구분"].eq("내국인")
                & card["기준기간"].isin(exact)
            ].copy()
            site_card["기간"] = site_card["기준기간"].map(exact)
            site_visit = visit[
                visit["지역키"].eq(key)
                & visit["국적구분"].eq("내국인")
                & visit["기준기간"].isin(exact)
            ].copy()
            site_visit["기간"] = site_visit["기준기간"].map(exact)
            site_actual = actual[
                actual["지역키"].eq(key)
                & actual["국적구분"].eq("내국인")
                & actual["기준기간"].isin(exact)
            ].copy()
            site_actual["기간"] = site_actual["기준기간"].map(exact)
            site_search = search[
                search["지역키"].eq(key) & search["기준기간"].isin(exact)
            ].copy()
            site_search["기간"] = site_search["기준기간"].map(exact)

            observed = {
                "소비": set(site_card["기간"].dropna()),
                "방문": set(site_visit["기간"].dropna()),
                "방문유입": set(site_actual["기간"].dropna()),
                "검색유입": set(site_search["기간"].dropna()),
            }
            missing = {name: set(PERIOD_NAMES) - periods for name, periods in observed.items()}
            if missing["소비"] or missing["방문"]:
                raise ValueError(f"{key}: 지정기간 읍면동 자료 누락 {missing}")

            cohort = {key: meta}
            card_dongs = {key: site_card[["기간", "지출지역명", "지출비율"]].rename(
                columns={"지출지역명": "읍면동", "지출비율": "점유율_pct"}
            )}
            visit_dongs = {key: site_visit[["기간", "하위지역명", "방문자수"]].rename(
                columns={"하위지역명": "읍면동"}
            )}
            base.SITES, base.PERIODS = cohort, bounds
            concentration, spatial_change, relative = base.spatial_tables(
                kpis[kpis["지역키"].eq(key)], card_dongs, visit_dongs
            )
            concentration_parts.append(concentration)
            change_parts.append(spatial_change)
            relative_parts.append(relative)
            if not missing["방문유입"] and not missing["검색유입"]:
                actual_all = {key: site_actual[["기간", "상대지역시도", "상대지역시군구", "비율"]].rename(
                    columns={"상대지역시도": "광역", "상대지역시군구": "기초", "비율": "점유율_pct"}
                )}
                search_all = {key: site_search[["기간", "유입시도", "유입시군구", "거주방문자비율"]].rename(
                    columns={"유입시도": "광역", "유입시군구": "기초", "거주방문자비율": "조건부점유율_pct"}
                )}
                alignment_parts.append(base.conditional_alignment(actual_all, search_all))
    finally:
        base.SITES, base.PERIODS = original_sites, original_periods

    return tuple(
        pd.concat(parts, ignore_index=True, sort=False)
        for parts in (concentration_parts, change_parts, relative_parts, alignment_parts)
    )


def mobility_detail_outputs(z: IntegratedZip, kpis: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """대시보드용 시설 소재 읍면동 방문과 방문자 출발지 표를 만든다."""
    visit = add_identity(z.read("이동통신/지역별방문자수.csv"))
    origin = add_identity(z.read("이동통신/방문자거주지및유출지.csv"))
    facility_rows = []
    origin_parts = []

    for key, meta in SITES.items():
        bounds = period_bounds(meta["year"], meta["month"])
        exact = {f"{start}-{end}": period for period, (start, end) in bounds.items()}
        site_visit = visit[
            visit["지역키"].eq(key)
            & visit["국적구분"].eq("내국인")
            & visit["기준기간"].isin(exact)
        ].copy()
        site_visit["기간"] = site_visit["기준기간"].map(exact)
        site_origin = origin[
            origin["지역키"].eq(key)
            & origin["국적구분"].eq("내국인")
            & origin["기준기간"].isin(exact)
        ].copy()
        site_origin["기간"] = site_origin["기준기간"].map(exact)
        site_origin = site_origin.rename(columns={
            "상대지역시도": "거주지(시도)", "상대지역시군구": "거주지(시군구)", "비율": "비율(%)"
        })
        site_origin["시설소재_읍면동"] = meta["dong"]
        origin_parts.append(site_origin[[
            "거주지(시도)", "거주지(시군구)", "비율(%)", "지역키", "지역", "시설", "기간", "시설소재_읍면동"
        ]])

        for period in PERIOD_NAMES:
            target = site_visit[
                site_visit["기간"].eq(period) & site_visit["하위지역명"].eq(meta["dong"])
            ]
            if len(target) != 1:
                raise ValueError(f"{key} {period}: {meta['dong']} 방문자료 {len(target)}행")
            target = target.iloc[0]
            county_total = kpis.loc[
                kpis["지역키"].eq(key) & kpis["기간"].eq(period), "전체방문자수"
            ].iloc[0]
            facility_rows.append({
                "지역키": key, "지역": meta["region"], "시설": meta["site"], "영역": "방문",
                "기간": period, "시설소재_읍면동": meta["dong"],
                "시설동_방문자수": target["방문자수"], "시설동_외지인방문자수": np.nan,
                "시군구_전체방문자수": county_total, "시설동_점유율_pct": target["방문자비율"],
                "자료범위": "통합 ZIP의 시군구 내 읍면동 방문자 분포; 외지인 세부값 없음",
            })

    facility = pd.DataFrame(facility_rows).sort_values(["지역키", "기간"])
    facility["시설동_성장률_pct"] = facility.groupby("지역키")["시설동_방문자수"].pct_change() * 100
    facility["시군구_성장률_pct"] = facility.groupby("지역키")["시군구_전체방문자수"].pct_change() * 100
    facility["상대집중도_RC_pctp"] = facility["시설동_성장률_pct"] - facility["시군구_성장률_pct"]
    facility["시설동_점유율변화_pctp"] = facility.groupby("지역키")["시설동_점유율_pct"].diff()
    origins = pd.concat(origin_parts, ignore_index=True, sort=False)
    return facility, origins


def status_table() -> pd.DataFrame:
    rows = []
    for key, meta in SITES.items():
        rows.append({"지역키": key, "항목": "Shift-Share", "상태": "NOT_COMPUTABLE", "사유": "서로 다른 선정연도의 event-time 자료를 합치면 경기연도가 달라지고 독립 일반관광 benchmark도 없음"})
        rows.extend([
            {"지역키": key, "항목": "LQ", "상태": "NOT_COMPUTABLE", "사유": "독립적인 전남·전북 일반 관광시장 출발지 benchmark 부재"},
            {"지역키": key, "항목": "WSPI", "상태": "NOT_COMPUTABLE", "사유": "대상지를 제외한 광역 일반 시군구 SPV benchmark 부재"},
        ])
    out = pd.DataFrame(rows)
    out["지역"] = out["지역키"].map(lambda k: SITES[k]["region"])
    out["시설"] = out["지역키"].map(lambda k: SITES[k]["site"])
    return out[["지역키", "지역", "시설", "항목", "상태", "사유"]]


def metric_dictionary() -> pd.DataFrame:
    rows = [
        ("외지인방문자수", "KT 내국인 외지인방문자(b); 외국인 미합산", "기간 내 12개월 합계"),
        ("전체방문자수", "KT 내국인 전체방문자(a+b); 외국인 미합산", "기간 내 12개월 합계"),
        ("숙박검색건수", "티맵 숙박 목적지 검색건수", "기간 내 12개월 합계"),
        ("내국인관광소비_천원", "신한카드 국적구분=내국인, 중분류=관광총소비", "기간 내 12개월 합계"),
        ("숙박자비율_pct", "월별 숙박자비율", "순방문자수 가중평균"),
        ("평균체류시간_분", "대상 시군구 월별 평균체류시간", "순방문자수 가중평균"),
        ("평균숙박일수", "월별 평균숙박일수", "순방문자수×숙박자비율 가중평균"),
        ("숙박자중_3박이상_pct", "3박+4박+5박+6박+7박이상", "추정 숙박방문자수 가중평균"),
        ("전체순방문자중_3박이상_pct", "숙박자비율×숙박자중 3박 이상 비율/100", "순방문자수 가중평균"),
        ("방문자대비관광소비_천원_proxy", "내국인 관광소비/내국인 외지인방문자", "카드·통신 모집단이 다른 proxy"),
        ("방문_CV", "월별 외지인방문자 표준편차/평균", "모집단 표준편차(ddof=0)"),
        ("DSI", "비계절성 보조지표", "1-방문_CV; 음수 가능"),
        ("성장률", "인접 P구간 변화", "(후기-전기)/전기×100"),
        ("비율 절대변화", "% 단위 KPI의 변화", "후기-전기 (%p)"),
    ]
    return pd.DataFrame(rows, columns=["지표", "정의", "연간화_수식"])


def quality_table(monthly: pd.DataFrame, availability: pd.DataFrame) -> pd.DataFrame:
    identity_error = (monthly["전체방문자수"] - monthly["외지인방문자수"] - monthly["현지인방문자수"]).abs().max()
    return pd.DataFrame([
        {"항목": "기간 매핑", "상태": "OK", "내용": "지역별 공식 신규선정 발표월(4월)에 따라 P1~P4 각 12개월 배정"},
        {"항목": "내국인 방문자 정의", "상태": "OK", "내용": f"외지인·전체는 국적구분=내국인만 사용; 전체=외지인+현지인 최대 반올림오차 {identity_error:g}"},
        {"항목": "외국인 중복", "상태": "CORRECTED", "내용": "기존 추가폴더처럼 외국인을 외지인/전체에 합산하지 않음"},
        {"항목": "연간 완전성", "상태": "STRICT", "내용": "12개월 중 한 달이라도 없으면 합계·가중평균을 계산하지 않음"},
        {"항목": "월합계 주의", "상태": "CAUTION", "내용": "데이터랩 보정·반올림으로 직접 연간조회 값과 미세 차이 가능; 변화율 중심 해석"},
        {"항목": "ITS 인과성", "상태": "CAUTION", "내용": "대조군이 없어 구조변화 탐색이며 인과효과가 아님; 무주 P1은 코로나 충격과 중첩"},
        {"항목": "분석단위", "상태": "CAUTION", "내용": "시설 자체가 아니라 시설 소재 시군구 전체 관광시장"},
        {"항목": "시장정합", "상태": "PROXY", "내용": "4개 지역 모두 지정기간 기준 광역 동일가중 조건부 Spearman/JSD; 전국시장 지표가 아님"},
        {"항목": "공간분석", "상태": "OK", "내용": "4개 지역 모두 지정기간 기준 읍면동 방문·소비 자료로 계산"},
        {"항목": "Shift-Share", "상태": "EXCLUDED", "내용": "선정연도가 다른 4개소를 event-time으로 합치면 서로 다른 경기연도를 섞으므로 계산하지 않음"},
    ])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    z = IntegratedZip(INPUT_ZIP)
    monthly = load_monthly(z)
    counts = monthly.groupby(["지역키", "기간"]).size()
    expected_rows = len(SITES) * len(PERIOD_NAMES) * 12
    if len(monthly) != expected_rows or not (counts == 12).all():
        raise AssertionError(f"{len(SITES)}지역×48개월 달력 골격 불완전: {counts}")
    availability = availability_table(monthly)
    kpis = aggregate_kpis(monthly)
    growth = growth_table(kpis)
    its, its_sensitivity, its_robustness = its_tables(monthly)
    categories = category_change(z)
    concentration, spatial_change, spatial_relative, alignment = exact_period_auxiliary(z, kpis)
    mobility, origins = mobility_detail_outputs(z, kpis)
    outputs = {
        "period_definitions.csv": period_table(),
        "metric_dictionary.csv": metric_dictionary(),
        "data_availability.csv": availability,
        "monthly_input.csv": monthly,
        "kpi_by_period.csv": kpis,
        "growth_bottleneck.csv": growth,
        "its_designation_hac3.csv": its,
        "its_hac_sensitivity.csv": its_sensitivity,
        "its_robustness.csv": its_robustness,
        "category_change.csv": categories,
        "spatial_concentration_available_sites.csv": concentration,
        "spatial_change_available_sites.csv": spatial_change,
        "spatial_relative_growth_available_sites.csv": spatial_relative,
        "market_alignment_conditional_available_sites.csv": alignment,
        "spatial_mobility_only.csv": mobility,
        "mobility_origin_by_period.csv": origins,
        "not_computable_status.csv": status_table(),
        "data_quality.csv": quality_table(monthly, availability),
    }
    for name, frame in outputs.items():
        base.round_numeric(frame).to_csv(OUT / name, index=False, encoding="utf-8-sig")
    print(f"saved: {OUT}")
    print(period_table().to_string(index=False))
    core = growth[growth["지표"].isin(base.MAIN_METRICS)]
    print(core[["지역", "지표", "g23_pct", "g34_pct"]].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
