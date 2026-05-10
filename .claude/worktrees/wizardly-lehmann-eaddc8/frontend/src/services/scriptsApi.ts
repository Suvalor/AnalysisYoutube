import apiClient from "./apiClient";

export type ScriptModelOption = { value: string; label: string };

export async function getScriptModelsApi(): Promise<ScriptModelOption[]> {
  const res = await apiClient.get("/api/v1/scripts/models");
  const list = (res.data?.models ?? []) as ScriptModelOption[];
  return Array.isArray(list) ? list : [];
}
