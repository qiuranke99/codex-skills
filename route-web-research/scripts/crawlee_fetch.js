#!/usr/bin/env node
const path = require("path");
const { createRequire } = require("module");

const nodeRoot =
  process.env.GLOBAL_SEARCH_NODE_ROOT || "D:\\AI\\toolchains\\global-search\\node";
const toolchainRequire = createRequire(path.join(nodeRoot, "package.json"));
const { gotScraping } = toolchainRequire("crawlee");

function titleFromHtml(html) {
  const match = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  return match ? match[1].replace(/\s+/g, " ").trim() : "";
}

function textFromHtml(html) {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, 12000);
}

async function main() {
  const url = process.argv[2];
  if (!url) {
    console.error("Usage: node crawlee_fetch.js <url>");
    process.exit(2);
  }

  const response = await gotScraping({ url, responseType: "text", timeout: { request: 30000 } });
  const body = String(response.body || "");
  console.log(
    JSON.stringify({
      url: response.url || url,
      title: titleFromHtml(body),
      text: textFromHtml(body),
      status: response.statusCode,
    })
  );
}

main().catch((err) => {
  console.error(err && err.stack ? err.stack : String(err));
  process.exit(1);
});
