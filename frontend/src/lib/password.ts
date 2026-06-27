export const PASSWORD_MIN_LENGTH = 8;

export const PASSWORD_RULE_HINT =
  "至少包含字母、数字、特殊符号中的两种，长度至少 8 位。";

function passwordCategoryCount(password: string): number {
  let count = 0;
  if (/[A-Za-z]/.test(password)) count += 1;
  if (/\d/.test(password)) count += 1;
  if (/[^A-Za-z0-9]/.test(password)) count += 1;
  return count;
}

/** 校验通过返回 null，否则返回错误文案 */
export function validatePasswordStrength(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return "密码至少 8 位";
  }
  if (passwordCategoryCount(password) < 2) {
    return "密码需包含字母、数字、特殊符号中的至少两种";
  }
  return null;
}
