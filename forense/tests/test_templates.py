"""Tests plantillas por industria."""

from __future__ import annotations

from forense.app.templates import list_templates, resolve_template


def test_list_templates():
    tpls = list_templates()
    assert len(tpls) >= 12
    ids = {t["id"] for t in tpls}
    assert "mineria" in ids
    assert "petroquimica" in ids
    assert "general" in ids
    assert tpls[0].get("meters_per_pixel") is not None


def test_resolve_template_defaults():
    tpl = resolve_template(None)
    assert tpl["id"] == "general"
    tpl2 = resolve_template("portuario")
    assert tpl2["profile"] == "portuario"
    tpl3 = resolve_template("unknown")
    assert tpl3["id"] == "general"
