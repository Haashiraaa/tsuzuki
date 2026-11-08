/** Query keys in one place, so a screen that changes data can refresh the right lists. */
export const keys = {
  series: ["series"] as const,
  seriesDetail: (id: number, order: string, all: boolean) => ["series", id, order, all] as const,
  queue: ["queue"] as const,
  sites: ["sites"] as const,
  restoreLink: ["restore-link"] as const,
};
