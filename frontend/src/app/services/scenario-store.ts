import { Injectable, computed, inject, signal } from '@angular/core';
import { AnalysisResult, CHANNEL_LABEL, Channel, Scenario, Verdict } from '../models/scenario';
import { ApiError, ApiService, HealthResponse } from './api.service';
import { byId, parseScenario, scenarioFromText } from './scenario-parser';

// HACK: until backend GET /api/scenarios/validation exists, the validation JSONs are served
// as static assets (angular.json copies Scam_Shield_Public_Kit/validation_set → /validation).
const VALIDATION_IDS = Array.from({ length: 11 }, (_, i) => `V${String(i + 1).padStart(2, '0')}`);

export type ChannelFilter = Channel | 'all';
export type VerdictFilter = Verdict | 'all';

export interface ScenarioGroup {
  label: string;
  items: Scenario[];
}

const VERDICT_GROUP: Record<Verdict, string> = {
  SCAM: 'Țeapă',
  SUSPICIOUS: 'Suspect',
  SAFE: 'Sigur',
};

/** Lowercase + strip diacritics so "mami" matches "Mami" and "tepa" matches "țeapă". */
export function normalize(s: string): string {
  return s.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

/** Holds the scenarios loaded in the UI. Messages stay in memory only (privacy: nothing is persisted). */
@Injectable({ providedIn: 'root' })
export class ScenarioStore {
  private readonly api = inject(ApiService);

  readonly scenarios = signal<Scenario[]>([]);
  readonly selectedId = signal<string | null>(null);
  readonly errors = signal<string[]>([]);
  readonly loading = signal(false);

  /** Detector output per scenario id (from the backend). */
  readonly results = signal<Record<string, AnalysisResult>>({});
  /** Ids currently being analysed (spinner on the card / detail). */
  readonly analyzing = signal<ReadonlySet<string>>(new Set());
  /** Last backend problem, shown as a banner; null when everything works. */
  readonly apiError = signal<string | null>(null);
  readonly health = signal<HealthResponse | null>(null);
  /** Consent checkbox: only when true does the backend store the conversation (?save=true). */
  readonly saveHistory = signal(false);

  // Inbox UI state
  readonly search = signal('');
  readonly channelFilter = signal<ChannelFilter>('all');
  readonly verdictFilter = signal<VerdictFilter>('all');
  readonly readIds = signal<ReadonlySet<string>>(new Set());
  readonly checkedIds = signal<ReadonlySet<string>>(new Set());

  readonly hasResults = computed(() => Object.keys(this.results()).length > 0);

  readonly selected = computed(
    () => this.scenarios().find((s) => s.id === this.selectedId()) ?? null,
  );
  readonly selectedResult = computed(() => {
    const id = this.selectedId();
    return id ? (this.results()[id] ?? null) : null;
  });

  readonly filtered = computed(() => {
    const q = normalize(this.search().trim());
    const ch = this.channelFilter();
    const vf = this.verdictFilter();
    const results = this.results();
    return this.scenarios().filter((s) => {
      if (ch !== 'all' && s.channel !== ch) return false;
      if (vf !== 'all' && results[s.id]?.verdict !== vf) return false;
      if (!q) return true;
      const hay = [s.id, s.sender.name ?? '', s.sender.address ?? '', ...s.messages.map((m) => m.text)];
      return hay.some((h) => normalize(h).includes(q));
    });
  });

  /** Groups by verdict once results exist, otherwise by channel. */
  readonly groups = computed<ScenarioGroup[]>(() => {
    const results = this.results();
    const keyOf = (s: Scenario) =>
      results[s.id] ? VERDICT_GROUP[results[s.id].verdict] : CHANNEL_LABEL[s.channel];
    const map = new Map<string, Scenario[]>();
    for (const s of this.filtered()) {
      const k = keyOf(s);
      map.set(k, [...(map.get(k) ?? []), s]);
    }
    return [...map].map(([label, items]) => ({ label, items }));
  });

  /** 1-based position of the selected scenario in the full list, for "Scenariul 4/11". */
  readonly selectedIndex = computed(() => {
    const id = this.selectedId();
    return id ? this.scenarios().findIndex((s) => s.id === id) + 1 : 0;
  });

  readonly allFilteredChecked = computed(() => {
    const list = this.filtered();
    const checked = this.checkedIds();
    return list.length > 0 && list.every((s) => checked.has(s.id));
  });

  select(id: string): void {
    this.selectedId.set(id);
    this.markRead([id]);
  }

  isRead(id: string): boolean {
    return this.readIds().has(id);
  }

  markRead(ids: Iterable<string>): void {
    this.readIds.update((r) => new Set([...r, ...ids]));
  }

  markUnread(id: string): void {
    this.readIds.update((r) => new Set([...r].filter((x) => x !== id)));
  }

  toggleChecked(id: string, on: boolean): void {
    this.checkedIds.update((c) => {
      const next = new Set(c);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });
  }

  setAllFilteredChecked(on: boolean): void {
    const ids = this.filtered().map((s) => s.id);
    this.checkedIds.update((c) => {
      const next = new Set(c);
      ids.forEach((id) => (on ? next.add(id) : next.delete(id)));
      return next;
    });
  }

  /** Removes scenarios from memory (privacy: the user can drop anything they loaded). */
  remove(ids: Iterable<string>): void {
    const drop = new Set(ids);
    this.scenarios.update((all) => all.filter((s) => !drop.has(s.id)));
    this.checkedIds.update((c) => new Set([...c].filter((x) => !drop.has(x))));
    this.readIds.update((r) => new Set([...r].filter((x) => !drop.has(x))));
    this.results.update((r) => Object.fromEntries(Object.entries(r).filter(([k]) => !drop.has(k))));
    if (this.selectedId() && drop.has(this.selectedId()!)) this.selectedId.set(null);
  }

  /** Accepts any mix of .json files (multi-select or a whole folder). */
  async loadFiles(files: FileList | File[]): Promise<void> {
    const list = Array.from(files).filter((f) => f.name.toLowerCase().endsWith('.json'));
    const errors: string[] = [];
    const parsed: Scenario[] = [];
    await Promise.all(
      list.map(async (f) => {
        try {
          const raw = JSON.parse(await f.text());
          const items = Array.isArray(raw) ? raw : [raw];
          items.forEach((it, i) =>
            parsed.push(parseScenario(it, f.name.replace(/\.json$/i, '') + (i ? `-${i}` : ''))),
          );
        } catch (e) {
          errors.push(`${f.name}: ${e instanceof Error ? e.message : 'nu poate fi citit'}`);
        }
      }),
    );
    if (list.length === 0) errors.push('Nu am găsit niciun fișier .json.');
    this.replace(parsed, errors);
    await this.analyze(parsed);
  }

  async loadValidationSet(): Promise<void> {
    this.loading.set(true);
    try {
      const fromApi = await this.api.validationSet();
      this.replace(fromApi.map((raw, i) => parseScenario(raw, VALIDATION_IDS[i] ?? `V${i + 1}`)), []);
      await this.analyze(this.scenarios());
      return;
    } catch {
      // HACK: backend down → fall back to the static copy so the UI still shows the conversations.
    } finally {
      this.loading.set(false);
    }
    await this.loadValidationSetStatic();
  }

  private async loadValidationSetStatic(): Promise<void> {
    this.loading.set(true);
    const errors: string[] = [];
    const parsed: Scenario[] = [];
    await Promise.all(
      VALIDATION_IDS.map(async (id) => {
        try {
          const res = await fetch(`validation/${id}.json`);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          parsed.push(parseScenario(await res.json(), id));
        } catch (e) {
          errors.push(`${id}: ${e instanceof Error ? e.message : 'eroare'}`);
        }
      }),
    );
    this.replace(parsed, errors);
    this.loading.set(false);
    await this.analyze(parsed);
  }

  /** Next free id for a pasted scenario: PASTE, PASTE-2, PASTE-3… */
  nextPasteId(): string {
    const ids = new Set(this.scenarios().map((s) => s.id));
    if (!ids.has('PASTE')) return 'PASTE';
    let i = 2;
    while (ids.has(`PASTE-${i}`)) i++;
    return `PASTE-${i}`;
  }

  /** Adds a pasted message (plain text) or a scenario built in the paste dialog, and opens it. */
  addPasted(input: string | Scenario): void {
    const s = typeof input === 'string' ? scenarioFromText(input) : input;
    s.id = this.nextPasteId();
    this.scenarios.update((all) => [...all, s].sort(byId));
    this.select(s.id);
    void this.analyze([s]);
  }

  isAnalyzing(id: string): boolean {
    return this.analyzing().has(id);
  }

  async refreshHealth(): Promise<void> {
    try {
      this.health.set(await this.api.health());
    } catch {
      this.health.set(null);
    }
  }

  /** Re-runs the detector on everything loaded (e.g. after the backend comes back). */
  reanalyzeAll(): Promise<void> {
    return this.analyze(this.scenarios());
  }

  /**
   * Sends scenarios to the backend (one batch call) and stores the results by id.
   * If saving was requested but the DB is down (503), retries without saving so the user still
   * gets the analysis.
   */
  async analyze(list: Scenario[]): Promise<void> {
    if (!list.length) return;
    const ids = list.map((s) => s.id);
    this.analyzing.update((a) => new Set([...a, ...ids]));
    const save = this.saveHistory();
    try {
      let responses;
      try {
        responses = await this.api.analyzeBatch(list, save);
      } catch (e) {
        if (!(save && e instanceof ApiError && e.status === 503)) throw e;
        responses = await this.api.analyzeBatch(list, false);
        this.apiError.set('Istoricul nu este disponibil acum; mesajele au fost verificate fără a fi salvate.');
      }
      const loaded = new Set(this.scenarios().map((s) => s.id));
      this.results.update((r) => {
        const next = { ...r };
        for (const { result } of responses) if (loaded.has(result.id)) next[result.id] = result;
        return next;
      });
      if (!save || responses.every((x) => x.saved)) this.apiError.set(null);
    } catch (e) {
      this.apiError.set(e instanceof Error ? e.message : 'Analiza nu a reușit.');
    } finally {
      this.analyzing.update((a) => new Set([...a].filter((x) => !ids.includes(x))));
      void this.refreshHealth();
    }
  }

  clear(): void {
    this.replace([], []);
  }

  private replace(scenarios: Scenario[], errors: string[]): void {
    scenarios.sort(byId);
    this.scenarios.set(scenarios);
    this.errors.set(errors);
    this.results.set({});
    this.readIds.set(new Set());
    this.checkedIds.set(new Set());
    this.selectedId.set(null);
    if (scenarios[0]) this.select(scenarios[0].id);
  }
}
