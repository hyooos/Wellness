"""네 웰니스 관광지의 시설 자체·주변 숙박 공급을 같은 기준으로 산출한다.

기준
- 원자료: data/문화_숙박업.csv
- 객실: 양실수 + 한실수
- 현재: 2026-02-28에 영업 중인 업체
- 주변: 시설 대표 좌표로부터 직선거리 1km·2km·5km
- 시설 자체로 확인된 인허가 행은 주변 공급에서 분리

주의: 인허가 자료에서 시설 자체 숙박업 행을 찾지 못한 경우는 0실이 아니라
"확인 안 됨"이다. 특히 태권도원과 아원고택의 자체 숙박 수용력은 별도 시설
자료가 필요하다.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pyproj

from geo_room_capacity import load_facilities, load_lodging


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output" / "대시보드_보조데이터"
OUT.mkdir(parents=True, exist_ok=True)

CURRENT_DATE = pd.Timestamp("2026-02-28")
RADII_KM = (1, 2, 5)

SITES = {
    "태권도원 상징지구": {
        "표시명": "무주 태권도원 상징지구", "지정연도": 2022,
        "부지면적_평": 140000, "기준경도": 127.7754294, "기준위도": 36.0095801,
        "기준점출처": "OpenStreetMap 태권도원 등록점(기존 도로 대표점 대체)",
    },
    "아원고택": {"표시명": "완주 아원고택", "지정연도": 2024},
    "쉴(SHIL)랜드": {
        "표시명": "순창 쉴랜드", "지정연도": 2024,
        "부지면적_평": 150000, "기준경도": 127.131587, "기준위도": 35.4315465,
        "기준점출처": "시설 주소 검증 대표점",
    },
    "완도 해양치유센터": {"표시명": "완도 해양치유센터", "지정연도": 2024},
}

# 명칭과 주소가 시설과 일치하는 숙박업 인허가 행만 시설 자체로 확정한다.
SELF_BUSINESSES = {"쉴(SHIL)랜드": {"순창군 쉴랜드"}}

SELF_SOURCE_STATUS = {
    "태권도원 상징지구": "공식 시설자료 도약관 265실·1,031명(인허가 원자료에는 미포착)",
    "아원고택": "시설 안내자료에서 예약 가능 7객실 확인(인허가 원자료에는 미포착)",
    "쉴(SHIL)랜드": "시설 안내자료 52개 숙박 단위 확인(인허가 원자료에는 한실 15실)",
    "완도 해양치유센터": "시설 자체 숙박업 인허가 행 없음",
}

# 인허가 원자료에서 포착되지 않는 시설 자체 객실을 시설 안내자료로 보완한다.
# 객실 수는 판매 가능한 예약 단위 기준이며, 내부의 물리적 침실 수와 다르다.
MANUAL_OWN_SUPPLY = {
    "태권도원 상징지구": {
        "숙박시설수": 1, "예약가능객실수": 265, "최대수용인원": 1031,
        "객실유형": "도약관 A~D동(침대·한실, 7·12·13·15평형)",
        "출처": "태권도원 공식 공간구성 자료(최종수정 2022-02-18)",
        "수용인원설명": "최대 1,031명",
    },
    "아원고택": {
        "숙박시설수": 1, "예약가능객실수": 7, "최대수용인원": 26,
        "객실유형": "한옥 스테이(천지인 안방·건너방, 안채, 사랑채, 별채 A·B, 서당)",
        "출처": "시설 객실 안내자료",
        "수용인원설명": "최대 26명",
    },
    "쉴(SHIL)랜드": {
        "숙박시설수": 1, "예약가능객실수": 52, "최대수용인원": np.nan,
        "객실유형": "쉴하우스 37실 + 황토·편백 방갈로 15동",
        "출처": "시설 숙박 안내자료",
        "수용인원설명": "방갈로 기준 68명 + 쉴하우스 수용인원 미확인",
    },
}

AWON_ROOMS = [
    {"객실명": "천지인(안방)", "구성": "방1, 욕실1, 노천탕", "기준인원": 2, "최대인원": 4,
     "평일_만원": 28, "주말_만원": 31, "성수기_만원": 34, "숙박가능": True},
    {"객실명": "천지인(건너방)", "구성": "방1, 욕실1, 노천탕", "기준인원": 2, "최대인원": 2,
     "평일_만원": 25, "주말_만원": 28, "성수기_만원": 31, "숙박가능": True},
    {"객실명": "천지인(다도방)", "구성": "다실", "기준인원": np.nan, "최대인원": np.nan,
     "평일_만원": 20, "주말_만원": 20, "성수기_만원": 20, "숙박가능": False},
    {"객실명": "안채", "구성": "방2, 욕실1, 노천탕", "기준인원": 2, "최대인원": 3,
     "평일_만원": 43, "주말_만원": 46, "성수기_만원": 49, "숙박가능": True},
    {"객실명": "사랑채", "구성": "방2, 욕실1, 누각마루", "기준인원": 2, "최대인원": 4,
     "평일_만원": 47, "주말_만원": 50, "성수기_만원": 53, "숙박가능": True},
    {"객실명": "별채(A)", "구성": "방1, 다실1, 욕실1, 노천탕", "기준인원": 2, "최대인원": 4,
     "평일_만원": 47, "주말_만원": 52, "성수기_만원": 57, "숙박가능": True},
    {"객실명": "별채(B)", "구성": "방1, 다실1, 욕실1, 노천탕", "기준인원": 2, "최대인원": 4,
     "평일_만원": 40, "주말_만원": 45, "성수기_만원": 50, "숙박가능": True},
    {"객실명": "서당", "구성": "방4, 욕실2, 히노끼탕, 노천탕", "기준인원": 2, "최대인원": 5,
     "평일_만원": 80, "주말_만원": 90, "성수기_만원": 100, "숙박가능": True},
]

SUNCHANG_ROOMS = [
    {"숙박구분": "쉴하우스(숙소동)", "예약단위수": 37, "단위": "객실",
     "기준인원_명": np.nan, "확인수용인원_명": np.nan,
     "구성": "1인실 위주의 침대방", "비고": "전체 수용인원 미확인"},
    {"숙박구분": "황토·편백 방갈로 A타입", "예약단위수": 11, "단위": "동",
     "기준인원_명": 4, "확인수용인원_명": 44,
     "구성": "독채", "비고": "4인 기준"},
    {"숙박구분": "황토·편백 방갈로 B타입", "예약단위수": 4, "단위": "동",
     "기준인원_명": 6, "확인수용인원_명": 24,
     "구성": "독채", "비고": "6인 기준"},
]


def active_on(lodging: pd.DataFrame, date: pd.Timestamp) -> pd.Series:
    return (lodging["인허가일자"] <= date) & (
        lodging["폐업일자"].isna() | (lodging["폐업일자"] > date)
    )


def period_months(year: int) -> dict[str, pd.DatetimeIndex]:
    return {
        "P1": pd.date_range(f"{year-2}-04-30", f"{year-1}-03-31", freq="ME"),
        "P2": pd.date_range(f"{year-1}-04-30", f"{year}-03-31", freq="ME"),
        "P3": pd.date_range(f"{year}-04-30", f"{year+1}-03-31", freq="ME"),
        "P4": pd.date_range(f"{year+1}-04-30", f"{year+2}-03-31", freq="ME"),
    }


def main() -> None:
    facilities = load_facilities()
    lodging = load_lodging()
    current_rows: list[dict] = []
    inventory_rows: list[dict] = []
    period_rows: list[dict] = []
    change_rows: list[dict] = []
    sensitivity_rows: list[dict] = []
    to_metric = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)

    for facility_name, meta in SITES.items():
        facility = facilities.loc[facilities["시설명"].eq(facility_name)].iloc[0]
        if "기준경도" in meta:
            facility_x, facility_y = to_metric.transform(meta["기준경도"], meta["기준위도"])
        else:
            facility_x, facility_y = facility["x5179"], facility["y5179"]
        distance_km = np.hypot(
            lodging["x5179"] - facility_x,
            lodging["y5179"] - facility_y,
        ) / 1000
        is_self = lodging["사업장명"].isin(SELF_BUSINESSES.get(facility_name, set()))
        current = active_on(lodging, CURRENT_DATE)

        nearby = lodging.loc[current & distance_km.le(5)].copy()
        nearby["거리_km"] = distance_km.loc[nearby.index]
        nearby["시설자체여부"] = np.where(is_self.loc[nearby.index], "시설 자체", "주변 외부")
        nearby["거리구간"] = pd.cut(
            nearby["거리_km"], bins=[-np.inf, 1, 2, 5],
            labels=["1km 이내", "1~2km", "2~5km"], include_lowest=True,
        ).astype(str)
        for _, row in nearby.sort_values("거리_km").iterrows():
            inventory_rows.append({
                "관광지": meta["표시명"], "시설명": facility_name,
                "시설자체여부": row["시설자체여부"], "거리구간": row["거리구간"],
                "거리_km": round(float(row["거리_km"]), 3),
                "사업장명": row["사업장명"], "업태구분명": row["업태구분명"],
                "양실수": float(row["양실수"] if pd.notna(row["양실수"]) else 0),
                "한실수": float(row["한실수"] if pd.notna(row["한실수"]) else 0),
                "총객실수": float(row["rooms"]), "인허가일자": row["인허가일자"].date(),
                "도로명주소": str(row["도로명주소"]).replace(
                    "전남광주통합특별시 완도군", "전라남도 완도군"
                ),
            })

        for radius in RADII_KM:
            within = current & distance_km.le(radius)
            own = within & is_self
            external = within & ~is_self
            external_types = lodging.loc[external].groupby("업태구분명")["rooms"].agg(["size", "sum"])
            type_text = ", ".join(
                f"{kind} {int(row['size'])}곳·{int(row['sum'])}실"
                for kind, row in external_types.iterrows()
            ) or "없음"
            manual_own = MANUAL_OWN_SUPPLY.get(facility_name)
            own_facilities = manual_own["숙박시설수"] if manual_own else int(own.sum())
            own_rooms = manual_own["예약가능객실수"] if manual_own else int(lodging.loc[own, "rooms"].sum())
            current_rows.append({
                "관광지": meta["표시명"], "기준일": CURRENT_DATE.date(), "반경_km": radius,
                "시설자체_숙박시설수": own_facilities,
                "시설자체_예약가능객실수": own_rooms,
                "시설자체_최대수용인원": manual_own["최대수용인원"] if manual_own else np.nan,
                "시설자체_수용인원설명": manual_own["수용인원설명"] if manual_own else "확인 안 됨",
                "시설자체_객실유형": manual_own["객실유형"] if manual_own else (
                    "한실" if facility_name == "쉴(SHIL)랜드" else "확인 안 됨"
                ),
                "시설자체_출처": manual_own["출처"] if manual_own else "숙박업 인허가 원자료",
                "시설자체_원자료상태": SELF_SOURCE_STATUS[facility_name],
                "주변외부_업체수": int(external.sum()),
                "주변외부_양실수": int(lodging.loc[external, "양실수"].fillna(0).sum()),
                "주변외부_한실수": int(lodging.loc[external, "한실수"].fillna(0).sum()),
                "주변외부_총객실수": int(lodging.loc[external, "rooms"].sum()),
                "주변외부_업태별": type_text,
                "시설좌표_신뢰도": (
                    "부지경계 미확보" if "부지면적_평" in meta else facility["match_confidence"]
                ),
            })

        if "부지면적_평" in meta:
            area_m2 = meta["부지면적_평"] * 3.305785
            equivalent_radius_km = np.sqrt(area_m2 / np.pi) / 1000
            strict = current & distance_km.le(5) & ~is_self
            sensitive = current & distance_km.le(5 + equivalent_radius_km) & ~is_self
            outside = lodging.loc[current & ~is_self & distance_km.gt(5)].copy()
            outside["거리_km"] = distance_km.loc[outside.index]
            nearest_outside = outside.sort_values("거리_km").iloc[0]
            sensitivity_rows.append({
                "관광지": meta["표시명"], "부지면적_평": meta["부지면적_평"],
                "부지면적_m2": round(area_m2),
                "동일면적_원형환산반지름_km": round(equivalent_radius_km, 3),
                "기준점_경도": meta["기준경도"], "기준점_위도": meta["기준위도"],
                "기준점_출처": meta["기준점출처"],
                "대표점5km_외부업체수": int(strict.sum()),
                "대표점5km_외부객실수": int(lodging.loc[strict, "rooms"].sum()),
                "면적민감도반경_km": round(5 + equivalent_radius_km, 3),
                "면적민감도_외부업체수": int(sensitive.sum()),
                "면적민감도_외부객실수": int(lodging.loc[sensitive, "rooms"].sum()),
                "5km밖_최근접업체": nearest_outside["사업장명"],
                "5km밖_최근접거리_km": round(float(nearest_outside["거리_km"]), 3),
                "5km밖_최근접객실수": int(nearest_outside["rooms"]),
                "판정": "안정" if int(strict.sum()) == int(sensitive.sum()) else "부지경계에 따라 달라질 수 있음",
            })

        for period, months in period_months(meta["지정연도"]).items():
            observed = months[months <= CURRENT_DATE]
            for radius in RADII_KM:
                external_mask = distance_km.le(radius) & ~is_self
                counts, rooms, western, korean = [], [], [], []
                for month in observed:
                    active = active_on(lodging, month)
                    mask = active & external_mask
                    counts.append(int(mask.sum()))
                    rooms.append(float(lodging.loc[mask, "rooms"].sum()))
                    western.append(float(lodging.loc[mask, "양실수"].fillna(0).sum()))
                    korean.append(float(lodging.loc[mask, "한실수"].fillna(0).sum()))
                period_rows.append({
                    "관광지": meta["표시명"], "지정연도": meta["지정연도"],
                    "기간": period, "반경_km": radius,
                    "관측개월수": len(observed), "필요개월수": len(months),
                    "주변외부_평균업체수": round(float(np.mean(counts)), 1) if counts else np.nan,
                    "주변외부_평균객실수": round(float(np.mean(rooms)), 1) if rooms else np.nan,
                    "주변외부_평균양실수": round(float(np.mean(western)), 1) if western else np.nan,
                    "주변외부_평균한실수": round(float(np.mean(korean)), 1) if korean else np.nan,
                })

        start = pd.Timestamp(f"{meta['지정연도']}-03-31")
        planned_end = pd.Timestamp(f"{meta['지정연도']+2}-03-31")
        end = min(planned_end, CURRENT_DATE)
        for radius in RADII_KM:
            external = distance_km.le(radius) & ~is_self
            before = active_on(lodging, start) & external
            after = active_on(lodging, end) & external
            opened = lodging["인허가일자"].gt(start) & lodging["인허가일자"].le(end) & external
            closed = lodging["폐업일자"].gt(start) & lodging["폐업일자"].le(end) & external
            change_rows.append({
                "관광지": meta["표시명"], "반경_km": radius,
                "지정직전_기준일": start.date(), "지정2년차_관측일": end.date(),
                "완전한24개월여부": end == planned_end,
                "지정직전_주변외부_업체수": int(before.sum()),
                "지정직전_주변외부_객실수": int(lodging.loc[before, "rooms"].sum()),
                "관측종료_주변외부_업체수": int(after.sum()),
                "관측종료_주변외부_객실수": int(lodging.loc[after, "rooms"].sum()),
                "신규인허가_업체수": int(opened.sum()),
                "신규인허가_객실수": int(lodging.loc[opened, "rooms"].sum()),
                "폐업_업체수": int(closed.sum()),
                "폐업_객실수": int(lodging.loc[closed, "rooms"].sum()),
                "객실재고_순변화": int(lodging.loc[after, "rooms"].sum() - lodging.loc[before, "rooms"].sum()),
            })

    pd.DataFrame(current_rows).to_csv(
        OUT / "4개_관광지_숙박공급_현재.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(inventory_rows).to_csv(
        OUT / "4개_관광지_숙박업체_상세.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(period_rows).to_csv(
        OUT / "4개_관광지_숙박공급_P1_P4.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(change_rows).to_csv(
        OUT / "4개_관광지_숙박공급_지정전후.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(sensitivity_rows).to_csv(
        OUT / "대형부지_5km반경_민감도.csv", index=False, encoding="utf-8-sig"
    )
    own_detail = pd.DataFrame(AWON_ROOMS)
    own_detail.insert(0, "관광지", "완주 아원고택")
    own_detail["객실수포함여부"] = np.where(own_detail["숙박가능"], "포함", "제외")
    own_detail["성수기"] = "4~5월·7~8월"
    own_detail.to_csv(
        OUT / "아원고택_시설자체_객실상세.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame(SUNCHANG_ROOMS).assign(관광지="순창 쉴랜드").to_csv(
        OUT / "순창쉴랜드_시설자체_객실상세.csv", index=False, encoding="utf-8-sig"
    )
    print("네 시설 숙박 공급 파일 4종과 시설 자체 객실 상세 2종 저장 완료")


if __name__ == "__main__":
    main()
