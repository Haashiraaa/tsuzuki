import { messageOf } from "@/api/errors";

import styles from "./StateMessage.module.css";

export function Loading({ what }: { what: string }) {
  return (
    <p className={styles.message} role="status">
      Loading {what}…
    </p>
  );
}

export function Failed({ error }: { error: unknown }) {
  return (
    <p className={`${styles.message} ${styles.error}`} role="alert">
      {messageOf(error)}
    </p>
  );
}
