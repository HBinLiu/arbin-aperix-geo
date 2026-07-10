import type { MenuPreviewProps } from "@/lib/menu";

const STAR_PATH = "M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z";
const IMAGE_PATH =
  "M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z";

const CHECK_PATH =
  "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z";

export default function ContentPreview({ className = "" }: MenuPreviewProps) {
  return (
    <div aria-hidden className={`cc-widgetContainer ${className}`.trim()}>
      <div className="cc-cardsWrapper">
        <div className="cc-card cc-bgCard cc-bgLeft">
          <div className="cc-bgLine" />
          <div className="cc-bgLine cc-bgLineHalf" />
        </div>
        <div className="cc-card cc-bgCard cc-bgRight">
          <div className="cc-bgLine" />
          <div className="cc-bgLine cc-bgLineHalf" />
        </div>
        <div className="cc-card cc-mainCard">
          <div className="cc-cardHeader">
            <svg className="cc-imgIcon" viewBox="0 0 24 24">
              <path d={IMAGE_PATH} />
            </svg>
          </div>
          <div className="cc-textLines">
            <div className="cc-line cc-lineTitle" />
            <div className="cc-line cc-lineSub" />
            <div className="cc-line cc-lineLast" />
          </div>
        </div>
      </div>
      <div className="cc-controlBar">
        <svg className="cc-starIcon" viewBox="0 0 24 24">
          <path d={STAR_PATH} />
        </svg>
        <div className="cc-sliderTrack" />
        <div className="cc-knob" />
      </div>
      <div className="cc-optBtn">
        <div className="cc-iconContainer">
          <div className="cc-circleDefault" />
          <div className="cc-circleSuccess">
            <svg viewBox="0 0 24 24">
              <path d={CHECK_PATH} />
            </svg>
          </div>
        </div>
        <span className="cc-btnText">优化</span>
      </div>
    </div>
  );
}
