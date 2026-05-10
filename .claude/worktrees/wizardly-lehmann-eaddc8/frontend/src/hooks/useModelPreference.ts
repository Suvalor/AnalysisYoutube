import { useCallback, useMemo } from "react";

const MODEL_PREFERENCE_STORAGE_KEY = "model_preferences";

type ModelPreferenceMap = Record<string, string>;

function readPreferenceMap(): ModelPreferenceMap {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(MODEL_PREFERENCE_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as unknown;
    if (!parsed || typeof parsed !== "object") return {};
    const entries = Object.entries(parsed as Record<string, unknown>).filter(
      ([k, v]) => typeof k === "string" && typeof v === "string"
    );
    return Object.fromEntries(entries);
  } catch {
    return {};
  }
}

function writePreferenceMap(next: ModelPreferenceMap): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(MODEL_PREFERENCE_STORAGE_KEY, JSON.stringify(next));
}

export default function useModelPreference(featureKey: string) {
  const value = useMemo(() => {
    const map = readPreferenceMap();
    return map[featureKey] ?? "";
  }, [featureKey]);

  const setValue = useCallback(
    (nextValue: string) => {
      const map = readPreferenceMap();
      const trimmed = nextValue.trim();
      if (trimmed) {
        map[featureKey] = trimmed;
      } else {
        delete map[featureKey];
      }
      writePreferenceMap(map);
    },
    [featureKey]
  );

  return { value, setValue };
}
