# SPDX-License-Identifier: AGPL-3.0-or-later
"""Theme API (M0S-E13-04; contract in docs/backlog/m0-star/E13-theming-system.md).

``GET /theme``, ``/theme/active.css`` and ``/theme/assets/…`` are public (the login page needs them) and expose
only theme data. Assets are served only when the theme references them, from a valid theme, by exact path.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import FileResponse, Response

from hauskraft_core.auth.deps import CurrentActor, CurrentSession
from hauskraft_core.db.session import DbSession
from hauskraft_core.settings_store.service import set_theme
from hauskraft_core.themes.compile import asset_url
from hauskraft_core.themes.model import ThemeReport
from hauskraft_core.themes.registry import ThemeRegistry, ThemeSummary, stored_theme_id
from hauskraft_core.themes.validate import referenced_assets
from hauskraft_core.uow import UnitOfWork
from hauskraft_sdk.errors import HauskraftError, NotFoundError

router = APIRouter(tags=["themes"])

CONTENT_TYPES = {
    ".woff2": "font/woff2",
    ".png": "image/png",
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".svg": "image/svg+xml",
}
ASSET_HEADERS = {"Cache-Control": "public, max-age=31536000, immutable", "X-Content-Type-Options": "nosniff"}
THEME_ID = r"^[a-z0-9]+(\.[a-z0-9-]+)+(:[a-z0-9-]+)?$"


class NoThemeError(HauskraftError):
    status = 503
    code = "no_theme"
    title = "No usable theme"


class _Out(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WidgetVariants(_Out):
    chrome: str
    header: str


class ButtonVariants(_Out):
    primary: str


class CheckboxVariants(_Out):
    style: str


class Components(_Out):
    widget: WidgetVariants
    button: ButtonVariants
    checkbox: CheckboxVariants


class Navigation(_Out):
    wide: str
    narrow: str


class Layout(_Out):
    navigation: Navigation
    density: str
    content_width: str


class Icons(_Out):
    sprite_url: str | None
    names: list[str]


class ActiveTheme(_Out):
    theme_id: str
    name: str
    hash: str
    css_url: str
    components: Components
    layout: Layout
    icons: Icons


class ThemeSelect(_Out):
    theme_id: Annotated[str, Field(min_length=1, max_length=200, pattern=THEME_ID)]


def _registry(request: Request) -> ThemeRegistry:
    registry: ThemeRegistry = request.app.state.themes
    return registry


async def _active(request: Request, db: DbSession) -> ThemeReport:
    report = _registry(request).resolve(await stored_theme_id(db))
    if report is None:
        raise NoThemeError("Neither the chosen theme nor the built-in Default theme is usable.")
    return report


def _active_out(report: ThemeReport) -> ActiveTheme:
    theme = report.theme
    components, layout = theme["components"], theme["layout"]
    pack = (theme.get("icons") or {}).get("pack")
    return ActiveTheme(
        theme_id=report.theme_id,
        name=report.name,
        hash=report.hash,
        css_url=f"/api/v1/theme/active.css?h={report.hash[:16]}",
        components=Components(
            widget=WidgetVariants(chrome=components["widget"]["chrome"], header=components["widget"]["header"]),
            button=ButtonVariants(primary=components["button"]["primary"]),
            checkbox=CheckboxVariants(style=components["checkbox"]["style"]),
        ),
        layout=Layout(
            navigation=Navigation(wide=layout["navigation"]["wide"], narrow=layout["navigation"]["narrow"]),
            density=layout["density"],
            content_width=layout["content_width"],
        ),
        icons=Icons(sprite_url=asset_url(report, pack) if pack else None, names=report.icon_names if pack else []),
    )


@router.get("/themes", operation_id="themes_list", responses={401: {}})
async def list_(request: Request, db: DbSession, _: CurrentSession) -> list[ThemeSummary]:
    registry = _registry(request)
    active = registry.resolve(await stored_theme_id(db))
    return registry.summaries(active.theme_id if active else None)


@router.get("/theme", responses={503: {}})
async def active(request: Request, db: DbSession) -> ActiveTheme:
    return _active_out(await _active(request, db))


@router.get(
    "/theme/active.css",
    response_class=Response,
    responses={200: {"content": {"text/css": {"schema": {"type": "string"}}}}, 304: {}, 503: {}},
)
async def active_css(
    request: Request, db: DbSession, if_none_match: Annotated[str | None, Header()] = None
) -> Response:
    report = await _active(request, db)
    etag = f'"{report.hash}"'
    headers = {"ETag": etag, "Cache-Control": "no-cache"}
    if if_none_match is not None and etag in {t.strip() for t in if_none_match.split(",")}:
        return Response(status_code=304, headers=headers)
    return Response(report.css or "", media_type="text/css", headers=headers)


@router.get(
    "/theme/assets/{theme_id}/{path:path}",
    response_class=FileResponse,
    responses={200: {"content": {t: {} for t in sorted(set(CONTENT_TYPES.values()))}}, 404: {}},
)
async def asset(theme_id: str, path: str, request: Request) -> Response:
    """Serve one asset the theme references. ``?h=`` is only a cache key; the URL changes with the hash."""
    report = _registry(request).get(theme_id)
    if report is None or not report.valid or path not in {rel for rel, _ in referenced_assets(report.theme)}:
        raise NotFoundError("No such theme asset.")
    file = report.folder / path
    content_type = CONTENT_TYPES.get(file.suffix.lower())
    if content_type is None or not file.is_file() or file.is_symlink():
        raise NotFoundError("No such theme asset.")
    return FileResponse(file, media_type=content_type, headers=ASSET_HEADERS)


@router.put(
    "/settings/theme",
    operation_id="settings_theme_set",
    responses={401: {}, 403: {}, 404: {}, 409: {}, 422: {}},
)
async def theme_set(body: ThemeSelect, request: Request, actor: CurrentActor) -> ThemeSummary:
    """Set the household theme for every user and device (any adult in M0*)."""
    state = request.app.state
    async with UnitOfWork(state.sessionmaker, state.policy, state.settings) as uow:
        report = await set_theme(uow, actor, state.themes, body.theme_id)
    return _registry(request).summary(report, report.theme_id)
