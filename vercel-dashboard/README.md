# WELL-FLOW Dashboard

WELL-FLOW 분석 결과를 보여주는 Next.js 정적 대시보드입니다. 전라도 지도에서 네
관광지를 선택하고 탐색·방문·숙박·체류·소비의 변화, 지정 시점 분석, 숙박 공급과
데이터 신뢰도를 확인할 수 있습니다.

**배포 주소:** [well-flow-dashboard.vercel.app](https://well-flow-dashboard.vercel.app/)

## 로컬 실행

저장소 루트에서 대시보드용 JSON을 만든 뒤 앱을 실행합니다.

```bash
python scripts/build_vercel_dashboard_data.py
cd vercel-dashboard
npm ci
npm run dev
```

프로덕션 빌드는 다음 명령으로 확인합니다.

```bash
npm run build
npm run start
```

## 데이터 갱신

`scripts/build_vercel_dashboard_data.py`는 핵심 CSV와 숙박 공급 자료를 읽어
`public/data/dashboard.json`을 생성합니다. 지도 경계와 관광지 사진도 `public/`에
포함하므로 배포 환경에서는 Python이나 원본 CSV를 읽지 않습니다.

분석 결과가 바뀌면 JSON을 다시 생성하고 빌드를 확인한 뒤 변경 파일을 커밋합니다.

## Vercel 설정

GitHub 저장소를 Vercel에 연결하고 프로젝트의 **Root Directory**를
`vercel-dashboard`로 지정합니다. Framework Preset은 Next.js 자동 감지를 사용하며
별도 출력 폴더를 설정하지 않습니다.

대시보드 수치는 시설 자체 성과가 아니라 시설 소재 시군구의 관광 흐름입니다. 다섯
성과 축은 전환 단계가 아닌 독립 관측 지표이며, 화면의 정책 방향은 진단 규칙에 따른
후속 확인 순서입니다.
