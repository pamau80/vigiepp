"""Recarga de singletons al cambiar sitio / faena activa."""

from __future__ import annotations

import logging

logger = logging.getLogger("vigiepp.site_reload")


def reload_site_context() -> None:
    from .identity import IdentityRegistry
    from .teach import TeachStore
    from . import notifications as notif_mod
    from . import watchlist as watch_mod
    from . import nvr as nvr_mod

    IdentityRegistry.reset_for_site()
    TeachStore.reset_for_site()
    notif_mod.refresh_paths()
    watch_mod.refresh_paths()
    nvr_mod.refresh_paths()
    try:
        from .stream_rtsp import stop_all

        stop_all()
    except Exception:  # noqa: BLE001
        logger.debug("stop_all streams omitido", exc_info=True)
    logger.info("Contexto de sitio recargado")
