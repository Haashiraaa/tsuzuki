import type { Step } from "@/api";

import styles from "./StepList.module.css";

/** The numbered result of testing a site: what each way of reading it found. */
export function StepList({ steps }: { steps: readonly Step[] }) {
  return (
    <ol className={styles.list}>
      {steps.map((step, index) => {
        const worked = step.outcome === "worked";
        return (
          <li key={step.title} className={`${styles.step} ${worked ? styles.worked : ""}`}>
            <span className={styles.number} aria-hidden="true">
              {index + 1}
            </span>
            <span className={styles.text}>
              <strong className={styles.title}>{step.title}</strong>
              <span className={worked ? styles.ok : styles.muted}> · {step.summary}</span>
              <br />
              <span className={styles.detail}>{step.detail}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
}
