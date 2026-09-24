# visitkoreadatalab

2026 한국관광 데이터랩 활용 경진대회 프로젝트입니다. 추천 웰니스 관광지로 선정된
시군구가 관심을 실제 방문, 숙박, 체류, 관광소비로 이어가는지 분석합니다.

## WELL-FLOW 대시보드

장성을 제외한 4개 지역의 선정 전후 흐름을 한눈에 보고, 관심·방문·숙박·체류·소비 단계를 눌러
세부 변화를 확인할 수 있습니다.

```bash
streamlit run v1.dashboard.py
```

기존 9패널 구조의 가독성을 높인 클린 모니터 버전:

```bash
streamlit run v2.dashboard_monitor_clean.py
```

지도에서 지역을 선택하고 9개 진단 패널과 패널별 상세 그래프·표를 보는 권장 버전:

```bash
streamlit run v3.dashboard_monitor_map.py
```

대시보드는 `output/five_sites_by_designation/`의 CSV 산출물을 읽습니다.

## 2024년 선정 3개소 Tier 1 분석

분석 대상은 완도 해양치유센터, 순창 쉴랜드, 완주 아원고택입니다.

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python scripts/analyze_2024_three_sites.py
```

- 방법론 및 결과: `2024_웰니스관광지_3개소_Tier1_분석결과.md`
- 계산 가이드: `2024_웰니스관광지_3개소_지표계산_가이드.md`
- 재현 결과: `output/2024_three_sites/`

## 데이터 주의사항

한국관광 데이터랩에서 내려받은 원본 ZIP과 로컬 환경 파일은 저장소에 포함하지
않습니다. 분석을 재실행하려면 원본 ZIP을 다음 구조로 배치해야 합니다.

```text
data/
├── 이동통신/{전남완도,전북순창,전북완주}/
├── 신용카드/{전남완도,전북순창,전북완주}/
└── 숙박체류시간/{전남완도,전북순창,전북완주}/
```

결과는 시설 자체의 인과효과가 아니라 시설 소재 시군구의 지정 전후 변화이며,
세부 한계와 추가 필요 데이터는 분석 결과 문서를 참고하세요.
