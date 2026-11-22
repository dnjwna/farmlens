"""
Integration tests for the forgot-password flow and token versioning.
Uses in-memory SQLite and a fake OTP sender: no network, no real database.

Run from the project root:
    python -m unittest tests.test_password_reset -v
"""
import os
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("SECRET_KEY", "test")
os.environ["OTP_PROVIDER"] = "console"
os.environ["ADMIN_API_KEY"] = "admin-test-key"

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.models.farmer import PasswordResetCode  # noqa: E402
from app.services import password_reset_service as prs  # noqa: E402
from main import app  # noqa: E402

settings.ADMIN_API_KEY = "admin-test-key"

PHONE = "081234567890"
OLD_PW = "password123"
NEW_PW = "passwordBaru9"


class PasswordResetTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        def override_db():
            db = self.Session()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_db
        self.client = TestClient(app)
        self.sent: list[tuple[str, str]] = []

        async def fake_send(phone, code, ttl):
            self.sent.append((phone, code))

        self.patcher = patch.object(prs, "send_reset_code", fake_send)
        self.patcher.start()

        r = self.client.post("/api/v1/auth/register", json={
            "full_name": "Pak Tani", "phone_number": PHONE, "password": OLD_PW,
            "province": "Jawa Barat", "city": "Bandung",
        })
        self.assertEqual(r.status_code, 201, r.text)

    def tearDown(self):
        self.patcher.stop()
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    # helpers
    def login(self, pw):
        return self.client.post("/api/v1/auth/login", json={"phone_number": PHONE, "password": pw})

    def me(self, token):
        return self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})

    def forgot(self, phone=PHONE):
        return self.client.post("/api/v1/auth/forgot-password", json={"phone_number": phone})

    def reset(self, code, pw=NEW_PW, phone=PHONE):
        return self.client.post("/api/v1/auth/reset-password",
                                json={"phone_number": phone, "code": code, "new_password": pw})

    # tests
    def test_full_reset_flow_logs_out_old_sessions(self):
        old_token = self.login(OLD_PW).json()["access_token"]
        self.assertEqual(self.me(old_token).status_code, 200)

        r = self.forgot()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(self.sent), 1)
        phone, code = self.sent[0]
        self.assertEqual(phone, "6281234567890")

        r = self.reset(code)
        self.assertEqual(r.status_code, 200, r.text)
        new_token = r.json()["access_token"]

        self.assertEqual(self.me(new_token).status_code, 200)
        self.assertEqual(self.me(old_token).status_code, 401)
        self.assertEqual(self.login(OLD_PW).status_code, 401)
        self.assertEqual(self.login(NEW_PW).status_code, 200)

    def test_unknown_number_gets_same_response_and_nothing_sent(self):
        known = self.forgot().json()
        unknown = self.forgot("081111111111").json()
        self.assertEqual(known, unknown)
        self.assertEqual([p for p, _ in self.sent], ["6281234567890"])

    def test_phone_formats_match_same_account(self):
        self.forgot("+62 812-3456-7890")
        self.assertEqual(len(self.sent), 1)
        r = self.reset(self.sent[0][1], phone="6281234567890")
        self.assertEqual(r.status_code, 200, r.text)

    def test_code_is_single_use(self):
        self.forgot()
        code = self.sent[0][1]
        self.assertEqual(self.reset(code).status_code, 200)
        self.assertEqual(self.reset(code, pw="lainlagi123").status_code, 400)

    def test_new_request_invalidates_previous_code(self):
        self.forgot()
        self.forgot()
        first, second = self.sent[0][1], self.sent[1][1]
        if first != second:
            self.assertEqual(self.reset(first).status_code, 400)
        self.assertEqual(self.reset(second).status_code, 200)

    def test_lockout_after_five_wrong_attempts(self):
        self.forgot()
        code = self.sent[0][1]
        wrong = "000000" if code != "000000" else "111111"
        for i in range(4):
            r = self.reset(wrong)
            self.assertEqual(r.status_code, 400)
            self.assertIn(f"Sisa {4 - i}", r.json()["detail"])
        r = self.reset(wrong)
        self.assertIn("Terlalu banyak", r.json()["detail"])
        # Even the right code no longer works
        self.assertEqual(self.reset(code).status_code, 400)

    def test_expired_code_rejected(self):
        self.forgot()
        code = self.sent[0][1]
        db = self.Session()
        db.query(PasswordResetCode).update(
            {PasswordResetCode.expires_at: datetime.utcnow() - timedelta(seconds=1)})
        db.commit()
        db.close()
        self.assertEqual(self.reset(code).status_code, 400)

    def test_rate_limit_applies_to_unknown_numbers_too(self):
        for _ in range(3):
            self.assertEqual(self.forgot().status_code, 200)
            self.assertEqual(self.forgot("081111111111").status_code, 200)
        self.assertEqual(self.forgot().status_code, 429)
        self.assertEqual(self.forgot("081111111111").status_code, 429)
        self.assertEqual(len(self.sent), 3)

    def test_code_stored_hashed(self):
        self.forgot()
        code = self.sent[0][1]
        db = self.Session()
        row = db.query(PasswordResetCode).filter(PasswordResetCode.farmer_id.isnot(None)).one()
        db.close()
        self.assertNotEqual(row.code_hash, code)
        self.assertNotIn(code, row.code_hash)

    def test_validation(self):
        self.assertEqual(self.forgot("12345").status_code, 422)
        self.assertEqual(self.reset("12ab56").status_code, 422)
        self.forgot()
        self.assertEqual(self.reset(self.sent[0][1], pw="pendek").status_code, 422)

    def test_change_password_returns_new_token_and_logs_out_others(self):
        device_a = self.login(OLD_PW).json()["access_token"]
        device_b = self.login(OLD_PW).json()["access_token"]
        r = self.client.post("/api/v1/auth/change-password",
                             headers={"Authorization": f"Bearer {device_a}"},
                             json={"current_password": OLD_PW, "new_password": NEW_PW})
        self.assertEqual(r.status_code, 200, r.text)
        fresh = r.json()["access_token"]
        self.assertEqual(self.me(fresh).status_code, 200)
        self.assertEqual(self.me(device_a).status_code, 401)
        self.assertEqual(self.me(device_b).status_code, 401)

    def test_legacy_token_without_ver_still_valid(self):
        from app.core.security import create_access_token
        db = self.Session()
        from app.models.farmer import Farmer
        farmer_id = db.query(Farmer).one().id
        db.close()
        legacy = create_access_token({"sub": str(farmer_id)})
        self.assertEqual(self.me(legacy).status_code, 200)

    def test_admin_reset_code(self):
        url = "/api/v1/admin/users/reset-password"
        self.assertEqual(self.client.post(url, json={"phone_number": PHONE}).status_code, 401)
        r = self.client.post(url, headers={"X-Admin-Key": "admin-test-key"},
                             json={"phone_number": "081111111111"})
        self.assertEqual(r.status_code, 404)
        r = self.client.post(url, headers={"X-Admin-Key": "admin-test-key"}, json={"phone_number": PHONE})
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["valid_hours"], 24)
        self.assertEqual(self.reset(r.json()["code"]).status_code, 200)
        self.assertEqual(self.sent, [])  # admin codes are not sent over WhatsApp


class OpenWASenderTests(unittest.IsolatedAsyncioTestCase):
    async def test_openwa_request_shape(self):
        import httpx
        from app.services import otp_sender

        captured = {}

        def handler(request: httpx.Request):
            captured["url"] = str(request.url)
            captured["key"] = request.headers.get("X-API-Key")
            captured["body"] = request.content.decode()
            return httpx.Response(200, json={"ok": True})

        real_client = httpx.AsyncClient
        with patch.object(otp_sender.settings, "OTP_PROVIDER", "openwa"), \
             patch.object(otp_sender.settings, "OPENWA_API_KEY", "k123"), \
             patch.object(otp_sender.settings, "OPENWA_SESSION_ID", "farmlens"), \
             patch.object(otp_sender.httpx, "AsyncClient",
                          lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
            await otp_sender.send_reset_code("6281234567890", "123456", 10)

        self.assertEqual(captured["url"], "http://localhost:2785/api/sessions/farmlens/messages/send-text")
        self.assertEqual(captured["key"], "k123")
        self.assertIn('"chatId":"6281234567890@c.us"', captured["body"].replace(" ", ""))
        self.assertIn("123456", captured["body"])

    async def test_openwa_error_raises(self):
        import httpx
        from app.services import otp_sender

        real_client = httpx.AsyncClient
        with patch.object(otp_sender.settings, "OTP_PROVIDER", "openwa"), \
             patch.object(otp_sender.settings, "OPENWA_API_KEY", "k"), \
             patch.object(otp_sender.settings, "OPENWA_SESSION_ID", "s"), \
             patch.object(otp_sender.httpx, "AsyncClient",
                          lambda **kw: real_client(
                              transport=httpx.MockTransport(lambda r: httpx.Response(500, text="down")), **kw)):
            with self.assertRaises(otp_sender.OTPDeliveryError):
                await otp_sender.send_reset_code("6281234567890", "123456", 10)


if __name__ == "__main__":
    unittest.main()
