import os
import sqlite3
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DB_FILE"] = _tmp.name
os.environ["ADMIN_CHAT_ID"] = "999"
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import httpx  # noqa: E402

import generators  # noqa: E402
import handlers  # noqa: E402
import storage  # noqa: E402
from config import ASK_DAILY_LIMIT, MEKTEP_MATERIALS, BALABAQSHA_MATERIALS, SECTIONS  # noqa: E402

NEW_MEKTEP = {
    "basic": ["Ашық сабақ жоспары", "Сабақты өзін-өзі талдау", "Үйірме жоспары",
              "Сыныптан тыс іс-шара", "Музыкалық терминдер сөздігі", "Жұмбақтар"],
    "premium": ["Конкурс жоспары", "Флешмоб сценарийі"],
}
NEW_BALA = {
    "basic": ["Шу оркестрі"],
    "premium": ["Наурыз сценарийі", "Жаңа жыл сценарийі", "Туған күн сценарийі", "Бітіру кеші",
                "Утренник", "Ашық есік күні", "Ата-ана жиналысы"],
}


def _tg(uid):
    return SimpleNamespace(id=uid, username="u", first_name="T", last_name=None)


class MaterialTests(unittest.TestCase):
    def test_totals(self):
        self.assertEqual(len(MEKTEP_MATERIALS), 37)
        self.assertEqual(len(BALABAQSHA_MATERIALS), 41)
        self.assertEqual(len(MEKTEP_MATERIALS) + len(BALABAQSHA_MATERIALS), 78)

    def test_new_materials_have_plan_and_russian_name(self):
        for materials, new in ((MEKTEP_MATERIALS, NEW_MEKTEP), (BALABAQSHA_MATERIALS, NEW_BALA)):
            by_name = {m.name: m for m in materials}
            for plan, names in new.items():
                for name in names:
                    self.assertIn(name, by_name)
                    self.assertEqual(by_name[name].min_plan, plan, name)
                    self.assertTrue(by_name[name].name_ru, name)

    def test_names_unique_within_section(self):
        for materials in (MEKTEP_MATERIALS, BALABAQSHA_MATERIALS):
            names = [m.name for m in materials]
            self.assertEqual(len(names), len(set(names)))

    def test_every_new_material_has_prompt_hint_in_both_languages(self):
        for name in NEW_MEKTEP["basic"] + NEW_MEKTEP["premium"] + NEW_BALA["basic"] + NEW_BALA["premium"]:
            kz, ru = generators.MATERIAL_HINTS[name]
            self.assertTrue(kz and ru, name)
            self.assertIn(name, handlers._TOPIC_EXAMPLES)

    def test_help_and_cards_use_real_counts(self):
        self.assertIn("37", handlers.HELP_TEXT)
        self.assertIn("41", handlers.HELP_TEXT)
        self.assertIn(f"Мектеп ({handlers._MEKTEP_BASIC} материал)", handlers.TARIF_CARDS["basic"])
        self.assertEqual(handlers._MEKTEP_BASIC, 30)
        self.assertEqual(handlers._BALA_BASIC, 28)

    def test_hint_reaches_prompt_in_both_languages(self):
        captured = []

        def fake(**kw):
            captured.append(kw["contents"])
            return SimpleNamespace(text="ok")

        import asyncio
        with patch.object(generators._gemini.models, "generate_content", side_effect=lambda **kw: fake(**kw)):
            asyncio.run(generators.gen_text("mektep", "Жұмбақтар", "Домбыра", "kz"))
            asyncio.run(generators.gen_text("mektep", "Жұмбақтар", "Домбра", "ru", name_ru="Загадки"))
        self.assertIn("Міндетті құрылым", captured[0])
        self.assertIn("Обязательная структура", captured[1])


class AskStorageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        storage.init_db()

    def setUp(self):
        with sqlite3.connect(storage.DB_FILE) as c:
            c.execute("DELETE FROM users")
            c.execute("DELETE FROM ask_usage")

    def test_no_plan_blocked(self):
        storage.ensure_user(_tg(1))
        self.assertEqual(storage.can_ask(1), (False, "no_plan"))
        self.assertEqual(storage.can_ask(404), (False, "no_plan"))

    def test_all_tariffs_allowed_with_daily_limit(self):
        for uid, plan in ((2, "basic"), (3, "standard"), (4, "premium")):
            storage.ensure_user(_tg(uid))
            storage.activate_plan(uid, plan)
            for _ in range(ASK_DAILY_LIMIT):
                self.assertTrue(storage.can_ask(uid)[0])
                storage.record_ask(uid)
            self.assertEqual(storage.can_ask(uid), (False, "limit"))
            self.assertEqual(storage.get_ask_used(uid), ASK_DAILY_LIMIT)

    def test_limit_is_per_day(self):
        storage.ensure_user(_tg(5))
        storage.activate_plan(5, "basic")
        with sqlite3.connect(storage.DB_FILE) as c:
            c.execute("INSERT INTO ask_usage VALUES (5, '2000-01-01', 99)")
        self.assertTrue(storage.can_ask(5)[0])
        self.assertEqual(storage.get_ask_used(5), 0)


def _update(uid, text):
    msg = MagicMock()
    msg.text = text
    sent = MagicMock()
    sent.delete = AsyncMock()
    msg.reply_text = AsyncMock(return_value=sent)
    return SimpleNamespace(effective_user=_tg(uid), message=msg)


def _sent(upd):
    return " ".join(str(c.args[0]) for c in upd.message.reply_text.await_args_list if c.args)


class AskHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        with sqlite3.connect(storage.DB_FILE) as c:
            c.execute("DELETE FROM users")
            c.execute("DELETE FROM ask_usage")

    def _user(self, uid, plan):
        storage.ensure_user(_tg(uid))
        if plan:
            storage.activate_plan(uid, plan)

    async def _press_ask(self, uid):
        query = MagicMock()
        query.data = "ask"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message.chat_id = uid
        upd = SimpleNamespace(callback_query=query, effective_user=_tg(uid))
        ctx = SimpleNamespace(user_data={}, bot=MagicMock())
        await handlers.button_handler(upd, ctx)
        return query, ctx

    def test_main_menu_has_ask_button(self):
        from keyboards import main_menu_kb
        cbs = [b.callback_data for row in main_menu_kb().inline_keyboard for b in row]
        self.assertIn("ask", cbs)

    async def test_button_closed_without_tariff(self):
        self._user(1, None)
        query, ctx = await self._press_ask(1)
        self.assertFalse(ctx.user_data.get("waiting_question"))
        self.assertIn("тарифпен", query.edit_message_text.await_args.args[0])

    async def test_button_opens_question_mode_on_each_tariff(self):
        for uid, plan in ((2, "basic"), (3, "standard"), (4, "premium")):
            self._user(uid, plan)
            query, ctx = await self._press_ask(uid)
            self.assertTrue(ctx.user_data["waiting_question"], plan)
            self.assertIn("Сұрағыңызды жазыңыз", query.edit_message_text.await_args.args[0])

    async def test_question_is_answered_split_and_counted(self):
        self._user(5, "basic")
        long_answer = ("жол\n" * 2500).strip()  # ~10 000 chars -> several parts
        upd, ctx = _update(5, "Домбыра деген не?"), SimpleNamespace(user_data={"waiting_question": True})
        gen = AsyncMock(return_value=long_answer)
        with patch.object(handlers.generators, "gen_answer", gen):
            await handlers.text_message_handler(upd, ctx)
        gen.assert_awaited_once_with("Домбыра деген не?")
        parts = [c.args[0] for c in upd.message.reply_text.await_args_list
                 if c.args and c.args[0].startswith("жол")]
        self.assertGreater(len(parts), 1)
        self.assertTrue(all(len(p) <= 4000 for p in parts))
        self.assertEqual(storage.get_ask_used(5), 1)
        self.assertTrue(ctx.user_data["waiting_question"])  # can keep asking

    async def test_daily_limit_blocks_31st_question(self):
        self._user(6, "premium")
        for _ in range(ASK_DAILY_LIMIT):
            storage.record_ask(6)
        upd, ctx = _update(6, "ещё вопрос"), SimpleNamespace(user_data={"waiting_question": True})
        gen = AsyncMock(return_value="x")
        with patch.object(handlers.generators, "gen_answer", gen):
            await handlers.text_message_handler(upd, ctx)
        gen.assert_not_awaited()
        self.assertIn("лимит", _sent(upd))
        self.assertEqual(storage.get_ask_used(6), ASK_DAILY_LIMIT)

    async def test_failed_answer_not_counted(self):
        self._user(7, "basic")
        upd, ctx = _update(7, "вопрос"), SimpleNamespace(user_data={"waiting_question": True})
        with patch.object(handlers.generators, "gen_answer", AsyncMock(side_effect=RuntimeError("boom"))):
            await handlers.text_message_handler(upd, ctx)
        self.assertEqual(storage.get_ask_used(7), 0)
        self.assertIn("Лимит жұмсалған жоқ", _sent(upd))

    async def test_user_without_tariff_cannot_ask_by_typing(self):
        self._user(8, None)
        upd, ctx = _update(8, "вопрос"), SimpleNamespace(user_data={"waiting_question": True})
        gen = AsyncMock(return_value="x")
        with patch.object(handlers.generators, "gen_answer", gen):
            await handlers.text_message_handler(upd, ctx)
        gen.assert_not_awaited()

    async def test_other_button_leaves_question_mode(self):
        self._user(9, "basic")
        query = MagicMock()
        query.data = "main_menu"
        query.answer = AsyncMock()
        query.edit_message_text = AsyncMock()
        query.message.chat_id = 9
        ctx = SimpleNamespace(user_data={"waiting_question": True}, bot=MagicMock())
        await handlers.button_handler(SimpleNamespace(callback_query=query, effective_user=_tg(9)), ctx)
        self.assertNotIn("waiting_question", ctx.user_data)


def _http_error(status, body):
    req = httpx.Request("POST", "https://api.openai.com/v1/images/generations")
    return httpx.HTTPStatusError("err", request=req, response=httpx.Response(status, text=body, request=req))


class ImageErrorTests(unittest.IsolatedAsyncioTestCase):
    def test_reason_per_failure_kind(self):
        d = generators.describe_image_error
        self.assertIn("кілті", d(_http_error(401, "bad key")))
        self.assertIn("лимит", d(_http_error(429, "rate")))
        self.assertIn("уақытша", d(_http_error(503, "down")))
        self.assertIn("қауіпсіздік", d(_http_error(400, '{"error":{"code":"content_policy_violation"}}')))
        self.assertIn("қауіпсіздік", d(generators.NoImageReturned("no image")))
        self.assertIn("уақытында", d(httpx.ReadTimeout("slow")))
        self.assertIn("күтпеген", d(RuntimeError("boom")))

    async def test_failure_logs_status_and_body_and_raises_friendly_error(self):
        with patch.object(generators, "_OPENAI_KEY", "k"), \
             patch.object(generators, "_gen_image_openai",
                          AsyncMock(side_effect=_http_error(429, "quota exceeded for org"))):
            with self.assertLogs("generators", level="ERROR") as cm:
                with self.assertRaises(generators.ImageGenError) as ctx:
                    await generators.gen_poster("mektep", "Сурет", "Домбыра")
        log = "\n".join(cm.output)
        self.assertIn("status=429", log)
        self.assertIn("quota exceeded for org", log)
        self.assertIn("HTTPStatusError", log)
        self.assertIn("лимит", ctx.exception.user_message)

    async def test_gemini_without_image_is_reported(self):
        empty = SimpleNamespace(candidates=[], prompt_feedback="BLOCKED")
        with patch.object(generators, "_OPENAI_KEY", ""), \
             patch.object(generators._gemini.models, "generate_content", return_value=empty):
            with self.assertLogs("generators", level="ERROR") as cm:
                with self.assertRaises(generators.ImageGenError) as ctx:
                    await generators.gen_poster("mektep", "Сурет", "Домбыра")
        self.assertIn("BLOCKED", "\n".join(cm.output))
        self.assertIn("қауіпсіздік", ctx.exception.user_message)

    async def test_poster_failure_tells_user_the_reason(self):
        from config import MType
        storage.init_db()
        storage.ensure_user(_tg(30))
        storage.activate_plan(30, "standard")
        upd = _update(30, "Домбыра")
        upd.message.reply_photo = AsyncMock()
        ctx = SimpleNamespace(user_data={
            "waiting_topic": True, "section": "mektep", "material_name": "Сурет",
            "material_name_ru": "", "material_type": MType.POSTER, "page": 0, "lang": "kz"})
        err = generators.ImageGenError("Сурет сервисінің лимиті/квотасы толды.")
        with patch.object(handlers.generators, "gen_poster", AsyncMock(side_effect=err)):
            await handlers.text_message_handler(upd, ctx)
        self.assertIn("лимиті/квотасы толды", _sent(upd))
        self.assertEqual(storage.get_remaining(30, "poster")[0], 0)

    async def test_slide_images_return_reason_when_all_fail(self):
        err = generators.ImageGenError("себеп")
        with patch.object(generators, "gen_poster", AsyncMock(side_effect=err)):
            images, reason = await generators.gen_slide_images("mektep", "T", [{"title": "a", "bullets": []}])
        self.assertEqual((images, reason), ({}, "себеп"))


if __name__ == "__main__":
    unittest.main()
