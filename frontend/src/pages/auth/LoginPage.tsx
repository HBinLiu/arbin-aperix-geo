import * as React from "react";
import { isAxiosError } from "axios";
import { useNavigate, useSearchParams } from "react-router-dom";

import { AuthShell } from "@/components/layouts/AuthShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchMe, loginWithOtp, sendAuthCode } from "@/api/auth";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/api/client";
import { sanitizeReturnPath } from "@/lib/auth";
import { toast } from "@/lib/toast";

type Channel = "email" | "phone";

/** Sync controlled value; also covers mobile autofill that skips onChange. */
function useFieldSync(initial = "") {
  const [value, setValue] = React.useState(initial);
  const onChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setValue(event.currentTarget.value);
  };
  const onInput = (event: React.FormEvent<HTMLInputElement>) => {
    setValue(event.currentTarget.value);
  };
  const onBlur = (event: React.FocusEvent<HTMLInputElement>) => {
    setValue(event.currentTarget.value);
  };
  return { value, setValue, onChange, onInput, onBlur };
}

export function LoginPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const returnPath = sanitizeReturnPath(searchParams.get("next"));
  const [channel, setChannel] = React.useState<Channel>("phone");
  const phone = useFieldSync();
  const email = useFieldSync();
  const code = useFieldSync();
  const [cooldown, setCooldown] = React.useState(0);
  const [sendingCode, setSendingCode] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [checkingSession, setCheckingSession] = React.useState(() => Boolean(getStoredToken()));

  React.useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setCheckingSession(false);
      return;
    }

    let cancelled = false;
    void (async () => {
      try {
        await fetchMe({ skipErrorToast: true });
        if (cancelled) return;
        navigate(returnPath, { replace: true });
      } catch (error) {
        if (cancelled) return;
        if (isAxiosError(error) && error.response?.status === 401) {
          clearStoredToken();
        }
        setCheckingSession(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [navigate, returnPath]);

  React.useEffect(() => {
    if (cooldown <= 0) return;
    const t = setInterval(() => setCooldown((c) => c - 1), 1000);
    return () => clearInterval(t);
  }, [cooldown]);

  const setChannelAndReset = (c: Channel) => {
    setChannel(c);
    code.setValue("");
    setCooldown(0);
  };

  const sendCode = async () => {
    const target = (channel === "email" ? email.value : phone.value).trim();
    if (!target) {
      toast.error(channel === "email" ? "请输入邮箱" : "请输入手机号");
      return;
    }
    setSendingCode(true);
    try {
      const data = await sendAuthCode({
        purpose: "login",
        channel,
        target,
      });
      setCooldown(60);
      if (data.dev_code) {
        code.setValue(String(data.dev_code));
      }
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setSendingCode(false);
    }
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    const target = (channel === "email" ? email.value : phone.value).trim();
    const otp = code.value.trim();
    if (!target) {
      toast.error(channel === "email" ? "请输入邮箱" : "请输入手机号");
      return;
    }
    if (!otp) {
      toast.error("请输入验证码");
      return;
    }
    setSubmitting(true);
    try {
      const data = await loginWithOtp({
        channel,
        target,
        code: otp,
      });
      setStoredToken(data.access_token);
      navigate(returnPath);
    } catch {
      /* 错误已由 API 拦截器弹出 Toast */
    } finally {
      setSubmitting(false);
    }
  };

  if (checkingSession) {
    return (
      <AuthShell title="登录 Aperix AI" description="正在确认登录状态…">
        <p className="text-muted-foreground text-sm">请稍候</p>
      </AuthShell>
    );
  }

  const sendDisabled = sendingCode || cooldown > 0;

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
          <form className="flex flex-col gap-4" onSubmit={(e) => void submit(e)}>
            <div className="space-y-2">
              <Input
                id="login-phone"
                className="h-11"
                value={phone.value}
                onChange={phone.onChange}
                onInput={phone.onInput}
                onBlur={phone.onBlur}
                placeholder="手机号"
                autoComplete="tel"
                inputMode="tel"
              />
            </div>
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  id="login-phone-code"
                  className="h-11 min-w-0 flex-1"
                  value={code.value}
                  onChange={code.onChange}
                  onInput={code.onInput}
                  onBlur={code.onBlur}
                  placeholder="验证码"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                />
                <Button
                  type="button"
                  variant="background"
                  className="bg-background h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
                  disabled={sendDisabled}
                  onClick={() => void sendCode()}
                >
                  {cooldown > 0 ? `${cooldown}s` : sendingCode ? "发送中…" : "发送验证码"}
                </Button>
              </div>
            </div>
            <Button
              type="submit"
              className="h-11 w-full text-base font-medium"
              disabled={submitting || sendingCode}
            >
              {submitting ? "登录中…" : "验证并登录"}
            </Button>
          </form>
        </TabsContent>

        <TabsContent value="email" className="mt-6">
          <form className="flex flex-col gap-4" onSubmit={(e) => void submit(e)}>
            <div className="space-y-2">
              <Input
                id="login-email"
                className="h-11"
                value={email.value}
                onChange={email.onChange}
                onInput={email.onInput}
                onBlur={email.onBlur}
                placeholder="电子邮箱"
                autoComplete="email"
                inputMode="email"
              />
            </div>
            <div className="space-y-2">
              <div className="flex gap-2">
                <Input
                  id="login-email-code"
                  className="h-11 min-w-0 flex-1"
                  value={code.value}
                  onChange={code.onChange}
                  onInput={code.onInput}
                  onBlur={code.onBlur}
                  placeholder="验证码"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                />
                <Button
                  type="button"
                  variant="background"
                  className="bg-background h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
                  disabled={sendDisabled}
                  onClick={() => void sendCode()}
                >
                  {cooldown > 0 ? `${cooldown}s` : sendingCode ? "发送中…" : "发送验证码"}
                </Button>
              </div>
            </div>
            <Button
              type="submit"
              className="h-11 w-full text-base font-medium"
              disabled={submitting || sendingCode}
            >
              {submitting ? "登录中…" : "验证并登录"}
            </Button>
          </form>
        </TabsContent>
      </Tabs>
    </AuthShell>
  );
}
