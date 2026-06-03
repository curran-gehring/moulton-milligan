"""Phase 3b: keying corrections for the 601-640 batch (σ section, σειρά->σύνοδος).

Verified directly against reference/strongs_lemma_index.json + page bodies.

This σ-compound stretch (esp. the συν-/συμ-/συγ- assimilation region and the
dense σύν- compound pages) produced a large snap crop + several OCR headword
mislabels. Most snaps are the legit unassimilated-ν -> assimilated NT-form
variant (συνκαλέω->συγκαλέω G4779 etc.) and are KEPT untouched. The corrections
below are the genuine bad snaps, rescues, relabels, and stub/non-NT tombstones.

BAD SNAPS re-keyed to the REAL Strong's (wrong-word coincidental snaps):
  id 4338 σιαίνομαι   G1230->G4525  (1 Th 3:3 FG reading of σαίνω; snapped διαγίνομαι)
  id 4362 Σίων        G4613->G4622  (Zion; snapped to Σίμων Simon — wrong proper noun)
  id 4463 στεῖρος     G0791->G4723  (στεῖρα 'barren'; snapped to ἀστεῖος 'beautiful')
  id 4530 συκομορέα   G4927->G4809  (sycamore, Lk 19:4 = συκομωραία; snapped συνομορέω)
  id 4546 συμμορφίζω  G4829->G4833  (Phil 3:10 = συμμορφόω; snapped συμμερίζω 'share')
  id 4571 συναλίζομαι G9299->G4871  (Ac 1:4 = συναλίζω; snapped συναυλίζομαι 'lodge')
  id 4654 συνμερίζω   G21192->G4829 (1 Cor 9:13 = συμμερίζω; snapped συνερίζω extended)
  id 4573 συναλλάσσω  G9996->G4900  (Ac 7:26 verse slot = συνελαύνω G4900 [Byz reading];
                                     placeholder G9996 was wrong)

NULL rescues (real NT double-form headwords that missed exact match on index form):
  id 4450 "στάδιος, στάδιον"   -> G4712 (furlong/stadium; Lk 24:13, Jn 6:19, Rev)
  id 4510 "στρώννυμι, στρωννύω"-> G4766 (spread; Mt 21:8, Mk 14:15, Ac 9:34)

RELABELS (vision-OCR headword mislabels; lemma re-derived from body, then keyed.
p632 is a shift-by-one cascade through the συναν-α cluster — bodies authoritative):
  id 4574 συναλλοιόομαι -> συναναβαίνω  G4872 (body 'go up with' Mk 15:41/Ac 13:31)
  id 4575 συναπάγομαι   -> συναναμίγνυμι G4874 (body 'associate with' 1 Cor 5:9,11)
  id 4576 συναναμίγνυμι -> συναναπαύομαι G4875 (body 'rest along with' Rom 15:32)
  id 4577 συνανάκειμαι  -> συναντάω      G4876 (body 'meet with/encounter' Lk 9:37)
  id 4601 συνείκω       -> σύνειμι       G4895 (body 'am with' from εἰμί; wedlock sense)
  id 4602 συνείπον      -> σύνειμι       G4896 (body 'come together' from εἶμι, Lk 8:4)
  id 4553 "συμφόρ[α]ζω" -> συμφυλέτης    G4853 (body 'fellow-countrymen' 1 Th 2:14;
                                               OCR garbled lemma + verse '4:14')

BAD SNAPS / non-NT / stubs reverted to N/A (strongs NULL; protected from re-snap via
manual:strongs-fix + reviewer_value='G_N/A'):
  id 4315 σειρόω    (body 'not found in the NT'; snapped στειρόω G21123)
  id 4554 συμφορά   (papyri 'planted/cultivated land', not NT; snapped συμφοράζω G9285)
  id 4637 σύνκλητος (Roman senate, not NT; snapped σύγκλητος G9235 extended)
  id 4600 συνεῖδον  (cross-ref STUB 'See s.v. σύνοιδα'; snapped συνεῖπον G21188)
  id 4524 συγχ—     (prefix cross-ref stub 'See passim συγχ-'; snapped συγχέω G4797)
  id 4535 συλλ—     (prefix cross-ref stub; snapped συλλυω G21165)
  id 4550 συμφ—     (prefix cross-ref stub; snapped συμφύω G4855)

N/A tombstones for already-NULL stubs / non-NT words (protect from a future bad snap):
  id 4522 συγκ—   id 4526 συζ—   id 4539 συμβ—   id 4545 συμι—   (prefix stubs)
  id 4348 Οὐάλεριος (proper name Valerius, not NT)
  id 4441 σποράδην  (adverb 'scatteredly', not NT)
  id 4618 σύνζυξ    (not NT)
  id 4633 συνιστορέω (body explicitly 'is not found in the NT')

LEFT FOR PHASE 5 (continuation fragments / needs audit cross-check):
  id 4572 συναλλάσσω p632 pos1 continuation fragment (merge target)
  id 4581 συμπεριφέρομαι p633 pos1 — flagged continuation; resolve in sweep w/ audit
"""
from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "state" / "run.sqlite"


def main() -> int:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    now = datetime.now(timezone.utc).isoformat()

    # (id, new_lemma_or_None, strongs_or_None, note, had_snap)
    #   new_lemma None  -> keep lemma_greek as-is
    #   strongs None     -> revert/keep NULL (G_N/A) + write protective tombstone
    fixes = [
        # --- bad snaps -> real key ---
        (4338, None, "G4525", "σιαίνομαι = σαίνω 1 Th 3:3 FG; bad snap διαγίνομαι G1230", True),
        (4362, None, "G4622", "Σιών 'Zion'; bad snap Σίμων G4613", True),
        (4463, None, "G4723", "στεῖρος = στεῖρα 'barren'; bad snap ἀστεῖος G0791", True),
        (4530, None, "G4809", "συκομορέα = συκομωραία Lk 19:4; bad snap συνομορέω G4927", True),
        (4546, None, "G4833", "συμμορφίζω = συμμορφόω Phil 3:10; bad snap συμμερίζω G4829", True),
        (4571, None, "G4871", "συναλίζομαι = συναλίζω Ac 1:4; bad snap συναυλίζομαι G9299", True),
        (4654, None, "G4829", "συνμερίζω = συμμερίζω 1 Cor 9:13; bad snap συνερίζω G21192", True),
        (4573, None, "G4900", "συναλλάσσω Ac 7:26 verse slot συνελαύνω G4900; was placeholder G9996", False),
        # --- NULL rescues ---
        (4450, None, "G4712", "στάδιος, στάδιον double-form -> G4712 (missed exact)", False),
        (4510, None, "G4766", "στρώννυμι, στρωννύω double-form -> G4766 (missed exact)", False),
        # --- relabels (lemma re-derived from body) ---
        (4574, "συναναβαίνω", "G4872", "p632 OCR mislabel; body 'go up with' Mk 15:41/Ac 13:31", True),
        (4575, "συναναμίγνυμι", "G4874", "p632 OCR mislabel; body 'associate with' 1 Cor 5:9,11", False),
        (4576, "συναναπαύομαι", "G4875", "p632 OCR mislabel; body 'rest along with' Rom 15:32", True),
        (4577, "συναντάω", "G4876", "p632 OCR mislabel; body 'meet with' Lk 9:37", True),
        (4601, "σύνειμι", "G4895", "p635 OCR mislabel συνείκω; body 'am with' (εἰμί)", True),
        (4602, "σύνειμι", "G4896", "p635 OCR mislabel συνείπον; body 'come together' (εἶμι) Lk 8:4", True),
        (4553, "συμφυλέτης", "G4853", "p628 OCR mislabel; body 'fellow-countrymen' 1 Th 2:14", False),
        # --- p603 σής/σθένος/σιαγόνιον scramble (Codex-confirmed); fix by body ---
        (4333, "σητόβρωτος", "G4598", "p603 OCR mislabel σθένος; body 'moth-eaten' Jas 5:2", False),
        # --- bad snaps / non-NT / stubs -> N/A ---
        (4315, None, None, "σειρόω 'not in NT'; revert bad snap στειρόω G21123 -> N/A", True),
        (4554, None, None, "συμφορά papyri 'planted', not NT; revert συμφοράζω G9285 -> N/A", True),
        (4637, None, None, "σύνκλητος Roman senate, not NT; revert σύγκλητος G9235 -> N/A", True),
        (4600, None, None, "συνεῖδον cross-ref stub; revert συνεῖπον G21188 -> N/A", True),
        (4524, None, None, "συγχ— prefix stub; revert συγχέω G4797 -> N/A", True),
        (4535, None, None, "συλλ— prefix stub; revert συλλυω G21165 -> N/A", True),
        (4550, None, None, "συμφ— prefix stub; revert συμφύω G4855 -> N/A", True),
        (4332, None, None, "p603 σής cross-ref stub 'see s.v. σηρικός' -> N/A", False),
        (4334, None, None, "p603 σιαγόνιον placeholder/non-NT -> N/A", False),
        # --- already-NULL stubs / non-NT: tombstone only ---
        (4522, None, None, "συγκ— prefix stub -> N/A", False),
        (4526, None, None, "συζ— prefix stub -> N/A", False),
        (4539, None, None, "συμβ— prefix stub -> N/A", False),
        (4545, None, None, "συμι— prefix stub -> N/A", False),
        (4441, None, None, "σποράδην adverb, not NT -> N/A", False),
        (4633, None, None, "συνιστορέω body 'not found in the NT' -> N/A", False),
    ]

    with con:
        for eid, new_lemma, strongs, note, had_snap in fixes:
            row = con.execute("SELECT lemma_greek FROM entries WHERE id=?", (eid,)).fetchone()
            if row is None:
                print(f"  WARN id={eid} not found; skipping")
                continue
            old_lemma = row["lemma_greek"]
            if new_lemma is not None:
                con.execute("UPDATE entries SET lemma_greek=?, strongs=? WHERE id=?",
                            (new_lemma, strongs, eid))
            else:
                con.execute("UPDATE entries SET strongs=? WHERE id=?", (strongs, eid))

            # Resolve any existing auto:strongs-snap disagreement -> manual:strongs-fix.
            if had_snap:
                con.execute(
                    """UPDATE disagreements SET resolution=?, resolution_by=?, resolved_at=?
                       WHERE entry_id=? AND resolution_by='auto:strongs-snap'""",
                    (note, "manual:strongs-fix", now, eid),
                )
            # For N/A results, ensure a protective tombstone exists
            # (manual:strongs-fix + reviewer_value='G_N/A') so phase3 won't re-snap.
            if strongs is None:
                has = con.execute(
                    """SELECT 1 FROM disagreements WHERE entry_id=?
                       AND resolution_by='manual:strongs-fix' AND reviewer_value='G_N/A'""",
                    (eid,),
                ).fetchone()
                if not has:
                    con.execute(
                        """INSERT INTO disagreements
                           (entry_id, field, producer_value, reviewer_value,
                            resolution, resolution_by, resolved_at)
                           VALUES (?,?,?,?,?,?,?)""",
                        (eid, "strongs", old_lemma, "G_N/A", note,
                         "manual:strongs-fix", now),
                    )
            # For relabels, record a lemma_swap note for transparency.
            if new_lemma is not None and new_lemma != old_lemma:
                con.execute(
                    """INSERT INTO disagreements
                       (entry_id, field, producer_value, reviewer_value,
                        resolution, resolution_by, resolved_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (eid, "lemma_greek", old_lemma, new_lemma, note,
                     "manual:lemma-swap", now),
                )

    print(f"applied {len(fixes)} keyfix decisions")
    for eid, *_ in fixes:
        r = con.execute("SELECT id,lemma_greek,strongs FROM entries WHERE id=?", (eid,)).fetchone()
        if r:
            print(f"  id={r['id']:5d} {r['lemma_greek']:24s} -> {r['strongs']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
