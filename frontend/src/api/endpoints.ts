import { api, request, session } from './client';
import type {
  AllocationMethod,
  AllocationResult,
  Container,
  ContainerCreate,
  Customer,
  CustomerCreate,
  CustomerUpdate,
  ContainerDetail,
  ContainerUpdate,
  DashboardSummary,
  Expense,
  ExpenseCreate,
  ExpenseUpdate,
  AuditLog,
  CategoryReport,
  ContainerReport,
  DemandSnapshot,
  Item,
  ItemCreate,
  ItemUpdate,
  ListParams,
  MarkSoldRequest,
  Organization,
  OrganizationCreate,
  OrganizationCreated,
  Paged,
  PricingAccuracy,
  PricingRequest,
  PricingResponse,
  ProfitReportItem,
  TokenResponse,
  User,
  UserAdminCreate,
  UserAdminUpdate,
} from './types';

/** Collection routes end with a slash because that is how the server defines them
 *  (without it FastAPI answers with a redirect). */
export const authApi = {
  async login(username: string, password: string): Promise<void> {
    const data = await request<TokenResponse>('POST', '/auth/login', { form: { username, password }, skipRefresh: true });
    session.set(data.access_token, data.expires_in);
  },
  async logout(): Promise<void> {
    try {
      await request<unknown>('POST', '/auth/logout', { skipRefresh: true });
    } finally {
      session.clear();
    }
  },
  me: () => api.get<User>('/users/me'),
};

export interface ContainerFilters extends ListParams {
  container_type?: string;
  is_shipped?: boolean;
  owner_id?: number;
}

export const containersApi = {
  list: (f: ContainerFilters = {}) => api.get<Paged<Container>>('/containers/', { ...f }),
  get: (id: number) => api.get<ContainerDetail>(`/containers/${id}`),
  create: (body: ContainerCreate, key: string) => api.post<Container>('/containers/', body, { idempotencyKey: key }),
  update: (id: number, body: ContainerUpdate) => api.put<Container>(`/containers/${id}`, body),
  seal: (id: number) => api.post<Container>(`/containers/${id}/seal`),
  remove: (id: number) => api.delete(`/containers/${id}`),
  allocate: (id: number, method: AllocationMethod) =>
    api.post<AllocationResult>(`/containers/${id}/allocate-costs`, undefined, { query: { allocation_method: method } }),
};

export interface ItemFilters extends ListParams {
  container_id?: number;
  category?: string;
  condition?: string;
  sold?: boolean;
  search?: string;
}

export const itemsApi = {
  list: (f: ItemFilters = {}) => api.get<Paged<Item>>('/items/', { ...f }),
  create: (body: ItemCreate, key: string) => api.post<Item>('/items/', body, { idempotencyKey: key }),
  update: (id: number, body: ItemUpdate) => api.put<Item>(`/items/${id}`, body),
  remove: (id: number) => api.delete(`/items/${id}`),
  markSold: (id: number, body: MarkSoldRequest, key: string) =>
    api.post<Item>(`/items/${id}/mark-sold`, body, { idempotencyKey: key }),
};

export const expensesApi = {
  create: (body: ExpenseCreate, key: string) => api.post<Expense>('/expenses/', body, { idempotencyKey: key }),
  update: (id: number, body: ExpenseUpdate) => api.put<Expense>(`/expenses/${id}`, body),
  remove: (id: number) => api.delete(`/expenses/${id}`),
};

export interface ProfitItemFilters {
  container_id?: number;
  category?: string;
  sold_only?: boolean;
  start_date?: string; // YYYY-MM-DD
  end_date?: string;
}

export const reportsApi = {
  dashboard: () => api.get<DashboardSummary>('/reports/dashboard'),
  profitCategories: () => api.get<CategoryReport[]>('/reports/profit/categories'),
  /** manager or admin only */
  profitContainers: () => api.get<ContainerReport[]>('/reports/profit/containers'),
  profitItems: (f: ProfitItemFilters = {}) => api.get<ProfitReportItem[]>('/reports/profit/items', { ...f }),
  /** refused to clerks (organisation-wide figures) */
  demand: () => api.get<DemandSnapshot[]>('/reports/demand'),
};

export interface CustomerFilters extends ListParams {
  search?: string;
}

export const customersApi = {
  list: (f: CustomerFilters = {}) => api.get<Paged<Customer>>('/customers/', { ...f }),
  create: (body: CustomerCreate, key: string) => api.post<Customer>('/customers/', body, { idempotencyKey: key }),
  update: (id: number, body: CustomerUpdate) => api.put<Customer>(`/customers/${id}`, body),
  remove: (id: number) => api.delete(`/customers/${id}`),
};

export const pricingApi = {
  /** Also SAVES the recommended price on the item, which is why the server requires clerk or higher. */
  generate: (itemId: number, body: PricingRequest) => api.post<PricingResponse>(`/pricing/generate/${itemId}`, body),
  refreshMarket: (itemId: number) => api.post<unknown>(`/pricing/refresh-market/${itemId}`),
  accuracy: () => api.get<PricingAccuracy>('/pricing/accuracy'),
};

export const usersApi = {
  list: (f: ListParams = {}) => api.get<Paged<User>>('/users/', { ...f }),
  create: (body: UserAdminCreate, key: string) => api.post<User>('/users/', body, { idempotencyKey: key }),
  update: (id: number, body: UserAdminUpdate) => api.put<User>(`/users/${id}`, body),
  /** The server DEACTIVATES the account (it is not deleted); edit the user to re-activate it. */
  deactivate: (id: number) => api.delete(`/users/${id}`),
};

export interface AuditFilters extends ListParams {
  action?: string;
  entity_type?: string;
  user_id?: number;
}

export const auditApi = {
  list: (f: AuditFilters = {}) => api.get<Paged<AuditLog>>('/audit-logs/', { ...f }),
};

export const organizationsApi = {
  me: () => api.get<Organization>('/organizations/me'),
  create: (body: OrganizationCreate, key: string) => api.post<OrganizationCreated>('/organizations/', body, { idempotencyKey: key }),
};
