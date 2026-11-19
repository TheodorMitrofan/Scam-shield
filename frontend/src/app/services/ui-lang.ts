import { Injectable, signal } from '@angular/core';
import { Verdict } from '../models/scenario';
import { FLAG_LABEL, SCAM_TYPE_LABEL, VERDICT_LABEL } from './result-utils';

export type Lang = 'ro' | 'en';

const VERDICT_LABEL_EN: Record<Verdict, string> = {
  SCAM: 'Looks like a scam! Do not reply',
  SUSPICIOUS: 'Careful, check before you reply',
  SAFE: 'Looks fine',
};

const SCAM_TYPE_LABEL_EN: Record<string, string> = {
  BANK_IMPERSONATION: 'Pretends to be a bank',
  COURIER_FEE: 'Fake courier fee',
  AUTHORITY_IMPERSONATION: 'Pretends to be an authority',
  FAMILY_EMERGENCY: 'Relative in trouble (new number)',
  TECH_SUPPORT: 'Fake tech support',
  MARKETPLACE: 'Fake buyer',
  ACCOUNT_TAKEOVER: 'Stolen account asking for a code',
  INVESTMENT: 'Fake investment',
  ROMANCE: 'Fake friendship asking for money',
  JOB_OFFER: 'Fake job offer',
  PRIZE_LOTTERY: 'Fake prize',
  OTHER: 'Other scam',
  NONE: 'Ordinary message',
};

const FLAG_LABEL_EN: Record<string, string> = {
  RF_CODE_REQUEST: 'Asks for a code you got by SMS',
  RF_REMOTE_ACCESS: 'Asks you to install a program',
  RF_DATA_REQUEST: 'Asks for card details or passwords',
  RF_PAYMENT_REQUEST: 'Asks for money',
  RF_SUSPICIOUS_CONTACT: 'Unofficial link, address or number',
  RF_NEW_NUMBER: 'New number claiming to be family',
  RF_SECRECY: 'Asks you to keep it secret',
  RF_TOO_GOOD: 'Too good to be true',
  RF_IMPERSONATION: 'Pretends to be someone else',
  RF_URGENCY: 'Rushes you',
  RF_THREAT: 'Scares you (blocked account, fine)',
  RF_EMOTIONAL_PRESSURE: 'Plays on your emotions',
  RF_CHANNEL_SWITCH: 'Moves you to another app',
};

/** Short UI strings of the result panel, the trusted-call button and the highlights. */
const TEXT = {
  risk: { ro: 'Risc', en: 'Risk' },
  type: { ro: 'Tip', en: 'Type' },
  firstAlert: { ro: 'Prima alertă', en: 'First alert' },
  atMessage: { ro: 'la mesajul', en: 'at message' },
  why: { ro: 'De ce:', en: 'Why:' },
  callTrusted: { ro: 'Sunați pe cineva de încredere', en: 'Call someone you trust' },
  callName: { ro: 'Sunați acum:', en: 'Call' },
  trustedHint: {
    ro: 'Înainte să faceți ceva, vorbiți cu cineva apropiat. Numărul rămâne doar pe acest telefon.',
    en: 'Before doing anything, talk to someone close to you. The number stays on this phone only.',
  },
  trustedName: { ro: 'Numele persoanei', en: 'Their name' },
  trustedPhone: { ro: 'Numărul de telefon', en: 'Phone number' },
  save: { ro: 'Salvează', en: 'Save' },
  change: { ro: 'Schimbă persoana', en: 'Change person' },
  cancel: { ro: 'Renunță', en: 'Cancel' },
  badPhone: { ro: 'Scrieți un număr de telefon valid.', en: 'Please enter a valid phone number.' },
  highlightHint: {
    ro: 'Cuvintele subliniate cu roșu sunt cele periculoase. Atingeți-le ca să vedeți de ce.',
    en: 'Words underlined in red are the dangerous ones. Tap them to see why.',
  },
} as const;

export type TextKey = keyof typeof TEXT;

const STORAGE_KEY = 'scamshield-lang';

/** Romanian / English toggle for the warning and the result explanations (brief: „English toggle”). */
@Injectable({ providedIn: 'root' })
export class UiLang {
  readonly lang = signal<Lang>(UiLang.initial());

  private static initial(): Lang {
    const q = new URLSearchParams(location.search).get('lang');
    if (q === 'en' || q === 'ro') return q;
    try {
      return localStorage.getItem(STORAGE_KEY) === 'en' ? 'en' : 'ro';
    } catch {
      return 'ro';
    }
  }

  set(lang: Lang): void {
    this.lang.set(lang);
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* storage blocked: the choice just isn't remembered */
    }
  }

  t(key: TextKey): string {
    return TEXT[key][this.lang()];
  }

  verdict(v: Verdict): string {
    return this.lang() === 'en' ? VERDICT_LABEL_EN[v] : VERDICT_LABEL[v];
  }

  flag(code: string): string {
    return (this.lang() === 'en' ? FLAG_LABEL_EN : FLAG_LABEL)[code] ?? code;
  }

  scamType(code: string): string {
    return (this.lang() === 'en' ? SCAM_TYPE_LABEL_EN : SCAM_TYPE_LABEL)[code] ?? code;
  }

  /** The detector's warning in the chosen language (falls back to Romanian if no English text). */
  warning(w: { ro: string; en?: string | null }): string {
    return this.lang() === 'en' && w.en ? w.en : w.ro;
  }
}
