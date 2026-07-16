export { BriefBlock } from "./definitions/BriefBlock";
export { CalloutBlock } from "./definitions/CalloutBlock";
export { ChapterBlock } from "./definitions/ChapterBlock";
export { FigureBlock } from "./definitions/FigureBlock";
export { HighlightBlock } from "./definitions/HighlightBlock";
export { InfoGridBlock } from "./definitions/InfoGridBlock";
export { InlineCtaBlock } from "./definitions/InlineCtaBlock";

import { BriefBlock } from "./definitions/BriefBlock";
import { CalloutBlock } from "./definitions/CalloutBlock";
import { ChapterBlock } from "./definitions/ChapterBlock";
import { FigureBlock } from "./definitions/FigureBlock";
import { HighlightBlock } from "./definitions/HighlightBlock";
import { InfoGridBlock } from "./definitions/InfoGridBlock";
import { InlineCtaBlock } from "./definitions/InlineCtaBlock";

/** news / blog / academy 正文编辑器可用 blocks */
export const contentLexicalBlocks = [
  CalloutBlock,
  HighlightBlock,
  ChapterBlock,
  InfoGridBlock,
  FigureBlock,
  BriefBlock,
  InlineCtaBlock,
];
