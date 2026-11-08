import type { ReactNode } from "react";

import styles from "./Page.module.css";

/** One screen's content: a column with even spacing between its blocks. */
export function Page({ gap = 28, children }: { gap?: number; children: ReactNode }) {
  return (
    <div className={styles.page} style={{ gap }}>
      {children}
    </div>
  );
}

/** Blocks that sit side by side when there is room, and stack when there is not. */
export function Columns({ children }: { children: ReactNode }) {
  return <div className={styles.columns}>{children}</div>;
}
