import { Columns, Page } from "@/components/layout/Page";
import { Failed, Loading } from "@/components/ui/StateMessage";
import { PageTitle, SectionTitle } from "@/components/ui/Titles";

import { ActiveDownloadCard } from "./ActiveDownloadCard";
import { FinishedList } from "./FinishedList";
import { useEpisodeActions, useQueue } from "./queries";
import styles from "./QueuePage.module.css";
import { WaitingList } from "./WaitingList";
import { WhereFilesGo } from "./WhereFilesGo";

export function QueuePage() {
  const queue = useQueue();
  const { retry, pause, cancel } = useEpisodeActions();

  if (queue.isPending) return <Loading what="the queue" />;
  if (queue.isError) return <Failed error={queue.error} />;

  const { active, waiting, finished, slots, exampleFile } = queue.data;
  const failed = waiting.filter((item) => item.failed).length;
  const summary = `${active.length} downloading · ${waiting.length - failed} waiting · ${failed} failed · up to ${slots} at a time`;

  return (
    <Page>
      <header className={styles.header}>
        <PageTitle>Queue</PageTitle>
        <p className={styles.summary}>{summary}</p>
      </header>

      <Columns>
        <div className={styles.main}>
          <section aria-labelledby="act" className={styles.section}>
            <SectionTitle id="act">Downloading</SectionTitle>
            {active.length === 0 ? <p className={styles.empty}>Nothing is downloading right now.</p> : null}
            {active.map((item) => (
              <ActiveDownloadCard
                key={item.id}
                item={item}
                onPause={(id) => pause.mutate(id)}
                onCancel={(id) => cancel.mutate(id)}
              />
            ))}
          </section>

          <section aria-labelledby="wait" className={styles.section}>
            <SectionTitle id="wait">Waiting and failed</SectionTitle>
            <WaitingList items={waiting} onRetry={(id) => retry.mutate(id)} />
          </section>

          <section aria-labelledby="done" className={styles.section}>
            <SectionTitle id="done">Finished</SectionTitle>
            <FinishedList items={finished} />
          </section>
        </div>

        <WhereFilesGo example={exampleFile} />
      </Columns>
    </Page>
  );
}
