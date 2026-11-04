import { useState } from "react";
import {
  getPromptEntries,
  type PromptEntry,
  type PromptCaseRow,
} from "@/lib/prompts-content";
import { CopyButton } from "./copy-button";


function CaseRow({ row }: { row: PromptCaseRow }) {
  return (
    <li className="pp-case-item">
      <span className="pp-case-row">
        <strong>{row.name}</strong>
        {row.packageName && <span className="pp-case-pinyin">{row.packageName}</span>}
      </span>
      {row.fact && <span className="pp-case-note-line">{row.fact}</span>}
      {row.note && <span className="pp-case-note-line">{row.note}</span>}
      {row.primaryDomain && (
        <span className="pp-case-note-line">
          <span className="pp-case-domains-label">推荐域名 </span>
          <span className="pp-case-domains">{row.primaryDomain}</span>
        </span>
      )}
      {row.domains && row.domains.length > 0 && (
        <span className="pp-case-note-line">
          <span className="pp-case-domains-label">候选域名 </span>
          <span className="pp-case-domains">
            {row.domains.map((domain) => domain.replace(/·(?:rdap|whois)(?=）)/g, "")).join("  ")}
          </span>
        </span>
      )}
    </li>
  );
}

/** 提示词默认只露几行，卡片底部一个文字 icon 按钮负责展开与收起。 */
function PromptBlock({ prompt, promptId }: { prompt: string; promptId: string }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="pp-prompt-card">
      <div
        id={promptId}
        className={open ? "pp-prompt pp-prompt-open" : "pp-prompt pp-prompt-clamp"}
      >
        <pre tabIndex={0}>{prompt}</pre>
      </div>
      <button
        type="button"
        className="pp-fold-toggle"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        aria-controls={promptId}
        aria-label={open ? "收起提示词全文" : "展开提示词全文"}
      >
        <span className="pp-fold-icon" aria-hidden="true">
          {open ? "▾" : "▸"}
        </span>
        {open ? "收起" : "展开"}
      </button>
    </div>
  );
}

function PromptEntrySection({ entry }: { entry: PromptEntry }) {
  return (
    <article className="pp-entry" id={entry.id}>
      <header className="pp-entry-head">
        <CopyButton text={entry.prompt} label={entry.promptLabel} />
      </header>

      <PromptBlock prompt={entry.prompt} promptId={`${entry.id}-prompt`} />

      {entry.inputText && (
        <div className="pp-case pp-case-input">
          <p className="pp-case-note">实测输入</p>
          <p className="pp-input-text">{entry.inputText}</p>
        </div>
      )}

      <div className="pp-case">
        <p className="pp-case-note">实测结果</p>
        <ul>
          {entry.caseRows.map((row) => (
            <CaseRow key={row.name} row={row} />
          ))}
        </ul>
        {entry.domainsNote && <p className="pp-case-note pp-case-domains-note">{entry.domainsNote}</p>}
      </div>
    </article>
  );
}

export function PromptsPage() {
  const promptEntries = getPromptEntries();
  const [first] = promptEntries;
  return (
    <div className="pp-doc">
      <header className="pp-doc-head">
        <div className="pp-doc-actions">
          <a
            className="pp-gh"
            href="https://github.com/hey-yx/NameYouLike"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="NameYouLike 的 GitHub 仓库"
            title="GitHub 仓库"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 .5C5.73.5.5 5.73.5 12c0 5.08 3.29 9.39 7.86 10.91.58.11.79-.25.79-.55 0-.27-.01-1.17-.02-2.12-3.2.7-3.88-1.36-3.88-1.36-.52-1.33-1.28-1.68-1.28-1.68-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.03 1.76 2.7 1.25 3.36.96.1-.75.4-1.25.72-1.54-2.56-.29-5.25-1.28-5.25-5.7 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.18 1.18a11.1 11.1 0 0 1 5.79 0c2.2-1.49 3.17-1.18 3.17-1.18.63 1.59.24 2.76.12 3.05.74.81 1.18 1.84 1.18 3.1 0 4.43-2.7 5.41-5.27 5.69.41.36.78 1.06.78 2.14 0 1.55-.01 2.8-.01 3.18 0 .31.21.67.8.55A11.51 11.51 0 0 0 23.5 12C23.5 5.73 18.27.5 12 .5z" />
            </svg>
          </a>
        </div>
        <h1>{first.title}</h1>
        {first.description && <p className="pp-doc-lede">{first.description}</p>}
      </header>

      <main>
        {promptEntries.map((entry) => (
          <PromptEntrySection key={entry.id} entry={entry} />
        ))}
      </main>

      <footer className="pp-doc-foot">
        <a href="https://beian.miit.gov.cn" target="_blank" rel="noopener noreferrer">
          鲁ICP备2024099705号
        </a>
      </footer>
    </div>
  );
}
