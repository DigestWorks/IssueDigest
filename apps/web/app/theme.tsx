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
  return <button type="button" className="theme-toggle" onClick={toggle} aria-label={`현재 ${theme === 'dark' ? '어두운' : '밝은'} 테마 · ${theme === 'dark' ? '밝게' : '어둡게'} 전환`}><span aria-hidden="true">{theme === 'dark' ? '☀' : '☾'}</span><span>{theme === 'dark' ? '밝게' : '어둡게'}</span></button>;
}
