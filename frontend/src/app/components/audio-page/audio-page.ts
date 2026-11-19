import { Component, OnDestroy, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ButtonModule } from 'primeng/button';
import { SelectButtonModule } from 'primeng/selectbutton';
import { TagModule } from 'primeng/tag';
import {
  AudioApiService,
  AuditEngine,
  AuditResult,
  AuditRisk,
  DemoResult,
  DemoScenario,
} from '../../services/audio-api.service';
import { FlightMap } from './flight-map';

const RISK: Record<AuditRisk, { title: string; text: string; icon: string; cls: string }> = {
  high: {
    title: 'Atenție: înregistrarea poate arăta unde vă aflați',
    text: 'Se aud cel puțin două avioane care trec. Din sunetul lor se poate afla locul înregistrării, uneori la câteva sute de metri. Nu trimiteți înregistrarea unor necunoscuți; înregistrați din nou într-un loc liniștit sau tăiați bucățile cu avioane.',
    icon: 'pi pi-exclamation-circle',
    cls: 'high',
  },
  medium: {
    title: 'Se aude un avion în fundal',
    text: 'Un singur avion nu ajunge de obicei pentru a afla locul, dar împreună cu ora înregistrării poate ajunge. Dacă trimiteți mesajul unui necunoscut, mai bine îl înregistrați din nou.',
    icon: 'pi pi-exclamation-triangle',
    cls: 'medium',
  },
  low: {
    title: 'Nu am găsit avioane în fundal',
    text: 'Înregistrarea nu pare să dezvăluie locul prin zgomotul avioanelor. Verificați totuși ce se mai aude: nume, adrese, anunțuri.',
    icon: 'pi pi-check-circle',
    cls: 'low',
  },
  undetermined: {
    title: 'Nu am putut verifica sigur',
    text: 'Înregistrarea e prea scurtă sau prea zgomotoasă pentru o verificare automată.',
    icon: 'pi pi-question-circle',
    cls: 'undetermined',
  },
};

/**
 * "Audio" channel — a side feature, separate from the scam scenarios (not scored by the competition).
 * 1. Privacy check of the user's OWN voice message: does background aircraft noise reveal where it was recorded?
 * 2. Synthetic demo of the full fly-over geolocation method (no real person is located).
 */
@Component({
  selector: 'app-audio-page',
  imports: [FormsModule, ButtonModule, SelectButtonModule, TagModule, FlightMap],
  templateUrl: './audio-page.html',
  styleUrl: './audio-page.scss',
})
export class AudioPage implements OnDestroy {
  private readonly api = inject(AudioApiService);

  // --- audit
  /** Detector engine; switching re-runs the last recording so the two can be compared. */
  protected readonly engine = signal<AuditEngine>('standard');
  protected readonly engines = [
    { label: 'Standard', value: 'standard' },
    { label: 'DOPPLERGEIST', value: 'dopplergeist' },
  ];
  private lastFile: { blob: Blob; name: string } | null = null;
  protected readonly fileName = signal<string | null>(null);
  protected readonly auditBusy = signal(false);
  protected readonly audit = signal<AuditResult | null>(null);
  protected readonly auditError = signal<string | null>(null);
  protected readonly risk = computed(() => {
    const a = this.audit();
    return a ? RISK[a.risk] : null;
  });

  // --- microphone
  protected readonly recording = signal(false);
  protected readonly recSeconds = signal(0);
  private recorder: MediaRecorder | null = null;
  private timer: ReturnType<typeof setInterval> | null = null;

  // --- demo
  protected readonly scenarios: { value: DemoScenario; flag: string; label: string }[] = [
    { value: 'ro', flag: '🇷🇴', label: 'București' },
    { value: 'it', flag: '🇮🇹', label: 'Milano' },
    { value: 'fr', flag: '🇫🇷', label: 'Paris' },
  ];
  protected readonly scenario = signal<DemoScenario>('ro');
  protected readonly demoBusy = signal(false);
  protected readonly demo = signal<DemoResult | null>(null);
  protected readonly demoError = signal<string | null>(null);

  constructor() {
    // Demo link for the pitch: /?view=audio&demo=1 (or demo=it / demo=fr) runs the synthetic demo straight away.
    const d = new URLSearchParams(location.search).get('demo');
    if (d) void this.runDemo((['ro', 'it', 'fr'].includes(d) ? d : 'ro') as DemoScenario);
  }

  /** OpenStreetMap link with a marker (no API key, no tracking parameters). */
  protected mapUrl(lat: number, lon: number): string {
    const la = lat.toFixed(5);
    const lo = lon.toFixed(5);
    return `https://www.openstreetmap.org/?mlat=${la}&mlon=${lo}#map=16/${la}/${lo}`;
  }

  /** Romanian number format: 1.304 (no decimals). */
  protected n(v: number): string {
    return Math.round(v).toLocaleString('ro-RO');
  }

  protected fmtDur(s: number): string {
    const m = Math.floor(s / 60);
    return m ? `${m} min ${Math.round(s % 60)} s` : `${s.toFixed(s < 10 ? 1 : 0)} s`;
  }

  protected onFile(ev: Event): void {
    const input = ev.target as HTMLInputElement;
    const f = input.files?.[0];
    input.value = '';
    if (f) void this.check(f, f.name);
  }

  protected onDrop(ev: DragEvent): void {
    ev.preventDefault();
    ev.stopPropagation(); // the page-level drop loads scenario JSONs; audio is handled here
    const f = ev.dataTransfer?.files[0];
    if (f) void this.check(f, f.name);
  }

  protected async toggleRecording(): Promise<void> {
    if (this.recording()) {
      this.recorder?.stop();
      return;
    }
    this.auditError.set(null);
    let stream: MediaStream;
    try {
      // No noise suppression: we want to hear what the recording really contains.
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { noiseSuppression: false, echoCancellation: false, autoGainControl: false },
      });
    } catch {
      this.auditError.set('Nu am primit acces la microfon.');
      return;
    }
    const chunks: Blob[] = [];
    this.recorder = new MediaRecorder(stream);
    this.recorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    this.recorder.onstop = () => {
      stream.getTracks().forEach((t) => t.stop());
      this.stopTimer();
      this.recording.set(false);
      const type = this.recorder?.mimeType || 'audio/webm';
      const ext = type.includes('mp4') ? 'm4a' : type.includes('ogg') ? 'ogg' : 'webm';
      void this.check(new Blob(chunks, { type }), `microfon.${ext}`);
    };
    this.recorder.start();
    this.recording.set(true);
    this.recSeconds.set(0);
    this.timer = setInterval(() => this.recSeconds.update((s) => s + 1), 1000);
  }

  private async check(blob: Blob, name: string): Promise<void> {
    this.fileName.set(name);
    this.audit.set(null);
    this.auditError.set(null);
    this.auditBusy.set(true);
    try {
      this.lastFile = { blob, name };
      this.audit.set(await this.api.audit(blob, name, this.engine()));
    } catch (e) {
      this.auditError.set(e instanceof Error ? e.message : 'Verificarea nu a reușit.');
    } finally {
      this.auditBusy.set(false);
    }
  }

  protected async setEngine(engine: AuditEngine): Promise<void> {
    this.engine.set(engine);
    if (!this.lastFile || this.auditBusy()) return;
    this.audit.set(null);
    this.auditError.set(null);
    this.auditBusy.set(true);
    try {
      this.audit.set(await this.api.audit(this.lastFile.blob, this.lastFile.name, engine));
    } catch (e) {
      this.auditError.set(e instanceof Error ? e.message : 'Verificarea nu a reușit.');
    } finally {
      this.auditBusy.set(false);
    }
  }

  protected recordingUrl(sc: DemoScenario): string {
    return this.api.recordingUrl(sc);
  }

  protected async runDemo(sc: DemoScenario = this.scenario()): Promise<void> {
    this.scenario.set(sc);
    this.demo.set(null);
    this.demoBusy.set(true);
    this.demoError.set(null);
    try {
      const d = await this.api.demo(sc);
      if (!d.ok) throw new Error(d.reason ?? 'Demonstrația nu a reușit.');
      this.demo.set(d);
    } catch (e) {
      this.demoError.set(e instanceof Error ? e.message : 'Demonstrația nu a reușit.');
    } finally {
      this.demoBusy.set(false);
    }
  }

  private stopTimer(): void {
    if (this.timer) clearInterval(this.timer);
    this.timer = null;
  }

  ngOnDestroy(): void {
    if (this.recording()) this.recorder?.stop();
    this.stopTimer();
  }
}
