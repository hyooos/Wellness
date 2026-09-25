import "./globals.css";

export const metadata = {
  title: "WELL-FLOW Monitor",
  description: "웰니스 관광지 성과 진단 대시보드",
};

export default function RootLayout({ children }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
