import type { ReactElement } from "react";
import { Outlet } from "react-router-dom";

// App shell for the TCC Config workspace. The workspace fills the
// viewport (sidebar and list scroll independently), so the main region
// is height-constrained rather than flowing with the document. A
// skip-link sits at the very top of the DOM for keyboard users.
export function Layout(): ReactElement {
  return (
    <div className="h-screen overflow-hidden bg-slate-50">
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:absolute focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-slate-900 focus:px-3 focus:py-1.5 focus:text-sm focus:font-medium focus:text-white"
      >
        Skip to main content
      </a>
      <main
        id="main-content"
        tabIndex={-1}
        className="relative h-full p-0 focus:outline-none md:p-6"
      >
        <div className="pointer-events-none absolute inset-0 hidden bg-[radial-gradient(#e2e8f0_1px,transparent_1px)] [background-size:16px_16px] opacity-50 md:block" />
        <div className="relative z-10 h-full max-w-7xl mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  );
}