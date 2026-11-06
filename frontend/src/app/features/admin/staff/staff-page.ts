import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { AuthService } from '../../../core/auth.service';
import { StaffAccount, StaffManagementService, StaffRole } from '../../../services/staff-management.service';

@Component({ standalone: true, imports: [ReactiveFormsModule], templateUrl: './staff-page.html' })
export class StaffPage {
  private readonly api = inject(StaffManagementService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  readonly auth = inject(AuthService);
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly form = new FormGroup({
    username: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.pattern(/^[A-Za-z0-9_.-]{3,50}$/)] }),
    email: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.email, Validators.maxLength(255)] }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.minLength(8), Validators.maxLength(128)] }),
    role: new FormControl<StaffRole>('staff', { nonNullable: true, validators: [Validators.required] }),
  });
  readonly staff = signal<StaffAccount[] | null>(null);
  readonly selected = signal<StaffAccount | null>(null);
  readonly loading = signal(true);
  readonly detailLoading = signal(false);
  readonly saving = signal(false);
  readonly statusSaving = signal(false);
  readonly error = signal('');
  readonly detailError = signal('');
  readonly actionError = signal('');
  readonly notice = signal('');
  readonly editor = signal<'create' | 'edit' | null>(null);
  readonly total = signal(0);
  readonly activeAdminCount = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly pageSize = 20;

  constructor() {
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.load();
  }

  isAdmin(): boolean { return this.auth.currentUser()?.role === 'admin'; }
  isSelf(user: StaffAccount): boolean { return this.auth.currentUser()?.id === user.id; }
  canAssignStaffRole(): boolean {
    const user = this.selected();
    return !user || (!this.isSelf(user) && !user.is_last_active_admin);
  }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true); this.error.set('');
    this.api.list(this.searchControl.value, this.page(), this.pageSize).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        this.staff.set(result.items); this.total.set(result.total); this.activeAdminCount.set(result.active_admin_count);
        this.totalPages.set(result.total_pages); this.loading.set(false);
        const selected = this.selected();
        if (selected) {
          const refreshed = result.items.find(item => item.id === selected.id);
          if (refreshed) this.selected.set(refreshed);
          else this.selected.set(null);
        }
      },
      error: error => { this.staff.set(null); this.error.set(error.error?.detail || 'Staff directory could not be loaded.'); this.loading.set(false); },
    });
  }

  openStaff(user: StaffAccount): void {
    this.selected.set(user); this.detailError.set(''); this.detailLoading.set(true);
    this.api.get(user.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: detail => { this.selected.set(detail); this.detailLoading.set(false); },
      error: error => { this.detailError.set(error.error?.detail || 'Staff details could not be loaded.'); this.detailLoading.set(false); },
    });
  }
  retryDetails(): void { const user = this.selected(); if (user) this.openStaff(user); }

  openEditor(mode: 'create' | 'edit'): void {
    if (!this.isAdmin()) return;
    const selected = this.selected();
    this.form.reset({ username: '', email: '', password: '', role: 'staff' });
    this.form.controls.password.setValidators(mode === 'create'
      ? [Validators.required, Validators.minLength(8), Validators.maxLength(128)]
      : [Validators.minLength(8), Validators.maxLength(128)]);
    this.form.controls.password.updateValueAndValidity({ emitEvent: false });
    if (mode === 'edit' && selected) {
      this.form.patchValue({ username: selected.username, email: selected.email, role: selected.role });
    }
    this.actionError.set(''); this.editor.set(mode);
  }

  save(): void {
    if (!this.isAdmin()) return;
    if (this.form.invalid) { this.form.markAllAsTouched(); return; }
    const selected = this.selected();
    const value = this.form.getRawValue();
    if (this.editor() === 'edit' && selected && this.isSelf(selected) && value.role !== 'admin') {
      this.actionError.set('You cannot demote your own administrator account.'); return;
    }
    this.saving.set(true); this.actionError.set(''); this.notice.set('');
    const request = this.editor() === 'edit' && selected
      ? this.api.update(selected.id, { username: value.username.trim(), email: value.email.trim(), role: value.role })
      : this.api.create({ username: value.username.trim(), email: value.email.trim(), password: value.password });
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        this.saving.set(false); this.editor.set(null); this.selected.set(result.staff);
        this.notice.set(result.message); this.load();
      },
      error: error => { this.saving.set(false); this.actionError.set(error.error?.detail || 'Staff account could not be saved.'); },
    });
  }

  toggleStatus(user: StaffAccount): void {
    if (!this.isAdmin() || this.isSelf(user) || (!user.is_active && user.is_last_active_admin)) return;
    const next = !user.is_active;
    if (!isPlatformBrowser(this.platformId)) return;
    const verb = next ? 'activate' : 'deactivate';
    if (!window.confirm(`Are you sure you want to ${verb} ${user.username}?`)) return;
    this.statusSaving.set(true); this.actionError.set(''); this.notice.set('');
    this.api.setActive(user.id, next).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => { this.statusSaving.set(false); this.selected.set(result.staff); this.notice.set(result.message); this.load(); },
      error: error => { this.statusSaving.set(false); this.actionError.set(error.error?.detail || 'Account status could not be updated.'); },
    });
  }

  changePage(page: number): void { if (page >= 1 && page <= this.totalPages()) { this.page.set(page); this.load(); } }
  formatDate(value: string): string { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)); }
}
