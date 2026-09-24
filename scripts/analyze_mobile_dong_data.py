"""Build mobility-only facility-dong outputs for the five-site dashboard.

The downloaded files cover the facility dong only.  They can therefore support
facility-dong visitor share and growth, but not county-wide spatial
concentration (HHI/Gini) or dong-level consumption without card data.
"""

from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "output" / "five_sites_by_designation"

SITES = {
    "북이면": {"지역키": "전남장성", "지역": "장성군", "시설": "국립장성숲체원", "dong": "북이면", "periods": {"201806": "P1", "201906": "P2", "202006": "P3", "202106": "P4"}},
    "설천면": {"지역키": "전북무주", "지역": "무주군", "시설": "태권도원 상징지구", "dong": "설천면", "periods": {"202004": "P1", "202104": "P2", "202204": "P3", "202304": "P4"}},
    "소양면": {"지역키": "전북완주", "지역": "완주군", "시설": "아원고택", "dong": "소양면", "periods": {"202204": "P1", "202304": "P2", "202404": "P3", "202504": "P4"}},
}


def read_domestic_zip(path: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Read the three domestic mobility tables from one period ZIP."""
    with ZipFile(path) as archive:
        members = archive.namelist()
        trend_name = next(name for name in members if name.endswith("방문자 수 추이.csv") and "외국인" not in name)
        dong_name = next(name for name in members if name.endswith("지역별 방문자 수.csv") and "외국인" not in name)
        origin_name = next(name for name in members if name.endswith("방문자 거주지.csv"))
        trend = pd.read_csv(archive.open(trend_name), encoding="utf-8-sig")
        dong = pd.read_csv(archive.open(dong_name), encoding="utf-8-sig")
        origin = pd.read_csv(archive.open(origin_name), encoding="utf-8-sig")
    return trend, dong, origin


def period_start(path: Path) -> str:
    match = re.search(r"_(\d{6})-\d{6}_", path.name)
    if not match:
        raise ValueError(f"기간을 파일명에서 찾지 못했습니다: {path.name}")
    return match.group(1)


def main() -> None:
    county = pd.read_csv(OUT / "monthly_input.csv", encoding="utf-8-sig")
    county["기준년월"] = county["기준년월"].astype(str).str.zfill(6)
    county["전체방문자수"] = pd.to_numeric(county["전체방문자수"], errors="coerce")
    county = county[["지역키", "기준년월", "기간", "전체방문자수"]]

    facility_rows: list[dict[str, object]] = []
    origin_rows: list[pd.DataFrame] = []

    for folder, meta in SITES.items():
        paths = sorted((DATA / folder).glob("*.zip"))
        for path in paths:
            start = period_start(path)
            period = meta["periods"].get(start)
            if period is None:
                continue
            with ZipFile(path) as archive:
                # Foreign-only downloads do not contain the domestic table.
                if not any(name.endswith("지역별 방문자 수.csv") and "외국인" not in name for name in archive.namelist()):
                    continue
            trend, dong, origin = read_domestic_zip(path)
            trend["기준년월"] = trend["기준년월"].astype(str).str.zfill(6)
            trend["방문자 수"] = pd.to_numeric(trend["방문자 수"], errors="coerce")
            trend = trend.loc[trend["행정동명"].eq(meta["dong"])]
            total_row = trend.loc[trend["방문자 구분"].eq("전체방문자(a+b)")]
            outside_row = trend.loc[trend["방문자 구분"].eq("외지인방문자(b)")]
            dong_total = total_row["방문자 수"].sum()
            dong_outside = outside_row["방문자 수"].sum()

            county_period = county.loc[county["지역키"].eq(meta["지역키"]) & county["기간"].eq(period)]
            county_total = county_period["전체방문자수"].sum()
            share = dong_total / county_total * 100 if county_total else float("nan")
            facility_rows.append(
                {
                    "지역키": meta["지역키"],
                    "지역": meta["지역"],
                    "시설": meta["시설"],
                    "영역": "방문",
                    "기간": period,
                    "시설소재_읍면동": meta["dong"],
                    "시설동_방문자수": dong_total,
                    "시설동_외지인방문자수": dong_outside,
                    "시군구_전체방문자수": county_total,
                    "시설동_점유율_pct": share,
                    "자료범위": "이동통신 읍면동 방문자만; 카드 소비 없음",
                }
            )

            origin = origin.copy()
            origin["지역키"] = meta["지역키"]
            origin["지역"] = meta["지역"]
            origin["设施"] = meta["시설"]
            origin["기간"] = period
            origin["시설소재_읍면동"] = meta["dong"]
            origin_rows.append(origin)

    facility = pd.DataFrame(facility_rows).sort_values(["지역키", "기간"])
    facility["시설동_성장률_pct"] = facility.groupby("지역키")["시설동_방문자수"].pct_change() * 100
    facility["시군구_성장률_pct"] = facility.groupby("지역키")["시군구_전체방문자수"].pct_change() * 100
    facility["상대집중도_RC_pctp"] = facility["시설동_성장률_pct"] - facility["시군구_성장률_pct"]
    facility["시설동_점유율변화_pctp"] = facility.groupby("지역키")["시설동_점유율_pct"].diff()
    facility.to_csv(OUT / "spatial_mobility_only.csv", index=False, encoding="utf-8-sig")

    origins = pd.concat(origin_rows, ignore_index=True)
    origins = origins.rename(columns={"设施": "시설"})
    origins.to_csv(OUT / "mobility_origin_by_period.csv", index=False, encoding="utf-8-sig")

    print(f"saved: {OUT / 'spatial_mobility_only.csv'} ({len(facility)} rows)")
    print(f"saved: {OUT / 'mobility_origin_by_period.csv'} ({len(origins)} rows)")
    print(facility[["지역", "기간", "시설동_방문자수", "시군구_전체방문자수", "시설동_점유율_pct", "상대집중도_RC_pctp"]].to_string(index=False))


if __name__ == "__main__":
    main()
