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
    assert len(presets) >= 22
    assert any(p["id"] == "preset-celular-zona" for p in presets)
    assert any(p["id"] == "preset-linea-fuego-1m" for p in presets)
    assert any(p["id"] == "preset-humo-incendio" for p in presets)


def test_detect_anywhere_celular():
    rules = actions_mod.get_rules()["rules"]
    for r in rules:
        if r["id"] == "preset-celular-faena":
            r["enabled"] = True
    actions_mod.save_rules(rules)
    actions_mod._last_trigger.clear()
    detections = [{"label": "cell phone", "box": [10, 10, 80, 120], "confidence": 0.85}]
    out = actions_mod.evaluate_actions(detections, 640, 480, compliance={"overall_compliant": True, "persons": []})
    assert any(t["rule_id"] == "preset-celular-faena" for t in out["triggered"])


def test_proximity_uses_meters_calibration():
    """Con m/px calibrado, distancia en metros controla el umbral."""
    actions_mod.save_settings({"meters_per_pixel": 0.05})
    rules = actions_mod.get_rules()["rules"]
    for r in rules:
        if r["id"] == "preset-montacargas-prox":
            r["enabled"] = True
            r["condition"]["max_distance_meters"] = 1.0
            r["condition"].pop("max_distance_ratio", None)
    actions_mod.save_rules(rules)
    actions_mod._last_trigger.clear()
    # Personas muy separadas (~200px en diagonal 800) — no debe disparar a 1m
    detections_far = [
        {"label": "Person", "box": [50, 50, 110, 210], "confidence": 0.9},
        {"label": "Forklift", "box": [400, 50, 460, 210], "confidence": 0.8},
    ]
    out_far = actions_mod.evaluate_actions(
        detections_far, 640, 480, compliance={"overall_compliant": True, "persons": []}
    )
    assert not any(t["rule_id"] == "preset-montacargas-prox" for t in out_far["triggered"])
    # Personas cercanas (< 1 m con 0.05 m/px ≈ 20 px) — debe disparar
    detections_near = [
        {"label": "Person", "box": [100, 100, 160, 260], "confidence": 0.9},
        {"label": "Forklift", "box": [110, 110, 170, 270], "confidence": 0.8},
    ]
    out_near = actions_mod.evaluate_actions(
        detections_near, 640, 480, compliance={"overall_compliant": True, "persons": []}
    )
    assert any(t["rule_id"] == "preset-montacargas-prox" for t in out_near["triggered"])


def test_source_filtering():
    rules = actions_mod.get_rules()["rules"]
    for r in rules:
        if r["id"] == "preset-epp-faena":
            r["enabled"] = True
            r["sources"] = ["watchlist:cam-1"]
    actions_mod.save_rules(rules)
    actions_mod._last_trigger.clear()
    detections = [{"label": "Person", "box": [10, 10, 100, 200], "confidence": 0.9}]
    compliance = {"overall_compliant": False, "persons": [{"missing": ["casco"]}]}
    live = actions_mod.evaluate_actions(detections, 640, 480, source_id="live", compliance=compliance)
    nvr = actions_mod.evaluate_actions(
        detections, 640, 480, source_id="watchlist:cam-1", compliance=compliance
    )
    assert not any(t["rule_id"] == "preset-epp-faena" for t in live["triggered"])
    assert any(t["rule_id"] == "preset-epp-faena" for t in nvr["triggered"])


def test_settings_roundtrip():
    payload = actions_mod.save_settings({"meters_per_pixel": 0.062, "reference": "Test ref"})
    assert payload["settings"]["meters_per_pixel"] == 0.062
    got = actions_mod.get_settings()
    assert got["meters_per_pixel"] == 0.062
    assert got["reference"] == "Test ref"


def test_action_audio_settings():
    actions_mod.save_settings(
        {"action_audio_enabled": False, "action_audio_severities": ["critical", "medium"]}
    )
    got = actions_mod.get_settings()
    assert got["action_audio_enabled"] is False
    assert got["action_audio_severities"] == ["critical", "medium"]
    assert actions_mod.should_play_action_audio("critical") is False
    actions_mod.save_settings({"action_audio_enabled": True})
    assert actions_mod.should_play_action_audio("critical") is True
    assert actions_mod.should_play_action_audio("high") is False


def test_list_action_events(tmp_path, monkeypatch):
    monkeypatch.setattr(actions_mod, "data_dir", lambda: tmp_path)
    actions_mod.log_action_event(
        {"rule_id": "r1", "severity": "high", "message": "Test A", "source": "live"}
    )
    actions_mod.log_action_event(
        {"rule_id": "r2", "severity": "critical", "message": "Test B", "source": "live"}
    )
    all_ev = actions_mod.list_action_events(limit=10)
    assert len(all_ev) == 2
    assert all_ev[0]["message"] == "Test B"
    crit = actions_mod.list_action_events(severity="critical")
    assert len(crit) == 1
    assert crit[0]["severity"] == "critical"
