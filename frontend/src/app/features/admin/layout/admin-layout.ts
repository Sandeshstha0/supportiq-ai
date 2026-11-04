import { Component, DestroyRef, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet, NavigationEnd } from '@angular/router';
import { filter } from 'rxjs';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AuthService } from '../../../core/auth.service';

interface AdminNavItem {
  label: string;
  path: string;
  icon: string;
  adminOnly?: boolean;
}

@Component({
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './admin-layout.html',
  styleUrl: './admin-layout.scss',
})
export class AdminLayout {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);

  readonly collapsed = signal(false);
  readonly mobileOpen = signal(false);
  readonly pageTitle = signal('Dashboard');

  readonly navItems: AdminNavItem[] = [
    { label: 'Dashboard', path: '/admin', icon: 'grid' },
    { label: 'Tickets', path: '/admin/tickets', icon: 'ticket' },
    { label: 'Orders', path: '/admin/orders', icon: 'box' },
    { label: 'Customers', path: '/admin/customers', icon: 'users' },
    { label: 'Conversations', path: '/admin/conversations', icon: 'message' },
    { label: 'Products', path: '/admin/products', icon: 'package' },
    { label: 'Knowledge Base', path: '/admin/knowledge-base', icon: 'book' },
    { label: 'Staff Management', path: '/admin/staff', icon: 'staff', adminOnly: true },
    { label: 'Settings', path: '/admin/settings', icon: 'settings' },
  ];

  constructor() {
    this.updateTitle();
    this.router.events.pipe(
      filter(event => event instanceof NavigationEnd),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(() => {
      this.updateTitle();
      this.mobileOpen.set(false);
    });
  }

  get visibleNavItems(): AdminNavItem[] {
    return this.navItems.filter(item => !item.adminOnly || this.auth.currentUser()?.role === 'admin');
  }

  toggleCollapse(): void { this.collapsed.update(value => !value); }
  toggleMobile(): void { this.mobileOpen.update(value => !value); }
  closeMobile(): void { this.mobileOpen.set(false); }

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/admin/login']);
  }

  private updateTitle(): void {
    const path = this.router.url.split('?')[0].replace(/\/$/, '');
    const item = this.navItems.find(nav => nav.path === path);
    this.pageTitle.set(item?.label ?? 'Dashboard');
  }
}
