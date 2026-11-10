/**
 * Hand-written DTOs that mirror the backend's Pydantic schemas.
 * Run `npm run api:export && npm run check:contract` to prove they still match the real OpenAPI spec.
 * Money in RESPONSES is a JSON number; money in REQUESTS is a decimal string.
 */
import type { Role } from '@/lib/permissions';

export type { Role };

export interface Paged<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export type ContainerType = '20ft' | '40ft';
export type AllocationMethod = 'weight_based' | 'value_based';
export type ItemCategory = 'electronics' | 'vehicles' | 'engines' | 'appliances' | 'food_items' | 'laptops' | 'other';
export type ItemCondition = 'new' | 'tokunbo' | 'used';
export type ExpenseType =
  | 'loading_fee'
  | 'shipping_fee'
  | 'clearing_fee'
  | 'offloading_fee'
  | 'warehouse_fee'
  | 'security_fee'
  | 'extra_fee';

export const CONTAINER_TYPES = ['20ft', '40ft'] as const satisfies readonly ContainerType[];
export const ALLOCATION_METHODS = ['weight_based', 'value_based'] as const satisfies readonly AllocationMethod[];
export const ITEM_CATEGORIES = ['electronics', 'vehicles', 'engines', 'appliances', 'food_items', 'laptops', 'other'] as const satisfies readonly ItemCategory[];
export const ITEM_CONDITIONS = ['new', 'tokunbo', 'used'] as const satisfies readonly ItemCondition[];
export const EXPENSE_TYPES = [
  'loading_fee',
  'shipping_fee',
  'clearing_fee',
  'offloading_fee',
  'warehouse_fee',
  'security_fee',
  'extra_fee',
] as const satisfies readonly ExpenseType[];
export const CURRENCIES = ['USD', 'EUR', 'CZK', 'NGN'] as const;

export interface TokenResponse {
  access_token: string;
  refresh_token: string | null;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role: Role;
  is_superuser: boolean;
  tenant_id: number;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export interface Container {
  id: number;
  tenant_id: number;
  owner_id: number;
  name: string;
  container_type: ContainerType;
  msc_container_number: string | null;
  allocation_method: AllocationMethod;
  notes: string | null;
  is_sealed: boolean;
  is_shipped: boolean;
  allocation_override: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Item {
  id: number;
  tenant_id: number;
  container_id: number;
  name: string;
  description: string | null;
  category: ItemCategory;
  condition: ItemCondition;
  purchase_price: number;
  purchase_currency: string;
  purchase_date: string | null;
  weight: number;
  volume: number | null;
  fx_rate_to_usd: number;
  purchase_price_usd: number;
  allocated_cost: number;
  landed_cost: number;
  recommended_price: number | null;
  selling_price: number | null;
  sold: boolean;
  sold_date: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface Expense {
  id: number;
  tenant_id: number;
  container_id: number;
  expense_type: ExpenseType;
  amount: number;
  currency: string;
  fx_rate_to_usd: number;
  amount_usd: number;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ContainerDetail extends Container {
  items: Item[];
  expenses: Expense[];
  item_count: number;
  items_sold: number;
  total_expenses: number | null;
  total_value: number | null;
  total_weight: number | null;
}

export interface AllocationResult {
  method: AllocationMethod;
  total_expenses: number;
  allocated_total: number;
  basis_total: number;
  items: { item_id: number; item_name: string; ratio: number; allocated_cost: number; landed_cost: number }[];
}

export interface DashboardSummary {
  active_containers: number;
  total_items: number;
  items_sold: number;
  total_revenue: number;
  cost_of_goods_sold: number;
  inventory_value: number;
  total_profit: number;
  avg_profit_margin: number;
  pending_shipments: number;
  low_stock_alerts: number;
  generated_at: string;
}

// ---------- request bodies (money as decimal strings) ----------
export interface ContainerCreate {
  name: string;
  container_type: ContainerType;
  msc_container_number?: string | null;
  allocation_method?: AllocationMethod; // optional: the server defaults it
  notes?: string | null;
}
export type ContainerUpdate = Partial<Omit<ContainerCreate, 'container_type'>>;

export interface ItemCreate {
  container_id: number;
  name: string;
  description?: string | null;
  category: ItemCategory;
  condition: ItemCondition;
  purchase_price: string;
  purchase_currency: string;
  purchase_date?: string | null;
  weight: string;
  volume?: string | null;
}
export type ItemUpdate = Partial<Omit<ItemCreate, 'container_id'>>;

export interface ExpenseCreate {
  container_id: number;
  expense_type: ExpenseType;
  amount: string;
  currency: string;
  description?: string | null;
}
export type ExpenseUpdate = Partial<Omit<ExpenseCreate, 'container_id'>>;

export interface MarkSoldRequest {
  selling_price: string;
  sold_date?: string | null;
  customer_id?: number | null;
  notes?: string | null;
}

export interface ListParams {
  page?: number;
  limit?: number;
}

// ---------- customers ----------
export interface Customer {
  id: number;
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}
export interface CustomerCreate {
  name: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
  notes?: string | null;
}
export type CustomerUpdate = Partial<CustomerCreate>;

// ---------- pricing ----------
export const PRICING_SOURCES = ['jiji', 'ebay', 'mobile_de', 'autoscout24', 'bazos_cz'] as const;
export type PricingSource = (typeof PRICING_SOURCES)[number];

export interface MarketPrice {
  source: PricingSource;
  price: number;
  currency: string;
  url: string | null;
  confidence: number;
  found_at: string;
  price_usd: number | null;
  age_days: number | null;
}

export interface PricingRequest {
  include_cost_based?: boolean;
  include_market_pricing?: boolean;
  include_last_sold?: boolean;
  /** target margin as a RATIO: 0.25 = 25% (the API accepts 0.05 to 1.0) */
  profit_margin?: number | null;
  sources?: PricingSource[] | null;
}

export interface PricingResponse {
  item_id: number;
  cost_based_price: number | null;
  market_prices: MarketPrice[];
  last_sold_price: number | null;
  recommended_price: number | null;
  profit_margin: number | null;
  landed_cost: number | null;
  generated_at: string;
  price_low: number | null;
  price_high: number | null;
  confidence: number | null;
  expected_margin: number | null;
  comparables_used: number;
  warnings: string[];
  explanation: string[];
}

export interface PricingAccuracy {
  n: number;
  mape: number;
  bias: number;
  within_10pct: number;
}

// ---------- administration ----------
export const ROLES = ['admin', 'manager', 'clerk', 'viewer'] as const satisfies readonly Role[];

export interface UserAdminCreate {
  email: string;
  first_name: string;
  last_name: string;
  password: string;
  role?: Role;
  is_active?: boolean;
  username: string;
}
export interface UserAdminUpdate {
  email?: string | null;
  first_name?: string | null;
  is_active?: boolean | null;
  last_name?: string | null;
  password?: string | null;
  role?: Role | null;
  username?: string | null;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  entity_type: string | null;
  entity_id: number | null;
  ip_address: string | null;
  extra_data: Record<string, unknown> | null;
  created_at: string;
}

export interface Organization {
  id: number;
  name: string;
  slug: string;
  plan: string;
  is_active: boolean;
  max_users: number;
  max_containers: number;
}
export interface OrganizationCreate {
  admin_email: string;
  admin_first_name: string;
  admin_last_name: string;
  admin_password: string;
  admin_username: string;
  name: string;
  slug: string;
}
export interface OrganizationCreated extends Organization {
  admin_user_id: number;
}

// ---------- reports ----------
export interface ProfitReportItem {
  allocated_cost: number;
  category: string;
  item_id: number;
  item_name: string;
  landed_cost: number;
  profit_amount: number | null;
  profit_margin: number | null;
  purchase_price_usd: number;
  selling_price: number | null;
  sold: boolean;
  sold_date: string | null;
}

export interface ContainerReport {
  container_id: number;
  container_name: string;
  container_type: string;
  cost_of_goods_sold: number;
  created_at: string;
  inventory_value: number;
  items_sold: number;
  profit_margin: number;
  total_cost: number;
  total_expenses: number;
  total_items: number;
  total_profit: number;
  total_revenue: number;
  unallocated_expenses: number;
}

export interface CategoryReport {
  average_margin: number;
  avg_sale_price: number | null;
  category: string;
  cost_of_goods_sold: number;
  inventory_value: number;
  items_sold: number;
  total_investment: number;
  total_items: number;
  total_profit: number;
  total_revenue: number;
}

export interface DemandSnapshot {
  avg_margin: number | null;
  avg_market_price: number | null;
  avg_sale_price: number | null;
  demand_score: number | null;
  item_category: string;
  units_sold_30d: number;
  units_sold_90d: number;
  updated_at: string | null;
}
