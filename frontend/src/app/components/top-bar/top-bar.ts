import { Component, computed, inject, model, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { SelectButtonModule } from 'primeng/selectbutton';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { TooltipModule } from 'primeng/tooltip';
import { ScenarioStore } from '../../services/scenario-store';
import { UiLang } from '../../services/ui-lang';

/** Header: brand on the left; backend status, consent switch, theme toggle and load actions on the right. */
@Component({
  selector: 'app-top-bar',
  imports: [FormsModule, ButtonModule, SelectButtonModule, ToggleSwitchModule, TooltipModule],
  templateUrl: './top-bar.html',
  styleUrl: './top-bar.scss',
})
export class TopBar {
  protected readonly store = inject(ScenarioStore);
  protected readonly lang = inject(UiLang);
  protected readonly langs = [
    { label: 'RO', value: 'ro' },
    { label: 'EN', value: 'en' },
  ];
  readonly paste = output<void>();
  /** Which part of the app is shown: the scam-check inbox, the results dashboard, or the audio feature. */
  readonly view = model<'messages' | 'dashboard' | 'audio'>('messages');
  protected readonly views = [
    { label: 'Mesaje', value: 'messages', icon: 'pi pi-inbox' },
    { label: 'Dashboard', value: 'dashboard', icon: 'pi pi-table' },
    { label: 'Audio', value: 'audio', icon: 'pi pi-volume-up' },
  ];
  protected readonly dark = signal(false);

  protected readonly status = computed(() => {
    const h = this.store.health();
    if (!h) {
      return { kind: 'off', label: 'Server oprit', hint: 'Backend-ul nu răspunde pe portul 8000. Apăsați ca să reîncercați.' };
    }
    if (h.detector_stub) {
      return { kind: 'stub', label: 'Detector demo', hint: 'Backend pornit, dar detectorul real nu e instalat încă (răspunde mereu „Sigur”).' };
    }
    return { kind: 'on', label: 'Detector activ', hint: h.db_connected ? 'Totul funcționează.' : 'Detector activ; istoricul (baza de date) nu e disponibil.' };
  });

  protected async recheck(): Promise<void> {
    await this.store.refreshHealth();
    if (this.store.health()) void this.store.reanalyzeAll();
  }

  constructor() {
    void this.store.refreshHealth();
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
