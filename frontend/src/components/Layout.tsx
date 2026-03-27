import type { ReactNode } from "react";

interface Props {
  sidebar: ReactNode;
  main: ReactNode;
  noScroll?: boolean;
}

export function Layout({ sidebar, main, noScroll }: Props) {
  return (
    <div className="app-layout">
      <header className="app-header">
        <div className="app-header__logo">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#06b6d4" strokeWidth="1.8">
            <circle cx="12" cy="12" r="3" />
            <path d="M12 1v4M12 19v4M4.22 4.22l2.83 2.83M16.95 16.95l2.83 2.83M1 12h4M19 12h4M4.22 19.78l2.83-2.83M16.95 7.05l2.83-2.83" />
          </svg>
          <span className="app-header__title">BloodShot</span>
        </div>
        <div className="app-header__meta">
        </div>
      </header>

      <div className="app-body">
        <aside className="app-sidebar">{sidebar}</aside>
        <main className={`app-main${noScroll ? " app-main--no-scroll" : ""}`}>{main}</main>
      </div>
    </div>
  );
}
