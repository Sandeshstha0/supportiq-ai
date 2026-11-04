import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { AuthService } from '../../../core/auth.service';
import { KnowledgeBaseService, KnowledgeDocument, KnowledgeDocumentDetails } from '../../../services/knowledge-base.service';

@Component({ standalone: true, imports: [ReactiveFormsModule], templateUrl: './knowledge-base-page.html' })
export class KnowledgeBasePage {
  private readonly api = inject(KnowledgeBaseService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  readonly auth = inject(AuthService);
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly documents = signal<KnowledgeDocument[] | null>(null);
  readonly selected = signal<KnowledgeDocumentDetails | null>(null);
  readonly selectedSummary = signal<KnowledgeDocument | null>(null);
  readonly loading = signal(true);
  readonly detailLoading = signal(false);
  readonly mutationLoading = signal(false);
  readonly error = signal('');
  readonly detailError = signal('');
  readonly mutationError = signal('');
  readonly notice = signal('');
  readonly total = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly pageSize = 20;
  readonly isAdmin = () => this.auth.currentUser()?.role === 'admin';

  constructor() {
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.load();
  }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true); this.error.set('');
    this.api.list(this.searchControl.value, this.page(), this.pageSize).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: response => {
        this.documents.set(response.items); this.total.set(response.total); this.totalPages.set(response.total_pages); this.loading.set(false);
        if (this.selectedSummary() && !response.items.some(item => item.id === this.selectedSummary()!.id)) {
          this.selected.set(null); this.selectedSummary.set(null);
        }
      },
      error: error => { this.documents.set(null); this.error.set(error.error?.detail || 'Knowledge documents could not be loaded.'); this.loading.set(false); },
    });
  }

  openDocument(document: KnowledgeDocument): void {
    this.selected.set(null); this.selectedSummary.set(document); this.detailError.set(''); this.detailLoading.set(true);
    this.api.get(document.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: detail => { this.selected.set(detail); this.detailLoading.set(false); },
      error: error => { this.detailError.set(error.error?.detail || 'Document details could not be loaded.'); this.detailLoading.set(false); },
    });
  }

  retryDetails(): void { const item = this.selectedSummary(); if (item) this.openDocument(item); }
  changePage(page: number): void { if (page >= 1 && page <= this.totalPages()) { this.page.set(page); this.load(); } }

  handleUpload(event: Event, replace = false): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0]; input.value = '';
    if (!file) return;
    const issue = this.validateFile(file);
    if (issue) { this.mutationError.set(issue); return; }
    const current = this.selectedSummary();
    if (replace && (!current || current.legacy)) return;
    this.mutationLoading.set(true); this.mutationError.set(''); this.notice.set('');
    const request = replace && current ? this.api.replace(current.id, file) : this.api.upload(file);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        this.mutationLoading.set(false); this.notice.set(`${result.filename || result.title} indexed successfully (${result.chunks_stored} chunks).`);
        this.page.set(1); this.load();
        const updated: KnowledgeDocument = {
          id: result.document_id, title: result.title, source: result.source, filename: result.filename,
          created_at: result.created_at, indexing_status: result.indexing_status, legacy: false,
          chunk_count: result.chunks_stored, preview: '',
        };
        this.openDocument(updated);
      },
      error: error => { this.mutationLoading.set(false); this.mutationError.set(error.error?.detail || 'Upload or indexing failed. The index was not confirmed.'); },
    });
  }

  deleteSelected(): void {
    const document = this.selectedSummary();
    if (!document || document.legacy || !this.isAdmin() || !isPlatformBrowser(this.platformId)) return;
    if (!window.confirm(`Delete “${document.title}” and its indexed vectors? This cannot be undone.`)) return;
    this.mutationLoading.set(true); this.mutationError.set(''); this.notice.set('');
    this.api.delete(document.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: result => {
        this.mutationLoading.set(false); this.notice.set(result.message); this.selected.set(null); this.selectedSummary.set(null); this.load();
      },
      error: error => { this.mutationLoading.set(false); this.mutationError.set(error.error?.detail || 'Document vectors could not be deleted.'); },
    });
  }

  formatDate(value: string | null): string {
    if (!value) return 'Date not recorded';
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }

  private validateFile(file: File): string {
    if (!file.name.toLowerCase().endsWith('.txt')) return 'Only UTF-8 .txt documents are supported.';
    if (file.size > 1024 * 1024) return 'This file exceeds the 1 MiB upload limit.';
    if (!file.size) return 'The selected text file is empty.';
    return '';
  }
}
