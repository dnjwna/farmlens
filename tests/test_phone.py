"""
Phone number normalization: parsing, register/login across formats, legacy-data migration.

Run from the project root:
    python -m unittest tests.test_phone -v
"""
import os
import unittest

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/test")
os.environ.setdefault("SECRET_KEY", "test")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.database import Base, get_db  # noqa: E402
from app.core.phone import lookup_variants, normalize_existing_phone_numbers, normalize_phone  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.farmer import Farmer  # noqa: E402
from main import app  # noqa: E402


class NormalizeTests(unittest.TestCase):
    def test_accepted_formats(self):
        for raw in ["081234567890", "+6281234567890", "6281234567890",
                    "0812-3456-7890", "+62 812 3456 7890", "(0812) 3456 7890", " 081234567890 "]:
            self.assertEqual(normalize_phone(raw), "+6281234567890", raw)

    def test_rejected(self):
        for raw in ["", None, "12345", "0212345678", "+6221234567", "+1 415 555 0100",
                    "08123", "0812345678901234", "abc"]:
            self.assertIsNone(normalize_phone(raw), raw)

    def test_length_bounds(self):
        self.assertIsNotNone(normalize_phone("081234567"))      # 9 digits local
        self.assertIsNotNone(normalize_phone("0812345678901"))  # 13 digits local
        self.assertIsNone(normalize_phone("08123456"))          # 8
        self.assertIsNone(normalize_phone("08123456789012"))    # 14

    def test_variants(self):
        self.assertEqual(lookup_variants("0812 3456 7890"),
                         ["+6281234567890", "081234567890", "6281234567890"])
        self.assertEqual(lookup_variants("bad"), [])


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(self.engine)

    def register(self, phone):
        return self.client.post("/api/v1/auth/register", json={
            "full_name": "  Pak Tani ", "phone_number": phone, "password": "password123"})

    def login(self, phone, pw="password123"):
        return self.client.post("/api/v1/auth/login", json={"phone_number": phone, "password": pw})

    def test_register_stores_canonical(self):
        r = self.register("0812-3456-7890")
        self.assertEqual(r.status_code, 201, r.text)
        self.assertEqual(r.json()["phone_number"], "+6281234567890")
        self.assertEqual(r.json()["full_name"], "Pak Tani")

    def test_login_with_any_format(self):
        self.register("081234567890")
        for phone in ["081234567890", "+6281234567890", "6281234567890", "0812 3456 7890"]:
            self.assertEqual(self.login(phone).status_code, 200, phone)

    def test_duplicate_in_other_format_rejected(self):
        self.assertEqual(self.register("081234567890").status_code, 201)
        r = self.register("+62 812-3456-7890")
        self.assertEqual(r.status_code, 400)
        self.assertIn("sudah terdaftar", r.json()["detail"])

    def test_invalid_register_and_login(self):
        self.assertEqual(self.register("12345").status_code, 422)
        self.assertEqual(self.login("12345").status_code, 401)  # same as wrong password

    def test_legacy_row_still_logs_in_before_migration(self):
        db = self.Session()
        db.add(Farmer(full_name="Lama", phone_number="081299998888", password_hash=hash_password("password123")))
        db.commit()
        db.close()
        self.assertEqual(self.login("+6281299998888").status_code, 200)

    def test_migration_normalizes_and_skips_conflicts(self):
        db = self.Session()
        pw = hash_password("password123")
        db.add_all([
            Farmer(full_name="A", phone_number="081111111111", password_hash=pw),
            Farmer(full_name="B", phone_number="+6282222222222", password_hash=pw),   # already canonical
            Farmer(full_name="C1", phone_number="083333333333", password_hash=pw),    # conflict pair
            Farmer(full_name="C2", phone_number="+6283333333333", password_hash=pw),
            Farmer(full_name="D", phone_number="12345", password_hash=pw),            # invalid
        ])
        db.commit()

        result = normalize_existing_phone_numbers(db)
        self.assertEqual(result["updated"], 1)
        self.assertEqual(result["invalid"], 1)
        self.assertEqual(len(result["conflicts"]), 1)

        phones = {f.full_name: f.phone_number for f in db.query(Farmer).all()}
        self.assertEqual(phones["A"], "+6281111111111")
        self.assertEqual(phones["C1"], "083333333333")  # untouched, needs manual review
        self.assertEqual(phones["D"], "12345")

        # Idempotent
        self.assertEqual(normalize_existing_phone_numbers(db)["updated"], 0)
        db.close()


if __name__ == "__main__":
    unittest.main()
