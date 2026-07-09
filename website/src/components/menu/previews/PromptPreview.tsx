import type { MenuPreviewProps } from "@/lib/menu";

export default function PromptPreview({ className = "" }: MenuPreviewProps) {
  return (
    <div aria-hidden className={`pve-widgetContainer ${className}`.trim()}>
      <div className="pve-windowFrame">
        <div className="pve-windowHeader">
          <div className="pve-dot" />
          <div className="pve-dot" />
          <div className="pve-dot" />
        </div>
        <div className="pve-chartArea">
          <div className="pve-bar" />
          <div className="pve-bar" />
          <div className="pve-bar" />
          <div className="pve-bar" />
          <div className="pve-bar" />
          <div className="pve-chartBaseline" />
          <div className="pve-tooltip">
            <span className="pve-tLabel">搜索量</span>
            <span className="pve-tValue">12.5M</span>
          </div>
        </div>
      </div>
    </div>
  );
}
