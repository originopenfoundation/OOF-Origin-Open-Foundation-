export class IncidentRepository {
  constructor(baseUrl = "/data/ai-incidents/public") {
    this.baseUrl = baseUrl;
  }

  async request(path) {
    const response = await fetch(`${this.baseUrl}/${path}`, { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error(`Incident data request failed (${response.status})`);
    return response.json();
  }

  summary() {
    return this.request("summary.json");
  }

  map() {
    return this.request("map.json");
  }

  aggregations() {
    return this.request("aggregations.json");
  }

  page(page = 1) {
    return this.request(`incidents-page-${Math.max(1, Number(page) || 1)}.json`);
  }

  index() {
    return this.request("incident-index.json");
  }

  detail(slug) {
    if (!/^[a-z0-9-]+$/.test(String(slug || ""))) {
      return Promise.reject(new Error("Invalid incident detail identifier"));
    }
    return this.request(`incident-details/${slug}.json`);
  }
}
