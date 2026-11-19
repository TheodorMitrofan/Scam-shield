import { Component, inject, signal } from '@angular/core';
import { Conversation } from './components/conversation/conversation';
import { ScenarioList } from './components/scenario-list/scenario-list';
import { CHANNEL_LABEL } from './models/scenario';
import { ScenarioStore } from './services/scenario-store';

@Component({
  selector: 'app-root',
  imports: [Conversation, ScenarioList],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly store = inject(ScenarioStore);
  protected readonly label = CHANNEL_LABEL;
  protected readonly pasted = signal('');

  constructor() {
    // Demo shortcut: /?load=validation&id=V04 opens the validation set directly.
    const q = new URLSearchParams(location.search);
    if (q.get('load') === 'validation') {
      void this.store
        .loadValidationSet()
        .then(() => q.get('id') && this.store.select(q.get('id')!));
    }
  }

  protected onFiles(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    if (input.files?.length) void this.store.loadFiles(input.files);
    input.value = '';
  }

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    if (ev.dataTransfer?.files.length) void this.store.loadFiles(ev.dataTransfer.files);
  }

  protected addPasted(): void {
    const t = this.pasted().trim();
    if (t) this.store.addPasted(t);
  }
}
