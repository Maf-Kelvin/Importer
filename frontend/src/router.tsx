import { createBrowserRouter } from 'react-router-dom';
import { RequireAccess, RequireAuth } from '@/auth';
import { AppShell } from '@/components/layout/AppShell';
import { NotFoundPage } from '@/features/NotFoundPage';

/** Every screen is loaded on demand, so the first page load only downloads what it needs. */
export const router = createBrowserRouter([
  { path: '/login', lazy: async () => ({ Component: (await import('@/features/auth')).LoginPage }) },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, lazy: async () => ({ Component: (await import('@/features/dashboard')).DashboardPage }) },
          { path: 'containers', lazy: async () => ({ Component: (await import('@/features/containers')).ContainerListPage }) },
          { path: 'containers/:id', lazy: async () => ({ Component: (await import('@/features/containers')).ContainerDetailPage }) },
          { path: 'items', lazy: async () => ({ Component: (await import('@/features/items')).ItemListPage }) },
          { path: 'reports', lazy: async () => ({ Component: (await import('@/features/reports')).ReportsPage }) },
          { path: 'customers', lazy: async () => ({ Component: (await import('@/features/customers')).CustomerListPage }) },
          {
            element: <RequireAccess action="users.manage" />,
            children: [{ path: 'admin/users', lazy: async () => ({ Component: (await import('@/features/admin')).UsersPage }) }],
          },
          {
            element: <RequireAccess action="audit.read" />,
            children: [{ path: 'admin/audit', lazy: async () => ({ Component: (await import('@/features/admin')).AuditLogPage }) }],
          },
          {
            element: <RequireAccess platformAdmin />,
            children: [{ path: 'admin/organizations', lazy: async () => ({ Component: (await import('@/features/admin')).OrganizationsPage }) }],
          },
          { path: 'settings', lazy: async () => ({ Component: (await import('@/features/settings')).SettingsPage }) },
        ],
      },
    ],
  },
  { path: '*', element: <NotFoundPage /> },
]);
