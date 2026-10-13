<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->

# Content Security Policy notes for the web shell

`index.html` carries one inline script: it applies the device's colour mode (`localStorage["hearthos.mode"]`,
falling back to `prefers-color-scheme`) before first paint, so a dark device never flashes light (M0S-E08-02).

A strict CSP (E11-01) allows exactly this script by hash:

```text
script-src 'self' 'sha256-KIh951ASrNEqT/NFVFX9b2OTZvn5mM0OSS49tXdSf/8='
```

Any change to the script changes the hash; `src/shell/ColorMode.test.tsx` fails until this file is updated.
