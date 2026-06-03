import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";

export function AboutPage() {
  return (
    <div className="mx-auto max-w-2xl p-6">
      <Button variant="ghost" asChild className="mb-4">
        <Link to="/app">← 控制台</Link>
      </Button>
      <h1 className="text-xl font-semibold">关于</h1>
      <p className="text-muted-foreground mt-2 text-sm">Aperix GEO 品牌监测与生成式对话采样平台。</p>
    </div>
  );
}
