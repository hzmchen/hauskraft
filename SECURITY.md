# Security policy

## Supported versions

HearthOS has no releases yet. Only the `main` branch is supported; fixes land there.

| Version | Supported |
|---|---|
| `main` | Yes |
| anything else | No |

## Reporting a vulnerability

Please **do not open a public issue** for security problems.

Report privately through GitHub: open the repository's **Security** tab and choose **Report a vulnerability** (GitHub private vulnerability reporting). Include what you found, how to reproduce it, which commit you tested and the impact you expect. If you cannot use GitHub, ask a maintainer in a public issue for a private contact without giving details.

We aim to acknowledge a report within 7 days and to agree on a disclosure date with you once a fix is ready. Reporters are credited unless they ask not to be.

## Scope notes

- The M0* demo runs over plain HTTP on localhost with `Secure` cookies off. Exposing it on a LAN or the internet without TLS is unsupported (spec §11.3).
- The demo password `hearthos-demo` is public by design and must never be used outside the demo.
- Theme packages are data only. A theme that executes script, loads remote resources or breaks out of a CSS declaration is a vulnerability in the validator or compiler; please report it (spec §11.1).
