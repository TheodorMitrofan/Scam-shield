import { Injectable, computed, signal } from '@angular/core';
import { API_BASE } from '../api.config';
import { AccountPreview, UserInfo } from '../models/auth';

const STORAGE_KEY = 'scamshield-user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  readonly user = signal<UserInfo | null>(this.readStored());
  readonly isAdmin = computed(() => this.user()?.role === 'admin');
  readonly isLoggedIn = computed(() => this.user() !== null);

  async login(username: string, password: string): Promise<UserInfo> {
    const u = await this.post<UserInfo>('/auth/login', { username, password });
    this.setUser(u);
    return u;
  }

  async register(username: string, password: string, display_name?: string): Promise<UserInfo> {
    const u = await this.post<UserInfo>('/auth/register', { username, password, display_name });
    this.setUser(u);
    return u;
  }

  async accounts(): Promise<AccountPreview[]> {
    try {
      const res = await fetch(`${API_BASE}/auth/accounts`);
      return res.ok ? ((await res.json()) as AccountPreview[]) : [];
    } catch {
      return [];
    }
  }

  logout(): void {
    this.setUser(null);
  }

  private setUser(u: UserInfo | null): void {
    this.user.set(u);
    try {
      if (u) localStorage.setItem(STORAGE_KEY, JSON.stringify(u));
      else localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  private readStored(): UserInfo | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? (JSON.parse(raw) as UserInfo) : null;
    } catch {
      return null;
    }
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    let res: Response;
    try {
      res = await fetch(`${API_BASE}${path}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
    } catch {
      throw new Error('Serverul de autentificare nu răspunde. Porniți backend-ul (port 8000).');
    }
    if (!res.ok) {
      let msg = `Eroare ${res.status}`;
      try {
        const j = await res.json();
        if (typeof j?.detail === 'string') msg = j.detail;
      } catch {
        /* ignore */
      }
      throw new Error(msg);
    }
    return (await res.json()) as T;
  }
}
