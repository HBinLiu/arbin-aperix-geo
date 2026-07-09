import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Aperix Payload CMS",
};

/** Payload RootLayout 会自行渲染 <html>/<body>，根布局勿再包一层。 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
