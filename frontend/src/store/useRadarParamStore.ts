import { create } from "zustand";
import {
  getLatestParamIterationApi,
  listParamIterationsApi,
  triggerAutoRetroApi,
} from "@/services/authApi";

interface ParamIterationItem {
  id: number;
  iteration_type: string;
  scan_params: Record<string, unknown>;
  recommended_params: Record<string, unknown> | null;
  scan_result_summary: Record<string, unknown> | null;
  iteration_effect: Record<string, unknown> | null;
  is_applied: boolean;
  applied_at: string | null;
  created_at: string;
}

interface RadarParamState {
  latestParams: Record<string, unknown> | null;
  iterationCount: number;
  lastIterationAt: string | null;
  history: ParamIterationItem[];
  historyTotal: number;
  loading: boolean;
  autoRetroLoading: boolean;

  fetchLatest: () => Promise<void>;
  fetchHistory: (limit?: number, offset?: number) => Promise<void>;
  triggerAutoRetro: (force?: boolean) => Promise<Record<string, unknown> | null>;
}

export const useRadarParamStore = create<RadarParamState>((set) => ({
  latestParams: null,
  iterationCount: 0,
  lastIterationAt: null,
  history: [],
  historyTotal: 0,
  loading: false,
  autoRetroLoading: false,

  fetchLatest: async () => {
    set({ loading: true });
    try {
      const res = await getLatestParamIterationApi();
      set({
        latestParams: res.recommended_params,
        iterationCount: res.iteration_count,
        lastIterationAt: res.last_iteration_at,
      });
    } finally {
      set({ loading: false });
    }
  },

  fetchHistory: async (limit = 20, offset = 0) => {
    set({ loading: true });
    try {
      const res = await listParamIterationsApi(limit, offset);
      set({ history: res.items as ParamIterationItem[], historyTotal: res.total });
    } finally {
      set({ loading: false });
    }
  },

  triggerAutoRetro: async (force = false) => {
    set({ autoRetroLoading: true });
    try {
      const res = await triggerAutoRetroApi(force);
      const latest = await getLatestParamIterationApi();
      set({
        latestParams: latest.recommended_params,
        iterationCount: latest.iteration_count,
        lastIterationAt: latest.last_iteration_at,
      });
      return res.recommended_params;
    } finally {
      set({ autoRetroLoading: false });
    }
  },
}));