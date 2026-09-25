"""검증된 4개 지역 CSV를 Vercel 대시보드용 정적 JSON으로 변환한다."""

from __future__ import annotations

import json
import math
import shutil
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping, shape


ROOT = Path(__file__).resolve().parent.parent
ANALYSIS = ROOT / "output" / "4개_웰니스관광지_성과분석"
SUPPORT = ROOT / "output" / "대시보드_보조데이터"
PUBLIC = ROOT / "vercel-dashboard" / "public"

SITES = {
    "전북완주": {
        "region": "완주군", "site": "아원고택", "dong": "소양면", "year": 2024,
        "longitude": 127.244624, "latitude": 35.903470, "geoName": "Wanju", "image": "wanju.jpg",
        "address": "전북특별자치도 완주군 소양면 송광수만로 516-7",
        "type": "숙박전환 병목형", "headline": "사람은 계속 오는데, 자고 가지 않는다",
        "bottleneck": ["숙박"], "bottleneckLabel": "방문 → 숙박 전환", "strength": "강함",
        "evidence": "숙박자 비율이 지정 시점에 원래 흐름보다 0.74%p 한 계단 떨어졌고, 2년차에도 돌아오지 않았습니다.",
        "good": "방문은 4년 연속 증가했고, 소비·체류는 지정 이후 회복 흐름입니다.",
        "recommend": [["1박 연계 상품", "숙박 가능한 웰니스 시설과 주변 관광지를 묶은 1박 패키지"], ["저녁·야간 웰니스", "당일 방문객이 하룻밤 머물 이유 만들기"], ["숙박 공급 확인", "숙소 부족인지 머물 이유 부족인지 구분"]],
        "avoid": ["방문객 유치 홍보 확대", "방문은 이미 4년 연속 늘고 있어 핵심 병목이 아닙니다."],
        "checkMetric": "숙박자비율_pct",
        "actions": [["지금", "1박 연계 상품·야간 프로그램 예산 배정"], ["6개월 뒤", "숙박자 비율 반등 여부 확인"], ["재지정 심사", "지정 직전 수준 회복 여부 제출"]],
        "needs": [["시설 직접 이용", "예약·방문·숙박 구분 실적"], ["숙박 공급", "숙박업 개폐업·객실 수"], ["숙박 원인", "방문객 숙박지·예약·이동 동선"]],
    },
    "전북순창": {
        "region": "순창군", "site": "쉴랜드", "dong": "인계면", "year": 2024,
        "longitude": 127.131587, "latitude": 35.431547, "geoName": "Sunchang", "image": "sunchang.jpg",
        "address": "전북특별자치도 순창군 인계면 인덕로 427-128",
        "type": "입구 단절형", "headline": "찾아보긴 하는데, 오지 않는다",
        "bottleneck": ["방문", "소비"], "bottleneckLabel": "관심 → 방문·소비", "strength": "강함",
        "evidence": "검색은 5.0% 늘었지만 방문은 3.9% 줄었고, 소비는 지정 시점에 크게 내려앉았습니다.",
        "good": "외식 소비는 버텼고 쉴랜드가 있는 인계면의 소비 비중은 올랐습니다.",
        "recommend": [["거점 교통 연계", "광주·전주 등 인근 거점과 쉴랜드를 잇는 셔틀·환승"], ["예약 + 이동 결합", "검색한 사람이 바로 올 수 있게 예약과 교통을 연결"], ["장류·음식 체류 상품", "외식 소비를 체류로 연결"]],
        "avoid": ["인지도 홍보", "검색 관심은 이미 늘었습니다. 문제는 실제 발걸음입니다."],
        "checkMetric": "내국인관광소비_천원",
        "actions": [["지금", "교통 연계·예약 결합 상품 예산 배정"], ["6개월 뒤", "외지인 방문과 교통 소비 회복 확인"], ["재지정 심사", "검색·방문 출발지 차이 축소 여부 제출"]],
        "needs": [["시설 직접 이용", "검색 이후 예약·실방문 전환"], ["접근성", "거점 도시별 교통·셔틀 이용"], ["이탈 원인", "가격·후기·예약 단계 이탈"]],
    },
    "전남완도": {
        "region": "완도군", "site": "완도 해양치유센터", "dong": "신지면", "year": 2024,
        "longitude": 126.818435, "latitude": 34.328049, "geoName": "Wando", "image": "wando.jpg",
        "address": "전라남도 완도군 신지면 내정2길 52-1",
        "type": "소비전환·시설거점형", "headline": "오래 머물지만 지갑은 닫혀 있고, 소비는 시설 주변에 머문다",
        "bottleneck": ["소비"], "bottleneckLabel": "체류 → 소비", "strength": "중간",
        "evidence": "방문자 대비 소비가 2년 연속 줄었고 소비가 센터가 있는 신지면으로 모였습니다.",
        "good": "체류는 가장 길고 장기체류 비율도 다른 지역보다 높습니다.",
        "recommend": [["타 읍면 연계 체험", "센터 이용객을 다른 읍면 체험·소비로 연결"], ["장기체류 소비 연계", "지역화폐·쿠폰으로 머무는 동안 쓸 거리 만들기"], ["군 단위 순환 동선", "신지면 방문객을 군 전체로 연결"]],
        "avoid": ["체류 기간 연장", "체류는 이미 가장 깁니다. 막힌 곳은 소비입니다."],
        "checkMetric": "방문자대비관광소비_천원_proxy",
        "actions": [["지금", "타 읍면 체험·소비 프로그램 배정"], ["6개월 뒤", "방문 대비 소비와 타 읍면 비중 확인"], ["재지정 심사", "소비 회복과 군 전체 확산 제출"]],
        "needs": [["시설 직접 이용", "예약·프로그램·재방문 실적"], ["이용 전환", "군 방문객 중 센터 실제 이용 비율"], ["소비 경로", "체류 중 결제와 타 읍면 이동"]],
    },
    "전북무주": {
        "region": "무주군", "site": "태권도원 상징지구", "dong": "설천면", "year": 2022,
        "longitude": 127.762090, "latitude": 36.012521, "geoName": "Muju", "image": "muju.jpg",
        "address": "전북특별자치도 무주군 설천면 무설로 1482",
        "type": "선행 성장형", "headline": "성과는 좋지만 상승은 지정 전에 이미 시작됐다",
        "bottleneck": ["체류"], "bottleneckLabel": "체류 길이·연박 전환", "strength": "약함",
        "evidence": "관심·방문·소비는 늘었지만 지정 시점의 뚜렷한 계단 변화는 없고 체류시간은 2년차에 줄었습니다.",
        "good": "관심·방문·숙박 전환·소비가 함께 오른 유일한 지역입니다.",
        "recommend": [["연박 프로그램", "태권도원 체험과 연계한 2박 이상 프로그램"], ["장기체류 상품", "숙박객 중 3박 이상 비율 끌어올리기"]],
        "avoid": ["무주 방식의 단순 복제", "성과 일부는 지정 전 코로나 회복기 흐름입니다."],
        "checkMetric": "평균체류시간_분",
        "actions": [["지금", "유입 확대보다 연박 프로그램 설계"], ["6개월 뒤", "3박 이상 비율과 체류시간 확인"], ["확산 전", "회복기 효과를 분리해 적용 요소 선별"]],
        "needs": [["시설 직접 이용", "방문·예약·체험 인원"], ["방문 목적", "웰니스 목적 방문 여부와 만족도"], ["체류 원인", "당일·연박 목적과 이동 동선"]],
    },
}


def records(name: str) -> list[dict]:
    frame = pd.read_csv(ANALYSIS / name, encoding="utf-8-sig")
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def clean(value):
    if isinstance(value, dict):
        return {key: clean(item) for key, item in value.items()}
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def main() -> None:
    (PUBLIC / "data").mkdir(parents=True, exist_ok=True)
    (PUBLIC / "sites").mkdir(parents=True, exist_ok=True)

    poi = pd.read_csv(SUPPORT / "geo_tourism_density.csv", encoding="utf-8-sig")
    nearest = pd.read_csv(SUPPORT / "geo_nearest_lodging.csv", encoding="utf-8-sig")
    aliases = {"쉴랜드": "쉴(SHIL)랜드"}
    environment = {}
    for key, site in SITES.items():
        lookup = aliases.get(site["site"], site["site"])
        p = poi[poi["시설명"].eq(lookup)]
        n = nearest[nearest["시설명"].eq(lookup)]
        environment[key] = {
            "poi": {str(row["구분"]): int(row["totalCount"]) for _, row in p.iterrows()},
            "nearest": None if n.empty else {
                "distanceKm": float(n.iloc[0]["최근접_거리_km"]),
                "name": str(n.iloc[0]["최근접_업체명"]),
                "type": str(n.iloc[0]["최근접_업태"]),
            },
        }

    origins = pd.DataFrame(records("mobility_origin_by_period.csv"))
    origin_top = {}
    for key in SITES:
        group = origins[(origins["지역키"] == key) & (origins["기간"] == "P4")].copy()
        group["비율(%)"] = pd.to_numeric(group["비율(%)"], errors="coerce")
        origin_top[key] = json.loads(group.nlargest(5, "비율(%)").to_json(orient="records", force_ascii=False))

    payload = clean({
        "sites": SITES,
        "kpi": records("kpi_by_period.csv"),
        "growth": records("growth_bottleneck.csv"),
        "monthly": records("monthly_input.csv"),
        "periods": records("period_definitions.csv"),
        "its": records("its_designation_hac3.csv"),
        "robustness": records("its_robustness.csv"),
        "spread": records("spatial_relative_growth_available_sites.csv"),
        "origins": origin_top,
        "environment": environment,
    })
    (PUBLIC / "data" / "dashboard.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    source_images = ROOT / "웰니스관광지_사진"
    image_map = {"wanju.jpg": "완주아원고택.jpg", "sunchang.jpg": "순창쉴랜드.jpg", "wando.jpg": "완도해양치유센터.jpg", "muju.jpg": "무주태권도원.jpg"}
    for target, source in image_map.items():
        shutil.copy2(source_images / source, PUBLIC / "sites" / target)

    raw_geo = json.loads((ROOT / "assets" / "jeolla-municipalities-geo.json").read_text(encoding="utf-8"))
    raw_geo["features"] = [
        {**feature, "geometry": mapping(shape(feature["geometry"]).simplify(0.003, preserve_topology=True))}
        for feature in raw_geo["features"]
    ]
    (PUBLIC / "data" / "jeolla.geojson").write_text(
        json.dumps(raw_geo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    print(f"saved: {PUBLIC / 'data' / 'dashboard.json'}")
    print(f"saved: {PUBLIC / 'data' / 'jeolla.geojson'}")


if __name__ == "__main__":
    main()
