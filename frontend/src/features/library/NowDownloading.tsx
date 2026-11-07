import { Link } from "react-router-dom";

import { formatEta, formatSpeed } from "@/api/format";
import { Panel } from "@/components/ui/Panel";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SectionTitle } from "@/components/ui/Titles";
import { useQueue } from "@/features/queue/queries";

import styles from "./NowDownloading.module.css";

export function NowDownloading() {
  const queue = useQueue();
  const active = queue.data?.active ?? [];
  return (
    <Panel as="aside" aria-labelledby="now" className={styles.rail}>
      <SectionTitle id="now" size="s">
        Downloading now
      </SectionTitle>
      {active.length === 0 ? <p className={styles.empty}>Nothing is downloading right now.</p> : null}
      {active.map((item) => (
        <div key={item.id} className={styles.row}>
          <div className={styles.head}>
            <span className={styles.name}>{item.name}</span>
            <span className={styles.percent}>{Math.round(item.percent)}%</span>
          </div>
          <ProgressBar percent={item.percent} label={item.name} />
          <span className={styles.detail}>
            {item.method} · {formatSpeed(item.bytesPerSecond)} · {formatEta(item.etaSeconds)}
          </span>
        </div>
      ))}
      <Link to="/queue" className={styles.link}>
        Open queue
      </Link>
    </Panel>
  );
}
