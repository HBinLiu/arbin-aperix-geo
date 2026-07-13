import { postgresAdapter } from "@payloadcms/db-postgres";
import path from "path";
import { buildConfig } from "payload";
import { fileURLToPath } from "url";
import sharp from "sharp";

import { FAQs } from "./collections/FAQs";
import { Media } from "./collections/Media";
import { PageSeoEntries } from "./collections/PageSeo";
import { News } from "./collections/News";
import { ResearchCategories } from "./collections/ResearchCategories";
import { Researches } from "./collections/Researches";
import { Users } from "./collections/Users";
import { AboutPage } from "./globals/AboutPage";
import { defaultLexicalEditor } from "./lib/lexical/default";
import { createEmailAdapter } from "./lib/email";
import { contactEndpoint, contactOptionsEndpoint } from "./endpoints/contact";
import { previewUrlEndpoint } from "./endpoints/preview-url";
import { getPayloadServerUrl, getWebsiteUrl } from "./lib/urls";
import { seo } from "./plugins/seo";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

const payloadAppDir = path.resolve(dirname, "./app/cms/(payload)");
const websiteUrl = getWebsiteUrl();

export default buildConfig({
  admin: {
    user: Users.slug,
    avatar: "default",
    importMap: {
      baseDir: payloadAppDir,
      importMapFile: path.resolve(payloadAppDir, "./admin/importMap.js"),
    },
    meta: {
      titleSuffix: " · Aperix Web",
    },
  },
  collections: [Users, Media, ResearchCategories, Researches, News, FAQs, PageSeoEntries],
  globals: [AboutPage],
  editor: defaultLexicalEditor,
  email: createEmailAdapter(),
  endpoints: [contactEndpoint, contactOptionsEndpoint, previewUrlEndpoint],
  secret: process.env.PAYLOAD_SECRET || "",
  typescript: {
    outputFile: path.resolve(dirname, "payload-types.ts"),
  },
  db: postgresAdapter({
    pool: {
      connectionString: process.env.DATABASE_URL || "",
    },
  }),
  routes: {
    admin: "/cms",
    api: "/cms/api",
    graphQL: "/cms/api/graphql",
    graphQLPlayground: "/cms/api/graphql-playground",
  },
  cors: [websiteUrl, getPayloadServerUrl()],
  csrf: [websiteUrl, getPayloadServerUrl()],
  sharp,
  plugins: [seo],
});
