import type { Episode } from "@/api";

import { isMissing } from "./episodeStatus";

/** Episode numbers are text ("12", "12.5", "SP1"). Non-numeric ones sort last. */
function numeric(episode: Episode): number {
  const value = Number(episode.number);
  return Number.isNaN(value) ? Number.NEGATIVE_INFINITY : value;
}

export function missingIds(episodes: readonly Episode[]): number[] {
  return episodes.filter((episode) => isMissing(episode.status)).map((episode) => episode.id);
}

/** The ids of the newest `count` missing episodes: what most people want first. */
export function newestMissing(episodes: readonly Episode[], count: number): number[] {
  return episodes
    .filter((episode) => isMissing(episode.status))
    .sort((a, b) => numeric(b) - numeric(a))
    .slice(0, count)
    .map((episode) => episode.id);
}
