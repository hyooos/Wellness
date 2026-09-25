# WELL-FLOW Monitor for Vercel

Streamlit v5의 화면 구조와 진단 내용을 Next.js로 옮긴 정적 대시보드입니다. 지도,
관광지 선택, 비교 구간, 상세 탭은 브라우저에서 바로 전환됩니다.

## 로컬 실행

저장소 루트에서 웹용 데이터를 먼저 만듭니다.

```bash
python scripts/build_vercel_dashboard_data.py
cd vercel-dashboard
npm install
npm run dev
```

프로덕션 빌드는 다음 명령으로 확인합니다.

```bash
npm run build
npm run start
```

## Vercel 설정

현재 GitHub 저장소를 Vercel에 연결하고 프로젝트의 **Root Directory**를
`vercel-dashboard`로 지정합니다. Framework Preset은 Next.js 자동 감지를 그대로
사용하며 별도의 빌드 명령이나 출력 폴더를 입력할 필요가 없습니다.

대시보드가 사용하는 JSON, 전라도 경계, 관광지 사진은 `public/`에 포함되어 있어
배포 환경에서 Python이나 원본 CSV가 필요하지 않습니다.
