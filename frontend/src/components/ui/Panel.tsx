import type { HTMLAttributes } from "react";

import styles from "./Panel.module.css";

interface Props extends HTMLAttributes<HTMLElement> {
  as?: "section" | "aside" | "article" | "div";
  /** "soft" is the slightly darker card used for explanations */
  tone?: "card" | "soft";
  /** padding in px; the default suits most cards */
  padding?: number;
}

/** A rounded card. Pass `aria-labelledby` when it is a landmark (section or aside). */
export function Panel({ as: Tag = "div", tone = "card", padding = 20, className, style, ...rest }: Props) {
  const classes = [styles.panel, styles[tone], className].filter(Boolean).join(" ");
  return <Tag {...rest} className={classes} style={{ padding, ...style }} />;
}

/** A list container: rows inside separate themselves with a thin divider. */
export function PanelList({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div {...rest} className={[styles.list, className].filter(Boolean).join(" ")} />;
}
