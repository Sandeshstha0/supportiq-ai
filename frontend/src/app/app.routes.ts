import { Routes } from '@angular/router';
import { App } from './app';
import { authenticatedGuard, guestOnlyGuard } from './core/auth.guards';
import { AdminHome } from './features/auth/admin-home';
import { LoginPage } from './features/auth/login-page';

export const routes: Routes = [
  { path: '', component: App },
  { path: 'admin/login', component: LoginPage, canActivate: [guestOnlyGuard] },
  { path: 'admin', component: AdminHome, canActivate: [authenticatedGuard] },
  { path: '**', redirectTo: '' },
];
