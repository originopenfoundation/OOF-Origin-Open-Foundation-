const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const sourceDir = path.join(root, "content", "pga");
const outputDir = path.join(root, "pdf", "content", "pga");
const baseUrl = process.env.OOF_EXPORT_BASE_URL || "http://127.0.0.1:8791";
const executablePath = process.env.OOF_CHROMIUM_PATH;

async function main() {
  fs.mkdirSync(outputDir, { recursive: true });
  const files = fs.readdirSync(sourceDir).filter((name) => name.endsWith(".html")).sort();
  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  for (const [index, file] of files.entries()) {
    const url = `${baseUrl}/content/pga/${encodeURIComponent(file)}`;
    await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForFunction(() => document.querySelector("#footer")?.textContent?.trim(), null, { timeout: 10000 });
    await page.pdf({
      path: path.join(outputDir, file.replace(/\.html$/, ".pdf")),
      format: "A4",
      printBackground: true,
      margin: { top: "14mm", right: "12mm", bottom: "14mm", left: "12mm" },
    });
    process.stdout.write(`\rExported ${index + 1}/${files.length}`);
  }
  await browser.close();
  process.stdout.write("\n");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
