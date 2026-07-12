import { researchCategoryDefaults } from "@shared/research/defaults/categories";

export const researchCategorySeedItems = researchCategoryDefaults;

export function researchCategorySeedCount(): number {
  return researchCategorySeedItems.length;
}
