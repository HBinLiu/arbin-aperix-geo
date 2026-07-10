import { postgresAdapter } from "@payloadcms/db-postgres";
import { lexicalEditor } from "@payloadcms/richtext-lexical";
import path from "path";
import { buildConfig } from "payload";
import { fileURLToPath } from "url";
import sharp from "sharp";

import { FAQs } from "./collections/FAQs";
import { Media } from "./collections/Media";
import { Pages } from "./collections/Pages";
import { Users } from "./collections/Users";

const filename = fileURLToPath(import.meta.url);
const dirname = path.dirname(filename);

const payloadAppDir = path.resolve(dirname, "./app/cms/(payload)");

export default buildConfig({
  admin: {
    user: Users.slug,
    importMap: {
      baseDir: payloadAppDir,
      importMapFile: path.resolve(payloadAppDir, "./admin/importMap.js"),
    },
  },
  collections: [Users, Media, Pages, FAQs],
  editor: lexicalEditor(),
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
  sharp,
  plugins: [],
});
