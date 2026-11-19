import { Component, effect, inject, input, model, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { CheckboxModule } from 'primeng/checkbox';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { MessageModule } from 'primeng/message';
import { TextareaModule } from 'primeng/textarea';
import { FraudReportDraft, PersonalData, PersonalField } from '../../models/report';
import { AnalysisResult, Scenario } from '../../models/scenario';
import { ApiError, ApiService } from '../../services/api.service';

const EMPTY: PersonalData = {
  last_name: null,
  first_name: null,
  cnp: null,
  id_series_number: null,
  address: null,
  phone: null,
  email: null,
  incident_date: null,
  lost_money: false,
  amount_lost: null,
  bank: null,
  additional_details: null,
};

const KIND_LABEL: Record<string, string> = {
  url: 'Adresă de internet',
  email: 'Adresă de e-mail',
  phone: 'Telefon',
  iban: 'Cont (IBAN)',
  amount: 'Sumă',
};

/**
 * „Raportează frauda” (risk ≥ 50): the backend generates what happened; the user fills in only their
 * personal data, can download the „Sesizare” PDF, and sends it by e-mail (demo inbox, never authorities).
 * Personal data lives only in this dialog's memory and is cleared when it closes.
 */
@Component({
  selector: 'app-report-dialog',
  imports: [
    FormsModule,
    DialogModule,
    ButtonModule,
    CheckboxModule,
    InputTextModule,
    MessageModule,
    TextareaModule,
  ],
  templateUrl: './report-dialog.html',
  styleUrl: './report-dialog.scss',
})
export class ReportDialog {
  private readonly api = inject(ApiService);

  readonly visible = model(false);
  readonly scenario = input<Scenario | null>(null);
  readonly result = input<AnalysisResult | null>(null);

  protected readonly draft = signal<FraudReportDraft | null>(null);
  protected readonly person = signal<PersonalData>({ ...EMPTY });
  protected readonly loading = signal(false);
  protected readonly busy = signal<'pdf' | 'send' | null>(null);
  protected readonly error = signal<string | null>(null);
  protected readonly sentTo = signal<string | null>(null);
  protected readonly kindLabel = KIND_LABEL;

  constructor() {
    // (Re)generate the report every time the dialog opens; forget personal data when it closes.
    effect(() => {
      const open = this.visible();
      untracked(() => (open ? void this.load() : this.reset()));
    });
  }

  protected value(f: PersonalField): unknown {
    return this.person()[f.key];
  }

  protected set(f: PersonalField, v: unknown): void {
    let val: unknown = v;
    if (f.type === 'number') val = v === '' || v === null ? null : Number(v);
    else if (typeof v === 'string' && f.type !== 'checkbox') val = v.trim() === '' ? null : v;
    this.person.update((p) => ({ ...p, [f.key]: val }));
  }

  protected async downloadPdf(): Promise<void> {
    const d = this.draft();
    if (!d) return;
    this.busy.set('pdf');
    this.error.set(null);
    try {
      const blob = await this.api.reportPdf(d, this.person());
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sesizare-${d.incident.scenario_id}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
    } catch (e) {
      this.error.set(this.message(e));
    } finally {
      this.busy.set(null);
    }
  }

  protected async send(): Promise<void> {
    const d = this.draft();
    if (!d) return;
    this.busy.set('send');
    this.error.set(null);
    try {
      const r = await this.api.reportSend(d, this.person());
      this.sentTo.set(r.recipient);
    } catch (e) {
      this.error.set(this.message(e));
    } finally {
      this.busy.set(null);
    }
  }

  private async load(): Promise<void> {
    const scenario = this.scenario();
    if (!scenario) return;
    this.reset();
    this.loading.set(true);
    try {
      this.draft.set(await this.api.reportDraft({ scenario, result: this.result() }));
    } catch (e) {
      this.error.set(this.message(e));
    } finally {
      this.loading.set(false);
    }
  }

  private reset(): void {
    this.draft.set(null);
    this.person.set({ ...EMPTY });
    this.error.set(null);
    this.sentTo.set(null);
    this.busy.set(null);
  }

  private message(e: unknown): string {
    return e instanceof ApiError ? e.message : 'A apărut o eroare. Încercați din nou.';
  }
}
