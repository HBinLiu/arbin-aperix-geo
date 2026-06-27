import { useEffect, useState } from "react";

export function useOtpCooldown(initial = 0) {
  const [cooldown, setCooldown] = useState(initial);

  useEffect(() => {
    if (cooldown <= 0) return;
    const timer = window.setInterval(() => setCooldown((value) => value - 1), 1000);
    return () => window.clearInterval(timer);
  }, [cooldown]);

  return {
    cooldown,
    startCooldown: (seconds = 60) => setCooldown(seconds),
    resetCooldown: () => setCooldown(0),
  };
}
