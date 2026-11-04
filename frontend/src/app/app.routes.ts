import { Routes } from '@angular/router';
import { App } from './app';
import { adminRoleGuard, authenticatedGuard, guestOnlyGuard } from './core/auth.guards';
import { LoginPage } from './features/auth/login-page';

const placeholder = (title: string, description: string, availability: string, endpoints: string) => ({
  path: title === 'Knowledge Base' ? 'knowledge' : title === 'Staff Management' ? 'staff' : title.toLowerCase().replaceAll(' ', '-'),
  loadComponent: () => import('./features/admin/placeholder-page').then(module => module.PlaceholderPage),
  data: { section: { title, description, availability, endpoints } },
});

export const routes: Routes = [
  { path: '', component: App },
  { path: 'admin/login', component: LoginPage, canActivate: [guestOnlyGuard] },
  {
    path: 'admin',
    loadComponent: () => import('./features/admin/layout/admin-layout').then(module => module.AdminLayout),
    canActivate: [authenticatedGuard],
    children: [
      { path: '', pathMatch: 'full', loadComponent: () => import('./features/admin/dashboard/dashboard-page').then(module => module.DashboardPage) },
      { path: 'tickets', loadComponent: () => import('./features/admin/tickets/tickets-page').then(module => module.TicketsPage) },
      { path: 'orders', loadComponent: () => import('./features/admin/orders/orders-page').then(module => module.OrdersPage) },
      { path: 'customers', loadComponent: () => import('./features/admin/customers/customers-page').then(module => module.CustomersPage) },
      placeholder('Conversations', 'Previous customer and AI support conversations.', 'Staff conversation search and listing APIs are not available yet.', 'Current conversation routes require a guest session and expose only that guest’s conversations.'),
      placeholder('Products', 'Product catalog, pricing, and stock information.', 'Read-only product APIs are available. Product administration actions are not supported.', 'Available: GET /api/v1/products, GET /api/v1/products/{id}, and GET /api/v1/products/{id}/stock. Product UI is deferred to a later phase.'),
      placeholder('Knowledge Base', 'Store policies and support information used by the assistant.', 'Knowledge search and document upload APIs exist; document management APIs do not.', 'Search: GET /api/v1/knowledge/search. Upload uses a separate admin API key, not staff JWT authentication.'),
      { ...placeholder('Staff Management', 'Staff accounts, roles, and account access.', 'Staff APIs are available, but staff management UI is deferred to a later phase.', 'Available under admin authorization: GET/POST /api/v1/auth/staff and PATCH /api/v1/auth/staff/{id}/status.'), canActivate: [adminRoleGuard] },
      placeholder('Settings', 'Your SupportIQ account and application preferences.', 'Profile retrieval exists; application settings APIs are not available.', 'Available: GET /api/v1/auth/me. No settings update endpoint exists.'),
    ],
  },
  { path: '**', redirectTo: '' },
];
