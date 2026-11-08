import { useState } from "react";

import { Page } from "@/components/layout/Page";
import { Button } from "@/components/ui/Button";
import { PageTitle } from "@/components/ui/Titles";

import { useRestoreLink } from "./queries";
import styles from "./SettingsPage.module.css";

/** Your library link: opening it in any browser brings this library and queue back. */
function LibraryLink() {
  const { data: path, isPending } = useRestoreLink();
  const [copied, setCopied] = useState(false);
  const link = path ? new URL(path, window.location.origin).toString() : "";

  async function copy() {
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard blocked: the field is selectable, so it can still be copied by hand.
    }
  }

  return (
    <section className={styles.block}>
      <h2 className={styles.heading}>Your library link</h2>
      <p className={styles.note}>
        There are no accounts. This browser is remembered, and your library and queue belong to it.
        Save this link somewhere private: opening it on another phone or computer, or after
        clearing your cookies, brings everything back. Anyone who has the link can see and use your
        library, so don&apos;t share it.
      </p>
      {link ? (
        <div className={styles.row}>
          <input
            className={styles.field}
            readOnly
            value={link}
            aria-label="Your library link"
            onFocus={(event) => event.currentTarget.select()}
          />
          <Button variant="secondary" onClick={() => void copy()}>
            {copied ? "Copied" : "Copy"}
          </Button>
        </div>
      ) : (
        <p className={styles.note}>
          {isPending ? "Loading…" : "Add a series first and your link will appear here."}
        </p>
      )}
    </section>
  );
}

export function SettingsPage() {
  return (
    <Page gap={24}>
      <PageTitle>Settings</PageTitle>
      <LibraryLink />
      <p className={styles.note}>
        Soon: how long finished files stay on the server, and how many downloads run at once.
      </p>
    </Page>
  );
}
