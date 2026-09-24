import type { ReactElement } from "react";

// Generic placeholder page used by every route in Task 1. Real page
// implementations replace these in Tasks 5–9.
interface PageStubProps {
  title: string;
  children?: React.ReactNode;
}

export function PageStub({ title, children }: PageStubProps): ReactElement {
  return (
    <section>
      <h1 className="text-2xl font-semibold text-slate-900">{title}</h1>
      <p className="mt-2 text-sm text-slate-500">
        This page is a Task 1 placeholder. It will be implemented in a later
        task — see <code>frontend/TASKS.md</code>.
      </p>
      {children ? <div className="mt-6">{children}</div> : null}
    </section>
  );
}
