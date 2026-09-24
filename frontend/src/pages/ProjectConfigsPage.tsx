import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { PageStub } from "../components/PageStub";

// §6.2 Project Config Page — implemented in Task 6.
export function ProjectConfigsPage(): ReactElement {
  const { project } = useParams<{ project: string }>();
  return <PageStub title={`Project: ${project ?? ""}`} />;
}
