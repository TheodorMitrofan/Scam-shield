import { Component, inject, signal } from '@angular/core';
import { AudioPage } from './components/audio-page/audio-page';
import { InboxList } from './components/inbox-list/inbox-list';
import { PasteDialog } from './components/paste-dialog/paste-dialog';
import { ScenarioDetail } from './components/scenario-detail/scenario-detail';
import { TopBar } from './components/top-bar/top-bar';
import { ScenarioStore } from './services/scenario-store';

@Component({
  selector: 'app-root',
  imports: [TopBar, InboxList, ScenarioDetail, PasteDialog, AudioPage],
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
  /** ?view=audio opens the audio side feature directly (demo links). */
  protected readonly view = signal<'messages' | 'audio'>(
    new URLSearchParams(location.search).get('view') === 'audio' ? 'audio' : 'messages',
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

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    if (this.view() !== 'messages') return;
    if (ev.dataTransfer?.files.length) void this.store.loadFiles(ev.dataTransfer.files);
  }
}
