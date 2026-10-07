import type { ReactElement } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { Layout } from "./components/Layout";
import { TccConfigPage } from "./pages/TccConfigPage";

// TCC Config is a single workspace; the selected project and any open
// dialog live in the query string so links stay shareable.
const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      { index: true, element: <TccConfigPage /> },
      { path: "*", element: <TccConfigPage /> },
    ],
  },
]);

export function App(): ReactElement {
  return <RouterProvider router={router} />;
}