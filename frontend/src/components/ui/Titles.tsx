import type { HTMLAttributes } from "react";

import styles from "./Titles.module.css";

interface PageProps extends HTMLAttributes<HTMLHeadingElement> {
  /** "l" is 36px (screen titles); "m" is 34px (a series' own name) */
  size?: "l" | "m";
}

export function PageTitle({ size = "l", className, ...rest }: PageProps) {
  return <h1 {...rest} className={[styles.page, styles[`page-${size}`], className].filter(Boolean).join(" ")} />;
}

interface SectionProps extends HTMLAttributes<HTMLHeadingElement> {
  /** "m" is the 20px section heading, "s" the 18px one inside side panels */
  size?: "m" | "s";
}

export function SectionTitle({ size = "m", className, ...rest }: SectionProps) {
  return <h2 {...rest} className={[styles.section, styles[size], className].filter(Boolean).join(" ")} />;
}
