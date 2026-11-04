import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';
import { DashboardService, DashboardStats, CategoryStat } from '../../../services/dashboard.service';
import { StaffTicket, TicketService, TicketStatus } from '../../../services/ticket.service';

const ticketStatuses: TicketStatus[] = ['open', 'in_progress', 'resolved', 'closed'];
const validTransitions: Record<TicketStatus, TicketStatus[]> = {
  open: ['open', 'in_progress', 'resolved', 'closed'],
  in_progress: ['in_progress', 'open', 'resolved', 'closed'],
  resolved: ['resolved', 'in_progress', 'closed'],
  closed: ['closed', 'open', 'in_progress'],
};

@Component({
  standalone: true,
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './tickets-page.html',
})
export class TicketsPage {
  private readonly ticketApi = inject(TicketService);
  private readonly dashboardApi = inject(DashboardService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly searchChanges = new Subject<string>();

  readonly statuses = ticketStatuses;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusFilter = signal<TicketStatus | ''>('');
  readonly categoryFilter = signal('');
  readonly categories = signal<CategoryStat[] | null>(null);
  readonly stats = signal<DashboardStats | null>(null);
  readonly statsLoading = signal(true);
  readonly statsError = signal(false);
  readonly tickets = signal<StaffTicket[] | null>(null);
  readonly total = signal<number | null>(null);
  readonly page = signal(1);
  readonly pageSize = 10;
  readonly totalPages = signal(0);
  readonly loading = signal(true);
  readonly error = signal('');

  readonly selectedTicket = signal<StaffTicket | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');
  readonly decisionControl = new FormControl('', {
    nonNullable: true,
    validators: [Validators.required, Validators.minLength(5), Validators.maxLength(3000)],
  });
  readonly decisionStatus = new FormControl<TicketStatus>('open', { nonNullable: true });
  readonly confirmUpdate = signal(false);
  readonly saving = signal(false);
  readonly updateMessage = signal('');
  readonly updateError = signal(false);
  readonly emailNotice = signal('');

  readonly statusLabel = (value: string): string => value.replaceAll('_', ' ');

  constructor() {
    this.searchControl.valueChanges.pipe(
      debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef),
    ).subscribe(value => this.searchChanges.next(value));
    this.searchChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.page.set(1);
      this.loadTickets();
    });
    this.loadTickets();
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.statsLoading.set(true);
    this.statsError.set(false);
    this.dashboardApi.getStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => { this.stats.set(value); this.statsLoading.set(false); },
      error: () => { this.stats.set(null); this.statsError.set(true); this.statsLoading.set(false); },
    });
    this.dashboardApi.getCategoryStats().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: value => this.categories.set(value),
      error: () => this.categories.set(null),
    });
  }

  statValue(stats: DashboardStats, key: string): number | undefined {
    return stats[key as keyof DashboardStats];
  }

  loadTickets(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true);
    this.error.set('');
    this.ticketApi.getTickets({
      search: this.searchControl.value,
      status: this.statusFilter() || undefined,
      category: this.categoryFilter() || undefined,
      page: this.page(),
      pageSize: this.pageSize,
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: response => {
        this.tickets.set(response.items);
        this.total.set(response.total);
        this.totalPages.set(response.total_pages);
        this.loading.set(false);
      },
      error: error => {
        this.tickets.set(null);
        this.total.set(null);
        this.totalPages.set(0);
        this.error.set(error.error?.detail || 'Tickets could not be loaded. Please retry.');
        this.loading.set(false);
      },
    });
  }

  setStatusFilter(value: string): void {
    this.statusFilter.set((value || '') as TicketStatus | '');
    this.page.set(1);
    this.loadTickets();
  }

  setCategoryFilter(value: string): void {
    this.categoryFilter.set(value);
    this.page.set(1);
    this.loadTickets();
  }

  changePage(nextPage: number): void {
    if (nextPage < 1 || nextPage > this.totalPages()) return;
    this.page.set(nextPage);
    this.loadTickets();
  }

  openTicket(ticketId: number): void {
    this.selectedTicket.set(null);
    this.detailError.set('');
    this.updateMessage.set('');
    this.emailNotice.set('');
    this.detailLoading.set(true);
    this.ticketApi.getTicket(ticketId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ticket => {
        this.selectedTicket.set(ticket);
        this.decisionControl.setValue(ticket.decision ?? '');
        this.decisionControl.markAsPristine();
        this.decisionStatus.setValue(ticket.status);
        this.detailLoading.set(false);
      },
      error: error => {
        this.detailError.set(error.error?.detail || 'Ticket details could not be loaded.');
        this.detailLoading.set(false);
      },
    });
  }

  closeDetails(): void {
    this.selectedTicket.set(null);
    this.detailError.set('');
    this.confirmUpdate.set(false);
  }

  allowedStatuses(ticket: StaffTicket): TicketStatus[] {
    return validTransitions[ticket.status] ?? [];
  }

  canSubmitDecision(): boolean {
    const ticket = this.selectedTicket();
    return !!ticket
      && this.decisionControl.valid
      && this.allowedStatuses(ticket).includes(this.decisionStatus.value)
      && (this.decisionControl.dirty || this.decisionStatus.value !== ticket.status);
  }

  askToSubmit(): void {
    this.decisionControl.markAsTouched();
    if (this.canSubmitDecision()) this.confirmUpdate.set(true);
  }

  submitDecision(): void {
    const ticket = this.selectedTicket();
    if (!ticket || !this.canSubmitDecision() || this.saving()) return;
    this.saving.set(true);
    this.updateMessage.set('');
    this.emailNotice.set('');
    this.ticketApi.updateDecision(ticket.id, this.decisionControl.value.trim(), this.decisionStatus.value)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => {
          this.selectedTicket.set(response.ticket);
          this.decisionControl.setValue(response.ticket.decision ?? '');
          this.decisionControl.markAsPristine();
          this.decisionStatus.setValue(response.ticket.status);
          this.confirmUpdate.set(false);
          this.saving.set(false);
          this.updateMessage.set(response.message);
          this.updateError.set(false);
          this.emailNotice.set(response.ticket.customer_email
            ? response.email_notification_sent
              ? 'Customer update email sent.'
              : response.message === 'No ticket changes to apply.'
                ? 'No email was sent because this update matched the saved decision and status.'
                : 'The decision was saved, but the email could not be sent. Check backend SMTP logs/configuration.'
            : 'No customer email is recorded for this ticket.');
          this.loadTickets();
          this.loadAnalytics();
        },
        error: error => {
          this.saving.set(false);
          this.confirmUpdate.set(false);
          this.updateMessage.set(error.error?.detail || 'Ticket update failed. Please retry.');
          this.updateError.set(true);
        },
      });
  }

  formatDate(value: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  statusClass(status: string): string {
    return ({
      open: 'border-amber-300/20 bg-amber-300/[0.08] text-amber-200',
      in_progress: 'border-sky-300/20 bg-sky-300/[0.08] text-sky-200',
      resolved: 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-200',
      closed: 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300',
    } as Record<string, string>)[status] ?? 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300';
  }
}
