/** 平台页 Hero 视频：桌面优先 WebM；iOS / 微信 / 不支持 WebM 时用 MP4；微信失败可点播 */

function isWeChatBrowser(): boolean {
  return /MicroMessenger/i.test(navigator.userAgent);
}

function isAppleTouchDevice(): boolean {
  const ua = navigator.userAgent;
  if (/iPhone|iPod|iPad/i.test(ua)) return true;
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

/** 微信 / iOS：强制 MP4；其它环境能播 WebM 才用 WebM */
function resolvePreferredSrc(video: HTMLVideoElement): string | null {
  const webm = video.dataset.srcWebm;
  const mp4 = video.dataset.srcMp4;
  if (!webm && !mp4) return null;

  if (isWeChatBrowser() || isAppleTouchDevice()) return mp4 || webm || null;
  if (webm && canPlayWebm(video)) return webm;
  return mp4 || webm || null;
}

function applyWeChatAttributes(video: HTMLVideoElement) {
  video.muted = true;
  video.defaultMuted = true;
  video.playsInline = true;
  video.setAttribute("muted", "");
  video.setAttribute("playsinline", "");
  video.setAttribute("webkit-playsinline", "");
  video.setAttribute("x5-playsinline", "true");
  video.setAttribute("x5-video-player-type", "h5");
  video.setAttribute("x5-video-player-fullscreen", "true");
}

function applyPreferredSource(video: HTMLVideoElement) {
  const src = resolvePreferredSrc(video);
  if (!src) return;

  // 微信/部分 WebView 对多 <source> 不稳定，直接设 src 更可靠
  video.replaceChildren();
  video.removeAttribute("src");
  video.src = src;
}

function showPlayButton(root: HTMLElement, show: boolean) {
  const btn = root.querySelector<HTMLButtonElement>("[data-aei-hero-play]");
  if (!btn) return;
  btn.hidden = !show;
}

function tryPlay(video: HTMLVideoElement): Promise<boolean> {
  applyWeChatAttributes(video);

  const result = video.play();
  if (result && typeof result.then === "function") {
    return result.then(() => true).catch(() => false);
  }
  return Promise.resolve(!video.paused);
}

function onWeixinReady(callback: () => void) {
  if (!isWeChatBrowser()) {
    callback();
    return;
  }

  const win = window as Window & {
    WeixinJSBridge?: { invoke?: (...args: unknown[]) => void };
  };

  if (win.WeixinJSBridge) {
    callback();
    return;
  }

  document.addEventListener("WeixinJSBridgeReady", callback, { once: true });
  // 部分场景 Bridge 不触发，超时后仍尝试播放
  window.setTimeout(callback, 1200);
}

function initHeroVideo(root: HTMLElement) {
  if (root.dataset.aeiVideoBound === "true") return;

  const video = root.querySelector<HTMLVideoElement>(".aei-hero-video");
  if (!video) return;

  root.dataset.aeiVideoBound = "true";
  applyWeChatAttributes(video);
  applyPreferredSource(video);

  const markReady = () => {
    root.classList.add("is-ready");
    root.removeAttribute("aria-busy");
  };

  const markNeedsGesture = () => {
    markReady();
    root.classList.add("is-needs-gesture");
    showPlayButton(root, true);
  };

  root.setAttribute("aria-busy", "true");
  showPlayButton(root, false);

  const playBtn = root.querySelector<HTMLButtonElement>("[data-aei-hero-play]");
  playBtn?.addEventListener("click", () => {
    void tryPlay(video).then((ok) => {
      if (ok) {
        root.classList.remove("is-needs-gesture");
        showPlayButton(root, false);
        markReady();
      }
    });
  });

  video.addEventListener(
    "error",
    () => {
      markReady();
      root.classList.add("is-error");
      showPlayButton(root, false);
    },
    { once: true },
  );

  video.addEventListener("playing", () => {
    markReady();
    root.classList.remove("is-needs-gesture");
    showPlayButton(root, false);
  });

  video.addEventListener("loadeddata", markReady, { once: true });
  video.addEventListener("canplay", markReady, { once: true });

  const attemptAutoplay = () => {
    void tryPlay(video).then((ok) => {
      if (ok) {
        markReady();
        return;
      }
      // 微信常拦截自动播放：露出点击播放
      markNeedsGesture();
    });
  };

  const observer = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          onWeixinReady(attemptAutoplay);
          observer.disconnect();
          break;
        }
      }
    },
    { rootMargin: "80px 0px", threshold: 0.15 },
  );

  observer.observe(root);
  video.load();
  onWeixinReady(attemptAutoplay);
}

export function initPlatformHeroVideos() {
  document.querySelectorAll<HTMLElement>("[data-aei-hero-video]").forEach(initHeroVideo);
}
