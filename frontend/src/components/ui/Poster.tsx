import styles from "./Poster.module.css";

const COLOURS = ["#3b4a6b", "#6b3b4a", "#3b6b58", "#6b5a3b"] as const;

/** The same title always gets the same colour. */
export function posterColour(title: string): string {
  let sum = 0;
  for (const char of title) sum += char.codePointAt(0) ?? 0;
  return COLOURS[sum % COLOURS.length] ?? COLOURS[0];
}

interface Props {
  title: string;
  /** "banner" fills the width of a card; "square" is the 96px tile beside a heading */
  shape?: "banner" | "square";
}

/** A flat colour tile with the title's first letter, standing in for cover art. */
export function Poster({ title, shape = "banner" }: Props) {
  return (
    <div className={`${styles.poster} ${styles[shape]}`} style={{ background: posterColour(title) }} aria-hidden="true">
      {title.trim().charAt(0).toUpperCase()}
    </div>
  );
}
