import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged, Subject } from 'rxjs';
import { CustomerDetails, CustomerDirectoryItem, CustomerDirectoryResponse, CustomerService } from '../../../services/customer.service';

@Component({
  standalone: true,
  imports: [ReactiveFormsModule],
  templateUrl: './customers-page.html',
})
export class CustomersPage {
  private readonly customerApi = inject(CustomerService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  private readonly route = inject(ActivatedRoute);
  private readonly searchChanges = new Subject<string>();

  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly customers = signal<CustomerDirectoryItem[] | null>(null);
  readonly summary = signal<CustomerDirectoryResponse['summary'] | null>(null);
  readonly identityNote = signal('');
  readonly total = signal<number | null>(null);
  readonly page = signal(1);
  readonly pageSize = 20;
  readonly totalPages = signal(0);
  readonly loading = signal(true);
  readonly error = signal('');
  readonly selectedCustomer = signal<CustomerDetails | null>(null);
  readonly detailLoading = signal(false);
  readonly detailError = signal('');

  constructor() {
    const initialSearch = this.route.snapshot.queryParamMap.get('search');
    if (initialSearch) this.searchControl.setValue(initialSearch, { emitEvent: false });
    this.searchControl.valueChanges.pipe(
      debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef),
    ).subscribe(value => this.searchChanges.next(value));
    this.searchChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.page.set(1);
      this.load();
    });
    this.load();
  }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true);
    this.error.set('');
    this.customerApi.getCustomers(this.searchControl.value, this.page(), this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: response => this.applyResponse(response),
        error: error => {
          this.customers.set(null);
          this.summary.set(null);
          this.total.set(null);
          this.error.set(error.error?.detail || 'Customer sessions could not be loaded. Please retry.');
          this.loading.set(false);
        },
      });
  }

  private applyResponse(response: CustomerDirectoryResponse): void {
    this.customers.set(response.items);
    this.summary.set(response.summary);
    this.identityNote.set(response.identity_note);
    this.total.set(response.total);
    this.totalPages.set(response.total_pages);
    this.loading.set(false);
  }

  changePage(nextPage: number): void {
    if (nextPage < 1 || nextPage > this.totalPages()) return;
    this.page.set(nextPage);
    this.load();
  }

  summaryValue(summary: CustomerDirectoryResponse['summary'], key: string): number | undefined {
    return summary[key as keyof CustomerDirectoryResponse['summary']];
  }

  openCustomer(customerId: number): void {
    this.selectedCustomer.set(null);
    this.detailError.set('');
    this.detailLoading.set(true);
    this.customerApi.getCustomer(customerId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: customer => {
        this.selectedCustomer.set(customer);
        this.detailLoading.set(false);
      },
      error: error => {
        this.detailError.set(error.error?.detail || 'Customer session details could not be loaded.');
        this.detailLoading.set(false);
      },
    });
  }

  closeDetails(): void {
    this.selectedCustomer.set(null);
    this.detailError.set('');
  }

  formatDate(date: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(date));
  }

  formatDateTime(date: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(date));
  }

  formatMoney(value: number): string {
    return new Intl.NumberFormat('en-NP', { style: 'currency', currency: 'NPR', maximumFractionDigits: 2 }).format(value);
  }

  statusClass(status: string): string {
    return ({
      pending_confirmation: 'border-amber-300/20 bg-amber-300/[0.08] text-amber-200',
      confirmed: 'border-sky-300/20 bg-sky-300/[0.08] text-sky-200',
      processing: 'border-indigo-300/20 bg-indigo-300/[0.08] text-indigo-200',
      out_for_delivery: 'border-violet-300/20 bg-violet-300/[0.08] text-violet-200',
      delivered: 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-200',
      cancelled: 'border-rose-300/20 bg-rose-300/[0.08] text-rose-200',
      open: 'border-amber-300/20 bg-amber-300/[0.08] text-amber-200',
      in_progress: 'border-sky-300/20 bg-sky-300/[0.08] text-sky-200',
      resolved: 'border-emerald-300/20 bg-emerald-300/[0.08] text-emerald-200',
      closed: 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300',
    } as Record<string, string>)[status] ?? 'border-slate-300/15 bg-slate-300/[0.06] text-slate-300';
  }
}
