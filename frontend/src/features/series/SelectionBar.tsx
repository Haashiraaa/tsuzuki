import { Link } from "react-router-dom";

import { plural } from "@/api/format";
import { Button } from "@/components/ui/Button";

import styles from "./SelectionBar.module.css";

interface Props {
  count: number;
  busy: boolean;
  onDownload: () => void;
  /** set once a request has gone through, so the screen can confirm it */
  queuedCount: number | null;
}

export function SelectionBar({ count, busy, onDownload, queuedCount }: Props) {
  const summary = count === 0 ? "No episodes selected" : `${plural(count, "episode")} selected`;
  return (
    <div className={styles.bar}>
      <span className={styles.summary} aria-live="polite">
        {queuedCount !== null && count === 0 ? `${plural(queuedCount, "episode")} added to the queue` : summary}
      </span>
      <Link to="/queue" className={styles.queue}>
        View queue
      </Link>
      <Button size="m" className={styles.go} disabled={count === 0 || busy} onClick={onDownload}>
        {count === 0 ? "Download" : `Download ${count}`}
      </Button>
    </div>
  );
}
