import { Link } from "react-router-dom";

import type { SeriesSummary } from "@/api";
import { plural } from "@/api/format";
import { buttonClass } from "@/components/ui/Button";
import { Poster } from "@/components/ui/Poster";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatusText } from "@/components/ui/StatusText";

import styles from "./SeriesCard.module.css";
import { lookOf } from "./seriesStatus";

export function SeriesCard({ series }: { series: SeriesSummary }) {
  const look = lookOf(series);
  const to = `/series/${series.id}`;
  return (
    <article className={styles.card}>
      <Poster title={series.title} />
      <h3 className={styles.title}>
        <Link to={to}>{series.title}</Link>
      </h3>
      <div className={styles.progress}>
        <ProgressBar percent={look.percent} tone={look.bar} label={`${series.title} downloaded`} />
        <div className={styles.facts}>
          <span>
            {series.downloaded} of {plural(series.total, "episode")}
          </span>
          <StatusText tone={look.tone}>{look.text}</StatusText>
        </div>
      </div>
      <Link to={to} className={buttonClass({ variant: "secondary", block: true })}>
        {look.action}
      </Link>
    </article>
  );
}
