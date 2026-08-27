from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

from .. import reports as reports_mod

router = APIRouter(prefix="/api/reports", tags=["reports"])

@router.get("/stats")
def reports_stats(days: int = 30, profile: str | None = None) -> dict[str, Any]:
    return reports_mod.compute_stats(days=max(1, min(days, 365)), profile=profile or None)


@router.get("/export.csv")
def reports_export_csv(
    days: int = 30,
    only_bad: bool = False,
    profile: str | None = None,
) -> Response:
    content = reports_mod.export_csv(
        days=max(1, min(days, 365)),
        only_non_compliant=only_bad,
        profile=profile or None,
    )
    filename = "vigiepp_incumplimientos.csv" if only_bad else "vigiepp_escaneos.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/print")
def reports_print(days: int = 7, profile: str | None = None) -> dict[str, Any]:
    return reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)


@router.get("/print.html", response_class=HTMLResponse)
def reports_print_html(days: int = 7, profile: str | None = None) -> HTMLResponse:
    report = reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)
    return HTMLResponse(report.get("html") or "<p>Sin informe</p>")


@router.get("/summary.txt")
def reports_summary_txt(days: int = 7, profile: str | None = None) -> PlainTextResponse:
    report = reports_mod.build_printable_report(days=max(1, min(days, 365)), profile=profile or None)
    return PlainTextResponse(report["text"], media_type="text/plain; charset=utf-8")


