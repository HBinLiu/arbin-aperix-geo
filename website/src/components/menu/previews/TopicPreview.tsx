import type { MenuPreviewProps } from "@/lib/menu";

function FloatCard({
  positionClass,
  orangeWidth,
  title,
  subtitle,
  iconPath,
}: {
  positionClass: string;
  orangeWidth?: string;
  title: string;
  subtitle: string;
  iconPath: string;
}) {
  return (
    <div className={`ftai-floatCard ${positionClass}`}>
      <div className="ftai-skeletonLayer">
        <div
          className="ftai-skLine ftai-skLineOrange"
          style={orangeWidth ? { width: orangeWidth } : undefined}
        />
        <div className="ftai-skLine ftai-skLineGrey" />
      </div>
      <div className="ftai-activeLayer">
        <div className="ftai-iconBox">
          <svg viewBox="0 0 24 24">
            <path d={iconPath} />
          </svg>
        </div>
        <div className="ftai-textCol">
          <div className="ftai-cardTitle">{title}</div>
          <div className="ftai-cardSub">{subtitle}</div>
        </div>
      </div>
    </div>
  );
}

export default function TopicPreview({ className = "" }: MenuPreviewProps) {
  return (
    <div aria-hidden className={`ftai-widgetContainer ${className}`.trim()}>
      <div className="ftai-radarCenter">
        <div className="ftai-ring ftai-ring4" />
        <div className="ftai-ring ftai-ring3" />
        <div className="ftai-ring ftai-ring2" />
        <div className="ftai-ring ftai-ring1" />
        <div className="ftai-centerIconWrapper">
          <svg className="ftai-centerIcon" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="10" />
            <path d="M2 12h20" />
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
          </svg>
        </div>
      </div>

      <FloatCard
        positionClass="ftai-cardLeft"
        title="问题"
        subtitle="50 ideas"
        iconPath="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"
      />

      <FloatCard
        positionClass="ftai-cardTopRight"
        orangeWidth="50%"
        title="趋势"
        subtitle="24.5k"
        iconPath="M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z"
      />

      <FloatCard
        positionClass="ftai-cardBottomRight"
        title="关键词"
        subtitle="高意图"
        iconPath="M20 3H4c-1.1 0-1.99.9-1.99 2L2 17c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-9 3h2v2h-2V6zm0 3h2v2h-2V9zM8 6h2v2H8V6zm0 3h2v2H8V9zm-1 4H5v-2h2v2zm0-3H5V9h2v2zm0-3H5V6h2v2zm9 7H8v-2h8v2zm0-3h-2V9h2v2zm0-3h-2V6h2v2zm3 6h-2v-2h2v2zm0-3h-2V9h2v2zm0-3h-2V6h2v2z"
      />
    </div>
  );
}
