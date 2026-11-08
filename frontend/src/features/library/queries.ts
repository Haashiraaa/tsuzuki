import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api";
import { keys } from "@/api/keys";

export function useSeriesList() {
  return useQuery({ queryKey: keys.series, queryFn: () => api.listSeries() });
}

export function useAddSeries() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => api.addSeries(url),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.series }),
  });
}
