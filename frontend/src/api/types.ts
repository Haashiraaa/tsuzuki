/** The shapes the Tsuzuki server sends. They follow the storage records in `backend/.../storage`. */

export type EpisodeStatus =
  | "available"
  | "queued"
  | "downloading"
  | "ready"
  | "delivered"
  | "expired"
  | "failed";

export type EpisodeOrder = "newest" | "oldest";

export interface SeriesSummary {
  id: number;
  title: string;
  site: string;
  url: string;
  total: number;
  downloaded: number;
  /** queued + downloading */
  inProgress: number;
  failed: number;
}

export interface Episode {
  id: number;
  number: string;
  status: EpisodeStatus;
}

/** One rung of "how Tsuzuki reads a site": saved profile, generic detection, yt-dlp, AI repair. */
export interface Step {
  title: string;
  outcome: "worked" | "skipped" | "missing";
  summary: string;
  detail: string;
}

export interface SeriesDetail {
  series: SeriesSummary;
  /** The page of episodes asked for, in the order asked for. */
  episodes: Episode[];
  /** How many episodes the site lists in all (the page may be shorter). */
  listed: number;
  steps: Step[];
}

export interface ActiveDownload {
  id: number;
  name: string;
  method: string;
  percent: number;
  bytesDone: number;
  bytesTotal: number;
  bytesPerSecond: number;
  etaSeconds: number | null;
}

export interface WaitingItem {
  id: number;
  name: string;
  note: string;
  failed: boolean;
}

export interface FinishedItem {
  id: number;
  name: string;
}

export interface QueueSnapshot {
  active: ActiveDownload[];
  waiting: WaitingItem[];
  finished: FinishedItem[];
  /** How many downloads may run at once. */
  slots: number;
  /** The folder on the server where downloads are saved. */
  downloadsFolder: string;
  /** Where one finished file sits inside it, shown as an example. */
  exampleFile: string;
}

export interface SiteInfo {
  host: string;
  how: string;
  state: "working" | "needs-look";
}

export interface SiteTest {
  host: string;
  steps: Step[];
  /** Where the profile would be saved, if the test worked. */
  profilePath: string | null;
}
