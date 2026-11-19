import { Component, inject, output, signal } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TooltipModule } from 'primeng/tooltip';
import { ScenarioStore } from '../../services/scenario-store';

/** Header: brand on the left, theme toggle + load actions on the right. */
@Component({
  selector: 'app-top-bar',
  imports: [ButtonModule, TooltipModule],
  templateUrl: './top-bar.html',
  styleUrl: './top-bar.scss',
})
export class TopBar {
  protected readonly store = inject(ScenarioStore);
  readonly paste = output<void>();
  protected readonly dark = signal(false);

  constructor() {
    // ?theme=dark|light wins (demo links), then the remembered choice.
    const fromUrl = new URLSearchParams(location.search).get('theme');
    let saved: string | null = null;
    try {
      saved = localStorage.getItem('theme');
    } catch {
      /* storage blocked: default to light */
    }
    this.apply((fromUrl ?? saved) === 'dark');
  }

  protected toggleTheme(): void {
    this.apply(!this.dark());
    try {
      localStorage.setItem('theme', this.dark() ? 'dark' : 'light');
    } catch {
      /* storage blocked: theme just won't be remembered */
    }
  }

  private apply(on: boolean): void {
    document.documentElement.classList.toggle('app-dark', on);
    this.dark.set(on);
  }

  protected onFiles(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    if (input.files?.length) void this.store.loadFiles(input.files);
    input.value = '';
  }
}
