import type { Access } from "payload";

/** CMS 管理员已登录 */
export const authenticatedOnly: Access = ({ req: { user } }) => Boolean(user);

/** 官网 SSR 可读：营销类公开内容 */
export const publicRead: Access = () => true;

/** 官网 SSR 可读：仅已发布；登录用户可读全部（含草稿） */
export const publishedOrAuthenticatedRead: Access = ({ req: { user } }) => {
  if (user) return true;
  return {
    status: {
      equals: "published",
    },
  };
};

/** 写操作：仅 CMS 管理员 */
export const authenticatedWrite: Access = authenticatedOnly;

/** 首个管理员可注册，之后仅已登录用户可创建 */
export const firstUserOrAuthenticatedCreate: Access = async ({ req }) => {
  if (req.user) return true;
  const { totalDocs } = await req.payload.count({ collection: "users" });
  return totalDocs === 0;
};
