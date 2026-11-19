import AsyncStorage from '@react-native-async-storage/async-storage';

/** Same contract as the web app (frontend/src/app/models/auth.ts, backend /api/auth/*). */
export type UserRole = 'admin' | 'user';

export interface UserInfo {
  id: string;
  username: string;
  role: UserRole;
  display_name: string;
}

/** Demo accounts seeded in the database (same as the web login screen). */
export const DEMO_ACCOUNTS: { username: string; password: string; role: UserRole; label: string }[] = [
  { username: 'admin', password: 'admin', role: 'admin', label: 'Admin (vede toate datele)' },
  { username: 'user', password: 'user', role: 'user', label: 'User (doar datele proprii)' },
  { username: 'maria', password: 'maria123', role: 'user', label: 'Maria (alt cont de user)' },
];

const STORAGE_KEY = 'scamshield-user';

/** Logged-in user, read synchronously by the API layer to send X-User-Id (like the web app). */
let current: UserInfo | null = null;

export function currentUser(): UserInfo | null {
  return current;
}

export async function loadStoredUser(): Promise<UserInfo | null> {
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    current = raw ? (JSON.parse(raw) as UserInfo) : null;
  } catch {
    current = null;
  }
  return current;
}

async function setUser(u: UserInfo | null): Promise<void> {
  current = u;
  try {
    if (u) await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(u));
    else await AsyncStorage.removeItem(STORAGE_KEY);
  } catch {
    /* storage unavailable: stays logged in for this session only */
  }
}

export async function login(apiBase: string, username: string, password: string): Promise<UserInfo> {
  let res: Response;
  try {
    res = await fetch(`${apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
  } catch {
    throw new Error(`Serverul nu răspunde (${apiBase}). Verificați backend-ul și Wi-Fi.`);
  }
  if (!res.ok) {
    let msg = `Eroare ${res.status}`;
    try {
      const j = await res.json();
      if (typeof j?.detail === 'string') msg = j.detail;
    } catch {
      /* non-JSON error */
    }
    throw new Error(msg);
  }
  const u = (await res.json()) as UserInfo;
  await setUser(u);
  return u;
}

export async function logout(): Promise<void> {
  await setUser(null);
}
