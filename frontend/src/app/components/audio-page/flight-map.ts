import { Component, computed, input } from '@angular/core';
import { DemoResult } from '../../services/audio-api.service';

const W = 640;
const H = 520;

/** Offline SVG map (no tiles): flight tracks, the two matched aircraft, true vs estimated position. */
@Component({
  selector: 'app-flight-map',
  template: `
    <svg [attr.viewBox]="'0 0 ' + w + ' ' + h" role="img" [attr.aria-label]="label()">
      <defs><clipPath [attr.id]="clipId"><rect [attr.width]="w" [attr.height]="h" /></clipPath></defs>
      <g [attr.clip-path]="'url(#' + clipId + ')'">
      <rect [attr.width]="w" [attr.height]="h" class="bg" />
      @for (f of paths().others; track f.id) {
        <polyline [attr.points]="f.d" [class]="f.prop ? 'trk prop' : 'trk jet'" />
      }
      @for (f of paths().matched; track f.id) {
        <polyline [attr.points]="f.d" class="trk matched" />
      }
      <circle [attr.cx]="est().x" [attr.cy]="est().y" [attr.r]="regionR()" class="region" />
      <circle [attr.cx]="truth().x" [attr.cy]="truth().y" r="9" class="truth" />
      <g [attr.transform]="'translate(' + est().x + ',' + est().y + ')'" class="est">
        <line x1="-9" y1="-9" x2="9" y2="9" /><line x1="-9" y1="9" x2="9" y2="-9" />
      </g>
      </g>
      <g [attr.transform]="'translate(16,' + (h - 18) + ')'" class="scale">
        <line x1="0" y1="0" [attr.x2]="scale().px" y2="0" />
        <text x="0" y="-6">{{ scale().label }}</text>
      </g>
    </svg>
  `,
  styles: `
    :host { display: block; }
    svg { width: 100%; height: auto; display: block; border-radius: 12px; border: 1px solid var(--app-border); }
    .bg { fill: var(--app-hover); }
    .trk { fill: none; stroke-linejoin: round; stroke-linecap: round; }
    .trk.jet { stroke: var(--app-border); stroke-width: 1; }
    .trk.prop { stroke: var(--app-muted); stroke-width: 1.2; opacity: 0.55; }
    .trk.matched { stroke: var(--p-primary-500); stroke-width: 3.5; }
    .region { fill: color-mix(in srgb, var(--p-red-500) 15%, transparent); stroke: var(--p-red-500); stroke-dasharray: 4 3; }
    .truth { fill: var(--p-green-500); stroke: #fff; stroke-width: 2.5; }
    .est line { stroke: var(--p-red-600); stroke-width: 4; stroke-linecap: round; }
    .scale line { stroke: var(--app-text); stroke-width: 3; }
    .scale text { fill: var(--app-text); font-size: 13px; }
  `,
})
export class FlightMap {
  readonly data = input.required<DemoResult>();
  /** When set, the map is a square of ±zoomM metres around the estimate instead of the whole area. */
  readonly zoomM = input<number | null>(null);
  protected readonly clipId = 'clip-' + Math.random().toString(36).slice(2, 8);
  protected readonly w = W;
  protected readonly h = H;

  /** Equirectangular projection fitted to the bbox (fine at this ~70 km scale). */
  private readonly proj = computed(() => {
    const z = this.zoomM();
    const e = this.data().estimate;
    const dLat = z ? z / 111_320 : 0;
    const dLon = z ? z / (111_320 * Math.cos((e.lat * Math.PI) / 180)) : 0;
    const [latMin, latMax, lonMin, lonMax] = z
      ? [e.lat - dLat, e.lat + dLat, e.lon - dLon * (W / H), e.lon + dLon * (W / H)]
      : this.data().bbox;
    const k = Math.cos((((latMin + latMax) / 2) * Math.PI) / 180);
    const spanX = (lonMax - lonMin) * k;
    const spanY = latMax - latMin;
    const s = Math.min((W - 20) / spanX, (H - 20) / spanY);
    const ox = (W - spanX * s) / 2;
    const oy = (H - spanY * s) / 2;
    const mPerPx = (spanY * 111_320) / (spanY * s);
    return {
      mPerPx,
      xy: (lat: number, lon: number) => ({ x: ox + (lon - lonMin) * k * s, y: H - (oy + (lat - latMin) * s) }),
    };
  });

  protected readonly paths = computed(() => {
    const { xy } = this.proj();
    const toD = (pts: [number, number][]) =>
      pts.map(([la, lo]) => xy(la, lo)).map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    const fl = this.data().flights.map((f) => ({ id: f.id, prop: f.prop, matched: f.matched, d: toD(f.points) }));
    return { others: fl.filter((f) => !f.matched), matched: fl.filter((f) => f.matched) };
  });

  protected readonly truth = computed(() => this.proj().xy(this.data().truth.lat, this.data().truth.lon));
  protected readonly est = computed(() => this.proj().xy(this.data().estimate.lat, this.data().estimate.lon));
  protected readonly regionR = computed(() => Math.max(6, this.data().region_radius_m / this.proj().mPerPx));

  protected readonly scale = computed(() => {
    // Largest "nice" length that fits in ~a third of the width.
    const maxM = (W / 3) * this.proj().mPerPx;
    const nice = [50, 100, 200, 250, 500, 1000, 2000, 5000, 10000, 20000].filter((m) => m <= maxM).pop() ?? 50;
    return { px: nice / this.proj().mPerPx, label: nice >= 1000 ? `${nice / 1000} km` : `${nice} m` };
  });

  protected readonly label = computed(
    () =>
      `Hartă simulată cu ${this.data().flights.length} zboruri; locul estimat este la ${Math.round(this.data().error_m)} m de cel real.`,
  );
}
