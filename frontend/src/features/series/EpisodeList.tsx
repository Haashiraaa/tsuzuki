import type { Episode } from "@/api";
import { PanelList } from "@/components/ui/Panel";

import styles from "./EpisodeList.module.css";
import { EpisodeRow } from "./EpisodeRow";

interface Props {
  episodes: readonly Episode[];
  listed: number;
  selected: ReadonlySet<number>;
  onToggle: (id: number) => void;
  showingAll: boolean;
  onShowAll: (all: boolean) => void;
}

export function EpisodeList({ episodes, listed, selected, onToggle, showingAll, onShowAll }: Props) {
  const canExpand = showingAll || episodes.length < listed;
  return (
    <PanelList>
      {episodes.map((episode) => (
        <EpisodeRow key={episode.id} episode={episode} checked={selected.has(episode.id)} onToggle={onToggle} />
      ))}
      <div className={styles.footer}>
        Showing {episodes.length} of {listed}
        {canExpand ? (
          <>
            {" · "}
            <button type="button" className={styles.link} onClick={() => onShowAll(!showingAll)}>
              {showingAll ? "Show fewer" : "Show all episodes"}
            </button>
          </>
        ) : null}
      </div>
    </PanelList>
  );
}
