import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, usingSample } from "@/api";
import { keys } from "@/api/keys";

/** How often the queue is re-read. A real server will push progress later; polling is enough now. */
const POLL_MS = usingSample ? 1500 : 2000;

export function useQueue() {
  return useQuery({ queryKey: keys.queue, queryFn: () => api.getQueue(), refetchInterval: POLL_MS });
}

/** Retry, pause and cancel: each changes one episode and then refreshes everything on screen. */
export function useEpisodeActions() {
  const client = useQueryClient();
  const refresh = () => client.invalidateQueries();
  const retry = useMutation({ mutationFn: (id: number) => api.retryEpisode(id), onSuccess: refresh });
  const pause = useMutation({ mutationFn: (id: number) => api.pauseEpisode(id), onSuccess: refresh });
  const cancel = useMutation({ mutationFn: (id: number) => api.cancelEpisode(id), onSuccess: refresh });
  return { retry, pause, cancel };
}
