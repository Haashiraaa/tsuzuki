import type { ActiveDownload } from "@/api";
import { formatEta, formatProgress, formatSpeed } from "@/api/format";
import { CloseIcon, PauseIcon } from "@/components/icons";
import { IconButton } from "@/components/ui/IconButton";
import { ProgressBar } from "@/components/ui/ProgressBar";

import styles from "./ActiveDownloadCard.module.css";

interface Props {
  item: ActiveDownload;
  onPause: (id: number) => void;
  onCancel: (id: number) => void;
}

export function ActiveDownloadCard({ item, onPause, onCancel }: Props) {
  return (
    <article className={styles.card}>
      <div className={styles.top}>
        <div className={styles.names}>
          <span className={styles.name}>{item.name}</span>
          <span className={styles.method}>{item.method}</span>
        </div>
        <div className={styles.actions}>
          <IconButton aria-label={`Pause ${item.name}`} onClick={() => onPause(item.id)}>
            <PauseIcon />
          </IconButton>
          <IconButton aria-label={`Cancel ${item.name}`} onClick={() => onCancel(item.id)}>
            <CloseIcon />
          </IconButton>
        </div>
      </div>
      <ProgressBar percent={item.percent} size="m" label={item.name} />
      <div className={styles.stats}>
        <strong className={styles.percent}>{Math.round(item.percent)}%</strong>
        <span>{formatProgress(item.bytesDone, item.bytesTotal)}</span>
        <span>{formatSpeed(item.bytesPerSecond)}</span>
        <span>{formatEta(item.etaSeconds)}</span>
      </div>
    </article>
  );
}
