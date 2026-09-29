"""Tests for the pure fix-application logic in sb_audit.py.

Run: python3 -m unittest scripts/test_sb_audit.py
"""
import json
import os
import sqlite3
import sys
import unicodedata
import unittest

sys.path.insert(0, os.path.dirname(__file__))
import sb_audit as sb  # noqa: E402


def make_db():
    c = sqlite3.connect(":memory:")
    c.execute(
        """CREATE TABLE entries (id INTEGER PRIMARY KEY, page_no INTEGER,
        position_on_page INTEGER, lemma_greek TEXT NOT NULL, lemma_translit TEXT,
        strongs TEXT, body_markdown TEXT NOT NULL, papyri_citations TEXT,
        nt_references TEXT, needs_review INTEGER DEFAULT 0)"""
    )
    c.execute("CREATE TABLE reviews (id INTEGER PRIMARY KEY, entry_id INTEGER)")
    c.execute("CREATE TABLE disagreements (id INTEGER PRIMARY KEY, entry_id INTEGER)")
    c.execute(
        "INSERT INTO entries VALUES (1, 300, 1, 'ἐχθρός', 'echthrós', 'G2190', ?, ?, '[]', 0)",
        ("*OGIS* 383⁸⁶ ἐχθρός", json.dumps(["OGIS 383⁸⁶"])),
    )
    return c


INDEX = {"G2190": {"lemma": "ἐχθρός", "translit": "echthrós"},
         "G0697": {"lemma": "Ἄρειος Πάγος", "translit": "Áreios Págos",
                   "variants": ["Αρειος Παγος"]}}


class CheckPatch(unittest.TestCase):
    def test_accepts_single_occurrence(self):
        self.assertIsNone(sb.check_patch("a 383⁸⁶ b", "383⁸⁶", "383²³⁷"))

    def test_rejects_missing_old(self):
        self.assertIn("found 0", sb.check_patch("a b", "383⁸⁶", "383²³⁷"))

    def test_rejects_ambiguous_old(self):
        self.assertIn("found 2", sb.check_patch("x x", "x", "y"))

    def test_rejects_noop(self):
        self.assertIn("no-op", sb.check_patch("x", "x", "x"))

    def test_rejects_empty_old(self):
        self.assertIn("empty", sb.check_patch("x", "", "y"))


class CheckStrongs(unittest.TestCase):
    def test_unknown_id_rejected(self):
        self.assertIn("unknown", sb.check_strongs("G999999", "ἐχθρός", INDEX))

    def test_lemma_mismatch_rejected(self):
        self.assertIn("lemma", sb.check_strongs("G2190", "λόγος", INDEX))

    def test_accent_insensitive_match_accepted(self):
        self.assertIsNone(sb.check_strongs("G2190", "εχθρος", INDEX))

    def test_rekey_allowed_when_current_id_is_wrong(self):
        self.assertIsNone(sb.check_rekey("G0697", "ἐχθρός", "G2190", INDEX))

    def test_rekey_allowed_when_unkeyed(self):
        self.assertIsNone(sb.check_rekey(None, "ἐχθρός", "G2190", INDEX))

    def test_rekey_refused_when_current_id_already_matches(self):
        idx = dict(INDEX, G9999={"lemma": "ἐχθρός", "translit": "echthrós"})
        self.assertIn("homograph", sb.check_rekey("G2190", "ἐχθρός", "G9999", idx))

    def test_unpadded_id_normalized(self):
        self.assertEqual(sb.norm_strongs("G697"), "G0697")
        self.assertEqual(sb.norm_strongs("G20014"), "G20014")


class ApplyFix(unittest.TestCase):
    def test_patch_updates_body_and_raw_citations(self):
        c = make_db()
        sb.apply_fix(c, {"id": 1, "patches": [{"old": "383⁸⁶", "new": "383²³⁷"}]}, INDEX)
        body, cites = c.execute(
            "SELECT body_markdown, papyri_citations FROM entries WHERE id=1").fetchone()
        self.assertEqual(body, "*OGIS* 383²³⁷ ἐχθρός")
        self.assertEqual(json.loads(cites), ["OGIS 383²³⁷"])

    def test_bad_patch_raises_and_changes_nothing(self):
        c = make_db()
        with self.assertRaises(sb.FixRejected):
            sb.apply_fix(c, {"id": 1, "patches": [
                {"old": "383⁸⁶", "new": "383²³⁷"},
                {"old": "not there", "new": "z"}]}, INDEX)
        body = c.execute("SELECT body_markdown FROM entries WHERE id=1").fetchone()[0]
        self.assertEqual(body, "*OGIS* 383⁸⁶ ἐχθρός")

    def test_strongs_change_refreshes_translit_from_index(self):
        c = make_db()
        sb.apply_fix(c, {"id": 1, "lemma_greek": "Ἄρειος Πάγος", "strongs": "G697"}, INDEX)
        row = c.execute(
            "SELECT lemma_greek, strongs, lemma_translit FROM entries WHERE id=1").fetchone()
        self.assertEqual(row, ("Ἄρειος Πάγος", "G0697", "Áreios Págos"))

    def test_delete_removes_entry_and_orphans(self):
        c = make_db()
        c.execute("INSERT INTO reviews (entry_id) VALUES (1)")
        sb.apply_fix(c, {"id": 1, "delete": True}, INDEX)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM entries").fetchone()[0], 0)
        self.assertEqual(c.execute("SELECT COUNT(*) FROM reviews").fetchone()[0], 0)


class BlindVerdict(unittest.TestCase):
    PATCH = {"kind": "patch", "old": "P Ryl I. 28²⁷", "new": "P Ryl I. 28¹³⁹"}

    def test_reading_matches_proposal_accepts(self):
        self.assertEqual(sb.blind_verdict(self.PATCH, {"printed": "P Ryl I.  28¹³⁹"}), "accept")

    def test_reading_matches_current_text_is_false_alarm(self):
        self.assertEqual(sb.blind_verdict(self.PATCH, {"printed": "P Ryl I. 28²⁷"}), "false_alarm")

    def test_third_reading_is_disagreement(self):
        self.assertEqual(sb.blind_verdict(self.PATCH, {"printed": "P Ryl I. 28¹³⁰"}), "disagree")

    def test_missing_reading_is_disagreement(self):
        self.assertEqual(sb.blind_verdict(self.PATCH, None), "disagree")

    def test_nfc_nfd_equivalent_accepts(self):
        ch = {"kind": "patch", "old": "ἀρχαῖα 1·1", "new": "ἀρχαῖα ⁱ·¹"}
        nfd = unicodedata.normalize("NFD", "ἀρχαῖα ⁱ·¹")
        self.assertEqual(sb.blind_verdict(ch, {"printed": nfd}), "accept")

    def test_delete_never_auto_applies(self):
        # 4/5 "spurious" entries were real continuation fragments (2026-09-29)
        ch = {"kind": "delete"}
        self.assertEqual(sb.blind_verdict(ch, {"present": False}), "manual_delete")
        self.assertEqual(sb.blind_verdict(ch, {"present": True}), "false_alarm")
        self.assertEqual(sb.blind_verdict(ch, {}), "disagree")

    def test_convention_only_difference_accepts(self):
        ch = {"kind": "patch", "old": "P Lond 937⁴ᶠ·", "new": "P Lond 937ᵇ⁸ᶠᶠ·"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": "P Lond 937 b⁸ff."}), "accept")

    def test_convention_only_difference_false_alarm(self):
        ch = {"kind": "patch", "old": "BGU IV. 1087ⁱⁱ·⁹", "new": "BGU IV. 1087ⁱⁱ·¹³"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": "BGU IV. 1087 ii. 9"}), "false_alarm")

    def test_formatting_only_fix_cannot_be_confirmed(self):
        ch = {"kind": "patch", "old": "222 b⁴", "new": "222ᵇ⁴"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": "222 b⁴ "}), "false_alarm")
        self.assertEqual(sb.blind_verdict(ch, {"printed": "222 ᵇ 4"}), "disagree")

    def test_strongs_passes_through_to_apply_guard(self):
        self.assertEqual(sb.blind_verdict({"kind": "strongs"}, None), "accept")


class TouchesGreek(unittest.TestCase):
    def test_citation_digit_fix_is_not_greek(self):
        self.assertFalse(sb.touches_greek("P Tebt I. 14⁵²", "P Tebt I. 14²⁰"))

    def test_accent_change_is_greek(self):
        self.assertTrue(sb.touches_greek("εὐσεβῶς τε βουλέι", "εὐσεβῶς τεὶ βουλεὶ"))

    def test_bracket_move_is_greek(self):
        self.assertTrue(sb.touches_greek("[ἄλλης ποταμοφο", "[ἄλλ]ης ποταμοφο"))

    def test_digit_fix_next_to_unchanged_greek_is_not_greek(self):
        self.assertFalse(sb.touches_greek("ἀρχαῖα 1·1, ἔχοντα", "ἀρχαῖα ⁱ·1, ἔχοντα"))

    def test_headword_change_routes_to_manual(self):
        ch = {"kind": "lemma_greek", "old": "μασσάομαι", "new": "μασάομαι"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": "μασάομαι"}), "manual_greek")

    def test_greek_patch_routes_to_manual(self):
        ch = {"kind": "patch", "old": "τε βουλέι", "new": "τεὶ βουλεὶ"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": "τεὶ βουλεὶ"}), "manual_greek")


class ChangesOf(unittest.TestCase):
    def test_strongs_equal_to_current_is_not_a_change(self):
        prop = {"entries": [{"id": 1, "strongs": "G2887", "_cur_strongs": "G2887"},
                            {"id": 2, "strongs": "G633", "_cur_strongs": "G0633"},
                            {"id": 3, "strongs": "G0697", "_cur_strongs": "G2190"}]}
        keys = [c["key"] for c in sb.changes_of(prop)]
        self.assertEqual(keys, ["3:strongs"])


class MultiSpan(unittest.TestCase):
    def test_two_separate_number_changes_route_to_manual(self):
        ch = {"kind": "patch", "old": "496⁸ (A.D. 127) and 528³ (ii/A.D.)",
              "new": "496³ (A.D. 127) and 528²⁰ (ii/A.D.)"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": ch["new"]}), "manual_multi")

    def test_single_span_change_still_accepts(self):
        ch = {"kind": "patch", "old": "P Ryl I. 28²⁷ (iv/A.D.)", "new": "P Ryl I. 28¹³⁹ (iv/A.D.)"}
        self.assertEqual(sb.blind_verdict(ch, {"printed": ch["new"]}), "accept")


if __name__ == "__main__":
    unittest.main()
