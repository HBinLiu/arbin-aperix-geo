/** 平台页 Hero 视频：桌面优先 WebM，iOS / 微信 / 不支持 WebM 时优先 MP4，进入视口后主动 play */

function isWeChatBrowser(): boolean {
  return /MicroMessenger/i.test(navigator.userAgent);
}

function isAppleTouchDevice(): boolean {
  const ua = navigator.userAgent;
  if (/iPhone|iPod|iPad/i.test(ua)) return true;
  // iPadOS 桌面 UA
  return navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1;
}

function canPlayWebm(video: HTMLVideoElement): boolean {
  const candidates = [
    'video/webm; codecs="vp9"',
    'video/webm; codecs="vp8"',
    "video/webm",
  ];
  return candidates.some((type) => {
    const result = video.canPlayType(type);
    return result === "probably" || result === "maybe";
  });
}

/** 需要优先 MP4：微信内置浏览器、iOS/iPadOS，或明确无法播 WebM */
function preferMp4(video: HTMLVideoElement): boolean {
  if (isWeChatBrowser() || isAppleTouchDevice()) return true;
  return !canPlayWebm(video);
}

function applyPreferredSources(video: HTMLVideoElement) {
  const webm = video.dataset.srcWebm;
  const mp4 = video.dataset.srcMp4;
  if (!webm || !mp4) return;

  const useMp4First = preferMp4(video);
  const ordered = useMp4First
    ? [
        { src: mp4, type: "video/mp4" },
        { src: webm, type: "video/webm" },
      ]
    : [
        { src: webm, type: "video/webm" },
        { src: mp4, type: "video/mp4" },
      ];

  video.replaceChildren();
  for (const item of ordered) {
    const source = document.createElement("source");
    source.src = item.src;
    source.type = item.type;
    video.appendChild(source);
  }
}

function tryPlay(video: HTMLVideoElement) {
  video.muted = true;
  video.defaultMuted = true;
  video.playsInline = true;
  video.setAttribute("playsinline", "");
  video.setAttribute("webkit-playsinline", "");

  const play = () => {
    const result = video.play();
    if (result && typeof result.catch === "function") {
      result.catch(() => {
        /* 低电量 / 策略拦截：保留静帧，不抛错 */
      });
    }
  };

  if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
    play();
    return;
  }

  video.addEventListener("canplay", play, { once: true });
  video.load();
}

function initHeroVideo(root: HTMLElement) {
  if (root.dataset.aeiVideoBound === "true") return;

  const video = root.querySelector<HTMLVideoElement>(".aei-hero-video");
  if (!video) return;

  root.dataset.aeiVideoBound = "true";
  applyPreferredSources(video);

  const markReady = () => {
    root.classList.add("is-ready");
    root.removeAttribute("aria-busy");
  };

  root.setAttribute("aria-busy", "true");

  const onError = () => {
    markReady();
    root.classList.add("is-error");
  };

  if (video.readyState >= HTMLMediaElement.HAVE_FUTURE_DATA) {
    markReady();
  } else {
    video.addEventListener("canplay", markReady, { once: true });
    video.addEventListener("loadeddata", markReady, { once: true });
    video.addEventListener("error", onError, { once: true });
  }

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          tryPlay(video);
          observer.disconnect();
          break;
        }
      }
    },
    { rootMargin: "80px 0px", threshold: 0.15 },
  );

  observer.observe(root);
  tryPlay(video);
}

export function initPlatformHeroVideos() {
  document.querySelectorAll<HTMLElement>("[data-aei-hero-video]").forEach(initHeroVideo);
}
