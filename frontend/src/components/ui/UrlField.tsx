import type { InputHTMLAttributes } from "react";

import styles from "./UrlField.module.css";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "size" | "id" | "type"> {
  id: string;
  /** Read by screen readers; the placeholder alone is not a label. */
  label: string;
  /** "l" is the tall field on the library screen, "m" the one inside cards */
  size?: "l" | "m";
  /** the card colour the field sits on */
  surface?: "panel" | "page";
}

export function UrlField({ id, label, size = "m", surface = "page", className, ...rest }: Props) {
  const classes = [styles.field, styles[size], styles[surface], className].filter(Boolean).join(" ");
  return (
    <>
      <label htmlFor={id} className="visually-hidden">
        {label}
      </label>
      <input {...rest} id={id} type="url" className={classes} />
    </>
  );
}
