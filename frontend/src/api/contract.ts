import type {
  EpisodeOrder,
  QueueSnapshot,
  SeriesDetail,
  SeriesSummary,
  SiteInfo,
  SiteTest,
} from "./types";

export interface EpisodeQuery {
  order: EpisodeOrder;
  /** false: just the first page of episodes. true: every episode. */
  all: boolean;
}

/**
 * Everything the UI asks of the server. `http.ts` implements it over `/api`, `sample.ts`
 * implements it with built-in data, and `index.ts` picks one. Screens only ever see this.
 */
export interface Api {
  listSeries(): Promise<SeriesSummary[]>;
  addSeries(url: string): Promise<SeriesSummary>;
  getSeries(id: number, query: EpisodeQuery): Promise<SeriesDetail>;
  /** Ask for these episodes to be downloaded. */
  queueEpisodes(seriesId: number, episodeIds: number[]): Promise<void>;
  getQueue(): Promise<QueueSnapshot>;
  retryEpisode(episodeId: number): Promise<void>;
  pauseEpisode(episodeId: number): Promise<void>;
  cancelEpisode(episodeId: number): Promise<void>;
  /** Link that makes the browser save a finished episode. */
  fileUrl(episodeId: number): string;
  /** Link that plays a finished episode in the browser. */
  streamUrl(episodeId: number): string;
  /** The private link that brings this library back in another browser; null before any use. */
  getRestoreLink(): Promise<string | null>;
  listSites(): Promise<SiteInfo[]>;
  testSite(url: string): Promise<SiteTest>;
  saveSiteProfile(url: string): Promise<void>;
}
