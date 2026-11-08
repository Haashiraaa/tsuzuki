import { Page } from "@/components/layout/Page";
import { PageTitle } from "@/components/ui/Titles";

import styles from "./SettingsPage.module.css";

/** A placeholder: settings such as how long finished files stay on the server come later. */
export function SettingsPage() {
  return (
    <Page gap={16}>
      <PageTitle>Settings</PageTitle>
      <p className={styles.note}>
        Nothing to change here yet. Soon: how long finished files stay on the server, and how many
        downloads run at once.
      </p>
    </Page>
  );
}
