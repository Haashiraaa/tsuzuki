import type { Tone } from "./tone";
import styles from "./ProgressBar.module.css";

interface Props {
  percent: number;
  /** what is progressing, for screen readers */
  label: string;
  tone?: Extract<Tone, "accent" | "ok" | "warn">;
  /** "s" is 6px tall (cards), "m" is 8px (the queue) */
  size?: "s" | "m";
}

export function ProgressBar({ percent, label, tone = "accent", size = "s" }: Props) {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  return (
    <div
      className={`${styles.track} ${styles[size]}`}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={value}
    >
      <div className={`${styles.fill} ${styles[tone]}`} style={{ width: `${value}%` }} />
    </div>
  );
}
