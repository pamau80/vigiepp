"""Tests motor de reglas Acciones inseguras."""

from __future__ import annotations

import pytest

from app import actions as actions_mod


@pytest.fixture(autouse=True)
def isolated_actions(tmp_path, monkeypatch):
    path = tmp_path / "action_rules.json"
    monkeypatch.setattr(actions_mod, "ACTIONS_FILE", path)
    actions_mod._last_trigger.clear()
    actions_mod.save_rules(actions_mod._default_payload()["rules"])
    yield


def test_epp_non_compliant_rule():
    detections = [{"label": "Person", "box": [10, 10, 100, 200], "confidence": 0.9}]
    compliance = {
        "overall_compliant": False,
        "persons": [{"missing": ["casco"], "violations": ["casco"]}],
    }
    out = actions_mod.evaluate_actions(detections, 640, 480, compliance=compliance)
    ids = [t["rule_id"] for t in out["triggered"]]
    assert "preset-epp-faena" in ids


def test_proximity_person_forklift():
    rules = actions_mod.get_rules()["rules"]
    for r in rules:
        if r["id"] == "preset-montacargas-prox":
            r["enabled"] = True
    actions_mod.save_rules(rules)
    detections = [
        {"label": "Person", "box": [100, 100, 160, 260], "confidence": 0.9},
        {"label": "Forklift", "box": [130, 120, 200, 280], "confidence": 0.8},
    ]
    out = actions_mod.evaluate_actions(detections, 640, 480, compliance={"overall_compliant": True, "persons": []})
    assert any(t["rule_id"] == "preset-montacargas-prox" for t in out["triggered"])


def test_cooldown_suppresses_repeat():
    detections = [{"label": "Person", "box": [10, 10, 100, 200], "confidence": 0.9}]
    compliance = {"overall_compliant": False, "persons": [{"missing": ["casco"]}]}
    first = actions_mod.evaluate_actions(detections, 640, 480, compliance=compliance)
    second = actions_mod.evaluate_actions(detections, 640, 480, compliance=compliance)
    assert len(first["triggered"]) >= 1
    assert len(second["triggered"]) == 0


def test_presets_api():
    presets = actions_mod.list_presets()
    assert any(p["id"] == "preset-celular-zona" for p in presets)
