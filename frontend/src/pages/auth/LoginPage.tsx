import * as React from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";

import { AuthShell } from "@/components/layouts/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { loginWithOtp, loginWithPassword, sendAuthCode } from "@/api/auth";
import { setStoredToken } from "@/api/client";
import { sanitizeReturnPath } from "@/lib/auth";
import { cn } from "@/lib/utils";

type Channel = "email" | "phone";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [channel, setChannel] = React.useState<Channel>("phone");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [code, setCode] = React.useState("");
  const [cooldown, setCooldown] = React.useState(0);
  const [info, setInfo] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const setChannelAndReset = (c: Channel) => {
    setChannel(c);
    setInfo(null);
    setCode("");
    setCooldown(0);
  };

  const sendPhoneCode = async () => {
    setInfo(null);
    setLoading(true);
    try {
      const data = await sendAuthCode({
        purpose: "login",
        channel: "phone",
        target: phone.trim(),
      });
      setCooldown(60);
      if (data.dev_code) {
        setCode(String(data.dev_code));
      } else if (data.message) {
        setInfo(data.message);
      }
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  const submitEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setInfo(null);
    setLoading(true);
    try {
      const data = await loginWithPassword({
        email: email.trim().toLowerCase(),
        password: password,
      });
      setStoredToken(data.access_token);
      navigate(sanitizeReturnPath(searchParams.get("next")));
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  const submitPhone = async (e: React.FormEvent) => {
    e.preventDefault();
    setInfo(null);
    setLoading(true);
    try {
      const data = await loginWithOtp({
        channel: "phone",
        target: phone.trim(),
        code: code.trim(),
      });
      setStoredToken(data.access_token);
      navigate(sanitizeReturnPath(searchParams.get("next")));
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  const description =
    channel === "email" ? (
      <>
        使用注册邮箱与密码登录。新用户？{" "}
        <Link
          className="text-foreground font-medium underline underline-offset-4 hover:text-primary"
          to="/auth/register"
        >
          注册账号
        </Link>
      </>
    ) : (
      <>手机号码若未注册，验证通过后将自动完成注册。</>
    );

  return (
    <AuthShell title="登录 Aperix AI" description={description}>
      <div className="grid h-10 grid-cols-2 gap-1 rounded-lg bg-muted p-1">
        <button
          type="button"
          className={cn(
            "rounded-md text-sm font-medium transition-all",
            channel === "phone"
              ? "bg-white text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setChannelAndReset("phone")}
        >
          手机号
        </button>
        <button
          type="button"
          className={cn(
            "rounded-md text-sm font-medium transition-all",
            channel === "email"
              ? "bg-white text-foreground shadow-xs"
              : "text-muted-foreground hover:text-foreground",
          )}
          onClick={() => setChannelAndReset("email")}
        >
          邮箱登录
        </button>
      </div>

      {channel === "email" ? (
        <form className="mt-6 flex flex-col gap-4" onSubmit={submitEmail}>
          <div className="space-y-2">
            <Input
              id="login-email"
              className="h-11"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="企业邮箱"
              autoComplete="email"
              required
            />
          </div>
          <div className="space-y-2">
            <Input
              id="login-password"
              className="h-11"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="登录密码"
              autoComplete="current-password"
              required
            />
          </div>
          <Button type="submit" className="h-11 w-full text-base font-medium" disabled={loading}>
            登录
          </Button>
        </form>
      ) : (
        <form className="mt-6 flex flex-col gap-4" onSubmit={submitPhone}>
          <div className="space-y-2">
            <Input
              id="login-phone"
              className="h-11"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="手机号"
              autoComplete="tel"
              required
            />
          </div>
          <div className="space-y-2">
            <div className="flex gap-2">
              <Input
                id="login-code"
                className="h-11 min-w-0 flex-1"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="验证码"
                inputMode="numeric"
                autoComplete="one-time-code"
                required
              />
              <Button
                type="button"
                variant="secondary"
                className="bg-muted h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
                disabled={loading || cooldown > 0}
                onClick={sendPhoneCode}
              >
                {cooldown > 0 ? `${cooldown}s` : "发送验证码"}
              </Button>
            </div>
          </div>
          {info ? <p className="text-muted-foreground text-sm">{info}</p> : null}
          <Button type="submit" className="h-11 w-full text-base font-medium" disabled={loading}>
            验证并登录
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
