type DashboardPlaceholderProps = {
  title: string;
};

export function DashboardPlaceholder({ title }: DashboardPlaceholderProps) {
  return (
    <div className="flex h-full min-h-[16rem] flex-col items-center justify-center px-6 py-12 text-center">
      <p className="text-muted-foreground text-sm">{title}功能开发中，敬请期待。</p>
    </div>
  );
}
