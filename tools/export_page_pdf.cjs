const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const root = path.resolve(__dirname, "..");
const baseUrl = process.env.OOF_EXPORT_BASE_URL || "http://127.0.0.1:8786";
const executablePath = process.env.OOF_CHROMIUM_PATH;

async function main() {
  const relativePage = process.argv[2];
  if (!relativePage || !relativePage.endsWith(".html")) {
    throw new Error("Usage: node tools/export_page_pdf.cjs <relative-page.html>");
  }

  const sourcePath = path.resolve(root, relativePage);
  const relativePath = path.relative(root, sourcePath);
  if (relativePath.startsWith("..") || path.isAbsolute(relativePath) || !fs.existsSync(sourcePath)) {
    throw new Error(`HTML page not found inside repository: ${relativePage}`);
  }

  const outputPath = path.join(root, "pdf", relativePath.replace(/\.html$/i, ".pdf"));
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });

  const browser = await chromium.launch({ headless: true, executablePath });
  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const url = `${baseUrl}/${relativePath.split(path.sep).map(encodeURIComponent).join("/")}`;
  await page.goto(url, { waitUntil: "domcontentloaded", timeout: 30000 });
  await page.waitForFunction(() => document.querySelector("#footer")?.textContent?.trim(), null, { timeout: 10000 });
  await page
    .locator(".back-btn, .history-back-fab, .burger, .burger-menu, .page-pdf-download")
    .evaluateAll((elements) => elements.forEach((element) => element.remove()));
  await page.pdf({
    path: outputPath,
    format: "A4",
    printBackground: true,
    margin: { top: "14mm", right: "12mm", bottom: "14mm", left: "12mm" },
  });
  await browser.close();
  console.log(path.relative(root, outputPath));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
