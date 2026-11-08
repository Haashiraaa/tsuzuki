import { Columns, Page } from "@/components/layout/Page";
import { PageTitle } from "@/components/ui/Titles";

import { KnownSites } from "./KnownSites";
import styles from "./SitesPage.module.css";
import { TrySite } from "./TrySite";

export function SitesPage() {
  return (
    <Page gap={32}>
      <header className={styles.header}>
        <PageTitle>Sites</PageTitle>
        <p className={styles.intro}>
          Tsuzuki is not tied to one website. Paste any series page and it works out how that site is
          built. What it learns is saved, so the next run is quick and free.
        </p>
      </header>
      <Columns>
        <KnownSites />
        <TrySite />
      </Columns>
    </Page>
  );
}
