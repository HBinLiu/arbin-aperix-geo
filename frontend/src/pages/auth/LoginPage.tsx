import * as React from "react";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AuthShell } from "@/components/layouts/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { loginWithOtp, sendAuthCode } from "@/api/auth";
import { setStoredToken } from "@/api/client";
import { sanitizeReturnPath } from "@/lib/auth";

type Channel = "email" | "phone";

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [channel, setChannel] = React.useState<Channel>("phone");
  const [email, setEmail] = React.useState("");
  const [phone, setPhone] = React.useState("");
  const [code, setCode] = React.useState("");
  const [cooldown, setCooldown] = React.useState(0);
  const [loading, setLoading] = React.useState(false);

  React.useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const setChannelAndReset = (c: Channel) => {
    setChannel(c);
    setCode("");
    setCooldown(0);
  };

  const target = channel === "email" ? email.trim() : phone.trim();

  const sendCode = async () => {
    setLoading(true);
    try {
      const data = await sendAuthCode({
        purpose: "login",
        channel,
        target,
      });
      setCooldown(60);
      // 开发环境后端可能回显 dev_code，仅静默填入，不展示接口 message
      if (data.dev_code) {
        setCode(String(data.dev_code));
      }
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setLoading(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await loginWithOtp({
        channel,
        target,
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

  return (
    <AuthShell
      title="登录 Aperix AI"
      description="使用手机号或邮箱接收验证码登录；若未开通账号，验证通过后将自动完成注册。"
    >
      <Tabs value={channel} onValueChange={(value) => setChannelAndReset(value as Channel)}>
        <TabsList className="grid h-10 w-full grid-cols-2 gap-1 p-1">
          <TabsTrigger value="phone" className="w-full">
            手机号
          </TabsTrigger>
          <TabsTrigger value="email" className="w-full">
            邮箱
          </TabsTrigger>
        </TabsList>

        <TabsContent value="phone" className="mt-6">
          <form className="flex flex-col gap-4" onSubmit={submit}>
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
                  id="login-phone-code"
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
                  variant="background"
                  className="bg-background h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
                  disabled={loading || cooldown > 0 || !phone.trim()}
                  onClick={() => void sendCode()}
                >
                  {cooldown > 0 ? `${cooldown}s` : "发送验证码"}
                </Button>
              </div>
            </div>
            <Button type="submit" className="h-11 w-full text-base font-medium" disabled={loading}>
              验证并登录
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="email" className="mt-6">
          <form className="flex flex-col gap-4" onSubmit={submit}>
            <div className="space-y-2">
              <Input
                id="login-email"
                className="h-11"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="电子邮箱"
                autoComplete="email"
                required
              />
            </div>
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  id="login-email-code"
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
                  variant="background"
                  className="bg-background h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
                  disabled={loading || cooldown > 0 || !email.trim()}
                  onClick={() => void sendCode()}
                >
                  {cooldown > 0 ? `${cooldown}s` : "发送验证码"}
                </Button>
              </div>
            </div>
            <Button type="submit" className="h-11 w-full text-base font-medium" disabled={loading}>
              验证并登录
            </Button>
          </form>
        </TabsContent>
      </Tabs>
    </AuthShell>
  );
}
