/** Turning raw numbers from the server into the short text the screens show. */

const MB = 1_000_000;

export function megabytes(bytes: number): number {
  return Math.round(bytes / MB);
}

/** "218 of 352 MB" */
export function formatProgress(done: number, total: number): string {
  return `${megabytes(done)} of ${megabytes(total)} MB`;
}

/** "4.2 MB/s" */
export function formatSpeed(bytesPerSecond: number): string {
  return `${(bytesPerSecond / MB).toFixed(1)} MB/s`;
}

/** "about 3 min left", "under a minute left", or "estimating" when the server cannot tell yet. */
export function formatEta(seconds: number | null): string {
  if (seconds === null) return "estimating";
  if (seconds < 60) return "under a minute left";
  return `about ${Math.round(seconds / 60)} min left`;
}

/** "4 episodes" / "1 episode" */
export function plural(count: number, one: string, many = `${one}s`): string {
  return `${count} ${count === 1 ? one : many}`;
}
