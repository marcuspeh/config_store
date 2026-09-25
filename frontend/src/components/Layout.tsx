import type { ReactElement } from "react";
import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";

// Shared layout for every page. Top bar + main content. A skip-link
// sits at the very top of the DOM for keyboard users (PRD §8
// accessibility: every page must be reachable via keyboard alone).
export function Layout(): ReactElement {
  return (
    <div className="min-h-screen bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-slate-900 focus:px-3 focus:py-1.5 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>
      <TopBar />
      <main
        id="main-content"
        tabIndex={-1}
        className="mx-auto max-w-5xl px-6 py-8 focus:outline-none"
      >
        <Outlet />
      </main>
    </div>
  );
}
