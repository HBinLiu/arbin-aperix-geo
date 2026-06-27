import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

type OtpCodeFieldProps = {
  value: string;
  onChange: (value: string) => void;
  cooldown: number;
  sending?: boolean;
  onSend: () => void;
  sendLabel?: string;
};

export function OtpCodeField({
  value,
  onChange,
  cooldown,
  sending = false,
  onSend,
  sendLabel = "发送验证码",
}: OtpCodeFieldProps) {
  return (
    <div className="flex gap-2">
      <Input
        className="h-11 min-w-0 flex-1"
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="验证码"
        inputMode="numeric"
        autoComplete="one-time-code"
        required
      />
      <Button
        type="button"
        variant="background"
        className="bg-background h-11 w-28 shrink-0 justify-center px-2 font-medium tabular-nums"
        disabled={sending || cooldown > 0}
        onClick={onSend}
      >
        {cooldown > 0 ? `${cooldown}s` : sendLabel}
      </Button>
    </div>
  );
}
