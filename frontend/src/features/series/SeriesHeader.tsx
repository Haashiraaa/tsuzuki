import { Link } from "react-router-dom";

import type { SeriesSummary } from "@/api";
import { plural } from "@/api/format";
import { ChevronLeftIcon } from "@/components/icons";
import { Poster } from "@/components/ui/Poster";
import { PageTitle } from "@/components/ui/Titles";

import styles from "./SeriesHeader.module.css";

export function SeriesHeader({ series, listed }: { series: SeriesSummary; listed: number }) {
  return (
    <>
      <Link to="/" className={styles.back}>
        <ChevronLeftIcon />
        Library
      </Link>
      <header className={styles.header}>
        <Poster title={series.title} shape="square" />
        <div className={styles.text}>
          <PageTitle size="m">{series.title}</PageTitle>
          <p className={styles.facts}>
            {series.site} · {plural(listed, "episode")} on the site · {series.downloaded} downloaded
          </p>
          <span className={styles.url}>{series.url}</span>
        </div>
      </header>
    </>
  );
}
