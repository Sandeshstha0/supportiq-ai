import { Routes } from '@angular/router';
import { App } from './app';
import { adminRoleGuard, authenticatedGuard, guestOnlyGuard } from './core/auth.guards';
import { LoginPage } from './features/auth/login-page';

const placeholder = (title: string, description: string, availability: string, endpoints: string) => ({
  path: title === 'Staff Management' ? 'staff' : title.toLowerCase().replaceAll(' ', '-'),
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
      { path: 'conversations', loadComponent: () => import('./features/admin/conversations/conversations-page').then(module => module.ConversationsPage) },
      { path: 'knowledge', pathMatch: 'full', redirectTo: 'knowledge-base' },
      { path: 'knowledge-base', loadComponent: () => import('./features/admin/knowledge-base/knowledge-base-page').then(module => module.KnowledgeBasePage) },
      { path: 'products', loadComponent: () => import('./features/admin/products/products-page').then(module => module.ProductsPage) },
      { path: 'staff', loadComponent: () => import('./features/admin/staff/staff-page').then(module => module.StaffPage), canActivate: [adminRoleGuard] },
      placeholder('Settings', 'Your SupportIQ account and application preferences.', 'Profile retrieval exists; application settings APIs are not available.', 'Available: GET /api/v1/auth/me. No settings update endpoint exists.'),
    ],
  },
  { path: '**', redirectTo: '' },
];
