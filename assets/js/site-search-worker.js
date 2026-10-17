let pages = [];

self.addEventListener("message", async event => {
  const message = event.data || {};

  if (message.type === "init") {
    try {
      const response = await fetch(message.indexUrl, { cache: "force-cache" });
      if (!response.ok) throw new Error("Search index not found");

      const index = await response.json();
      pages = index.map(page => {
        const title = page.title || page.url || "";
        const text = (page.text || "").replace(/\s+/g, " ").trim();
        return {
          title,
          url: page.url || "",
          text,
          titleLower: title.toLowerCase(),
          textLower: text.toLowerCase()
        };
      });
      self.postMessage({ type: "ready" });
    } catch (error) {
      self.postMessage({ type: "error", message: error.message });
    }
    return;
  }

  if (message.type !== "search") return;

  const words = String(message.query || "").trim().toLowerCase().split(/\s+/).filter(Boolean);
  const matches = [];

  pages.forEach(page => {
    let score = 0;
    words.forEach(word => {
      if (page.titleLower.includes(word)) score += 10;
      if (page.textLower.includes(word)) score += 1;
    });

    if (score > 0) matches.push({ page, score });
  });

  matches.sort((a, b) => b.score - a.score || a.page.title.localeCompare(b.page.title));
  self.postMessage({
    type: "results",
    requestId: message.requestId,
    resultsId: message.resultsId,
    words,
    matches: matches.slice(0, 12).map(({ page }) => ({
      title: page.title,
      url: page.url,
      excerpt: makeSearchExcerpt(page, words)
    }))
  });
});

function makeSearchExcerpt(page, words) {
  const foundAt = words
    .map(word => page.textLower.indexOf(word))
    .filter(index => index >= 0)
    .sort((a, b) => a - b)[0];
  const start = Math.max(0, (foundAt || 0) - 55);
  const excerpt = page.text.slice(start, start + 150);
  return (start > 0 ? "..." : "") + excerpt + (start + 150 < page.text.length ? "..." : "");
}
