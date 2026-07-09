import React from "react";

type Props = {
  words: string[];
};

export default function DiagnosticWord({ words }: Props) {
  const [index, setIndex] = React.useState(0);

  React.useEffect(() => {
    if (words.length <= 1) return;

    const interval = window.setInterval(() => {
      setIndex((current) => (current + 1) % words.length);
    }, 2800);

    return () => window.clearInterval(interval);
  }, [words.length]);

  if (!words.length) return null;

  return (
    <span className="diagnostic-word-shell" aria-live="polite">
      <span key={words[index]} className="diagnostic-word">
        {words[index]}
      </span>
    </span>
  );
}
