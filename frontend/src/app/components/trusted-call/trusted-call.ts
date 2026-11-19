import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { UiLang } from '../../services/ui-lang';

interface TrustedContact {
  name: string;
  phone: string;
}

const STORAGE_KEY = 'scamshield-trusted-contact';

/**
 * HACK (hackathon demo): pre-filled trusted contact so the jury can press the button once and see it ring.
 * It is the team member's own number, used with his consent. The user can still change it ("Schimbă persoana").
 * Remove after the demo.
 */
const DEMO_CONTACT: TrustedContact = { name: 'Theodor', phone: '0760 042 470' };

/**
 * „Sunați pe cineva de încredere” (brief nice-to-have). One big button that opens the phone's dialer
 * (tel: link) for a person the USER chose. The number is typed by the user and kept only in this
 * browser — never a number taken from the suspicious message.
 */
@Component({
  selector: 'app-trusted-call',
  imports: [FormsModule, ButtonModule, InputTextModule],
  template: `
    @if (contact(); as c) {
      @if (!editing()) {
        <div class="row">
          <a class="call" [href]="telHref(c.phone)">
            <i class="pi pi-phone" aria-hidden="true"></i>
            <span>{{ lang.t('callName') }} {{ c.name }}</span>
          </a>
          <button type="button" class="link" (click)="startEdit()">{{ lang.t('change') }}</button>
        </div>
        <p class="hint">{{ lang.t('trustedHint') }}</p>
      }
    } @else if (!editing()) {
      <button type="button" class="call" (click)="startEdit()">
        <i class="pi pi-phone" aria-hidden="true"></i>
        <span>{{ lang.t('callTrusted') }}</span>
      </button>
      <p class="hint">{{ lang.t('trustedHint') }}</p>
    }

    @if (editing()) {
      <form class="form" (ngSubmit)="save()">
        <label>
          <span>{{ lang.t('trustedName') }}</span>
          <input pInputText name="name" [(ngModel)]="name" autocomplete="off" required />
        </label>
        <label>
          <span>{{ lang.t('trustedPhone') }}</span>
          <input pInputText name="phone" type="tel" inputmode="tel" [(ngModel)]="phone" autocomplete="tel" required />
        </label>
        @if (error()) {
          <p class="err" role="alert">{{ error() }}</p>
        }
        <div class="btns">
          <p-button type="submit" [label]="lang.t('save')" icon="pi pi-check" size="large" />
          <p-button [label]="lang.t('cancel')" severity="secondary" [text]="true" (onClick)="editing.set(false)" />
        </div>
      </form>
    }
  `,
  styles: `
    :host { display: block; margin: 0 0 18px; }
    .row { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; }
    .call {
      display: inline-flex; align-items: center; gap: 12px; min-height: 56px; padding: 12px 22px;
      border-radius: 14px; border: none; cursor: pointer; text-decoration: none;
      background: var(--p-green-600); color: #fff; font: inherit; font-size: 20px; font-weight: 700;
      i { font-size: 22px; }
      &:hover { background: var(--p-green-700); }
      &:focus-visible { outline: 3px solid var(--p-green-800); outline-offset: 2px; }
    }
    .link {
      border: none; background: none; padding: 4px; cursor: pointer; font: inherit; font-size: 18px;
      color: var(--app-accent); text-decoration: underline;
    }
    .hint { margin: 8px 0 0; font-size: 18px; line-height: 1.45; color: var(--app-muted); }
    .form {
      display: grid; gap: 12px; padding: 14px; border-radius: 12px;
      border: 1px solid var(--app-border); background: var(--app-hover);
      label { display: grid; gap: 6px; font-size: 18px; font-weight: 600; }
      input { font-size: 18px; width: 100%; }
    }
    .btns { display: flex; flex-wrap: wrap; gap: 8px; }
    .err { margin: 0; font-size: 18px; color: var(--p-red-600); }
  `,
})
export class TrustedCall {
  protected readonly lang = inject(UiLang);
  protected readonly contact = signal<TrustedContact | null>(TrustedCall.load());
  protected readonly editing = signal(false);
  protected readonly error = signal<string | null>(null);
  protected name = '';
  protected phone = '';

  private static load(): TrustedContact | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      const c = raw ? JSON.parse(raw) : null;
      return c && typeof c.name === 'string' && typeof c.phone === 'string' ? c : DEMO_CONTACT;
    } catch {
      return DEMO_CONTACT;
    }
  }

  /** tel: link with only digits and a leading +, so any spacing the user typed still dials. */
  protected telHref(phone: string): string {
    return 'tel:' + phone.replace(/(?!^\+)[^\d]/g, '');
  }

  protected startEdit(): void {
    const c = this.contact();
    this.name = c?.name ?? '';
    this.phone = c?.phone ?? '';
    this.error.set(null);
    this.editing.set(true);
  }

  protected save(): void {
    const name = this.name.trim();
    const phone = this.phone.trim();
    const digits = phone.replace(/\D/g, '');
    if (!name || digits.length < 6 || digits.length > 15 || !/^\+?[\d\s().-]+$/.test(phone)) {
      this.error.set(this.lang.t('badPhone'));
      return;
    }
    const c = { name, phone };
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(c));
    } catch {
      /* storage blocked: works for this session only */
    }
    this.contact.set(c);
    this.editing.set(false);
  }
}
