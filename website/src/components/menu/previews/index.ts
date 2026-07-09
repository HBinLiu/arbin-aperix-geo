import type { ComponentType } from "react";

import AnswerEnginePreview from "./AnswerEnginePreview";
import ContentCreationPreview from "./ContentCreationPreview";
import FindTopicsPreview from "./FindTopicsPreview";
import PromptVolumesPreview from "./PromptVolumesPreview";
import type { MenuPreviewId, MenuPreviewProps } from "./types";

export type { MenuPreviewId, MenuPreviewProps };

export const MENU_PREVIEWS: Record<MenuPreviewId, ComponentType<MenuPreviewProps>> = {
  "answer-engine": AnswerEnginePreview,
  "prompt-volumes": PromptVolumesPreview,
  "find-topics": FindTopicsPreview,
  "content-creation": ContentCreationPreview,
};
