import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_FILE"] = _tmp.name
os.environ["ADMIN_CHAT_ID"] = "999"

import storage  # noqa: E402
from config import TARIFFS  # noqa: E402


class _TgUser:
    def __init__(self, uid):
        self.id = uid
        self.username = f"u{uid}"
        self.first_name = "T"
        self.last_name = None


def _set_expiry(uid, dt):
    with sqlite3.connect(storage.DB_FILE) as c:
        c.execute("UPDATE users SET expires_at=? WHERE user_id=?", (dt.isoformat(), uid))


def _plan(uid):
    with sqlite3.connect(storage.DB_FILE) as c:
        return c.execute("SELECT plan FROM users WHERE user_id=?", (uid,)).fetchone()[0]


class TariffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        storage.init_db()

    def setUp(self):
        with sqlite3.connect(storage.DB_FILE) as c:
            c.execute("DELETE FROM users")

    def _user(self, uid, plan=None):
        storage.ensure_user(_TgUser(uid))
        if plan:
            storage.activate_plan(uid, plan)

    def test_admin_gets_full_access_without_tariff(self):
        storage.ensure_user(_TgUser(999))
        self.assertEqual(_plan(999), "premium")
        for mtype in ("text", "poster", "music"):
            self.assertTrue(storage.check_quota(999, mtype)[0], mtype)
        # admin access never expires
        self.assertNotIn(999, storage.downgrade_expired_users())
        self.assertEqual(_plan(999), "premium")

    def test_non_admin_still_needs_tariff(self):
        storage.ensure_user(_TgUser(1000))
        self.assertEqual(_plan(1000), "free")

    def test_prices(self):
        self.assertEqual(
            [TARIFFS[p]["price"] for p in ("basic", "standard", "premium")],
            [6990, 8990, 14990],
        )

    def test_free_user_has_no_access(self):
        self._user(1)
        ok, reason = storage.check_quota(1, "text")
        self.assertFalse(ok)
        self.assertNotIn("0 сұраныс", reason)
        self.assertFalse(storage.check_quota(1, "poster")[0])
        self.assertFalse(storage.check_quota(1, "music")[0])

    def test_basic_text_only(self):
        self._user(2, "basic")
        for _ in range(200):
            storage.record_usage(2, "text")
        self.assertTrue(storage.check_quota(2, "text")[0])
        self.assertEqual(storage.check_quota(2, "poster"), (False, "no_poster_access"))
        self.assertEqual(storage.check_quota(2, "music"), (False, "no_music_access"))

    def test_standard_poster_30(self):
        self._user(3, "standard")
        for _ in range(30):
            self.assertTrue(storage.check_quota(3, "poster")[0])
            storage.record_usage(3, "poster")
        self.assertFalse(storage.check_quota(3, "poster")[0])
        self.assertEqual(storage.check_quota(3, "music"), (False, "no_music_access"))

    def test_premium_poster_50_music_10(self):
        self._user(4, "premium")
        for _ in range(10):
            self.assertTrue(storage.check_quota(4, "music")[0])
            storage.record_usage(4, "music")
        self.assertFalse(storage.check_quota(4, "music")[0])
        for _ in range(50):
            storage.record_usage(4, "poster")
        self.assertFalse(storage.check_quota(4, "poster")[0])
        self.assertTrue(storage.check_quota(4, "text")[0])

    def test_all_expired_plans_lose_access(self):
        for uid, plan in ((10, "basic"), (11, "standard"), (12, "premium")):
            self._user(uid, plan)
            _set_expiry(uid, datetime.utcnow() - timedelta(hours=2))
        self._user(13, "basic")  # still active
        affected = storage.downgrade_expired_users()
        self.assertEqual(sorted(affected), [10, 11, 12])
        for uid in (10, 11, 12):
            self.assertEqual(_plan(uid), "free")
            self.assertFalse(storage.check_quota(uid, "text")[0])
        self.assertEqual(_plan(13), "basic")

    def test_renewal_extends_remaining_days(self):
        self._user(20, "standard")
        storage.activate_plan(20, "standard")
        with sqlite3.connect(storage.DB_FILE) as c:
            exp = c.execute("SELECT expires_at FROM users WHERE user_id=20").fetchone()[0]
        days_left = (datetime.fromisoformat(exp) - datetime.utcnow()).days
        self.assertGreaterEqual(days_left, 58)

    def test_upgrade_starts_fresh_30_days(self):
        self._user(21, "basic")
        storage.activate_plan(21, "premium")
        with sqlite3.connect(storage.DB_FILE) as c:
            exp = c.execute("SELECT expires_at FROM users WHERE user_id=21").fetchone()[0]
        days_left = (datetime.fromisoformat(exp) - datetime.utcnow()).days
        self.assertLessEqual(days_left, 30)


if __name__ == "__main__":
    unittest.main()
