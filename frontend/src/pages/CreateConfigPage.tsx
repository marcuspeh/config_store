import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { PageStub } from "../components/PageStub";

// §6.5 Create Config Page — implemented in Task 9.
//
// The `project` param is present on /projects/:project/new (project
// field will be prefilled+disabled). It is absent on /projects/new
// (project field editable).
export function CreateConfigPage(): ReactElement {
  const { project } = useParams<{ project?: string }>();
  const prefilled = Boolean(project);
  return (
    <PageStub title={prefilled ? `New config in ${project}` : "New config"}>
      <p className="text-sm text-slate-500">
        {prefilled
          ? "Project field will be prefilled and disabled in Task 9."
          : "Project field will be an editable combobox in Task 9."}
      </p>
    </PageStub>
  );
}
