import { useQuery } from "@tanstack/react-query";

import { api } from "@/api";
import { keys } from "@/api/keys";

export function useRestoreLink() {
  return useQuery({ queryKey: keys.restoreLink, queryFn: () => api.getRestoreLink() });
}
