/// <reference types="vite/client" />

interface ViewTransition {
  ready: Promise<void>;
  finished: Promise<void>;
  skipTransition: () => void;
  updateCallbackDone: Promise<void>;
}

interface Document {
  startViewTransition?(callback: () => void | Promise<void>): ViewTransition;
}
