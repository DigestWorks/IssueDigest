import { useEffect, useState } from 'react';

type Theme = 'light' | 'dark';
// This self-contained initializer also runs in <head>, before styles and hydration.
export function initializeTheme(): Theme {
  if (typeof document === 'undefined' || typeof window === 'undefined') return 'light';
  let preference: string | null = null;
  try { preference = window.localStorage.getItem('issuedigest.theme.v1'); } catch { /* Device preference may be unavailable. */ }
  let dark = false;
  try { dark = window.matchMedia('(prefers-color-scheme: dark)').matches; } catch { /* Older browsers use light. */ }
  const theme = preference === 'light' || preference === 'dark' ? preference : dark ? 'dark' : 'light';
  document.documentElement.dataset.theme = theme;
  document.documentElement.dataset.themeSource = preference === 'light' || preference === 'dark' ? 'user' : 'system';
  return theme;
}
export const themeBootstrap = `(${initializeTheme.toString()})();`;
export function ThemeToggle() {
  // Stable server/client initial markup; the head script already paints the right palette.
  const [theme, setTheme] = useState<Theme>('light');
  useEffect(() => {
    const current = document.documentElement.dataset.theme;
    setTheme(current === 'dark' || current === 'light' ? current : initializeTheme());
    let media: MediaQueryList | undefined;
    try { media = window.matchMedia('(prefers-color-scheme: dark)'); } catch { /* Static light remains usable. */ }
    const followSystem = (event: MediaQueryListEvent) => {
      if (document.documentElement.dataset.themeSource === 'user') return;
      const next = event.matches ? 'dark' : 'light';
      document.documentElement.dataset.theme = next; setTheme(next);
    };
    media?.addEventListener?.('change', followSystem);
    return () => media?.removeEventListener?.('change', followSystem);
  }, []);
  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.dataset.theme = next;
    document.documentElement.dataset.themeSource = 'user';
    try { window.localStorage.setItem('issuedigest.theme.v1', next); } catch { /* Still applies for this page/session. */ }
    setTheme(next);
  }
  const label = `현재 ${theme === 'dark' ? '어두운' : '밝은'} 테마 · ${theme === 'dark' ? '밝게' : '어둡게'} 전환`;
  return <button type="button" className="theme-toggle" onClick={toggle} aria-label={label} title={label}>
    <svg aria-hidden="true" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {theme === 'dark' ? <><circle cx="12" cy="12" r="4" /><path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.9 4.9l1.4 1.4m11.4 11.4 1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></> : <path d="M20.5 14.3A9 9 0 0 1 9.7 3.5a9 9 0 1 0 10.8 10.8Z" />}
    </svg>
  </button>;
}
