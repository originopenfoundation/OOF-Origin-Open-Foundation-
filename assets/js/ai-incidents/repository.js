export class IncidentRepository {
  constructor(baseUrl = "/data/ai-incidents/public") {
    this.baseUrl = baseUrl;
  }

  async request(path, signal) {
    const response = await fetch(`${this.baseUrl}/${path}`, { headers: { Accept: "application/json" }, signal });
    if (!response.ok) throw new Error(`Incident data request failed (${response.status})`);
    return response.json();
  }

  summary(signal) {
    return this.request("summary.json", signal);
  }

  map(signal) {
    return this.request("map.json", signal);
  }

  aggregations(signal) {
    return this.request("aggregations.json", signal);
  }

  page(page = 1, signal) {
    return this.request(`incidents-page-${Math.max(1, Number(page) || 1)}.json`, signal);
  }

  search(signal) {
    return this.request("incident-search.json", signal);
  }

  detail(slug) {
    if (!/^[a-z0-9-]+$/.test(String(slug || ""))) {
      return Promise.reject(new Error("Invalid incident detail identifier"));
    }
    return this.request(`incident-details/${slug}.json`);
  }
}
