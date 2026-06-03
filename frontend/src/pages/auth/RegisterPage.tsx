import * as React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { AuthShell } from "@/components/layouts/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { registerWithOtp, sendAuthCode } from "@/api/auth";
import { setStoredToken } from "@/api/client";
import { sanitizeReturnPath } from "@/lib/auth";
import { toast } from "@/lib/toast";

export function RegisterPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [tenantName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [code, setCode] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [password2, setPassword2] = React.useState("");
  const [cooldown, setCooldown] = React.useState(0);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const sendCode = async () => {
    setLoading(true);
    try {
      const data = await sendAuthCode({
        purpose: "register",
        channel: "email",
        target: email.trim(),
      });
      setCooldown(60);
      if (data.dev_code) {
        setCode(String(data.dev_code));
      } else if (data.message) {
        toast.info(data.message);
      }
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password !== password2) {
      toast.error("两次输入的密码不一致");
      return;
    }
    if (password.length < 8) {
      toast.error("密码至少 8 位");
      return;
    }
    setLoading(true);
    try {
      const data = await registerWithOtp({
        tenant_name: tenantName.trim(),
        channel: "email",
        target: email.trim(),
        code: code.trim(),
        password,
      });
      setStoredToken(data.access_token);
      navigate(sanitizeReturnPath(searchParams.get("next")));
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="注册 Aperix AI"
      description={
        <>
          使用邮箱获取验证码完成注册。
          已有账号？{" "}
          <Link
            className="text-foreground font-medium underline underline-offset-4 hover:text-primary"
            to="/auth/login"
          >
            登录
          </Link>
        </>
      }
    >
      <form className="flex flex-col gap-4" onSubmit={submit}>
        <div className="space-y-2">
          <label className="text-foreground text-sm font-medium" htmlFor="reg-email">
            电子邮箱
          </label>
          <Input
            id="reg-email"
            className="h-11"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </div>
        <div className="space-y-2">
          <label className="text-foreground text-sm font-medium" htmlFor="reg-code">
            邮箱验证码
          </label>
          <div className="flex items-center gap-2">
            <Input
              id="reg-code"
              className="h-11 flex-1"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="6 位数字"
              inputMode="numeric"
              required
            />
            <Button
              type="button"
              variant="secondary"
              className="h-11 w-32 shrink-0 px-4 font-medium whitespace-nowrap"
              disabled={loading || cooldown > 0}
              onClick={sendCode}
            >
              {cooldown > 0 ? `${cooldown}s 后重试` : "发送验证码"}
            </Button>
          </div>
        </div>
        <div className="space-y-2">
          <label className="text-foreground text-sm font-medium" htmlFor="reg-password">
            登录密码
          </label>
          <Input
            id="reg-password"
            className="h-11"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="new-password"
            placeholder="登录密码"
            required
            minLength={8}
          />
        </div>
        <div className="space-y-2">
          <label className="text-foreground text-sm font-medium" htmlFor="reg-password2">
            确认密码
          </label>
          <Input
            id="reg-password2"
            className="h-11"
            type="password"
            value={password2}
            onChange={(e) => setPassword2(e.target.value)}
            autoComplete="new-password"
            placeholder="确认密码"
            required
            minLength={8}
          />
        </div>
        <Button type="submit" className="h-11 w-full text-base font-medium" disabled={loading}>
          注册并登录
        </Button>
      </form>
    </AuthShell>
  );
}
