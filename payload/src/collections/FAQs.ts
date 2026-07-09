import type { CollectionConfig } from "payload";

export const FAQs: CollectionConfig = {
  slug: "faqs",
  admin: {
    useAsTitle: "question",
    defaultColumns: ["question", "sortOrder", "updatedAt"],
  },
  fields: [
    {
      name: "question",
      type: "text",
      required: true,
    },
    {
      name: "answer",
      type: "textarea",
      required: true,
    },
    {
      name: "sortOrder",
      type: "number",
      required: true,
      defaultValue: 0,
      admin: {
        description: "越小越靠前",
      },
    },
  ],
};
