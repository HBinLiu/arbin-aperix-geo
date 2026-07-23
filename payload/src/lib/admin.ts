/** Admin 侧边栏「站点设置」分组 */
export const SITE_ADMIN_GROUP = "站点设置";

/** Admin 侧边栏「资源探索」分组（研究分类、研究报告） */
export const RESOURCE_EXPLORATION_ADMIN_GROUP = "资源探索";

/** 全站日期时间展示（列表 createdAt 等）：24 小时制 */
export const ADMIN_DATE_TIME_FORMAT = "yyyy-MM-dd HH:mm";

/** 仅日期字段展示（publishedAt 等 dayOnly） */
export const ADMIN_DATE_ONLY_FORMAT = "yyyy-MM-dd";

/** dayOnly 日期字段的 admin.date 公共配置 */
export const adminDayOnlyDate = {
  pickerAppearance: "dayOnly" as const,
  displayFormat: ADMIN_DATE_ONLY_FORMAT,
};
