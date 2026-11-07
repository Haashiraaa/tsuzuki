import { useState } from "react";
import { useParams } from "react-router-dom";

import type { EpisodeOrder } from "@/api";
import { Columns, Page } from "@/components/layout/Page";
import { Failed, Loading } from "@/components/ui/StateMessage";

import { EpisodeList } from "./EpisodeList";
import { EpisodeToolbar } from "./EpisodeToolbar";
import { useQueueEpisodes, useSeriesDetail } from "./queries";
import { SelectionBar } from "./SelectionBar";
import styles from "./SeriesPage.module.css";
import { SeriesHeader } from "./SeriesHeader";
import { SourceLadder } from "./SourceLadder";
import { useSelection } from "./useSelection";

export function SeriesPage() {
  const id = Number(useParams().id);
  const [order, setOrder] = useState<EpisodeOrder>("newest");
  const [all, setAll] = useState(false);

  const detail = useSeriesDetail(id, order, all);
  const { selected, toggle, selectMissing, clear } = useSelection(detail.data?.episodes);
  const queue = useQueueEpisodes(id);

  if (Number.isNaN(id)) return <Failed error={new Error("That is not a series in your library")} />;
  if (detail.isPending) return <Loading what="the series" />;
  if (detail.isError) return <Failed error={detail.error} />;

  const { series, episodes, listed, steps } = detail.data;
  const download = () => queue.mutate([...selected], { onSuccess: clear });

  return (
    <Page>
      <SeriesHeader series={series} listed={listed} />
      <Columns>
        <section aria-labelledby="eps" className={styles.episodes}>
          <EpisodeToolbar order={order} onOrder={setOrder} onSelectMissing={selectMissing} onClear={clear} />
          <EpisodeList
            episodes={episodes}
            listed={listed}
            selected={selected}
            onToggle={toggle}
            showingAll={all}
            onShowAll={setAll}
          />
          <SelectionBar
            count={selected.size}
            busy={queue.isPending}
            onDownload={download}
            queuedCount={queue.isSuccess ? (queue.variables?.length ?? null) : null}
          />
          {queue.isError ? <Failed error={queue.error} /> : null}
        </section>
        <SourceLadder steps={steps} />
      </Columns>
    </Page>
  );
}
