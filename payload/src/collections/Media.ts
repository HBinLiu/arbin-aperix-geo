import type { CollectionConfig } from "payload";
import { authenticatedWrite, publicRead } from "../access";

export const Media: CollectionConfig = {
  slug: "media",
  access: {
    read: publicRead,
    create: authenticatedWrite,
    update: authenticatedWrite,
    delete: authenticatedWrite,
  },
  upload: {
    staticDir: "media",
    mimeTypes: ["image/*"],
  },
  fields: [
    {
      name: "alt",
      type: "text",
      required: true,
    },
  ],
};
