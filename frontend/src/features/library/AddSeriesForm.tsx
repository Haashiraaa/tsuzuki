import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import { Failed } from "@/components/ui/StateMessage";
import { UrlField } from "@/components/ui/UrlField";

import styles from "./AddSeriesForm.module.css";
import { useAddSeries } from "./queries";

export function AddSeriesForm() {
  const [url, setUrl] = useState("");
  const add = useAddSeries();

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = url.trim();
    if (value) add.mutate(value, { onSuccess: () => setUrl("") });
  }

  return (
    <div className={styles.block}>
      <form className={styles.form} onSubmit={submit}>
        <UrlField
          id="series-url"
          label="Series URL"
          size="l"
          surface="panel"
          placeholder="Paste a series page URL from any anime site"
          value={url}
          onChange={(event) => setUrl(event.target.value)}
        />
        <Button type="submit" size="l" disabled={add.isPending || url.trim() === ""}>
          {add.isPending ? "Adding…" : "Add series"}
        </Button>
      </form>
      {add.isError ? <Failed error={add.error} /> : null}
      <p className={styles.hint}>
        AnimeHeaven works out of the box. For other sites Tsuzuki tries to work it out itself.{" "}
        <Link to="/sites">See how sites are handled</Link>
      </p>
    </div>
  );
}
