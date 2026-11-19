import { Component, ElementRef, computed, inject, model, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TextareaModule } from 'primeng/textarea';
import { TooltipModule } from 'primeng/tooltip';
import { CHANNELS, CHANNEL_LABEL, Channel, Message, Scenario } from '../../models/scenario';
import { scenarioFromConversation } from '../../services/scenario-parser';
import { ScenarioStore } from '../../services/scenario-store';
import { Conversation } from '../conversation/conversation';

type Side = Message['from'];
interface Draft {
  id: number;
  from: Side;
  text: string;
}

const CHANNEL_ICON: Record<Channel, string> = {
  sms: 'pi pi-comment',
  whatsapp: 'pi pi-whatsapp',
  email: 'pi pi-envelope',
  chat: 'pi pi-comments',
  call_transcript: 'pi pi-phone',
};

const other = (s: Side): Side => (s === 'sender' ? 'reader' : 'sender');

/**
 * Paste dialog: pick the app the message came from and type/paste the conversation one message per
 * box. Enter starts the next message from the other person automatically (Shift+Enter = new line),
 * so nobody has to type "eu:" / "tu:". The preview renders it exactly like that app.
 */
@Component({
  selector: 'app-paste-dialog',
  imports: [
    FormsModule,
    DialogModule,
    ButtonModule,
    CheckboxModule,
    InputTextModule,
    SelectButtonModule,
    TextareaModule,
    TooltipModule,
    Conversation,
  ],
  templateUrl: './paste-dialog.html',
  styleUrl: './paste-dialog.scss',
})
export class PasteDialog {
  private readonly store = inject(ScenarioStore);
  private readonly host = inject<ElementRef<HTMLElement>>(ElementRef);
  readonly visible = model(false);

  protected readonly channelOptions = CHANNELS.map((c) => ({
    value: c,
    label: CHANNEL_LABEL[c],
    icon: CHANNEL_ICON[c],
  }));

  protected readonly channel = signal<Channel>('sms');
  protected readonly senderName = signal('');
  protected readonly senderAddress = signal('');
  protected readonly knownContact = signal(false);

  private nextId = 1;
  protected readonly drafts = signal<Draft[]>([this.newDraft('sender')]);

  protected readonly addressLabel = computed(() =>
    this.channel() === 'email' ? 'Adresa de e-mail' : 'Numărul de telefon',
  );
  protected readonly placeholder = computed(() =>
    this.channel() === 'email' ? 'Lipiți e-mailul aici…' : 'Scrieți sau lipiți mesajul…',
  );

  protected readonly preview = computed<Scenario>(() => ({
    id: 'PASTE',
    channel: this.channel(),
    sender: {
      name: this.senderName().trim() || null,
      address: this.senderAddress().trim() || null,
      known_contact: this.knownContact(),
    },
    messages: this.drafts()
      .filter((d) => d.text.trim())
      .map((d, i) => ({ n: i + 1, from: d.from, text: d.text.trim() })),
  }));
  protected readonly count = computed(() => this.preview().messages.length);

  protected sideLabel(from: Side): string {
    return from === 'reader' ? 'Eu' : 'Expeditor';
  }

  protected setText(i: number, text: string): void {
    this.drafts.update((ds) => ds.map((d, k) => (k === i ? { ...d, text } : d)));
  }

  protected toggleSide(i: number): void {
    this.drafts.update((ds) => ds.map((d, k) => (k === i ? { ...d, from: other(d.from) } : d)));
  }

  /** Flip every message (when the whole conversation was typed from the wrong side). */
  protected swapAll(): void {
    this.drafts.update((ds) => ds.map((d) => ({ ...d, from: other(d.from) })));
  }

  protected onEnter(ev: Event, i: number): void {
    const ke = ev as KeyboardEvent;
    if (ke.shiftKey || ke.isComposing) return; // Shift+Enter = new line inside the same message
    ke.preventDefault();
    const cur = this.drafts()[i];
    if (!cur.text.trim()) return;
    const next = this.drafts()[i + 1];
    if (next && !next.text.trim()) {
      this.focus(i + 1);
      return;
    }
    this.drafts.update((ds) => [...ds.slice(0, i + 1), this.newDraft(other(cur.from)), ...ds.slice(i + 1)]);
    this.focus(i + 1);
  }

  protected onBackspace(ev: Event, i: number): void {
    if (i === 0 || this.drafts()[i].text) return;
    ev.preventDefault();
    this.remove(i);
  }

  protected remove(i: number): void {
    if (this.drafts().length === 1) {
      this.setText(0, '');
      return;
    }
    this.drafts.update((ds) => ds.filter((_, k) => k !== i));
    this.focus(Math.max(0, i - 1));
  }

  /** Pasting "exp1: … ⏎ exp2: …" (or Eu:/Tu:) splits it into separate messages automatically. */
  protected onPaste(ev: ClipboardEvent, i: number): void {
    const text = ev.clipboardData?.getData('text/plain') ?? '';
    const parsed = scenarioFromConversation(text, {
      channel: this.channel(),
      senderName: '',
      senderAddress: '',
      knownContact: false,
      swap: false,
    });
    if (parsed.messages.length < 2) return; // a single message: let the browser paste it as-is
    ev.preventDefault();
    if (!this.senderName().trim() && parsed.sender.name) this.senderName.set(parsed.sender.name);
    const pasted = parsed.messages.map((m) => ({ ...this.newDraft(m.from), text: m.text }));
    this.drafts.update((ds) => {
      const keep = ds[i].text.trim() ? ds.slice(0, i + 1) : ds.slice(0, i);
      return [...keep, ...pasted, ...ds.slice(i + 1)];
    });
  }

  protected submit(): void {
    if (!this.count()) return;
    this.store.addPasted(structuredClone(this.preview()));
    this.reset();
    this.visible.set(false);
  }

  private newDraft(from: Side): Draft {
    return { id: this.nextId++, from, text: '' };
  }

  private focus(i: number): void {
    setTimeout(() => {
      const el = this.host.nativeElement.ownerDocument.querySelector<HTMLTextAreaElement>(
        `#paste-msg-${i}`,
      );
      el?.focus();
      el?.setSelectionRange(el.value.length, el.value.length);
    });
  }

  private reset(): void {
    this.drafts.set([this.newDraft('sender')]);
    this.senderName.set('');
    this.senderAddress.set('');
    this.knownContact.set(false);
  }
}
