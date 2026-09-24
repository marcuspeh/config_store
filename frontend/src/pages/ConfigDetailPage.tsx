import type { ReactElement } from "react";
import { useParams } from "react-router-dom";
import { PageStub } from "../components/PageStub";

// §6.3 Config Detail Page — implemented in Task 7.
export function ConfigDetailPage(): ReactElement {
  const { project, key } = useParams<{ project: string; key: string }>();
  return <PageStub title={`${project ?? ""} / ${key ?? ""}`} />;
}
