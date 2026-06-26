import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { preloadGeistFonts } from "@/lib/fonts";
import { initTheme } from "@/lib/theme";
import { installRechartsMeasurementSpanFix } from "@/lib/recharts";

import "@/styles/geist.css";

import App from "./App.tsx";
import "./index.css";

preloadGeistFonts();
installRechartsMeasurementSpanFix();
initTheme();

async function mount() {
  try {
    await Promise.race([
      document.fonts.load('400 1rem "Geist Variable"'),
      new Promise<void>((resolve) => {
        window.setTimeout(resolve, 120);
      }),
    ]);
  } catch {
    /* 字体不可用时仍正常挂载 */
  }

  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}

void mount();
