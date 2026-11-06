import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { AuthService } from '../../../core/auth.service';
import { ManagedProduct, ProductInput, ProductManagementService } from '../../../services/product-management.service';

@Component({ standalone: true, imports: [ReactiveFormsModule], templateUrl: './products-page.html' })
export class ProductsPage {
  private readonly api = inject(ProductManagementService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  readonly auth = inject(AuthService);
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly categoryControl = new FormControl('', { nonNullable: true });
  readonly availabilityControl = new FormControl('', { nonNullable: true });
  readonly stockControl = new FormControl(0, { nonNullable: true, validators: [Validators.required, Validators.min(0), Validators.pattern(/^\d+$/)] });
  readonly form = new FormGroup({
    name: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(150)] }),
    category: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(100)] }),
    price: new FormControl(0, { nonNullable: true, validators: [Validators.required, Validators.min(0), Validators.pattern(/^\d+(\.\d{1,2})?$/)] }),
    unit: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(30)] }),
    stock: new FormControl(0, { nonNullable: true, validators: [Validators.required, Validators.min(0), Validators.pattern(/^\d+$/)] }),
    description: new FormControl('', { nonNullable: true, validators: [Validators.maxLength(5000)] }),
    brand: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/\S/), Validators.maxLength(100)] }),
  });
  readonly products = signal<ManagedProduct[] | null>(null);
  readonly categories = signal<string[]>([]);
  readonly selected = signal<ManagedProduct | null>(null);
  readonly loading = signal(true);
  readonly detailLoading = signal(false);
  readonly saving = signal(false);
  readonly stockSaving = signal(false);
  readonly deleting = signal(false);
  readonly error = signal('');
  readonly detailError = signal('');
  readonly actionError = signal('');
  readonly notice = signal('');
  readonly editor = signal<'create' | 'edit' | null>(null);
  readonly total = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly pageSize = 20;
  readonly isAdmin = () => this.auth.currentUser()?.role === 'admin';

  constructor() {
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.categoryControl.valueChanges.pipe(distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.availabilityControl.valueChanges.pipe(distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.load();
  }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true); this.error.set('');
    this.api.list(this.searchControl.value, this.categoryControl.value, this.availabilityControl.value, this.page(), this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: response => {
          this.products.set(response.items); this.categories.set(response.categories); this.total.set(response.total);
          this.totalPages.set(response.total_pages); this.loading.set(false);
          const selected = this.selected();
          const refreshed = selected && response.items.find(item => item.id === selected.id);
          if (refreshed) this.selected.set(refreshed);
          else if (selected && !response.items.some(item => item.id === selected.id)) this.selected.set(null);
        },
        error: error => { this.products.set(null); this.error.set(error.error?.detail || 'Products could not be loaded.'); this.loading.set(false); },
      });
  }

  openProduct(product: ManagedProduct): void {
    this.selected.set(product); this.detailError.set(''); this.detailLoading.set(true); this.stockControl.setValue(product.stock);
    this.api.get(product.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: detail => { this.selected.set(detail); this.stockControl.setValue(detail.stock); this.detailLoading.set(false); },
      error: error => { this.detailError.set(error.error?.detail || 'Product details could not be loaded.'); this.detailLoading.set(false); },
    });
  }

  openEditor(mode: 'create' | 'edit'): void {
    if (!this.isAdmin()) return;
    this.actionError.set(''); this.form.reset({ name: '', category: '', price: 0, unit: '', stock: 0, description: '', brand: '' });
    if (mode === 'edit' && this.selected()) {
      const product = this.selected()!;
      this.form.reset({ name: product.name, category: product.category, price: product.price, unit: product.unit, stock: product.stock, description: product.description, brand: product.brand });
    }
    this.editor.set(mode);
  }

  saveProduct(): void {
    if (!this.isAdmin()) return;
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const value = this.form.getRawValue();
    const payload: ProductInput = {
      name: value.name.trim(), category: value.category.trim(), price: Number(value.price), unit: value.unit.trim(),
      stock: Number(value.stock), description: value.description.trim(), brand: value.brand.trim(),
    };
    this.saving.set(true); this.actionError.set(''); this.notice.set('');
    const request = this.editor() === 'edit' && this.selected()
      ? this.api.update(this.selected()!.id, { name: payload.name, category: payload.category, price: payload.price, unit: payload.unit, description: payload.description, brand: payload.brand })
      : this.api.create(payload);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: product => { this.saving.set(false); this.editor.set(null); this.notice.set(`Product “${product.name}” saved.`); this.selected.set(product); this.load(); },
      error: error => { this.saving.set(false); this.actionError.set(error.error?.detail || 'Product could not be saved.'); },
    });
  }

  saveStock(): void {
    const product = this.selected();
    if (!product || !this.isAdmin()) return;
    if (this.stockControl.invalid) { this.stockControl.markAsTouched(); return; }
    this.stockSaving.set(true); this.actionError.set(''); this.notice.set('');
    this.api.updateStock(product.id, Number(this.stockControl.value)).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: updated => { this.stockSaving.set(false); this.selected.set(updated); this.notice.set(`Stock updated for “${updated.name}”.`); this.load(); },
      error: error => { this.stockSaving.set(false); this.actionError.set(error.error?.detail || 'Stock could not be updated.'); },
    });
  }

  deleteSelected(): void {
    const product = this.selected();
    if (!product || !this.isAdmin() || product.has_order_history || !isPlatformBrowser(this.platformId)) return;
    if (!window.confirm(`Delete “${product.name}” from the catalogue? This cannot be undone.`)) return;
    this.deleting.set(true); this.actionError.set(''); this.notice.set('');
    this.api.delete(product.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => { this.deleting.set(false); this.notice.set(result.message); this.selected.set(null); this.load(); },
      error: error => { this.deleting.set(false); this.actionError.set(error.error?.detail || 'Product could not be deleted.'); },
    });
  }

  changePage(page: number): void { if (page >= 1 && page <= this.totalPages()) { this.page.set(page); this.load(); } }
  formatMoney(price: number): string { return new Intl.NumberFormat('en-NP', { style: 'currency', currency: 'NPR', minimumFractionDigits: 2 }).format(price); }
}
