import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/api";
import { keys } from "@/api/keys";

export function useSites() {
  return useQuery({ queryKey: keys.sites, queryFn: () => api.listSites() });
}

export function useTestSite() {
  return useMutation({ mutationFn: (url: string) => api.testSite(url) });
}

export function useSaveProfile() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (url: string) => api.saveSiteProfile(url),
    onSuccess: () => client.invalidateQueries({ queryKey: keys.sites }),
  });
}
