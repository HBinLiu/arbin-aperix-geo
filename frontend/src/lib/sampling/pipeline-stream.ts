import type { PipelineStatus } from "@/types";

import { getStoredToken } from "@/api/client";
import { isPipelineComplete } from "@/lib/sampling/job-status";

export type PipelineStreamMeta = {
  connected: boolean;
  complete: boolean;
  error: string | null;
};

export type PipelineStreamListener = (
  status: PipelineStatus,
  meta: PipelineStreamMeta,
) => void;

function parseSseChunk(chunk: string): { event: string; data: string } | null {
  let event = "message";
  let data = "";
  for (const line of chunk.split("\n")) {
    if (line.startsWith("event:")) {
      event = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }
  if (!data) return null;
  return { event, data };
}

class PipelineStreamHub {
  private subjectId: string | null = null;
  private abort: AbortController | null = null;
  private listeners = new Set<PipelineStreamListener>();
  private lastStatus: PipelineStatus | null = null;
  private meta: PipelineStreamMeta = { connected: false, complete: false, error: null };
  private reconnectTimer: number | null = null;

  subscribe(subjectId: string, listener: PipelineStreamListener): () => void {
    this.listeners.add(listener);
    if (this.lastStatus && this.subjectId === subjectId) {
      listener(this.lastStatus, this.meta);
    }
    this.ensureStream(subjectId);
    return () => {
      this.listeners.delete(listener);
      if (this.listeners.size === 0) {
        this.stop();
      }
    };
  }

  reconnect(subjectId: string) {
    this.stop();
    this.lastStatus = null;
    this.meta = { connected: false, complete: false, error: null };
    this.ensureStream(subjectId);
  }

  private emit(status: PipelineStatus, meta: PipelineStreamMeta) {
    this.lastStatus = status;
    this.meta = meta;
    for (const listener of this.listeners) {
      listener(status, meta);
    }
  }

  private ensureStream(subjectId: string) {
    if (this.subjectId === subjectId && this.abort) return;
    this.stop();
    this.subjectId = subjectId;
    void this.runStream(subjectId);
  }

  private scheduleReconnect(subjectId: string) {
    if (this.listeners.size === 0 || this.meta.complete) return;
    if (this.reconnectTimer != null) return;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      if (this.listeners.size > 0 && this.subjectId === subjectId && !this.meta.complete) {
        this.ensureStream(subjectId);
      }
    }, 3000);
  }

  private stop() {
    if (this.reconnectTimer != null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.abort?.abort();
    this.abort = null;
    this.subjectId = null;
    this.meta = { ...this.meta, connected: false };
  }

  private async runStream(subjectId: string) {
    const controller = new AbortController();
    this.abort = controller;

    const token = getStoredToken();
    const headers: Record<string, string> = { Accept: "text/event-stream" };
    if (token) headers.Authorization = `Bearer ${token}`;

    try {
      const response = await fetch(`/api/v1/subjects/${subjectId}/pipeline/stream`, {
        headers,
        signal: controller.signal,
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      if (!response.body) {
        throw new Error("Empty stream");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      this.meta = { connected: true, complete: false, error: null };
      if (this.lastStatus) {
        for (const listener of this.listeners) {
          listener(this.lastStatus, this.meta);
        }
      }

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const frames = buffer.split("\n\n");
        buffer = frames.pop() ?? "";

        for (const frame of frames) {
          if (!frame.trim() || frame.trim().startsWith(":")) continue;
          const parsed = parseSseChunk(frame);
          if (!parsed) continue;

          if (parsed.event === "error") {
            this.emit(this.lastStatus ?? emptyPipelineStatus(), {
              connected: false,
              complete: false,
              error: "无法获取采样进度",
            });
            return;
          }

          const status = JSON.parse(parsed.data) as PipelineStatus;
          const complete =
            parsed.event === "complete" || isPipelineComplete(status);
          this.emit(status, { connected: true, complete, error: null });
          if (complete) {
            controller.abort();
            return;
          }
        }
      }
    } catch (error) {
      if (controller.signal.aborted) return;
      this.emit(this.lastStatus ?? emptyPipelineStatus(), {
        connected: false,
        complete: this.meta.complete,
        error: error instanceof Error ? error.message : "连接中断",
      });
      this.scheduleReconnect(subjectId);
    }
  }
}

function emptyPipelineStatus(): PipelineStatus {
  return {
    stage: "verify",
    worker_phase: null,
    latest_job: null,
    llm_pending_count: 0,
    llm_ready_count: 0,
    crawl_ready_count: 0,
    response_count: 0,
    parsed_count: 0,
  };
}

export const pipelineStreamHub = new PipelineStreamHub();

export function reconnectPipelineStream(subjectId: string) {
  pipelineStreamHub.reconnect(subjectId);
}
