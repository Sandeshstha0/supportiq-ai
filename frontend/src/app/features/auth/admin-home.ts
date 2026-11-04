import { Component, inject } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';

@Component({
  standalone: true,
  template: `
    <main class="flex min-h-dvh items-center justify-center bg-[#080F1D] px-5 text-slate-100">
      <section class="w-full max-w-xl rounded-3xl border border-white/10 bg-[#101b2a] p-8 shadow-2xl sm:p-10">
        <div class="mb-7 flex items-center justify-between gap-4">
          <div class="flex items-center gap-3"><span class="grid h-11 w-11 place-items-center rounded-xl bg-sky-400 text-xl font-extrabold text-[#071321]">S</span><div><p class="font-semibold">SupportIQ AI</p><p class="text-xs text-slate-500">Staff access confirmed</p></div></div>
          <span class="rounded-full border border-sky-300/20 bg-sky-300/10 px-3 py-1 text-xs font-medium capitalize text-sky-200">{{ auth.currentUser()?.role }}</span>
        </div>
        <h1 class="text-2xl font-semibold">Welcome, {{ auth.currentUser()?.username }}.</h1>
        <p class="mt-3 leading-6 text-slate-400">Your staff sign-in is active. The admin dashboard will be added in the next phase.</p>
        <div class="mt-7 rounded-xl border border-white/[0.07] bg-[#080f1d]/70 p-4 text-sm"><p class="text-slate-500">Signed in as</p><p class="mt-1 text-slate-200">{{ auth.currentUser()?.email }}</p></div>
        <button class="mt-7 rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:border-rose-300/30 hover:bg-rose-300/[0.06] hover:text-rose-200" (click)="logout()">Sign out</button>
      </section>
    </main>
  `,
})
export class AdminHome {
  readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  logout(): void {
    this.auth.logout();
    void this.router.navigate(['/admin/login']);
  }
}
