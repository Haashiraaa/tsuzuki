import type { EpisodeOrder } from "@/api";
import { Button } from "@/components/ui/Button";
import { SectionTitle } from "@/components/ui/Titles";

import styles from "./EpisodeToolbar.module.css";

interface Props {
  order: EpisodeOrder;
  onOrder: (order: EpisodeOrder) => void;
  onSelectMissing: () => void;
  onClear: () => void;
}

export function EpisodeToolbar({ order, onOrder, onSelectMissing, onClear }: Props) {
  return (
    <div className={styles.toolbar}>
      <SectionTitle id="eps">Episodes</SectionTitle>
      <div className={styles.buttons}>
        <Button variant="outline" aria-pressed={order === "newest"} onClick={() => onOrder("newest")}>
          Newest first
        </Button>
        <Button variant="outline" aria-pressed={order === "oldest"} onClick={() => onOrder("oldest")}>
          Oldest first
        </Button>
        <Button variant="outline" onClick={onSelectMissing}>
          Select all missing
        </Button>
        <Button variant="outline" onClick={onClear}>
          Clear
        </Button>
      </div>
    </div>
  );
}
