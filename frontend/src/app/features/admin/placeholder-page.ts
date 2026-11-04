import { Component, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';

interface SectionInfo {
  title: string;
  description: string;
  availability: string;
  endpoints: string;
}

@Component({
  standalone: true,
  template: `
    <div class="mx-auto w-full max-w-5xl p-4 sm:p-6 lg:p-8">
      <p class="mb-2 text-[11px] font-semibold uppercase tracking-[.18em] text-sky-300">Workspace section</p>
      <h2 class="text-2xl font-semibold tracking-tight text-white">{{ section.title }}</h2>
      <p class="mt-2 max-w-2xl text-sm leading-6 text-slate-400">{{ section.description }}</p>
      <section class="mt-8 rounded-2xl border border-white/[0.075] bg-[#101b2a] p-5 sm:p-7">
        <div class="flex items-start gap-4">
          <span class="grid h-11 w-11 shrink-0 place-items-center rounded-xl border border-amber-300/15 bg-amber-300/[0.07] text-amber-200"><svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7"><circle cx="12" cy="12" r="9"/><path d="M12 11v5m0-8h.01"/></svg></span>
          <div><p class="text-sm font-semibold text-slate-200">{{ section.availability }}</p><p class="mt-2 text-xs leading-5 text-slate-500">{{ section.endpoints }}</p></div>
        </div>
      </section>
    </div>
  `,
})
export class PlaceholderPage {
  private readonly route = inject(ActivatedRoute);
  readonly section = this.route.snapshot.data['section'] as SectionInfo;
}
