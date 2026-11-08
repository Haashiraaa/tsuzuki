import { Panel } from "@/components/ui/Panel";
import { SectionTitle } from "@/components/ui/Titles";

import styles from "./WhereFilesGo.module.css";

/** Plain-words explanation of the two steps: the server downloads, then you collect. */
export function WhereFilesGo({ example }: { example: string }) {
  return (
    <Panel as="aside" tone="soft" aria-labelledby="where" className={styles.aside}>
      <SectionTitle id="where" size="s">
        Where do the files go?
      </SectionTitle>
      <p className={styles.text}>
        Downloads happen on the computer or server running Tsuzuki, not in this browser tab. You can
        close the page and they keep going.
      </p>
      <p className={styles.text}>Finished files are saved in</p>
      <span className={styles.path}>{example}</span>
      <p className={styles.text}>
        Use <strong>Save to this device</strong> to copy a finished episode to the phone or laptop you
        are using, or <strong>Play</strong> to watch it right here. Once a copy has reached your
        device, the server deletes its own to free the space.
      </p>
    </Panel>
  );
}
