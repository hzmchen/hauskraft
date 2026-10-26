// SPDX-License-Identifier: AGPL-3.0-or-later
// A safe markdown subset for assistant answers (M2S-E06-03): paragraphs, "- " and "1. " lists, **bold** and links to
// app routes. Everything is rendered as React text; there is no raw HTML.
import { Link } from "@tanstack/react-router";
import type { ReactNode } from "react";

const INLINE = /(\*\*[^*]+\*\*|\[[^\]]+\]\(\/[^)\s]*\))/g;

function inline(text: string): ReactNode[] {
  return text.split(INLINE).map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**") && part.length > 4)
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    const link = /^\[([^\]]+)\]\((\/[^)\s]*)\)$/.exec(part);
    if (link)
      return (
        <Link key={i} to={link[2]} className="underline">
          {link[1]}
        </Link>
      );
    return part;
  });
}

export function Markdown({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/);
  return (
    <>
      {blocks.map((block, i) => {
        const lines = block.split("\n");
        const bullet = lines.every((l) => /^\s*[-*] /.test(l));
        const numbered = lines.every((l) => /^\s*\d+\. /.test(l));
        if (bullet || numbered) {
          const items = lines.map((l, j) => <li key={j}>{inline(l.replace(/^\s*([-*]|\d+\.) /, ""))}</li>);
          return numbered ? (
            <ol key={i} className="list-decimal pl-5">
              {items}
            </ol>
          ) : (
            <ul key={i} className="list-disc pl-5">
              {items}
            </ul>
          );
        }
        return (
          <p key={i} className="whitespace-pre-line">
            {inline(block)}
          </p>
        );
      })}
    </>
  );
}
