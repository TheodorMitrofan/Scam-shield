import { Component, inject, signal } from '@angular/core';
import { AudioPage } from './components/audio-page/audio-page';
import { DashboardView } from './components/dashboard-view/dashboard-view';
import { InboxList } from './components/inbox-list/inbox-list';
import { LoginView } from './components/login-view/login-view';
import { PasteDialog } from './components/paste-dialog/paste-dialog';
import { ScenarioDetail } from './components/scenario-detail/scenario-detail';
import { TopBar } from './components/top-bar/top-bar';
import { AuthService } from './services/auth.service';
import { ScenarioStore } from './services/scenario-store';

@Component({
  selector: 'app-root',
  imports: [TopBar, InboxList, DashboardView, ScenarioDetail, PasteDialog, AudioPage, LoginView],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  host: {
    '(dragover)': '$event.preventDefault()',
    '(drop)': 'onDrop($event)',
  },
})
export class App {
  protected readonly auth = inject(AuthService);
  protected readonly store = inject(ScenarioStore);
  protected readonly pasteOpen = signal(false);
  /** Mobile only: whether the detail panel replaces the list. */
  protected readonly showDetail = signal(false);
  /** ?view=audio|dashboard opens that view directly (demo links). */
  protected readonly view = signal<'messages' | 'dashboard' | 'audio'>(
    (() => {
      const v = new URLSearchParams(location.search).get('view');
      return v === 'audio' ? 'audio' : v === 'dashboard' ? 'dashboard' : 'messages';
    })(),
  );

  constructor() {
    if (this.auth.isLoggedIn()) {
      void this.onAuthenticated();
    }
  }

  protected async onAuthenticated(): Promise<void> {
    this.showDetail.set(false);
    await this.store.loadTenantHistory();
    const q = new URLSearchParams(location.search);
    if (q.get('load') === 'validation' && this.auth.isAdmin()) {
      await this.store.loadValidationSet();
      if (q.get('id')) this.store.select(q.get('id')!);
    } else if (q.get('id')) {
      this.store.select(q.get('id')!);
    }
  }

  protected onLogout(): void {
    this.auth.logout();
    this.store.clear();
    this.showDetail.set(false);
    this.view.set('messages');
  }

  protected openFromDashboard(): void {
    this.showDetail.set(true);
    this.view.set('messages');
  }

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    if (this.view() === 'audio') return;
    if (ev.dataTransfer?.files.length) void this.store.loadFiles(ev.dataTransfer.files);
  }
}
