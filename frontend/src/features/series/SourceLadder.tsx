import type { Step } from "@/api";
import { CheckCircleIcon, MinusCircleIcon } from "@/components/icons";
import { Panel } from "@/components/ui/Panel";
import { SectionTitle } from "@/components/ui/Titles";

import styles from "./SourceLadder.module.css";

function Rung({ step }: { step: Step }) {
  const worked = step.outcome === "worked";
  return (
    <li className={`${styles.rung} ${worked ? "" : styles.dim}`}>
      <span className={worked ? styles.ok : undefined}>{worked ? <CheckCircleIcon /> : <MinusCircleIcon />}</span>
      <span className={styles.text}>
        <strong className={styles.title}>{step.title}</strong>
        <br />
        <span className={worked ? styles.ok : undefined}>{step.summary}</span>
        {step.detail ? ` · ${step.detail}` : null}
      </span>
    </li>
  );
}

/** Shows which way of reading the site worked for this series, in the order they are tried. */
export function SourceLadder({ steps }: { steps: readonly Step[] }) {
  return (
    <Panel as="aside" aria-labelledby="how" className={styles.aside}>
      <SectionTitle id="how" size="s">
        How this site is read
      </SectionTitle>
      <p className={styles.intro}>Tsuzuki tries each step in order and stops at the first that works.</p>
      <ol className={styles.list}>
        {steps.map((step) => (
          <Rung key={step.title} step={step} />
        ))}
      </ol>
    </Panel>
  );
}
