"""
§7의 "제천 허위 양성" 가설 실증 — "청풍호반 리조트 등 무관한 인근
관광지에서 발생한 것으로 추정된다"는 문구를 TourAPI + 문화_숙박업.csv
좌표로 검증한다.

실행:
    venv/bin/python3 scripts/verify_jecheon_hypothesis.py

결과 요약(2026-08 실행 기준, 재현 검증용):
    - TourAPI에 "청풍호반리조트"라는 단일 명칭의 숙박시설은 등록돼
      있지 않음(대신 "청풍리조트"가 관광지(contentTypeId=12)로 등록).
    - 문화_숙박업.csv에서 국립제천치유의숲과 같은 "청풍" 권역의 영업 중
      숙박업체 12곳, 객실 합계 376실을 확인.
    - 최대 시설은 **레이크관광호텔**(관광호텔 등급, 180실) —
      국립제천치유의숲으로부터 **6.0km** 떨어져 있어, §8-5의 반경 5km
      분석 범위 밖에 위치한다. 즉 국립제천치유의숲 좌표 기준으로는
      정당하게 "반경 내 숙박 0"으로 잡히는 게 맞고, 제천시 전체
      관광소비 증가는 이 6km 밖 클러스터가 견인했을 가능성이 높다는
      §7의 가설을 정량적으로 뒷받침한다.
"""
from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import pyproj

ROOT = Path(__file__).resolve().parent.parent
API_BASE = "https://apis.data.go.kr/B551011/KorService2/searchKeyword2"


def load_api_key() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.startswith("TOUR_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("TOUR_API_KEY not found")


def search_keyword(keyword: str, api_key: str, num_rows: int = 10) -> list[dict]:
    params = {
        "serviceKey": api_key, "MobileOS": "ETC", "MobileApp": "wellness_pipeline",
        "numOfRows": num_rows, "pageNo": 1, "_type": "json", "keyword": keyword,
    }
    url = f"{API_BASE}?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    items = body.get("response", {}).get("body", {}).get("items", "")
    if items == "" or items is None:
        return []
    item = items.get("item", [])
    return [item] if isinstance(item, dict) else item


def main():
    api_key = load_api_key()

    print("=== 1) TourAPI에서 '청풍호반리조트' 계열 검색 ===")
    for kw in ["청풍호반리조트", "청풍호", "청풍호반", "청풍리조트"]:
        res = search_keyword(kw, api_key)
        print(f"'{kw}' -> {len(res)}건")
        for r in res[:5]:
            print(f"   {r.get('title')} | {r.get('addr1')} | contentTypeId={r.get('contenttypeid')}")
        time.sleep(0.15)

    print("\n=== 2) 문화_숙박업.csv에서 국립제천치유의숲과 같은 '청풍' 권역 실측 ===")
    fac = pd.read_csv(ROOT / "wellness_88_geocoded.csv")
    frow = fac[fac["시설명"] == "국립제천치유의숲"].iloc[0]
    t1 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:5179", always_xy=True)
    fx, fy = t1.transform(frow["mapx"], frow["mapy"])

    lodge = pd.read_csv(ROOT / "data" / "문화_숙박업.csv", encoding="cp949", low_memory=False)
    addr = lodge["도로명주소"].fillna("") + " " + lodge["지번주소"].fillna("")
    mask = addr.str.contains("제천") & addr.str.contains("청풍") & (lodge["영업상태명"] == "영업/정상")
    sub = lodge[mask].dropna(subset=["좌표정보(X)", "좌표정보(Y)"]).copy()
    sub["rooms"] = sub["양실수"].fillna(0) + sub["한실수"].fillna(0)

    t2 = pyproj.Transformer.from_crs("EPSG:5174", "EPSG:5179", always_xy=True)
    bx, by = t2.transform(sub["좌표정보(X)"].values, sub["좌표정보(Y)"].values)
    sub["dist_km"] = np.hypot(bx - fx, by - fy) / 1000

    sub = sub.sort_values("dist_km")
    print(sub[["사업장명", "업태구분명", "rooms", "dist_km"]].to_string(index=False))
    print(f"\n청풍 권역 영업중 업체 {len(sub)}곳, 객실 합계 {sub['rooms'].sum():.0f}실")
    top = sub.sort_values("rooms", ascending=False).iloc[0]
    print(f"최대 시설: {top['사업장명']}({top['rooms']:.0f}실, {top['업태구분명']}), "
          f"국립제천치유의숲으로부터 {top['dist_km']:.1f}km")


if __name__ == "__main__":
    main()
