import { request } from "./client";
import type { Api } from "./contract";
import type { QueueSnapshot, SeriesDetail, SeriesSummary, SiteInfo, SiteTest } from "./types";

/** The real API. These paths are the contract the server has to provide (see frontend/README). */
export const httpApi: Api = {
  listSeries: () => request<SeriesSummary[]>("/series"),
  addSeries: (url) => request<SeriesSummary>("/series", { method: "POST", body: { url } }),
  getSeries: (id, { order, all }) =>
    request<SeriesDetail>(`/series/${id}`, { query: { order, all } }),
  queueEpisodes: (seriesId, episodeIds) =>
    request<void>("/downloads", { method: "POST", body: { seriesId, episodeIds } }),
  getQueue: () => request<QueueSnapshot>("/queue"),
  retryEpisode: (id) => request<void>(`/episodes/${id}/retry`, { method: "POST" }),
  pauseEpisode: (id) => request<void>(`/episodes/${id}/pause`, { method: "POST" }),
  cancelEpisode: (id) => request<void>(`/episodes/${id}/cancel`, { method: "POST" }),
  fileUrl: (id) => `/api/episodes/${id}/file`,
  streamUrl: (id) => `/api/episodes/${id}/stream`,
  getRestoreLink: async () =>
    (await request<{ restorePath: string | null }>("/me")).restorePath,
  listSites: () => request<SiteInfo[]>("/sites"),
  testSite: (url) => request<SiteTest>("/sites/test", { method: "POST", body: { url } }),
  saveSiteProfile: (url) => request<void>("/sites/profiles", { method: "POST", body: { url } }),
};
