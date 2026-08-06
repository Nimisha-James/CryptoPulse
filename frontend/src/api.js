const DASHBOARD_API = "/api";
const AGENT_API = "/agent";

async function getJSON(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json();
}

export const api = {
  getAssets: () => getJSON(`${DASHBOARD_API}/assets`),
  getLiveMetrics: () => getJSON(`${DASHBOARD_API}/live-metrics`),
  getSeries: (asset, limit = 40) =>
    getJSON(`${DASHBOARD_API}/live-metrics/series?asset=${encodeURIComponent(asset)}&limit=${limit}`),
  getDailySummary: () => getJSON(`${DASHBOARD_API}/daily-summary`),

  getLatestBriefing: () => getJSON(`${AGENT_API}/briefing/latest`),
  generateBriefing: () => getJSON(`${AGENT_API}/briefing`, { method: "POST" }),
};
