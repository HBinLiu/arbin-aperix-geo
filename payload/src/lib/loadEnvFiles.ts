import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";

/**
 * 解析 dotenv 行写入 process.env（不覆盖已有值）。
 * `payload run` 不会像 `next start` 那样自动加载 `.env.production`。
 */
export function loadEnvFiles(cwd = process.cwd()): void {
  const files = [".env", ".env.local", ".env.production", ".env.production.local"];
  for (const name of files) {
    const path = resolve(cwd, name);
    if (!existsSync(path)) continue;
    const text = readFileSync(path, "utf8");
    for (const raw of text.split("\n")) {
      const line = raw.trim();
      if (!line || line.startsWith("#")) continue;
      const eq = line.indexOf("=");
      if (eq <= 0) continue;
      const key = line.slice(0, eq).trim();
      if (!key || process.env[key] !== undefined) continue;
      let value = line.slice(eq + 1).trim();
      if (
        (value.startsWith('"') && value.endsWith('"')) ||
        (value.startsWith("'") && value.endsWith("'"))
      ) {
        value = value.slice(1, -1);
      }
      process.env[key] = value;
    }
  }
}
