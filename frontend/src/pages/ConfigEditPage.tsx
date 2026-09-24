import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { PageStub } from "../components/PageStub";

// §6.4 Edit Page — implemented in Task 8.
export function ConfigEditPage(): ReactElement {
  const { project, key } = useParams<{ project: string; key: string }>();
  return (
    <PageStub title={`Edit: ${project ?? ""} / ${key ?? ""}`}>
      <p className="text-sm text-slate-500">
        Save / Cancel + dirty guard arrive in Task 8.
      </p>
    </PageStub>
  );
}
