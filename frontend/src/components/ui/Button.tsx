import type { ButtonHTMLAttributes } from "react";

import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "outline" | "success";
export type ButtonSize = "s" | "m" | "l";

interface Look {
  variant?: ButtonVariant;
  size?: ButtonSize;
  /** stretch to the full width of its container */
  block?: boolean;
}

/** Class names for anything that should look like a button, such as a router `<Link>`. */
export function buttonClass({ variant = "primary", size = "s", block = false }: Look = {}): string {
  return [styles.button, styles[variant], styles[size], block ? styles.block : ""]
    .filter(Boolean)
    .join(" ");
}

export function Button({
  variant,
  size,
  block,
  className,
  type = "button",
  ...rest
}: Look & ButtonHTMLAttributes<HTMLButtonElement>) {
  const classes = [buttonClass({ variant, size, block }), className].filter(Boolean).join(" ");
  return <button {...rest} type={type} className={classes} />;
}
