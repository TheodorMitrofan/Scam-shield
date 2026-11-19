import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import rawValidation from '../data/validationSet.json';
import { defaultApiBase, defaultAudioBase, getStoredApiUrls, mobileApi, setStoredApiUrls } from '../api';
import { normalizeText, parseScenario, scenarioFromText } from '../labels';
import { AnalysisResult, Channel, HealthResponse, Scenario, Verdict } from '../types';

export type ChannelFilter = Channel | 'all';
export type VerdictFilter = Verdict | 'all';

interface ScamShieldState {
  scenarios: Scenario[];
  results: Record<string, AnalysisResult>;
  analyzingIds: Set<string>;
  readIds: Set<string>;
  selectedId: string | null;
  loading: boolean;
  errors: string[];
  apiError: string | null;
  health: HealthResponse | null;
  saveHistory: boolean;
  search: string;
  channelFilter: ChannelFilter;
  verdictFilter: VerdictFilter;
  apiBase: string;
  audioBase: string;
  filtered: Scenario[];
  selected: Scenario | null;
  selectedResult: AnalysisResult | null;
  setSearch: (s: string) => void;
  setChannelFilter: (c: ChannelFilter) => void;
  setVerdictFilter: (v: VerdictFilter) => void;
  setSaveHistory: (v: boolean) => void;
  selectScenario: (id: string | null) => void;
  markUnread: (id: string) => void;
  removeScenario: (id: string) => void;
  loadValidationSet: () => Promise<void>;
  analyzeScenarios: (list: Scenario[]) => Promise<void>;
  addPastedScenario: (input: string | Scenario, opts?: { channel: Channel; senderName?: string; senderAddress?: string; knownContact?: boolean }) => Promise<string>;
  importParsedScenarios: (items: Scenario[], errs: string[]) => Promise<void>;
  updateServerUrls: (apiBase: string, audioBase: string) => Promise<void>;
  checkHealth: () => Promise<HealthResponse | null>;
}

const Ctx = createContext<ScamShieldState | null>(null);

export function ScamShieldProvider({ children }: { children: React.ReactNode }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [results, setResults] = useState<Record<string, AnalysisResult>>({});
  const [analyzingIds, setAnalyzingIds] = useState<Set<string>>(new Set());
  const [readIds, setReadIds] = useState<Set<string>>(new Set());
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [apiError, setApiError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [saveHistory, setSaveHistory] = useState(false);
  const [search, setSearch] = useState('');
  const [channelFilter, setChannelFilter] = useState<ChannelFilter>('all');
  const [verdictFilter, setVerdictFilter] = useState<VerdictFilter>('all');
  const [apiBase, setApiBase] = useState(defaultApiBase);
  const [audioBase, setAudioBase] = useState(defaultAudioBase);

  const checkHealthWith = useCallback(async (base: string): Promise<HealthResponse | null> => {
    try {
      const h = await mobileApi.health(base);
      setHealth(h);
      setApiError(null);
      return h;
    } catch (e) {
      setHealth(null);
      setApiError(e instanceof Error ? e.message : 'Serverul nu răspunde.');
      return null;
    }
  }, []);

  const analyzeWithBase = useCallback(
    async (list: Scenario[], base: string, save: boolean) => {
      if (!list.length) return;
      const ids = list.map((s) => s.id);
      setAnalyzingIds((prev) => new Set([...prev, ...ids]));
      try {
        const res = await mobileApi.analyzeBatch(base, list, save);
        setResults((prev) => {
          const next = { ...prev };
          for (const item of res) next[item.result.id] = item.result;
          return next;
        });
        setApiError(null);
      } catch (e) {
        setApiError(e instanceof Error ? e.message : 'Analiza nu a reușit.');
      } finally {
        setAnalyzingIds((prev) => {
          const next = new Set(prev);
          ids.forEach((id) => next.delete(id));
          return next;
        });
      }
    },
    [],
  );

  const loadValidationWithBase = useCallback(
    async (base: string, save: boolean) => {
      setLoading(true);
      setErrors([]);
      let loaded: Scenario[];
      try {
        const fromApi = await mobileApi.validationSet(base);
        loaded = fromApi.map((raw, i) => parseScenario(raw, `V${String(i + 1).padStart(2, '0')}`));
      } catch {
        // Fallback to bundled validation JSONs so the app works immediately offline too.
        loaded = (rawValidation as unknown[]).map((raw, i) =>
          parseScenario(raw, `V${String(i + 1).padStart(2, '0')}`),
        );
      }
      loaded.sort((a, b) => a.id.localeCompare(b.id));
      setScenarios(loaded);
      setResults({});
      setSelectedId(null);
      setLoading(false);
      await analyzeWithBase(loaded, base, save);
    },
    [analyzeWithBase],
  );

  useEffect(() => {
    let alive = true;
    (async () => {
      const urls = await getStoredApiUrls();
      if (!alive) return;
      setApiBase(urls.apiBase);
      setAudioBase(urls.audioBase);
      await checkHealthWith(urls.apiBase);
      await loadValidationWithBase(urls.apiBase, false);
    })();
    return () => {
      alive = false;
    };
  }, [checkHealthWith, loadValidationWithBase]);

  const selectScenario = useCallback((id: string | null) => {
    setSelectedId(id);
    if (id) setReadIds((prev) => new Set([...prev, id]));
  }, []);

  const markUnread = useCallback((id: string) => {
    setReadIds((prev) => new Set([...prev].filter((x) => x !== id)));
  }, []);

  const removeScenario = useCallback((id: string) => {
    setScenarios((prev) => prev.filter((s) => s.id !== id));
    setResults((prev) => Object.fromEntries(Object.entries(prev).filter(([k]) => k !== id)));
    setReadIds((prev) => new Set([...prev].filter((x) => x !== id)));
    setSelectedId((cur) => (cur === id ? null : cur));
  }, []);

  const addPastedScenario = useCallback(
    async (
      input: string | Scenario,
      opts: { channel: Channel; senderName?: string; senderAddress?: string; knownContact?: boolean } = {
        channel: 'sms',
      },
    ): Promise<string> => {
      const ids = new Set(scenarios.map((s) => s.id));
      let nextId = 'PASTE';
      if (ids.has(nextId)) {
        let n = 2;
        while (ids.has(`PASTE-${n}`)) n++;
        nextId = `PASTE-${n}`;
      }
      const s = typeof input === 'string' ? scenarioFromText(input, opts, nextId) : { ...input, id: nextId };
      setScenarios((prev) => [s, ...prev]);
      setSelectedId(s.id);
      setReadIds((prev) => new Set([...prev, s.id]));
      await analyzeWithBase([s], apiBase, saveHistory);
      return s.id;
    },
    [analyzeWithBase, apiBase, saveHistory, scenarios],
  );

  const importParsedScenarios = useCallback(
    async (items: Scenario[], errs: string[]) => {
      setErrors(errs);
      if (!items.length) return;
      const sorted = [...items].sort((a, b) => a.id.localeCompare(b.id));
      setScenarios(sorted);
      setResults({});
      setSelectedId(null);
      await analyzeWithBase(sorted, apiBase, saveHistory);
    },
    [analyzeWithBase, apiBase, saveHistory],
  );

  const updateServerUrls = useCallback(
    async (nextApi: string, nextAudio: string) => {
      const cleanApi = nextApi.trim().replace(/\/+$/, '') || defaultApiBase();
      const cleanAudio = nextAudio.trim().replace(/\/+$/, '') || defaultAudioBase();
      setApiBase(cleanApi);
      setAudioBase(cleanAudio);
      await setStoredApiUrls(cleanApi, cleanAudio);
      await checkHealthWith(cleanApi);
    },
    [checkHealthWith],
  );

  const filtered = useMemo(() => {
    const q = normalizeText(search.trim());
    return scenarios.filter((s) => {
      if (channelFilter !== 'all' && s.channel !== channelFilter) return false;
      if (verdictFilter !== 'all' && results[s.id]?.verdict !== verdictFilter) return false;
      if (!q) return true;
      const hay = [s.id, s.sender.name ?? '', s.sender.address ?? '', ...s.messages.map((m) => m.text)];
      return hay.some((h) => normalizeText(h).includes(q));
    });
  }, [channelFilter, results, scenarios, search, verdictFilter]);

  const selected = useMemo(
    () => scenarios.find((s) => s.id === selectedId) ?? null,
    [scenarios, selectedId],
  );

  const selectedResult = useMemo(
    () => (selectedId ? (results[selectedId] ?? null) : null),
    [results, selectedId],
  );

  const value: ScamShieldState = {
    scenarios,
    results,
    analyzingIds,
    readIds,
    selectedId,
    loading,
    errors,
    apiError,
    health,
    saveHistory,
    search,
    channelFilter,
    verdictFilter,
    apiBase,
    audioBase,
    filtered,
    selected,
    selectedResult,
    setSearch,
    setChannelFilter,
    setVerdictFilter,
    setSaveHistory,
    selectScenario,
    markUnread,
    removeScenario,
    loadValidationSet: () => loadValidationWithBase(apiBase, saveHistory),
    analyzeScenarios: (list) => analyzeWithBase(list, apiBase, saveHistory),
    addPastedScenario,
    importParsedScenarios,
    updateServerUrls,
    checkHealth: () => checkHealthWith(apiBase),
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useScamShield(): ScamShieldState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useScamShield must be used inside ScamShieldProvider');
  return v;
}
