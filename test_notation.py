import io
import os
import unittest

os.environ.setdefault("GEMINI_API_KEY", "test-key")

from PIL import Image  # noqa: E402

import generators  # noqa: E402
import notation  # noqa: E402

RAW = """```json
{"title": "Көктем", "time": "4/4", "tempo": 96,
 "measures": [
  [{"p": "C4", "d": 1, "l": "кек"}, {"p": "D4", "d": 1, "l": "тем"}, {"p": "E4", "d": 2, "l": "кел"}],
  [{"p": "G4", "d": 1.5, "l": "ді"}, {"p": "F4", "d": 0.5, "l": "ақ"}, {"p": "R", "d": 2}],
  [{"p": "A5", "d": 2}, {"p": "A3", "d": 2}],
  [{"p": "E4", "d": 4, "l": "ай"}]
 ]}
```"""


class NotationTests(unittest.TestCase):
    def test_pitch_to_step(self):
        self.assertEqual(notation.pitch_to_step("E4"), (30, ""))   # bottom line of treble staff
        self.assertEqual(notation.pitch_to_step("F5"), (38, ""))   # top line
        self.assertEqual(notation.pitch_to_step("C4"), (28, ""))   # first ledger line below
        self.assertEqual(notation.pitch_to_step("F#4"), (31, "#"))
        self.assertEqual(notation.pitch_to_step("Bb4"), (34, "b"))
        with self.assertRaises(ValueError):
            notation.pitch_to_step("H9")

    def test_parse_melody_fits_every_measure_to_the_time_signature(self):
        m = generators.parse_melody(RAW)
        self.assertEqual(m["title"], "Көктем")
        self.assertEqual(m["beats"], 4.0)
        for bar in m["measures"]:
            self.assertAlmostEqual(sum(n["d"] for n in bar), 4.0)
        # bar 2 summed to 4 already; bar 3 and 4 as well; short bars get padded
        short = generators.parse_melody(
            '{"time": "3/4", "measures": [[{"p": "C4", "d": 1}, {"p": "D4", "d": 1}]'
            ', [{"p": "E4", "d": 1}, {"p": "F4", "d": 1}, {"p": "G4", "d": 1}, {"p": "A4", "d": 1}]]}'
        )
        self.assertAlmostEqual(sum(n["d"] for n in short["measures"][0]), 3.0)
        self.assertAlmostEqual(sum(n["d"] for n in short["measures"][1]), 3.0)

    def test_parse_melody_rejects_garbage(self):
        with self.assertRaises(ValueError):
            generators.parse_melody("nothing")
        with self.assertRaises(ValueError):
            generators.parse_melody('{"time": "4/4", "measures": []}')

    def test_render_returns_png_with_content(self):
        png = notation.render_notation(generators.parse_melody(RAW))
        img = Image.open(io.BytesIO(png))
        self.assertEqual(img.format, "PNG")
        self.assertGreaterEqual(img.width, 1200)
        colors = img.convert("L").getcolors(maxcolors=1 << 20)
        dark = sum(c for c, v in colors if v < 80)
        self.assertGreater(dark, 2000)   # staff lines and notes were drawn

    def test_many_measures_wrap_into_several_systems(self):
        bar = [{"p": "C4", "d": 1, "l": "ла"}] * 4
        m = {"title": "t", "beats": 4.0, "time": (4, 4), "tempo": 90, "measures": [bar] * 12}
        tall = Image.open(io.BytesIO(notation.render_notation(m)))
        short = Image.open(io.BytesIO(notation.render_notation({**m, "measures": [bar] * 2})))
        self.assertGreater(tall.height, short.height)


if __name__ == "__main__":
    unittest.main()
