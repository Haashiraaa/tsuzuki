import { Columns, Page } from "@/components/layout/Page";
import { Failed, Loading } from "@/components/ui/StateMessage";
import { PageTitle, SectionTitle } from "@/components/ui/Titles";

import { AddSeriesForm } from "./AddSeriesForm";
import styles from "./LibraryPage.module.css";
import { NowDownloading } from "./NowDownloading";
import { useSeriesList } from "./queries";
import { SeriesCard } from "./SeriesCard";

export function LibraryPage() {
  const list = useSeriesList();

  return (
    <Page gap={32}>
      <header className={styles.header}>
        <PageTitle>Library</PageTitle>
        <AddSeriesForm />
      </header>

      <Columns>
        <section aria-labelledby="yours" className={styles.series}>
          <SectionTitle id="yours">Your series</SectionTitle>
          {list.isPending ? <Loading what="your series" /> : null}
          {list.isError ? <Failed error={list.error} /> : null}
          {list.data?.length === 0 ? (
            <p className={styles.empty}>Nothing here yet. Paste a series page URL above to start.</p>
          ) : null}
          <div className={styles.grid}>
            {list.data?.map((series) => <SeriesCard key={series.id} series={series} />)}
          </div>
        </section>

        <NowDownloading />
      </Columns>
    </Page>
  );
}
