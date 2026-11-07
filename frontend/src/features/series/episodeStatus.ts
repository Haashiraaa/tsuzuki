import type { EpisodeStatus } from "@/api";
import type { Tone } from "@/components/ui/tone";

interface Label {
  text: string;
  tone: Tone;
}

/** The words and colour for an episode's status on the series screen. */
export function describeStatus(status: EpisodeStatus): Label {
  switch (status) {
    case "ready":
    case "delivered":
    case "expired":
      return { text: "Downloaded", tone: "ok" };
    case "downloading":
      return { text: "Downloading", tone: "accent" };
    case "queued":
      return { text: "Waiting", tone: "muted" };
    case "failed":
      return { text: "Failed", tone: "warn" };
    case "available":
      return { text: "Not downloaded", tone: "muted" };
  }
}

/** Episodes worth asking for: not on a device, and not already on their way. */
export function isMissing(status: EpisodeStatus): boolean {
  return status === "available" || status === "failed" || status === "expired";
}
