/**
 * CONTRACT CHECK (type level, no runtime code).
 *
 * `npm run check:contract` regenerates `generated/schema.d.ts` from openapi.json and compiles this file.
 * If the backend renames, adds or removes a field, or changes an enum, THIS FILE STOPS COMPILING, so the
 * build fails instead of a user hitting a broken screen. Refresh the spec with `npm run api:export`.
 */
import type { components } from './generated/schema';
import type {
  AllocationMethod, Container, ContainerCreate, ContainerDetail, ContainerType, Customer, CustomerCreate, DashboardSummary, Expense,
  ExpenseCreate, ExpenseType, Item, ItemCategory, ItemCondition, ItemCreate, MarkSoldRequest, MarketPrice, PricingAccuracy,
  PricingRequest, PricingResponse, PricingSource, Role, TokenResponse, User, AuditLog, Organization, OrganizationCreate,
  OrganizationCreated, UserAdminCreate, UserAdminUpdate, CategoryReport, ContainerReport, DemandSnapshot, ProfitReportItem,
} from './types';

type Schemas = components['schemas'];

/** `true` when A and B have exactly the same property names; otherwise the assignment below fails to compile. */
type SameKeys<A, B> = [keyof A] extends [keyof B] ? ([keyof B] extends [keyof A] ? true : never) : never;
/** `true` when two string unions have exactly the same members. */
type SameUnion<A, B> = [A] extends [B] ? ([B] extends [A] ? true : never) : never;

export const responseShapes: [
  SameKeys<TokenResponse, Schemas['Token']>,
  SameKeys<User, Schemas['UserInDB']>,
  SameKeys<Container, Schemas['ContainerInDB']>,
  SameKeys<ContainerDetail, Schemas['ContainerWithItems']>,
  SameKeys<Item, Schemas['ItemInDB']>,
  SameKeys<Expense, Schemas['ExpenseInDB']>,
  SameKeys<DashboardSummary, Schemas['DashboardSummary']>,
  SameKeys<Customer, Schemas['CustomerInDB']>,
  SameKeys<PricingResponse, Schemas['PricingResponse']>,
  SameKeys<MarketPrice, Schemas['MarketPrice']>,
  SameKeys<PricingAccuracy, Schemas['PricingAccuracy']>,
  SameKeys<AuditLog, Schemas['AuditLogOut']>,
  SameKeys<Organization, Schemas['OrganizationOut']>,
  SameKeys<OrganizationCreated, Schemas['OrganizationCreated']>,
  SameKeys<ProfitReportItem, Schemas['ProfitReportItem']>,
  SameKeys<ContainerReport, Schemas['ContainerReport']>,
  SameKeys<CategoryReport, Schemas['CategoryReport']>,
  SameKeys<DemandSnapshot, Schemas['DemandSnapshot']>,
] = [true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true, true];

export const requestShapes: [
  SameKeys<ContainerCreate, Schemas['ContainerCreate']>,
  SameKeys<ItemCreate, Schemas['ItemCreate']>,
  SameKeys<ExpenseCreate, Schemas['ExpenseCreate']>,
  SameKeys<MarkSoldRequest, Schemas['MarkSoldRequest']>,
  SameKeys<CustomerCreate, Schemas['CustomerCreate']>,
  SameKeys<PricingRequest, Schemas['PricingRequest']>,
  SameKeys<OrganizationCreate, Schemas['OrganizationCreate']>,
  SameKeys<UserAdminCreate, Schemas['UserAdminCreate']>,
  SameKeys<UserAdminUpdate, Schemas['UserAdminUpdate']>,
] = [true, true, true, true, true, true, true, true, true];

export const enums: [
  SameUnion<ContainerType, Schemas['ContainerType']>,
  SameUnion<AllocationMethod, Schemas['AllocationMethod']>,
  SameUnion<ItemCategory, Schemas['ItemCategory']>,
  SameUnion<ItemCondition, Schemas['ItemCondition']>,
  SameUnion<ExpenseType, Schemas['ExpenseType']>,
  SameUnion<Role, Schemas['UserRole']>,
  SameUnion<PricingSource, Schemas['PricingSource']>,
] = [true, true, true, true, true, true, true];
