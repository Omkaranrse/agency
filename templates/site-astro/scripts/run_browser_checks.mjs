import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

let playwright;
try {
  playwright = require('playwright');
} catch (e1) {
  try {
    playwright = require('/usr/local/lib/node_modules/playwright');
  } catch (e2) {
    console.error('Playwright could not be loaded from local or global paths:', e1.message, e2.message);
    process.exit(1);
  }
}

const { chromium } = playwright;
const baseUrl = process.env.BASE_URL || 'http://localhost:4321';
const screenshotsDir = path.resolve(__dirname, '..', 'screenshots');
fs.mkdirSync(screenshotsDir, { recursive: true });

const pages = [
  { name: 'home', route: '/' },
  { name: 'about', route: '/about/' },
  { name: 'projects', route: '/projects/' },
  { name: 'contact', route: '/contact/' },
];

const viewports = [
  { width: 390, height: 844, label: '390' },
  { width: 1280, height: 800, label: '1280' },
];

const qaChecks = [];

async function main() {
  const browser = await chromium.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage'],
  });

  try {
    for (const pageInfo of pages) {
      for (const vp of viewports) {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
        });
        const page = await context.newPage();

        const consoleErrors = [];
        const failedRequests = [];

        page.on('console', (msg) => {
          if (msg.type() === 'error') {
            consoleErrors.push(msg.text());
          }
        });

        page.on('requestfailed', (req) => {
          failedRequests.push(`${req.method()} ${req.url()}: ${req.failure()?.errorText || 'failed'}`);
        });

        const targetUrl = `${baseUrl}${pageInfo.route}`;
        let statusOk = false;
        let responseStatus = 0;
        try {
          const resp = await page.goto(targetUrl, { waitUntil: 'networkidle', timeout: 15000 });
          responseStatus = resp ? resp.status() : 0;
          statusOk = responseStatus >= 200 && responseStatus < 400;
        } catch (err) {
          console.error(`Navigation error for ${targetUrl}:`, err.message);
        }

        // Check heading presence
        let headingText = '';
        try {
          const h1 = await page.$('h1');
          if (h1) {
            headingText = (await h1.textContent() || '').trim();
          }
        } catch (_) {}

        // Check horizontal overflow
        let hasOverflow = false;
        try {
          hasOverflow = await page.evaluate(() => {
            return document.documentElement.scrollWidth > window.innerWidth;
          });
        } catch (_) {}

        // Capture screenshot
        const screenshotFilename = `${pageInfo.name}-${vp.label}.png`;
        const screenshotPath = path.join(screenshotsDir, screenshotFilename);
        let screenshotOk = false;
        try {
          await page.screenshot({ path: screenshotPath, fullPage: false });
          screenshotOk = fs.existsSync(screenshotPath) && fs.statSync(screenshotPath).size > 0;
        } catch (err) {
          console.error(`Screenshot error for ${screenshotFilename}:`, err.message);
        }

        qaChecks.push({
          name: `page_response_${pageInfo.name}_${vp.label}`,
          passed: statusOk,
          details: `HTTP status ${responseStatus} for ${targetUrl}`,
        });

        qaChecks.push({
          name: `heading_${pageInfo.name}_${vp.label}`,
          passed: headingText.length > 0,
          details: headingText.length > 0 ? `Heading present: "${headingText.slice(0, 50)}"` : 'Missing or empty <h1>',
        });

        qaChecks.push({
          name: `console_errors_${pageInfo.name}_${vp.label}`,
          passed: consoleErrors.length === 0,
          details: consoleErrors.length === 0 ? 'Zero console errors' : `Errors: ${consoleErrors.join('; ')}`,
        });

        qaChecks.push({
          name: `overflow_${pageInfo.name}_${vp.label}`,
          passed: !hasOverflow,
          details: !hasOverflow ? 'No horizontal overflow detected' : 'Horizontal overflow detected',
        });

        qaChecks.push({
          name: `screenshot_${pageInfo.name}_${vp.label}`,
          passed: screenshotOk,
          details: screenshotOk ? `Screenshot saved: ${screenshotFilename}` : `Screenshot capture failed for ${screenshotFilename}`,
        });

        await context.close();
      }
    }
  } finally {
    await browser.close();
  }

  const overallPassed = qaChecks.length > 0 && qaChecks.every((c) => c.passed);
  const report = {
    checks: qaChecks,
    overall_passed: overallPassed,
  };

  const reportPath = path.resolve(__dirname, '..', 'qa-report.json');
  fs.writeFileSync(reportPath, JSON.stringify(report, null, 2));
  console.log(`QA Report written to ${reportPath}: ${overallPassed ? 'ALL PASSED' : 'CHECKS FAILED'}`);

  if (!overallPassed) {
    process.exit(1);
  }
}

main().catch((err) => {
  console.error('Fatal error in browser checks:', err);
  process.exit(1);
});
