import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api";
import type { EpisodeOrder } from "@/api";
import { keys } from "@/api/keys";

export function useSeriesDetail(id: number, order: EpisodeOrder, all: boolean) {
  return useQuery({
    queryKey: keys.seriesDetail(id, order, all),
    queryFn: () => api.getSeries(id, { order, all }),
  });
}

export function useQueueEpisodes(seriesId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (episodeIds: number[]) => api.queueEpisodes(seriesId, episodeIds),
    onSuccess: () => client.invalidateQueries(),
  });
}
