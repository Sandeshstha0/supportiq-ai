import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DashboardService, DashboardStats, DashboardTicket, CategoryStat, StatusStat } from '../../../services/dashboard.service';

@Component({
  standalone: true,
  imports: [RouterLink],
  templateUrl: './dashboard-page.html',
  styleUrl: './dashboard-page.scss',
})
export class DashboardPage {
  private readonly dashboard = inject(DashboardService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);

  readonly stats = signal<DashboardStats | null>(null);
  readonly recentTickets = signal<DashboardTicket[] | null>(null);
  readonly categoryStats = signal<CategoryStat[] | null>(null);
  readonly statusStats = signal<StatusStat[] | null>(null);
  readonly statsLoading = signal(true);
  readonly ticketsLoading = signal(true);
  readonly categoriesLoading = signal(true);
  readonly statusesLoading = signal(true);
  readonly statsError = signal(false);
  readonly ticketsError = signal(false);
  readonly categoriesError = signal(false);
  readonly statusesError = signal(false);

  constructor() { this.load(); }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.statsLoading.set(true); this.statsError.set(false);
    this.dashboard.getStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => { this.stats.set(value); this.statsLoading.set(false); },
      error: () => { this.stats.set(null); this.statsError.set(true); this.statsLoading.set(false); },
    });
    this.ticketsLoading.set(true); this.ticketsError.set(false);
    this.dashboard.getRecentTickets().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => { this.recentTickets.set(value); this.ticketsLoading.set(false); },
      error: () => { this.recentTickets.set(null); this.ticketsError.set(true); this.ticketsLoading.set(false); },
    });
    this.categoriesLoading.set(true); this.categoriesError.set(false);
    this.dashboard.getCategoryStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => { this.categoryStats.set(value); this.categoriesLoading.set(false); },
      error: () => { this.categoryStats.set(null); this.categoriesError.set(true); this.categoriesLoading.set(false); },
    });
    this.statusesLoading.set(true); this.statusesError.set(false);
    this.dashboard.getStatusDistribution().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => { this.statusStats.set(value); this.statusesLoading.set(false); },
      error: () => { this.statusStats.set(null); this.statusesError.set(true); this.statusesLoading.set(false); },
    });
  }

  maxCategoryTotal(): number {
    return Math.max(1, ...(this.categoryStats() ?? []).map(item => item.total));
  }

  statValue(stats: DashboardStats, key: string): number | undefined {
    return stats[key as keyof DashboardStats];
  }

  categoryWidth(total: number): string {
    return `${Math.max(3, Math.round((total / this.maxCategoryTotal()) * 100))}%`;
  }

  statusColor(status: string): string {
    return ({ open: '#f4c85a', in_progress: '#4fc6f2', resolved: '#42d6a2', closed: '#8190a5' } as Record<string, string>)[status] ?? '#a78bfa';
  }

  statusLabel(status: string): string {
    return status.replaceAll('_', ' ');
  }

  ticketStatusClass(status: string): string {
    return ({ open: 'border-amber-300/20 bg-amber-300/[0.08] text-amber-200', in_progress: 'border-sky-300/20 bg-sky-300/[0.08] text-sky-200', resolved: 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-200', closed: 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300' } as Record<string, string>)[status] ?? 'border-violet-300/20 bg-violet-300/[0.08] text-violet-200';
  }

  formatDate(date: string): string {
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(date));
  }
}
