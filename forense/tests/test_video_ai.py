"""Tests interpretación visual."""

from __future__ import annotations

from forense.app.video_ai import format_video_ai_markdown


def test_format_video_ai_markdown_parsed():
    md = format_video_ai_markdown(
        {
            "parsed": {
                "resumen": "Se observa retroceso de camión.",
                "secuencia": [{"hora": "01:10", "observacion": "Persona cerca de carga"}],
                "posibles_falsos_positivos": ["Contenedor marcado como persona"],
            }
        }
    )
    assert "retroceso" in md
    assert "falsos positivos" in md.lower()


def test_format_video_ai_missing():
    assert "no disponible" in format_video_ai_markdown(None).lower()
