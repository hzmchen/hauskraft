// SPDX-License-Identifier: AGPL-3.0-or-later
// The browser title inside the shell (M1S-E04-04): "<page heading> · <household name>", so several open tabs can
// be told apart. The heading is read from the page's <h1>, which every core and plugin page has; signed-out pages
// keep "Hauskraft".
import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { householdQuery } from "../household";

export const APP_TITLE = "Hauskraft";

export function DocumentTitle() {
  const { data: household } = useQuery(householdQuery());
  const [heading, setHeading] = useState("");

  useEffect(() => {
    const main = document.getElementById("content");
    if (!main) return;
    const read = () => setHeading(main.querySelector("h1")?.textContent?.trim() ?? "");
    read();
    const observer = new MutationObserver(read);
    observer.observe(main, { childList: true, subtree: true, characterData: true });
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    document.title = [heading, household?.name].filter(Boolean).join(" · ") || APP_TITLE;
  }, [heading, household?.name]);

  useEffect(
    () => () => {
      document.title = APP_TITLE;
    },
    [],
  );

  return null;
}
