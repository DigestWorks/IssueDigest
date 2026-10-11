import type { ReactNode } from 'react';
import { Links, Meta, Outlet, Scripts, ScrollRestoration } from 'react-router';
import './styles.css';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.svg" type="image/svg+xml" />
        <title>IssueDigest · 이슈 조사와 근거 비교</title>
        <meta name="description" content="자료를 함께 읽고 이슈의 근거를 비교하는 작업 공간" />
        <Meta />
        <Links />
      </head>
      <body>{children}<ScrollRestoration /><Scripts /></body>
    </html>
  );
}

export function HydrateFallback() {
  return <p className="loading-shell" role="status">IssueDigest 작업 공간을 준비하고 있습니다.</p>;
}

export default function App() {
  return <Outlet />;
}
