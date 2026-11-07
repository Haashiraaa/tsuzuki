import { PanelList } from "@/components/ui/Panel";
import { Failed, Loading } from "@/components/ui/StateMessage";
import { StatusText } from "@/components/ui/StatusText";
import { SectionTitle } from "@/components/ui/Titles";

import styles from "./KnownSites.module.css";
import { useSites } from "./queries";

export function KnownSites() {
  const sites = useSites();
  return (
    <section aria-labelledby="known" className={styles.section}>
      <SectionTitle id="known">Known sites</SectionTitle>
      {sites.isPending ? <Loading what="sites" /> : null}
      {sites.isError ? <Failed error={sites.error} /> : null}
      {sites.data ? (
        <PanelList>
          {sites.data.map((site) => (
            <div key={site.host} className={styles.row}>
              <div className={styles.text}>
                <span className={styles.host}>{site.host}</span>
                <span className={styles.how}>{site.how}</span>
              </div>
              <StatusText tone={site.state === "working" ? "ok" : "warn"}>
                {site.state === "working" ? "Working" : "Needs a look"}
              </StatusText>
            </div>
          ))}
        </PanelList>
      ) : null}
    </section>
  );
}
