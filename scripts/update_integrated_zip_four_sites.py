"""통합 ZIP을 무주·완주 정확 P구간 원자료로 갱신하고 장성군을 제외한다."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os
import re
import unicodedata
import zipfile

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TARGET = DATA / "한국관광데이터랩 데이터 통합.zip"
SITES = {
    "전북무주": {"city": "무주군", "province": "전북특별자치도", "folder": DATA / "전북무주"},
    "전북완주": {"city": "완주군", "province": "전북특별자치도", "folder": DATA / "전북완주"},
}
PERIOD_RE = re.compile(r"(20\d{4})-(20\d{4})")


def decode_name(name: str) -> str:
    try:
        name = name.encode("cp437").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass
    return unicodedata.normalize("NFC", name)


def read_zip_csv(path: Path, suffix: str) -> pd.DataFrame:
    normalized = suffix.replace(" ", "")
    with zipfile.ZipFile(path) as archive:
        matches = [
            info for info in archive.infolist()
            if decode_name(info.filename).replace(" ", "").endswith(normalized)
        ]
        if len(matches) != 1:
            raise ValueError(f"{path.name}: {suffix!r} 파일 {len(matches)}개")
        return pd.read_csv(BytesIO(archive.read(matches[0])), encoding="utf-8-sig")


def has_member(path: Path, text: str) -> bool:
    with zipfile.ZipFile(path) as archive:
        return any(text in decode_name(info.filename) for info in archive.infolist())


def period(path: Path) -> str:
    match = PERIOD_RE.search(path.name)
    if not match:
        raise ValueError(f"기간을 찾을 수 없음: {path}")
    return "-".join(match.groups())


def meta(frame: pd.DataFrame, site: dict, nationality: str | None = None) -> pd.DataFrame:
    out = frame.copy()
    out.insert(0, "공간단위", "시군구")
    out.insert(0, "읍면동", np.nan)
    out.insert(0, "시군구", site["city"])
    out.insert(0, "시도", site["province"])
    if nationality is not None:
        out.insert(4, "국적구분", nationality)
    return out


def align(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column not in out:
            out[column] = np.nan
    return out[columns]


def card_frames(site: dict, schemas: dict[str, list[str]]) -> dict[str, pd.DataFrame]:
    rows = {name: [] for name in ("관광소비추이.csv", "업종별지출액.csv", "지역별지출액.csv")}
    grouped: dict[str, list[Path]] = {}
    for path in sorted((site["folder"] / "신용카드").glob("*.zip")):
        grouped.setdefault(period(path), []).append(path)
    for bounds, paths in sorted(grouped.items()):
        if len(paths) != 2:
            raise ValueError(f"{site['city']} {bounds}: 신용카드 ZIP 2개 필요")
        totals = {}
        for path in paths:
            trend = read_zip_csv(path, "관광소비 추이.csv")
            totals[path] = float(trend.loc[trend["중분류"].eq("관광총소비"), "소비액(천원)"].sum())
        domestic = max(totals, key=totals.get)
        for path in paths:
            nationality = "내국인" if path == domestic else "외국인"
            trend = read_zip_csv(path, "관광소비 추이.csv").rename(columns={"소비액(천원)": "소비액천원"})
            rows["관광소비추이.csv"].append(meta(trend, site, nationality))

            industry = read_zip_csv(path, "업종별 지출액.csv").rename(columns={
                "대분류 지출액 비율": "대분류지출액비율", "중분류 지출액 비율": "중분류지출액비율"
            })
            industry.insert(0, "기준기간", bounds)
            rows["업종별지출액.csv"].append(meta(industry, site, nationality))

            region = read_zip_csv(path, "지역별 지출액.csv")
            region = region.rename(columns={region.columns[0]: "지출지역명", "비율(%)": "지출비율"})
            region.insert(0, "지출지역공간단위", "읍면동")
            region.insert(0, "기준기간", bounds)
            rows["지역별지출액.csv"].append(meta(region, site, nationality))
    return {
        name: align(pd.concat(parts, ignore_index=True), schemas[f"신용카드/{name}"])
        for name, parts in rows.items()
    }


def mobile_frames(site: dict, schemas: dict[str, list[str]]) -> dict[str, pd.DataFrame]:
    rows = {name: [] for name in ("방문자수추이.csv", "지역별방문자수.csv", "방문자거주지및유출지.csv")}
    for path in sorted((site["folder"] / "이동통신").glob("*.zip")):
        bounds = period(path)
        foreign = has_member(path, "외국인 방문자 수 추이.csv")
        if foreign:
            trend = read_zip_csv(path, "외국인 방문자 수 추이.csv").rename(columns={
                "날짜": "기준년월", "외국인 방문자수": "방문자수"
            })[["기준년월", "방문자수"]]
            trend["방문자구분"] = "외국인방문자"
            rows["방문자수추이.csv"].append(meta(trend, site, "외국인"))

            region = read_zip_csv(path, "외국인 지역별 방문자 수.csv").rename(columns={
                "지역": "하위지역명", "외국인 방문자수": "방문자수"
            })
            total = pd.to_numeric(region["방문자수"], errors="coerce").sum()
            region["방문자비율"] = pd.to_numeric(region["방문자수"], errors="coerce") / total * 100 if total else np.nan
            region["기준기간"], region["자료계열"], region["하위공간단위"] = bounds, "기본본", "읍면동"
            rows["지역별방문자수.csv"].append(meta(region, site, "외국인"))

            origin = read_zip_csv(path, "외국인 방문자 거주지(국가).csv").rename(columns={
                "국가명": "상대국가", "비율(%)": "비율"
            })
            origin["기준기간"], origin["흐름구분"], origin["상대지역단위"] = bounds, np.nan, "국가"
            rows["방문자거주지및유출지.csv"].append(meta(origin, site, "외국인"))
        else:
            trend = read_zip_csv(path, "방문자 수 추이.csv").rename(columns={
                "방문자 구분": "방문자구분", "방문자 수": "방문자수"
            })[["기준년월", "방문자구분", "방문자수"]]
            rows["방문자수추이.csv"].append(meta(trend, site, "내국인"))

            region = read_zip_csv(path, "지역별 방문자 수.csv").rename(columns={
                "기초지자체명": "하위지역명", "기초지자체 방문자 수": "방문자수", "기초지자체 방문자 비율": "방문자비율"
            })
            region["기준기간"], region["자료계열"], region["하위공간단위"] = bounds, "기본본", "읍면동"
            rows["지역별방문자수.csv"].append(meta(region, site, "내국인"))

            origin = read_zip_csv(path, "방문자 거주지.csv").rename(columns={
                "거주지(시도)": "상대지역시도", "거주지(시군구)": "상대지역시군구", "비율(%)": "비율"
            })
            origin["기준기간"], origin["흐름구분"], origin["상대지역단위"] = bounds, np.nan, "시군구"
            rows["방문자거주지및유출지.csv"].append(meta(origin, site, "내국인"))
    return {
        name: align(pd.concat(parts, ignore_index=True), schemas[f"이동통신/{name}"])
        for name, parts in rows.items()
    }


def stay_frames(site: dict, schemas: dict[str, list[str]]) -> dict[str, pd.DataFrame]:
    names = (
        "방문자체류특성.csv", "숙박목적지검색.csv", "숙박목적지유입.csv", "숙박방문자비율추이.csv",
        "숙박유형별비율.csv", "순방문자숙박비율.csv", "평균숙박일.csv", "평균체류시간추이.csv",
    )
    rows = {name: [] for name in names}
    for path in sorted((site["folder"] / "숙박체류시간").glob("*.zip")):
        bounds = period(path)
        feature = read_zip_csv(path, "방문자 체류특성.csv").rename(columns={
            "지역코드": "비교지역코드", "지역명": "비교지역명", "평균 체류시간": "평균체류시간분"
        })
        feature.insert(0, "기준기간", bounds)
        rows["방문자체류특성.csv"].append(meta(feature, site))

        search = read_zip_csv(path, "숙박 목적지 검색건수.csv").rename(columns={
            "기준연월": "기준년월", "전년동기 검색건수": "전년동기검색건수", "전년동기 대비 증감률": "전년동기대비증감률"
        })
        rows["숙박목적지검색.csv"].append(meta(search, site))

        inflow = read_zip_csv(path, "숙박 목적지 유입 지역 분포.csv").rename(columns={
            "광역지자체명": "유입시도", "기초지자체명": "유입시군구", "기초지자체별 거주 방문자 비율": "거주방문자비율"
        })
        inflow.insert(0, "기준기간", bounds)
        rows["숙박목적지유입.csv"].append(meta(inflow, site))

        overnight = read_zip_csv(path, "숙박방문자 비율 추이 .csv").rename(columns={
            "기준연월": "기준년월", "숙박방문자 비율": "숙박방문자비율"
        })
        rows["숙박방문자비율추이.csv"].append(meta(overnight, site))

        types = read_zip_csv(path, "숙박 유형별 방문자 비율.csv").rename(columns=lambda c: c.replace(" ", ""))
        types = types.rename(columns={"기준연월": "기준년월"})
        rows["숙박유형별비율.csv"].append(meta(types, site))

        unique = read_zip_csv(path, "순 방문자 수 및 숙박 비율.csv").rename(columns={
            "기준연월": "기준년월", "순 방문자수": "순방문자수", "숙박자 비율": "숙박자비율"
        })
        rows["순방문자숙박비율.csv"].append(meta(unique, site))

        nights = read_zip_csv(path, "평균 숙박일.csv").rename(columns={"기준연월": "기준년월", "평균 숙박일수": "평균숙박일수"})
        rows["평균숙박일.csv"].append(meta(nights, site))

        stay = read_zip_csv(path, "평균 체류시간 추이.csv").rename(columns={
            "기준연월": "기준년월", "지역명": "비교지역명", "체류시간(분)": "체류시간분"
        })
        rows["평균체류시간추이.csv"].append(meta(stay, site))
    return {
        name: align(pd.concat(parts, ignore_index=True), schemas[f"숙박체류/{name}"])
        for name, parts in rows.items()
    }


def read_integrated() -> dict[str, pd.DataFrame]:
    out = {}
    with zipfile.ZipFile(TARGET) as archive:
        for info in archive.infolist():
            name = decode_name(info.filename)
            if info.file_size <= 1000 or not name.endswith(".csv") or name.startswith("__MACOSX"):
                continue
            out[name] = pd.read_csv(BytesIO(archive.read(info)), encoding="utf-8-sig")
    return out


def main() -> None:
    integrated = read_integrated()
    schemas = {name: frame.columns.tolist() for name, frame in integrated.items()}
    replacements: dict[str, list[pd.DataFrame]] = {name: [] for name in integrated}
    for site in SITES.values():
        for prefix, built in (
            ("신용카드", card_frames(site, schemas)),
            ("이동통신", mobile_frames(site, schemas)),
            ("숙박체류", stay_frames(site, schemas)),
        ):
            for filename, frame in built.items():
                replacements[f"{prefix}/{filename}"].append(frame)

    updated = {}
    for name, frame in integrated.items():
        keep = frame.loc[~frame["시군구"].isin(["장성군", "무주군", "완주군"])].copy()
        parts = [keep] + replacements[name]
        result = pd.concat(parts, ignore_index=True, sort=False)
        result = align(result, schemas[name])
        if result["시군구"].eq("장성군").any():
            raise AssertionError(f"{name}: 장성군 제거 실패")
        updated[name] = result

    temporary = TARGET.with_suffix(".tmp.zip")
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, frame in sorted(updated.items()):
            archive.writestr(name, frame.to_csv(index=False, encoding="utf-8-sig"))
    os.replace(temporary, TARGET)
    print(f"updated: {TARGET}")
    for name, frame in sorted(updated.items()):
        counts = frame.groupby("시군구").size().to_dict()
        print(name, counts)


if __name__ == "__main__":
    main()
