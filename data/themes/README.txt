Hauskraft theme folder
=====================

Put each theme package in its own folder here, for example:

    data/themes/my-theme/hauskraft.plugin.json
    data/themes/my-theme/theme.json
    data/themes/my-theme/tokens.light.json
    data/themes/my-theme/tokens.dark.json

Start from themes/template in the repository, check it with
`hauskraft themes validate data/themes/my-theme`, then run
`docker compose restart api` and pick the theme in Settings -> Appearance.
Invalid themes are listed with their reasons but cannot be selected.

Guide: docs/themes.md
