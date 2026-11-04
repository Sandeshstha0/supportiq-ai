import { Component, DestroyRef, inject, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, forkJoin, Subject } from 'rxjs';
import { CustomerOrder, OrderService, OrderStatus } from '../../../services/order.service';

const statuses: OrderStatus[] = [
  'pending_confirmation', 'confirmed', 'processing', 'out_for_delivery', 'delivered', 'cancelled',
];

const transitions: Record<OrderStatus, OrderStatus[]> = {
  pending_confirmation: ['confirmed', 'cancelled'],
  confirmed: ['processing', 'cancelled'],
  processing: ['out_for_delivery', 'cancelled'],
  out_for_delivery: ['delivered'],
  delivered: [],
  cancelled: [],
};

@Component({
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './orders-page.html',
})
export class OrdersPage {
  private readonly ordersApi = inject(OrderService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly searchInput = new Subject<string>();

  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusFilter = signal<OrderStatus | ''>('');
  readonly page = signal(1);
  readonly pageSize = 10;
  readonly total = signal<number | null>(null);
  readonly totalPages = signal(0);
  readonly orders = signal<CustomerOrder[] | null>(null);
  readonly listLoading = signal(true);
  readonly listError = signal('');

  readonly stats = signal<Record<OrderStatus | 'total', number> | null>(null);
  readonly statsLoading = signal(true);
  readonly statsError = signal(false);

  readonly selectedOrder = signal<CustomerOrder | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');
  readonly pendingStatus = signal<OrderStatus | null>(null);
  readonly statusSaving = signal(false);
  readonly actionMessage = signal('');
  readonly actionError = signal(false);

  readonly statusOptions = statuses;
  readonly statusLabel = (status: string): string => status.replaceAll('_', ' ');

  constructor() {
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(value => this.searchInput.next(value));
    this.searchInput.pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(() => {
      this.page.set(1);
      this.loadOrders();
    });
    this.loadOrders();
    this.loadStats();
  }

  loadOrders(): void {
    this.listLoading.set(true);
    this.listError.set('');
    this.ordersApi.getOrders({
      search: this.searchControl.value,
      status: this.statusFilter() || undefined,
      page: this.page(),
      page_size: this.pageSize,
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: response => {
        this.orders.set(response.items);
        this.total.set(response.total);
        this.totalPages.set(response.total_pages);
        this.listLoading.set(false);
      },
      error: error => {
        this.orders.set(null);
        this.total.set(null);
        this.totalPages.set(0);
        this.listError.set(error.error?.detail || 'Orders could not be loaded. Please retry.');
        this.listLoading.set(false);
      },
    });
  }

  loadStats(): void {
    this.statsLoading.set(true);
    this.statsError.set(false);
    const requests = [this.ordersApi.getOrders({ page: 1, page_size: 1 }), ...statuses.map(status =>
      this.ordersApi.getOrders({ status, page: 1, page_size: 1 }),
    )];
    forkJoin(requests).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ([all, ...byStatus]) => {
        const counts: Record<OrderStatus | 'total', number> = { total: all.total } as Record<OrderStatus | 'total', number>;
        statuses.forEach((status, index) => counts[status] = byStatus[index].total);
        this.stats.set(counts);
        this.statsLoading.set(false);
      },
      error: () => {
        this.stats.set(null);
        this.statsError.set(true);
        this.statsLoading.set(false);
      },
    });
  }

  setStatusFilter(value: string): void {
    this.statusFilter.set((value || '') as OrderStatus | '');
    this.page.set(1);
    this.loadOrders();
  }

  statValue(stats: Record<OrderStatus | 'total', number>, key: string): number | undefined {
    return stats[key as keyof typeof stats];
  }

  changePage(nextPage: number): void {
    if (nextPage < 1 || nextPage > this.totalPages()) return;
    this.page.set(nextPage);
    this.loadOrders();
  }

  openDetails(orderId: number): void {
    this.selectedOrder.set(null);
    this.detailError.set('');
    this.detailLoading.set(true);
    this.ordersApi.getOrder(orderId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: order => {
        this.selectedOrder.set(order);
        this.detailLoading.set(false);
      },
      error: error => {
        this.detailError.set(error.error?.detail || 'Order details could not be loaded.');
        this.detailLoading.set(false);
      },
    });
  }

  closeDetails(): void {
    this.selectedOrder.set(null);
    this.pendingStatus.set(null);
    this.actionMessage.set('');
  }

  availableTransitions(order: CustomerOrder): OrderStatus[] {
    return transitions[order.status] ?? [];
  }

  askForStatusChange(status: string): void {
    this.pendingStatus.set(status as OrderStatus);
    this.actionMessage.set('');
  }

  cancelStatusChange(): void { this.pendingStatus.set(null); }

  confirmStatusChange(): void {
    const order = this.selectedOrder();
    const newStatus = this.pendingStatus();
    if (!order || !newStatus || this.statusSaving()) return;

    this.statusSaving.set(true);
    this.actionMessage.set('');
    this.ordersApi.updateStatus(order.id, newStatus).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: updated => {
        this.selectedOrder.set(updated);
        this.pendingStatus.set(null);
        this.statusSaving.set(false);
        this.actionMessage.set(`Order #${updated.id} updated to ${this.statusLabel(updated.status)}.`);
        this.actionError.set(false);
        this.loadOrders();
        this.loadStats();
      },
      error: error => {
        this.statusSaving.set(false);
        this.actionMessage.set(error.error?.detail || 'Could not update the order status.');
        this.actionError.set(true);
      },
    });
  }

  formatMoney(amount: number): string {
    return new Intl.NumberFormat('en-NP', { style: 'currency', currency: 'NPR', maximumFractionDigits: 2 }).format(amount);
  }

  formatDate(date: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(date));
  }

  statusClasses(status: string): string {
    return ({
      pending_confirmation: 'border-amber-300/20 bg-amber-300/[0.08] text-amber-200',
      confirmed: 'border-sky-300/20 bg-sky-300/[0.08] text-sky-200',
      processing: 'border-indigo-300/20 bg-indigo-300/[0.08] text-indigo-200',
      out_for_delivery: 'border-violet-300/20 bg-violet-300/[0.08] text-violet-200',
      delivered: 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-200',
      cancelled: 'border-rose-300/20 bg-rose-300/[0.08] text-rose-200',
    } as Record<string, string>)[status] ?? 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300';
  }
}
