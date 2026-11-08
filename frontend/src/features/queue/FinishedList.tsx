import { api } from "@/api";
import type { FinishedItem } from "@/api";
import { DownloadIcon } from "@/components/icons";
import { buttonClass } from "@/components/ui/Button";
import { PanelList } from "@/components/ui/Panel";

import styles from "./QueueRows.module.css";

export function FinishedList({ items }: { items: readonly FinishedItem[] }) {
  if (items.length === 0) return <p className={styles.empty}>Nothing has finished yet.</p>;
  return (
    <PanelList>
      {items.map((item) => (
        <div key={item.id} className={styles.row}>
          <div className={styles.text}>
            <span className={styles.name}>{item.name}</span>
            <span className={styles.saved}>Saved on the server</span>
          </div>
          <a href={api.streamUrl(item.id)} className={buttonClass({ variant: "secondary" })}>
            Play
          </a>
          <a href={api.fileUrl(item.id)} download className={buttonClass({ variant: "outline" })}>
            <DownloadIcon size={16} />
            Save to this device
          </a>
        </div>
      ))}
    </PanelList>
  );
}
