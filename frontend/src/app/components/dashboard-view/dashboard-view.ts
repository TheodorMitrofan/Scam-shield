import { Component, computed, inject, output } from '@angular/core';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { AnalysisResult, Scenario, Verdict } from '../../models/scenario';
import { TagSeverity, flagLabel, scamTypeLabel } from '../../services/result-utils';
import { ScenarioStore } from '../../services/scenario-store';

interface DashboardRow {
  scenario: Scenario;
  result: AnalysisResult | null;
  analyzing: boolean;
}

const VERDICT_SEVERITY: Record<Verdict, TagSeverity> = {
  SCAM: 'danger',
  SUSPICIOUS: 'warn',
  SAFE: 'success',
};

const VERDICT_ICON: Record<Verdict, string> = {
  SCAM: 'pi pi-times-circle',
  SUSPICIOUS: 'pi pi-exclamation-triangle',
  SAFE: 'pi pi-check-circle',
};

/**
 * Results Dashboard (brief M8): summary counts + ID-sorted table of all loaded scenarios
 * with official columns (ID, Verdict, Scam type, Risk score, First alert, Red flags) and CSV export.
 */
@Component({
  selector: 'app-dashboard-view',
  imports: [ButtonModule, TagModule, TooltipModule],
  templateUrl: './dashboard-view.html',
  styleUrl: './dashboard-view.scss',
})
export class DashboardView {
  protected readonly store = inject(ScenarioStore);
  readonly openScenario = output<string>();

  protected readonly flagLabel = flagLabel;
  protected readonly scamTypeLabel = scamTypeLabel;

  protected readonly rows = computed<DashboardRow[]>(() => {
    const results = this.store.results();
    return this.store.scenarios().map((scenario) => ({
      scenario,
      result: results[scenario.id] ?? null,
      analyzing: this.store.isAnalyzing(scenario.id),
    }));
  });

  protected readonly summary = computed(() => {
    let scam = 0;
    let suspicious = 0;
    let safe = 0;
    let pending = 0;
    for (const r of this.rows()) {
      if (r.analyzing || !r.result) pending++;
      else if (r.result.verdict === 'SCAM') scam++;
      else if (r.result.verdict === 'SUSPICIOUS') suspicious++;
      else safe++;
    }
    return { total: this.rows().length, scam, suspicious, safe, pending };
  });

  protected severityOf(v: Verdict): TagSeverity {
    return VERDICT_SEVERITY[v];
  }

  protected iconOf(v: Verdict): string {
    return VERDICT_ICON[v];
  }

  protected open(id: string): void {
    this.store.select(id);
    this.openScenario.emit(id);
  }

  protected exportCsv(): void {
    const header = 'id,verdict,scam_type,risk_score,first_alert,red_flags';
    const lines = this.rows()
      .filter((r): r is DashboardRow & { result: AnalysisResult } => r.result !== null)
      .map(({ result }) => {
        const firstAlert = result.verdict === 'SAFE' ? '' : (result.first_alert ?? '');
        const flags = result.red_flags.join(';');
        return [
          this.csvCell(result.id),
          this.csvCell(result.verdict),
          this.csvCell(result.scam_type),
          this.csvCell(result.risk_score),
          this.csvCell(firstAlert),
          this.csvCell(flags),
        ].join(',');
      });
    const csv = '\uFEFF' + [header, ...lines].join('\r\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'scam-shield-results.csv';
    a.click();
    URL.revokeObjectURL(url);
  }

  private csvCell(value: string | number | null | undefined): string {
    const s = value == null ? '' : String(value);
    return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s;
  }
}
