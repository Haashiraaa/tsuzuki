import type { WaitingItem } from "@/api";
import { Button } from "@/components/ui/Button";
import { PanelList } from "@/components/ui/Panel";

import styles from "./QueueRows.module.css";

interface Props {
  items: readonly WaitingItem[];
  onRetry: (id: number) => void;
}

export function WaitingList({ items, onRetry }: Props) {
  if (items.length === 0) return <p className={styles.empty}>Nothing is waiting.</p>;
  return (
    <PanelList>
      {items.map((item) => (
        <div key={item.id} className={styles.row}>
          <div className={styles.text}>
            <span className={styles.name}>{item.name}</span>
            <span className={item.failed ? styles.warn : styles.note}>{item.note}</span>
          </div>
          {item.failed ? (
            <Button className={styles.retry} onClick={() => onRetry(item.id)}>
              Retry
            </Button>
          ) : null}
        </div>
      ))}
    </PanelList>
  );
}
