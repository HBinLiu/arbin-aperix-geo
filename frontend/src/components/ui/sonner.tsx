import { useEffect, useState } from "react";
import { Toaster as Sonner, type ToasterProps } from "sonner";

function useDocumentTheme(): "light" | "dark" {
  const [theme, setTheme] = useState<"light" | "dark">(() =>
    typeof document !== "undefined" && document.documentElement.classList.contains("dark") ? "dark" : "light",
  );

  useEffect(() => {
    const root = document.documentElement;
    const sync = () => setTheme(root.classList.contains("dark") ? "dark" : "light");
    const observer = new MutationObserver(sync);
    observer.observe(root, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return theme;
}

export function Toaster(props: ToasterProps) {
  const theme = useDocumentTheme();

  return (
    <Sonner
      theme={theme}
      position="bottom-right"
      visibleToasts={5}
      duration={5200}
      className="toaster group"
      toastOptions={{
        classNames: {
          toast: "group toast rounded-lg border p-4 shadow-lg",
          title: "text-sm font-medium leading-relaxed",
          description: "text-sm leading-relaxed",
          actionButton: "group-[.toast]:bg-primary group-[.toast]:text-primary-foreground",
          cancelButton: "group-[.toast]:bg-muted group-[.toast]:text-muted-foreground",
          error: "!border-error/50 !bg-error !text-muted-background [&_[data-icon]]:text-muted-background",
          success: "!border-success/50 !bg-success !text-muted-background [&_[data-icon]]:text-muted-background",
          info: "!border-border !bg-muted-background !text-foreground [&_[data-icon]]:text-foreground",
        },
      }}
      {...props}
    />
  );
}
