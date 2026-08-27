"""Tests control de acceso físico (torniquete / Modbus / HTTP / Wiegand)."""

from __future__ import annotations

from app.access_gate import merge_gate, sync_from_scan


def test_merge_gate_defaults():
    gate = merge_gate(None)
    assert gate["driver"] == "esp32"
    assert gate["esp32"]["alarma_path"] == "/alarma"


def test_merge_gate_modbus_patch():
    gate = merge_gate({"driver": "modbus", "modbus": {"host": "192.168.1.10", "coil_allow": 2}})
    assert gate["driver"] == "modbus"
    assert gate["modbus"]["host"] == "192.168.1.10"
    assert gate["modbus"]["coil_allow"] == 2


def test_sync_from_scan_gate_disabled():
    identity = {"known": True, "id": "w1", "name": "Juan", "rut": "11.111.111-1"}
    compliance = {"overall_compliant": True}
    gate = merge_gate({"enabled": False})
    result = sync_from_scan(
        identity,
        compliance,
        gate=gate,
        access_enabled=True,
        require_identity=True,
    )
    assert result is None


def test_sync_from_scan_access_allow_known():
    identity = {"known": True, "id": "w1", "name": "Juan", "rut": "11.111.111-1"}
    compliance = {"overall_compliant": True}
    gate = merge_gate({"enabled": False})
    result = sync_from_scan(
        identity,
        compliance,
        gate=gate,
        access_enabled=True,
        require_identity=True,
    )
    assert result is None
