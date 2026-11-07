import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";

import { useQueue } from "@/features/queue/queries";

import { DownloadIcon, GlobeIcon, LibraryIcon, SlidersIcon } from "../icons";
import styles from "./Sidebar.module.css";

interface ItemProps {
  to: string;
  active: boolean;
  icon: ReactNode;
  children: ReactNode;
  badge?: number;
}

function NavItem({ to, active, icon, children, badge }: ItemProps) {
  return (
    <Link to={to} className={styles.item} aria-current={active ? "page" : undefined}>
      {icon}
      {children}
      {badge ? <span className={styles.badge}>{badge}</span> : null}
    </Link>
  );
}

export function Sidebar() {
  const { pathname } = useLocation();
  const queue = useQueue();
  const running = queue.data?.active.length ?? 0;
  const inLibrary = pathname === "/" || pathname.startsWith("/series");

  return (
    <nav className={styles.sidebar} aria-label="Main">
      <Link to="/" className={styles.brand}>
        <span className={styles.mark} lang="ja">
          続き
        </span>
        <span className={styles.name}>Tsuzuki</span>
      </Link>

      <div className={styles.nav}>
        <NavItem to="/" active={inLibrary} icon={<LibraryIcon />}>
          Library
        </NavItem>
        <NavItem to="/queue" active={pathname.startsWith("/queue")} icon={<DownloadIcon />} badge={running}>
          Queue
        </NavItem>
        <NavItem to="/sites" active={pathname.startsWith("/sites")} icon={<GlobeIcon />}>
          Sites
        </NavItem>
        <NavItem to="/settings" active={pathname.startsWith("/settings")} icon={<SlidersIcon />}>
          Settings
        </NavItem>
      </div>

      {queue.data ? (
        <div className={styles.saving}>
          <span className={styles.savingLabel}>Saving to</span>
          <span className={styles.savingPath}>{queue.data.downloadsFolder}</span>
        </div>
      ) : null}
    </nav>
  );
}
