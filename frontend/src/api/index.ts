import type { Api } from "./contract";
import { httpApi } from "./http";
import { sampleApi } from "./sample";

/** Sample data unless `VITE_USE_SAMPLE=false`. Screens import `api` and never care which it is. */
export const usingSample: boolean = import.meta.env.VITE_USE_SAMPLE !== "false";

export const api: Api = usingSample ? sampleApi : httpApi;

export type { Api } from "./contract";
export * from "./types";
