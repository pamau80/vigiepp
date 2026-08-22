"""Auth, PIN de fábrica, rate limit y health (sin depender de YOLO)."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import auth as auth_mod  # noqa: E402


class AuthLogicTests(unittest.TestCase):
    def test_default_pins_when_unset(self) -> None:
        env = {"VIGIEPP_ADMIN_PIN": "", "VIGIEPP_OPERATOR_PIN": ""}
        with patch.dict(os.environ, env, clear=False):
            self.assertTrue(auth_mod.using_default_pins())
            self.assertEqual(auth_mod.admin_pin(), "vigiepp")
            self.assertEqual(auth_mod.operator_pin(), "porteria")

    def test_custom_pins_are_not_factory(self) -> None:
        env = {"VIGIEPP_ADMIN_PIN": "secreto-admin", "VIGIEPP_OPERATOR_PIN": "secreto-op"}
        with patch.dict(os.environ, env, clear=False):
            self.assertFalse(auth_mod.using_default_pins())
            self.assertEqual(auth_mod.admin_pin(), "secreto-admin")
            self.assertEqual(auth_mod.resolve_pin_role("secreto-admin"), auth_mod.ROLE_ADMIN)
            self.assertEqual(auth_mod.resolve_pin_role("secreto-op"), auth_mod.ROLE_OPERATOR)
            self.assertIsNone(auth_mod.resolve_pin_role("vigiepp"))

    def test_hosted_on_render_flag(self) -> None:
        with patch.dict(os.environ, {"RENDER": "true"}, clear=False):
            self.assertTrue(auth_mod.hosted_on_render())
        with patch.dict(os.environ, {"RENDER": "", "RENDER_SERVICE_ID": ""}, clear=False):
            self.assertFalse(auth_mod.hosted_on_render())

    def test_login_rate_limit(self) -> None:
        ip = "198.51.100.77"
        auth_mod.clear_login_rate(ip)
        for _ in range(auth_mod.LOGIN_MAX_ATTEMPTS):
            auth_mod.check_login_rate(ip)
        with self.assertRaises(HTTPException) as ctx:
            auth_mod.check_login_rate(ip)
        self.assertEqual(ctx.exception.status_code, 429)
        auth_mod.clear_login_rate(ip)


class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("VIGIEPP_AUTH", "1")
        os.environ.setdefault("VIGIEPP_DOCS", "1")
        from fastapi.testclient import TestClient

        from app.main import app

        cls.client = TestClient(app)

    def test_health_reports_pins_and_host(self) -> None:
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual(body.get("product"), "VigiEPP")
        self.assertIn("default_pins", body)
        self.assertIn("hosted_on_render", body)
        self.assertFalse(body["hosted_on_render"])

    def test_login_admin_and_bad_pin(self) -> None:
        bad = self.client.post("/api/auth/login", json={"pin": "no-existe"})
        self.assertEqual(bad.status_code, 401)
        ok = self.client.post("/api/auth/login", json={"pin": auth_mod.admin_pin()})
        self.assertEqual(ok.status_code, 200)
        self.assertTrue(ok.json().get("ok"))
        self.assertEqual(ok.json().get("role"), "admin")

    def test_enroll_photos_requires_consent(self) -> None:
        login = self.client.post("/api/auth/login", json={"pin": auth_mod.admin_pin()})
        self.assertEqual(login.status_code, 200)
        jpeg = (
            b"\xff\xd8\xff\xdb\x00C\x00"
            + b"\x08" * 64
            + b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
            + b"\xff\xd9"
        )
        res = self.client.post(
            "/api/identity/enroll-photos",
            data={"name": "Test", "consent": "false"},
            files={"files": ("x.jpg", jpeg, "image/jpeg")},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("consentimiento", (res.json().get("detail") or "").lower())


if __name__ == "__main__":
    unittest.main()
