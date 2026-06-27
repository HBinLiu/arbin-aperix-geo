import { useEffect, useState } from "react";

import { EyeBall } from "@/components/user/EyeBall";
import { useMousePosition } from "@/hooks/useMousePosition";
import { DEFAULT_USER_AVATAR_COLOR, resolveAvatarSeed, setStoredAvatarSeed, userAvatarColor } from "@/lib/avatar";
import { cn } from "@/lib/utils";

type UserAvatarProps = {
  size?: "sm" | "md";
  /** 稳定取色种子，通常传 `user.id` */
  seed?: string;
  className?: string;
};

const AVATAR_SPEC = {
  sm: {
    box: "size-7",
    eyeSize: 8,
    pupilSize: 3,
    gap: "gap-1",
    maxDistance: 2,
    smileWidth: 11,
    smileHeight: 5,
    smileStroke: 1.1,
    faceGap: "gap-1",
    faceHeight: 17,
    faceOffset: "translate-y-px",
  },
  md: {
    box: "size-9",
    eyeSize: 10,
    pupilSize: 4,
    gap: "gap-1.5",
    maxDistance: 2.5,
    smileWidth: 14,
    smileHeight: 6,
    smileStroke: 1.25,
    faceGap: "gap-1.5",
    faceHeight: 22,
    faceOffset: "translate-y-0.5",
  },
} as const;

function AvatarSmile({
  width,
  height,
  stroke,
  className,
}: {
  width: number;
  height: number;
  stroke: number;
  className?: string;
}) {
  return (
    <svg
      width={width}
      height={height}
      viewBox="0 0 14 6"
      className={className}
      aria-hidden
    >
      <path
        d="M1.5 1.5 Q7 6 12.5 1.5"
        stroke="rgb(255 255 255 / 0.92)"
        strokeWidth={stroke}
        fill="none"
        strokeLinecap="round"
      />
    </svg>
  );
}

function usePrefersReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setPrefersReducedMotion(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, []);

  return prefersReducedMotion;
}

function useRandomBlink(enabled: boolean) {
  const [isBlinking, setIsBlinking] = useState(false);

  useEffect(() => {
    if (!enabled) return;

    let blinkTimeout: ReturnType<typeof setTimeout> | undefined;
    let reopenTimeout: ReturnType<typeof setTimeout> | undefined;

    const scheduleBlink = () => {
      blinkTimeout = setTimeout(() => {
        setIsBlinking(true);
        reopenTimeout = setTimeout(() => {
          setIsBlinking(false);
          scheduleBlink();
        }, 120);
      }, 1500 + Math.random() * 2000);
    };

    scheduleBlink();

    return () => {
      if (blinkTimeout) clearTimeout(blinkTimeout);
      if (reopenTimeout) clearTimeout(reopenTimeout);
    };
  }, [enabled]);

  return isBlinking;
}

export function UserAvatar({ size = "sm", seed, className }: UserAvatarProps) {
  const spec = AVATAR_SPEC[size];
  const prefersReducedMotion = usePrefersReducedMotion();
  const animateEyes = !prefersReducedMotion;
  const { x: mouseX, y: mouseY } = useMousePosition(animateEyes);
  const isBlinking = useRandomBlink(animateEyes);
  const effectiveSeed = resolveAvatarSeed(seed);
  const backgroundColor = effectiveSeed ? userAvatarColor(effectiveSeed) : DEFAULT_USER_AVATAR_COLOR;

  useEffect(() => {
    const trimmed = seed?.trim();
    if (trimmed) setStoredAvatarSeed(trimmed);
  }, [seed]);

  return (
    <span
      className={cn(
        "relative box-border inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full align-middle leading-none",
        spec.box,
        className,
      )}
      style={{ backgroundColor }}
      aria-hidden
    >
      <span
        className={cn("flex shrink-0 flex-col items-center", spec.faceGap, spec.faceOffset)}
        style={{ height: spec.faceHeight }}
      >
        <span
          className={cn("flex shrink-0 items-center", spec.gap)}
          style={{ height: spec.eyeSize }}
        >
          <EyeBall
            size={spec.eyeSize}
            pupilSize={spec.pupilSize}
            maxDistance={spec.maxDistance}
            mouseX={mouseX}
            mouseY={mouseY}
            isBlinking={isBlinking}
            animate={animateEyes}
          />
          <EyeBall
            size={spec.eyeSize}
            pupilSize={spec.pupilSize}
            maxDistance={spec.maxDistance}
            mouseX={mouseX}
            mouseY={mouseY}
            isBlinking={isBlinking}
            animate={animateEyes}
          />
        </span>
        <AvatarSmile
          width={spec.smileWidth}
          height={spec.smileHeight}
          stroke={spec.smileStroke}
          className="shrink-0"
        />
      </span>
    </span>
  );
}
