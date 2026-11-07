import { createBrowserRouter } from "react-router-dom";

import { AppShell } from "@/components/layout/AppShell";
import { LibraryPage } from "@/features/library/LibraryPage";
import { QueuePage } from "@/features/queue/QueuePage";
import { SeriesPage } from "@/features/series/SeriesPage";
import { SettingsPage } from "@/features/settings/SettingsPage";
import { SitesPage } from "@/features/sites/SitesPage";

export const router = createBrowserRouter([
  {
    element: <AppShell />,
    children: [
      { path: "/", element: <LibraryPage /> },
      { path: "/series/:id", element: <SeriesPage /> },
      { path: "/queue", element: <QueuePage /> },
      { path: "/sites", element: <SitesPage /> },
      { path: "/settings", element: <SettingsPage /> },
    ],
  },
]);
