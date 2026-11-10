import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { auditApi, organizationsApi, usersApi, type AuditFilters } from '@/api/endpoints';
import { qk } from '@/api/queryKeys';
import type { OrganizationCreate, UserAdminCreate, UserAdminUpdate } from '@/api/types';

export function useUsers(page: number) {
  return useQuery({ queryKey: qk.users.list(page), queryFn: () => usersApi.list({ page, limit: 20 }), placeholderData: keepPreviousData });
}

/** id -> "First Last" for labelling who did what in the audit log (first 100 users of the organisation). */
export function useUserNames() {
  return useQuery({
    queryKey: qk.users.options,
    queryFn: async () => {
      const page = await usersApi.list({ limit: 100 });
      return new Map(page.items.map((u) => [u.id, `${u.first_name} ${u.last_name}`] as const));
    },
    staleTime: 60_000,
  });
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { body: UserAdminCreate; key: string }) => usersApi.create(v.body, v.key),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }),
  });
}

export function useUpdateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (v: { id: number; body: UserAdminUpdate }) => usersApi.update(v.id, v.body),
    onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }),
  });
}

export function useDeactivateUser() {
  const qc = useQueryClient();
  return useMutation({ mutationFn: (id: number) => usersApi.deactivate(id), onSuccess: () => qc.invalidateQueries({ queryKey: qk.users.all }) });
}

export function useAuditLogs(filters: AuditFilters) {
  return useQuery({ queryKey: qk.audit.list(filters), queryFn: () => auditApi.list(filters), placeholderData: keepPreviousData });
}

export function useCreateOrganization() {
  return useMutation({ mutationFn: (v: { body: OrganizationCreate; key: string }) => organizationsApi.create(v.body, v.key) });
}
