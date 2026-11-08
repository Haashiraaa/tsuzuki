import type { ButtonHTMLAttributes } from "react";

import styles from "./IconButton.module.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Required: an icon alone does not say what the button does. */
  "aria-label": string;
}

export function IconButton({ className, type = "button", ...rest }: Props) {
  return <button {...rest} type={type} className={[styles.iconButton, className].filter(Boolean).join(" ")} />;
}
