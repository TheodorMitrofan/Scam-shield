import { Injectable, computed, signal } from '@angular/core';
import { Scenario } from '../models/scenario';
import { byId, parseScenario, scenarioFromText } from './scenario-parser';

// HACK: until backend GET /api/scenarios/validation exists, the validation JSONs are served
// as static assets (angular.json copies Scam_Shield_Public_Kit/validation_set → /validation).
const VALIDATION_IDS = Array.from({ length: 11 }, (_, i) => `V${String(i + 1).padStart(2, '0')}`);

/** Holds the scenarios loaded in the UI. Messages stay in memory only (privacy: nothing is persisted). */
@Injectable({ providedIn: 'root' })
export class ScenarioStore {
  readonly scenarios = signal<Scenario[]>([]);
  readonly selectedId = signal<string | null>(null);
  readonly errors = signal<string[]>([]);
  readonly loading = signal(false);

  readonly selected = computed(
    () => this.scenarios().find((s) => s.id === this.selectedId()) ?? null,
  );

  select(id: string): void {
    this.selectedId.set(id);
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
  }

  async loadValidationSet(): Promise<void> {
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
  }

  addPasted(text: string): void {
    const s = scenarioFromText(text);
    this.scenarios.update((all) => [...all.filter((x) => x.id !== s.id), s].sort(byId));
    this.selectedId.set(s.id);
  }

  clear(): void {
    this.replace([], []);
  }

  private replace(scenarios: Scenario[], errors: string[]): void {
    scenarios.sort(byId);
    this.scenarios.set(scenarios);
    this.errors.set(errors);
    this.selectedId.set(scenarios[0]?.id ?? null);
  }
}
