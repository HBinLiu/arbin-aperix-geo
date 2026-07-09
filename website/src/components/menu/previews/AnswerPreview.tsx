import type { MenuPreviewProps } from "@/lib/menu";

const STAR_PATH = "M12 2L14.5 9.5L22 12L14.5 14.5L12 22L9.5 14.5L2 12L9.5 9.5L12 2Z";

export default function AnswerPreview({ className = "" }: MenuPreviewProps) {
  return (
    <div aria-hidden className={`ae-widgetContainer ${className}`.trim()}>
      <div className="ae-layoutWrapper">
        <div className="ae-iconCircle">
          <svg className="ae-starSvg" viewBox="0 0 24 24">
            <path d={STAR_PATH} />
          </svg>
        </div>
        <div className="ae-connectorLine" />
        <div className="ae-contentCard">
          <div className="ae-line ae-lineTitle" />
          <div className="ae-line ae-lineLong" />
          <div className="ae-line ae-lineShort" />
          <div className="ae-badge"># 1 来源</div>
        </div>
      </div>
    </div>
  );
}
