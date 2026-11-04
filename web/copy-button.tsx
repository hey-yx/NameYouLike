"use client";

import { useRef, useState } from "react";

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  return (
    <button
      type="button"
      className={copied ? "pp-copy pp-copy-done" : "pp-copy"}
      data-copy={text}
      aria-label={`复制${label}全文`}
      onClick={() => {
        navigator.clipboard
          .writeText(text)
          .then(() => {
            setCopied(true);
            if (timer.current) clearTimeout(timer.current);
            timer.current = setTimeout(() => setCopied(false), 1600);
          })
          .catch(() => {
            // 非安全上下文或未授权时保持静默，不影响阅读
          });
      }}
    >
      {copied ? "已复制" : "复制"}
    </button>
  );
}
