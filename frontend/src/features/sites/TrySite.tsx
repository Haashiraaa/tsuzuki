import { useState, type FormEvent } from "react";

import { Button } from "@/components/ui/Button";
import { Panel } from "@/components/ui/Panel";
import { Failed } from "@/components/ui/StateMessage";
import { SectionTitle } from "@/components/ui/Titles";
import { UrlField } from "@/components/ui/UrlField";

import { useSaveProfile, useTestSite } from "./queries";
import { StepList } from "./StepList";
import styles from "./TrySite.module.css";

export function TrySite() {
  const [url, setUrl] = useState("");
  const test = useTestSite();
  const save = useSaveProfile();
  const result = test.data;

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (value) test.mutate(value);
  }

  return (
    <Panel as="section" aria-labelledby="try" padding={24} className={styles.panel}>
      <SectionTitle id="try">Try a new site</SectionTitle>

      <form className={styles.form} onSubmit={submit}>
        <UrlField
          id="site-url"
          label="Series URL to test"
          placeholder="https://new-anime-site.example/series/…"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
        />
        <Button type="submit" size="m" disabled={test.isPending || url.trim() === ""}>
          {test.isPending ? "Testing…" : "Test this site"}
        </Button>
      </form>

      {test.isError ? <Failed error={test.error} /> : null}

      {result ? (
        <>
          <div className={styles.result}>
            <span className={styles.caption}>Result for {result.host}</span>
            <StepList steps={result.steps} />
          </div>
          <div className={styles.save}>
            <Button
              variant="success"
              size="m"
              disabled={save.isPending || save.isSuccess}
              onClick={() => save.mutate(url.trim())}
            >
              {save.isSuccess ? "Profile saved" : "Save as a site profile"}
            </Button>
            {result.profilePath ? (
              <span className={styles.where}>
                Saved to <span className={styles.path}>{result.profilePath}</span>
              </span>
            ) : null}
          </div>
          {save.isError ? <Failed error={save.error} /> : null}
        </>
      ) : null}
    </Panel>
  );
}
