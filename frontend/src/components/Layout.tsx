import type { ReactElement } from "react";
import { Outlet } from "react-router-dom";
import { TopBar } from "./TopBar";

// Shared layout for every page. Top bar + content area.
export function Layout(): ReactElement {
  return (
    <div className="min-h-screen bg-slate-50">
      <TopBar />
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
