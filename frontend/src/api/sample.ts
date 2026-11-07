import type { Api, EpisodeQuery } from "./contract";
import type {
  ActiveDownload,
  Episode,
  EpisodeStatus,
  QueueSnapshot,
  SeriesDetail,
  SeriesSummary,
  SiteInfo,
  SiteTest,
  Step,
} from "./types";

/**
 * Built-in sample data, so the whole UI works with no server. It behaves like the real thing:
 * queued episodes start when a slot frees up, and downloads creep forward each time the queue is
 * read. Nothing here is real; it exists so screens can be built and looked at.
 */

const MB = 1_000_000;
const PAGE = 12;
const SLOTS = 3;
const PROGRESS_STEP = 3;
const DOWNLOADED: readonly EpisodeStatus[] = ["ready", "delivered", "expired"];

interface SampleSeries {
  id: number;
  title: string;
  url: string;
  total: number;
  downloaded: number;
}

interface SampleEpisode extends Episode {
  seriesId: number;
  percent: number;
}

const SERIES: SampleSeries[] = [
  { id: 1, title: "Sousou no Frieren", url: "https://animeheaven.me/anime.php?…", total: 28, downloaded: 12 },
  { id: 2, title: "Dandadan", url: "https://animeheaven.me/anime.php?…", total: 12, downloaded: 12 },
  { id: 3, title: "Kaiju No. 8", url: "https://animeheaven.me/anime.php?…", total: 12, downloaded: 9 },
  { id: 4, title: "Blue Lock", url: "https://animeheaven.me/anime.php?…", total: 24, downloaded: 0 },
];

const START_PERCENT: Record<number, number> = { 1013: 62, 1014: 18, 3010: 35 };

function initialStatus(series: SampleSeries, n: number): EpisodeStatus {
  if (n === series.total && series.downloaded === series.total) return "ready";
  if (n === 12 && series.id === 1) return "ready";
  if (n <= series.downloaded) return "delivered";
  if (series.id === 1 && (n === 13 || n === 14)) return "downloading";
  if (series.id === 1 && (n === 15 || n === 16)) return "queued";
  if (series.id === 3 && n === 10) return "downloading";
  if (series.id === 3 && n === 11) return "failed";
  return "available";
}

function buildEpisodes(series: SampleSeries): SampleEpisode[] {
  return Array.from({ length: series.total }, (_, index) => {
    const n = index + 1;
    const id = series.id * 1000 + n;
    return {
      id,
      seriesId: series.id,
      number: String(n),
      status: initialStatus(series, n),
      percent: START_PERCENT[id] ?? 0,
    };
  });
}

const catalog = [...SERIES];
const episodes: SampleEpisode[] = SERIES.flatMap(buildEpisodes);

function settle<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), 120));
}

function episodeById(id: number): SampleEpisode | undefined {
  return episodes.find((episode) => episode.id === id);
}

function titleOf(episode: SampleEpisode): string {
  return catalog.find((series) => series.id === episode.seriesId)?.title ?? "Unknown";
}

function summarize(series: SampleSeries): SeriesSummary {
  const mine = episodes.filter((episode) => episode.seriesId === series.id);
  const count = (test: (status: EpisodeStatus) => boolean) =>
    mine.filter((episode) => test(episode.status)).length;
  return {
    id: series.id,
    title: series.title,
    site: "animeheaven.me",
    url: series.url,
    total: mine.length,
    downloaded: count((status) => DOWNLOADED.includes(status)),
    inProgress: count((status) => status === "queued" || status === "downloading"),
    failed: count((status) => status === "failed"),
  };
}

const LADDER: Step[] = [
  { title: "Saved profile", outcome: "worked", summary: "Used", detail: "built-in AnimeHeaven adapter" },
  { title: "Generic detection", outcome: "skipped", summary: "Skipped", detail: "" },
  { title: "yt-dlp", outcome: "skipped", summary: "Skipped", detail: "" },
  { title: "AI repair", outcome: "skipped", summary: "Skipped", detail: "only runs when everything above fails" },
];

function page(series: SampleSeries, { order, all }: EpisodeQuery): Episode[] {
  const mine = episodes.filter((episode) => episode.seriesId === series.id);
  const sorted = order === "newest" ? [...mine].reverse() : mine;
  return (all ? sorted : sorted.slice(0, PAGE)).map(({ id, number, status }) => ({
    id,
    number,
    status,
  }));
}

/** Move the clock on: running downloads advance, finished ones free a slot for the next. */
function tick(): void {
  for (const episode of episodes) {
    if (episode.status !== "downloading") continue;
    episode.percent = Math.min(100, episode.percent + PROGRESS_STEP);
    if (episode.percent >= 100) episode.status = "ready";
  }
  const running = episodes.filter((episode) => episode.status === "downloading").length;
  const waiting = episodes.filter((episode) => episode.status === "queued");
  for (const episode of waiting.slice(0, Math.max(0, SLOTS - running))) {
    episode.status = "downloading";
    episode.percent = 0;
  }
}

function isHls(episode: SampleEpisode): boolean {
  return episode.seriesId === 3;
}

function describe(episode: SampleEpisode, index: number): ActiveDownload {
  const total = (isHls(episode) ? 320 : 350) * MB;
  return {
    id: episode.id,
    name: `${titleOf(episode)} · Episode ${episode.number}`,
    method: isHls(episode) ? "yt-dlp · HLS stream, joined with ffmpeg" : "aria2 · 8 connections",
    percent: episode.percent,
    bytesDone: Math.round((total * episode.percent) / 100),
    bytesTotal: total,
    bytesPerSecond: [4.2, 3.9, 2.1][index % 3] * MB,
    etaSeconds: Math.round(((100 - episode.percent) / PROGRESS_STEP) * 2),
  };
}

function snapshot(): QueueSnapshot {
  const named = (episode: SampleEpisode) => `${titleOf(episode)} · Episode ${episode.number}`;
  const downloading = episodes.filter((episode) => episode.status === "downloading");
  const queued = episodes.filter((episode) => episode.status === "queued");
  const failed = episodes.filter((episode) => episode.status === "failed");
  const ready = episodes.filter((episode) => episode.status === "ready");
  return {
    active: downloading.map(describe),
    waiting: [
      ...queued.map((e) => ({ id: e.id, name: named(e), note: "Waiting for a free slot", failed: false })),
      ...failed.map((e) => ({
        id: e.id,
        name: named(e),
        note: "Failed: timed out after 5 attempts. Safe to retry.",
        failed: true,
      })),
    ],
    finished: ready.map((e) => ({ id: e.id, name: named(e) })),
    slots: SLOTS,
    downloadsFolder: "~/tsuzuki/Downloads",
    exampleFile: "Downloads/Sousou-no-Frieren/episode_12.mp4",
  };
}

function move(id: number, from: EpisodeStatus[], to: EpisodeStatus): void {
  const episode = episodeById(id);
  if (episode && from.includes(episode.status)) {
    episode.status = to;
    episode.percent = 0;
  }
}

function hostOf(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return "new-anime-site.example";
  }
}

const SITES: SiteInfo[] = [
  { host: "animeheaven.me", how: "Built-in adapter", state: "working" },
  { host: "new-anime-site.example", how: "Learned profile, checked on 24 episodes", state: "working" },
  {
    host: "older-anime-site.example",
    how: "yt-dlp finds the video, episode list found by detection",
    state: "needs-look",
  },
];

function trySteps(): Step[] {
  return [
    { title: "Saved profile", outcome: "missing", summary: "None yet", detail: "This site has not been seen before." },
    { title: "Generic detection", outcome: "worked", summary: "Found 24 episodes", detail: "Links that look like episodes, in a sensible order." },
    { title: "yt-dlp", outcome: "worked", summary: "Found a video", detail: "Episode 1 resolves to an HLS stream, so it will be joined with ffmpeg." },
    { title: "AI repair", outcome: "skipped", summary: "Not needed", detail: "Optional. Runs only when the steps above fail, and needs an API key." },
  ];
}

export const sampleApi: Api = {
  listSeries: () => settle(catalog.map(summarize)),

  addSeries(url) {
    const id = catalog.length + 1;
    const fresh: SampleSeries = { id, title: `New series from ${hostOf(url)}`, url, total: 12, downloaded: 0 };
    catalog.push(fresh);
    episodes.push(...buildEpisodes(fresh));
    return settle(summarize(fresh));
  },

  getSeries(id, query) {
    const series = catalog.find((item) => item.id === id);
    if (!series) return Promise.reject(new Error("That series is not in your library"));
    const detail: SeriesDetail = {
      series: summarize(series),
      episodes: page(series, query),
      listed: series.total,
      steps: LADDER,
    };
    return settle(detail);
  },

  queueEpisodes(_seriesId, ids) {
    ids.forEach((id) => move(id, ["available", "failed", "delivered", "expired"], "queued"));
    return settle(undefined);
  },

  getQueue() {
    tick();
    return settle(snapshot());
  },

  retryEpisode: (id) => (move(id, ["failed"], "queued"), settle(undefined)),
  pauseEpisode: (id) => (move(id, ["downloading"], "queued"), settle(undefined)),
  cancelEpisode: (id) => (move(id, ["queued", "downloading"], "available"), settle(undefined)),

  fileUrl: (id) => `#save-${id}`,
  streamUrl: (id) => `#play-${id}`,

  listSites: () => settle(SITES),

  testSite(url) {
    const result: SiteTest = {
      host: hostOf(url),
      steps: trySteps(),
      profilePath: `sites/${hostOf(url)}.json`,
    };
    return settle(result);
  },

  saveSiteProfile: () => settle(undefined),
};
