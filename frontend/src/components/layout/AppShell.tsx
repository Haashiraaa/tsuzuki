import { Outlet } from "react-router-dom";

import styles from "./AppShell.module.css";
import { Sidebar } from "./Sidebar";

/**
 * The frame around every screen: sidebar on the left, content on the right. On a narrow screen
 * the sidebar wraps above the content (no media query needed: it is a wrapping flex row).
 */
export function AppShell() {
  return (
    <div className={styles.shell}>
      <Sidebar />
      <main className={styles.main}>
        <Outlet />
      </main>
    </div>
  );
}
