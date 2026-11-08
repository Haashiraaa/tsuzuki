import type { SeriesSummary } from "@/api";
import type { Tone } from "@/components/ui/tone";

export interface SeriesLook {
  /** the short status shown on the card */
  text: string;
  tone: Tone;
  /** colour of the progress bar */
  bar: "accent" | "ok" | "warn";
  /** what the card's button says */
  action: string;
  percent: number;
}

/** How a series card should look and read, decided from its counts alone. */
export function lookOf(series: SeriesSummary): SeriesLook {
  const percent = series.total > 0 ? (series.downloaded / series.total) * 100 : 0;
  const missing = series.total - series.downloaded;

  if (series.failed > 0) {
    return { text: `${series.failed} failed`, tone: "warn", bar: "warn", action: "Review failure", percent };
  }
  if (series.inProgress > 0) {
    return { text: `${series.inProgress} in progress`, tone: "accent", bar: "accent", action: "Pick episodes", percent };
  }
  if (series.total > 0 && missing <= 0) {
    return { text: "Up to date", tone: "ok", bar: "ok", action: "Check for new episodes", percent };
  }
  const text = series.downloaded === 0 ? "Not started" : `${missing} missing`;
  return { text, tone: "muted", bar: "accent", action: "Pick episodes", percent };
}
