import type { ReactNode } from "react";

import styles from "./StatusText.module.css";
import type { Tone } from "./tone";

export function StatusText({ tone, children }: { tone: Tone; children: ReactNode }) {
  return <span className={`${styles.status} ${styles[tone]}`}>{children}</span>;
}
