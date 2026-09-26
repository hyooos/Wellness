# 이전 Streamlit 대시보드

이 폴더는 Next.js/Vercel 대시보드로 전환하기 전에 만든 Streamlit 화면의 보관본입니다.
현재 배포와 해석 기준은 프로젝트 루트의 `vercel-dashboard/`와 `README.md`를
따릅니다. 보관본에는 개발 당시의 용어와 화면 구성이 남아 있을 수 있습니다.

## 버전

| 파일 | 설명 |
|---|---|
| `v1.dashboard.py` | 초기 대시보드 |
| `v2.dashboard_monitor_clean.py` | 클린 모니터 버전 |
| `v3.dashboard_monitor_map.py` | 초기 지도 선택 버전 |
| `v4.dashboard_monitor_map.py` | 지도 모니터 개선 버전 |
| `v5.dashboard_monitor_map.py` | 마지막 Streamlit 지도 모니터 버전 |

프로젝트 루트에서 다음처럼 실행한다.

```bash
streamlit run streamlit-dashboard/v5.dashboard_monitor_map.py
```

각 앱은 루트의 `output/`, `assets/`, `웰니스관광지_사진/`과 CSV 파일을 읽습니다.
