import type { ReactElement } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ProjectsPage } from "./pages/ProjectsPage";
import { ProjectConfigsPage } from "./pages/ProjectConfigsPage";
import { ConfigDetailPage } from "./pages/ConfigDetailPage";
import { ConfigEditPage } from "./pages/ConfigEditPage";
import { CreateConfigPage } from "./pages/CreateConfigPage";

// Route tree matches PRD §5. Placeholder pages for now; Tasks 5–9 fill
// them in.
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <ProjectsPage /> },
      { path: "projects/new", element: <CreateConfigPage /> },
      { path: "projects/:project", element: <ProjectConfigsPage /> },
      { path: "projects/:project/new", element: <CreateConfigPage /> },
      { path: "projects/:project/:key", element: <ConfigDetailPage /> },
      { path: "projects/:project/:key/edit", element: <ConfigEditPage /> },
      // Fallback to projects list for unknown paths so deep links don't
      // 404 during scaffolding; later we can show a 404 page here.
      { path: "*", element: <ProjectsPage /> },
    ],
  },
]);

export function App(): ReactElement {
  return <RouterProvider router={router} />;
}
