import { useCallback, useEffect, useRef, useState } from "react";

import type { Episode } from "@/api";

import { missingIds, newestMissing } from "./selection";

/** How many of the newest missing episodes are ticked when the screen first opens. */
const DEFAULT_PICK = 3;

/** Which episodes are ticked. Starts with the newest few missing ones, once they have loaded. */
export function useSelection(episodes: readonly Episode[] | undefined) {
  const [selected, setSelected] = useState<ReadonlySet<number>>(new Set());
  const seeded = useRef(false);

  useEffect(() => {
    if (!episodes || seeded.current) return;
    seeded.current = true;
    setSelected(new Set(newestMissing(episodes, DEFAULT_PICK)));
  }, [episodes]);

  const toggle = useCallback((id: number) => {
    setSelected((current) => {
      const next = new Set(current);
      if (!next.delete(id)) next.add(id);
      return next;
    });
  }, []);

  const selectMissing = useCallback(() => {
    setSelected(new Set(missingIds(episodes ?? [])));
  }, [episodes]);

  const clear = useCallback(() => setSelected(new Set()), []);

  return { selected, toggle, selectMissing, clear };
}
