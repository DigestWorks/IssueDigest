import type { ReactNode } from 'react';
import { Links, Meta, Outlet, Scripts, ScrollRestoration } from 'react-router';
import { ResearchDraftProvider } from './research-drafts';
import { themeBootstrap } from './theme';
import './styles.css';

export function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <script dangerouslySetInnerHTML={{ __html: themeBootstrap }} />
        <link rel="icon" href="/brand/issuedigest-mark-v1.png" type="image/png" />
        <title>IssueDigest · 질문에서 시작하는 이슈 브리핑</title>
        <meta name="description" content="궁금한 이슈를 질문하고 원자료와 근거를 살펴보세요." />
        <Meta />
        <Links />
      </head>
      <body>{children}<ScrollRestoration /><Scripts /></body>
    </html>
  );
}

export function HydrateFallback() {
  return <p className="loading-shell" role="status">IssueDigest를 준비하고 있습니다.</p>;
}

export default function App() {
  return <ResearchDraftProvider><Outlet /></ResearchDraftProvider>;
}
