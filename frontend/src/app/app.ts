import { Component, inject, signal } from '@angular/core';
import { AudioPage } from './components/audio-page/audio-page';
import { DashboardView } from './components/dashboard-view/dashboard-view';
import { InboxList } from './components/inbox-list/inbox-list';
import { PasteDialog } from './components/paste-dialog/paste-dialog';
import { ScenarioDetail } from './components/scenario-detail/scenario-detail';
import { TopBar } from './components/top-bar/top-bar';
import { ScenarioStore } from './services/scenario-store';

@Component({
  selector: 'app-root',
  imports: [TopBar, InboxList, DashboardView, ScenarioDetail, PasteDialog, AudioPage],
  templateUrl: './app.html',
  styleUrl: './app.scss',
  host: {
    '(dragover)': '$event.preventDefault()',
    '(drop)': 'onDrop($event)',
  },
})
export class App {
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
    // Demo shortcut: /?load=validation&id=V04 opens the validation set directly.
    const q = new URLSearchParams(location.search);
    if (q.get('load') === 'validation') {
      void this.store
        .loadValidationSet()
        .then(() => q.get('id') && this.store.select(q.get('id')!));
    }
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
