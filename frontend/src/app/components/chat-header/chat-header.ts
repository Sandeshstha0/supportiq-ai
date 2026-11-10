
import {
  Component,
  Inject,
  OnInit,
  OnDestroy,
  PLATFORM_ID,
  ChangeDetectorRef,
} from '@angular/core';

import { isPlatformBrowser, NgClass } from '@angular/common';

type BackendStatus = 'checking' | 'online' | 'offline';

@Component({
  selector: 'app-chat-header',
  standalone: true,
  imports: [NgClass],
  templateUrl: './chat-header.html',
  styleUrl: './chat-header.scss'
})
export class ChatHeader implements OnInit, OnDestroy {
  backendStatus: BackendStatus = 'checking';

  private checkInterval?: ReturnType<typeof setInterval>;
  private isChecking = false;

  private readonly healthUrl =
    'https://supportiq-ai-1-r0du.onrender.com/';

  constructor(
    @Inject(PLATFORM_ID) private platformId: Object,
    private cdr: ChangeDetectorRef
  ) {}

  ngOnInit(): void {
    if (!isPlatformBrowser(this.platformId)) return;

    this.checkBackend();

    this.checkInterval = setInterval(() => {
      this.checkBackend();
    }, 30000);
  }

  async checkBackend(): Promise<void> {
    if (this.isChecking) return;

    this.isChecking = true;
    this.backendStatus = 'checking';
    this.cdr.detectChanges();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);

    try {
      const response = await fetch(this.healthUrl, {
        method: 'GET',
        cache: 'no-store',
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Backend returned ${response.status}`);
      }

      this.backendStatus = 'online';

    } catch (error) {
      console.error('Backend status check failed:', error);
      this.backendStatus = 'offline';

    } finally {
      clearTimeout(timeout);
      this.isChecking = false;
      this.cdr.detectChanges();
    }
  }

  ngOnDestroy(): void {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
    }
  }
}
