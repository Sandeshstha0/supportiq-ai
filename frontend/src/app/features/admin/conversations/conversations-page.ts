import { isPlatformBrowser } from '@angular/common';
import { Component, DestroyRef, inject, PLATFORM_ID, signal } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { debounceTime, distinctUntilChanged } from 'rxjs';
import { ConversationService, StaffConversation, StaffConversationDetails } from '../../../services/conversation.service';

@Component({ standalone: true, imports: [ReactiveFormsModule, RouterLink], templateUrl: './conversations-page.html' })
export class ConversationsPage {
  private readonly api = inject(ConversationService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly platformId = inject(PLATFORM_ID);
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly fromControl = new FormControl('', { nonNullable: true });
  readonly toControl = new FormControl('', { nonNullable: true });
  readonly conversations = signal<StaffConversation[] | null>(null);
  readonly activeConversation = signal<StaffConversation | null>(null);
  readonly selected = signal<StaffConversationDetails | null>(null);
  readonly loading = signal(true);
  readonly detailLoading = signal(false);
  readonly error = signal('');
  readonly detailError = signal('');
  readonly total = signal(0);
  readonly page = signal(1);
  readonly totalPages = signal(0);
  readonly pageSize = 20;

  constructor() {
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => { this.page.set(1); this.load(); });
    this.load();
  }

  load(): void {
    if (!isPlatformBrowser(this.platformId)) return;
    this.loading.set(true); this.error.set('');
    this.api.list(this.searchControl.value, this.fromControl.value, this.toControl.value, this.page(), this.pageSize)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: result => {
          this.conversations.set(result.items); this.total.set(result.total); this.totalPages.set(result.total_pages); this.loading.set(false);
          if (this.selected() && !result.items.some(item => item.id === this.selected()!.id)) this.selected.set(null);
        },
        error: error => {
          this.conversations.set(null); this.error.set(error.error?.detail || 'Conversations could not be loaded. Please retry.'); this.loading.set(false);
        },
      });
  }

  applyFilters(): void { this.page.set(1); this.load(); }
  openConversation(conversation: StaffConversation): void {
    this.activeConversation.set(conversation);
    this.selected.set(null); this.detailError.set(''); this.detailLoading.set(true);
    this.api.get(conversation.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: details => { this.selected.set(details); this.detailLoading.set(false); },
      error: error => { this.detailError.set(error.error?.detail || 'Conversation details could not be loaded.'); this.detailLoading.set(false); },
    });
  }
  retryDetails(): void {
    const row = this.activeConversation();
    if (row) this.openConversation(row);
  }
  changePage(value: number): void { if (value >= 1 && value <= this.totalPages()) { this.page.set(value); this.load(); } }
  formatDateTime(value: string): string {
    return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
  }
}
