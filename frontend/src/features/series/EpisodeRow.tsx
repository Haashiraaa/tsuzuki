import type { Episode } from "@/api";
import { StatusText } from "@/components/ui/StatusText";

import { describeStatus } from "./episodeStatus";
import styles from "./EpisodeRow.module.css";

interface Props {
  episode: Episode;
  checked: boolean;
  onToggle: (id: number) => void;
}

/** The whole row is the label, so the tap target is the full width, not just the box. */
export function EpisodeRow({ episode, checked, onToggle }: Props) {
  const status = describeStatus(episode.status);
  return (
    <label className={`${styles.row} ${checked ? styles.checked : ""}`}>
      <input
        type="checkbox"
        className={styles.box}
        checked={checked}
        onChange={() => onToggle(episode.id)}
        aria-label={`Select episode ${episode.number}`}
      />
      <span className={styles.name}>Episode {episode.number}</span>
      <StatusText tone={status.tone}>{status.text}</StatusText>
    </label>
  );
}
