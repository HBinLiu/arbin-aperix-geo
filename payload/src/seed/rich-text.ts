import { convertHTMLToLexical, editorConfigFactory } from "@payloadcms/richtext-lexical";
import { JSDOM } from "jsdom";

import config from "@payload-config";

/** Seed 专用：HTML → Lexical（仅 CMS 初始化，非官网路径） */
export async function htmlToLexical(html: string) {
  const sanitizedConfig = await config;

  return convertHTMLToLexical({
    editorConfig: await editorConfigFactory.default({ config: sanitizedConfig }),
    html,
    JSDOM,
  });
}
