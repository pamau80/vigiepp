"""Tests de etiquetas en español chileno."""

from __future__ import annotations

from forense.app.i18n_es_cl import label_event_type, label_kind, label_severity


def test_event_type_labels_es_cl():
    assert label_event_type("speed_violation") == "exceso de velocidad"
    assert label_event_type("proximity") == "proximidad crítica"
    assert label_kind("machinery") == "maquinaria"
    assert label_severity("critical") == "crítica"
