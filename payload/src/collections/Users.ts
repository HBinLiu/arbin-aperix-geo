import type { CollectionConfig } from "payload";
import { authenticatedOnly, firstUserOrAuthenticatedCreate } from "../access";

export const Users: CollectionConfig = {
  slug: "users",
  admin: {
    useAsTitle: "email",
  },
  auth: {
    useAPIKey: true,
  },
  access: {
    read: authenticatedOnly,
    create: firstUserOrAuthenticatedCreate,
    update: authenticatedOnly,
    delete: authenticatedOnly,
  },
  fields: [],
};
