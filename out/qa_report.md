# Whole-book QA audit — FINAL SUMMARY (2026-06-03)

Two-layer audit over the completed digitization (4,804 entries after fixes).

## Layer 1 — deterministic integrity (scripts/qa_audit.py)
Initial findings -> fixes (scripts/qa_fix.py + targeted):
- 251 early-wave (pages 31-399) unmerged same-lemma continuation pairs: the
  export dedup had been CLIPPING the shorter half of each. 249 merged
  (+2 mega-entry chain merges: epi p262-265, kata p352-354). Guard correctly
  refused the 2 true homograph adjacencies (eis G1519/heis G1520,
  Stephanos G4736/stephanos G4735) - permanent benign flags.
- 7 literal 'G_N/A' strings -> NULL + tombstone (honest coverage).
- 5 deliberate reachability keys documented with exemption rows.
- 31 pre-convention NULLs tombstoned.
- 19 entries' alpha-era bare chain refs prefixed with their book; 6 odd refs
  fixed individually (I Pet->1 Pet, Ev. Joh->Jn, 2 ib.-NT-anaphors, v.32 merge,
  2 Peter->2 Pet 1:19).
- 2 embedded page-furniture lines stripped.

## Layer 2 — stratified sampled content re-verification (100 entries)
30 alpha (31-80) / 30 early (81-320) / 20 mid (321-600) / 20 late (601-735),
independently verified against page OCR by 10 parallel agents:
- 97/100 clean.
- 2 genuine key refinements applied: epeimi G7376->G1966 (classic id lives
  under participle lemma epiousa), kyklos G20618->G2945 (body cites dat.
  kyklo, Rev 4:6).
- 1 false alarm (pote 'Rom 1:10' IS cited in the full body; reviewer saw a
  truncated excerpt).

## Final state
- qa_audit: every category 0 except 2 verified-legit homograph adjacencies and
  79 'See s.v.' stubs + 1 legit one-line entry.
- Export: 4,804 entries -> deduped set, gates 98.3% Strong's / 88.6%
  agree+minor (agree+minor UP from 87.0% as fragment-major reviews merged away).
- Estimated residual content-defect rate from the sample: ~1-3% minor issues,
  0 critical.

Details below are the last full qa_audit category dump.

# Whole-book QA audit report

## A_order — 0

## B_dup — 0

## C_unmerged — 2
- p216->217: εἰς id1423 | id1425
- p618->619: Στέφανος id4476 | id4477

## D_short — 80
- p33 id99 ἄγγος: 'See s.v. ἀγγεῖον.'
- p58 id309 ἀμφιάζω: 'See under ἀμφιέννυμι.'
- p64 id355 ἀνακαινίζω: 'See *s.v.* ἀνακαινόω.'
- p186 id1223 διαυγής: 'see *διαφανής*.'
- p203 id1346 δώδεκα: 'See under δεκαδύο. It is MGr.'
- p209 id1373 ἐγκ.: 'See also ἐνκ.'
- p210 id1378 ἐγκοπή: 'See ἐκκοπή, ἐκκόπτω.'
- p211 id1390 ἐθέλω: 'See θέλω.'
- p214 id1413 εἱλίσσω: 'See ἑλίσσω.'
- p215 id1416 εἵνεκεν: 'See ἕνεκα.'
- p215 id1417 εἴπερ: 'See εἰ.'
- p219 id1440 εἴωθα: 'See ἔθω.'
- p224 id1471 ἐκκακέω: 'See ἐνκακέω.'
- p232 id1545 ἐλεάω: 'See *s.v.* ἐλεέω.'
- p246 id1656 ἐνκοπή: 'See *s.v.* ἐκκοπή.'
- p246 id1659 ἔννατος: 'See *s.v.* ἔνατος.'
- p246 id1660 ἐννεός: 'See *s.v.* ἐνεός.'
- p252 id1718 ἔξειμι: 'from εἰμί, see *s.v.* ἔξεστι.'
- p255 id1737 ἐξόν: 'See *s.v.* ἔξεστι.'
- p312 id2153 ἤτοι: 'See *s.v.* ἤ.'
- p331 id2276 Ἱερουσαλήμ: 'See *s.v.* Ἱεροσόλυμα.'
- p339 id2332 ἰχθύδιον: '*P Flor* II. 119⁷ (A.D. 254) ἰχθύδια.'
- p371 id2596 κεραία: 'See *s.v.* κερέα.'
- p372 id2612 κεφαλιόω: 'See *s.v.* κεφαλαιόω.'
- p373 id2622 Κηφᾶς: 'See F. C. Burkitt *Syriac Forms*, p. 5.'
- p375 id2638 Κλαῦδα: 'See *s.v.* Καῦδα.'
- p420 id2965 μασθός: 'See *s.v.* μαστός.'
- p425 id3006 μελίσσιος: 'See s.v. μέλι.'
- p426 id3016 μενοῦν: 'See *s.v.* μέν.'
- p439 id3086 μήγε: 'For εἰ δὲ μήγε see *s.v.* γε.'
- p440 id3100 μήπου: 'See *s.v.* μήπω.'
- p453 id3202 Νεάπολις: 'See *s.v.* νέος *ad finem.*'
- p453 id3203 Νεεμάν: 'See *s.v.* Ναιμάν.'
- p454 id3210 νεοσσός: 'See *s.v.* νοσσός.'
- p457 id3238 Νικολαΐτης: 'See *s.v.* Νικόλαος.'
- p460 id3266 νουμηνία: 'See νεομηνία.'
- p473 id3341 οἰκουρός: 'See *s.v.* οἰκουργός.'
- p496 id3507 οὐρανόθεν: 'See Lob. *Phryn*. p. 93 f.'
- p528 id3723 πατραλῴας: 'See *s.v.* πατρολῴας.'
- p541 id3834 πετρώδης: 'See *s.v.* πέτρα.'
- p542 id3847 πιθός: 'See *s.v.* πειθός.'
- p543 id3852 Πιλᾶτος: 'See *s.v.* Πειλᾶτος.'
- p546 id3878 πλατεῖα: 'See *s.v.* πλατύς.'
- p548 id3895 πλήθω: 'See *s.v.* πίμπλημι.'
- p562 id3996 πραγματεία: 'See *s.v.* πραγματία.'
- p583 id4147 προσωπολήμπτης: 'See *s.v.* **προσωπολημπτέω.**'
- p583 id4148 προσωπολημψία: 'See *s.v.* **προσωπολημπτέω.**'
- p586 id4171 πρώϊμος: 'See *s.v.* **πρόϊμος**'
- p587 id4176 πρωτοκαθεδρία: 'See *s.v.* πρωτοκλισία.'
- p592 id4221 ῥαββουνεί: 'See *s.v.* ῥαββεί.'
- p593 id4233 ῥαχά: 'See *s.v.* ῥακά.'
- p593 id4235 Ῥεφάν: 'See *s.v.* Ῥομφά.'
- p593 id4241 ῥήσσω: 'See *s.v.* ῥήγνυμι.'
- p598 id4283 Σαλω(ο)μών: 'See *s.v.* **Σολομών.**'
- p598 id4290 Σαούλ: 'See *s.v.* **Σαῦλος.**'
- p601 id4320 σεληνιάζομαι: 'See *s.v.* σελήνη *ad fin.*'
- p603 id4332 σής: 'for σ.ηρός. See *s.v.* σηρικός.'
- p603 id4334 σιαγόνιον: '(See note.)'
- p611 id4409 Σμύρνα: 'See *s.v.* **Ζμύρνα**.'
- p616 id4449 σπυρίς: 'See *s.v.* σφυρίς.'
- p620 id4489 Στοϊκός: 'See *s.v.* Στωϊκός.'
- p625 id4521 συγγνώμη: 'See *s.v.* συνγνώμη.'
- p625 id4522 συγκ—: 'See *passim* συνκ—'
- p625 id4524 συγχ—: 'See *passim* συνχ—'
- p625 id4526 συζ—: 'See συνζ—'
- p626 id4535 συλλ—: 'See *passim* συνλ—'
- p627 id4539 συμβ—: 'See *passim* συνβ—'
- p628 id4545 συμι—: 'See *s.v.* συμ.'
- p628 id4550 συμφ—: 'See *s.v.* συμφ.'
- p635 id4600 συνεῖδον: 'See *s.v.* σύνοιδα.'
- p642 id4673 συνπίνω: 'See *s.v.* συνεσθίω.'
- p642 id4679 συνσο—: 'See *passim* συσσο—'
- p657 id4779 τάχε(ι)ον: 'See *s.v.* **ταχέως.**'
- p657 id4782 τάχιστα: 'See *s.v.* **ταχέως.**'
- p672 id4898 τρίτον: 'See *s.v.* τρίτος.'
- p691 id5050 ὑσσός: 'See *s.v.* ὕσσωπος.'
- p693 id5064 φαιλόνης: 'See *s.v.* φελόνης.'
- p703 id5153 Φοινίκισσα: 'See *s.v.* Συροφοινίκισσα.'
- p719 id5268 χόος: 'See χοῦς.'
- p721 id5279 χράω: 'See κίχρημι.'

## D_lemma?? — 0

## D_heading_in_body — 0

## D_furniture — 0

## E_badformat — 0

## E_unknown_g — 0

## E_mismatch — 0

## F_null_no_tombstone — 0

## G_ref — 0

## H_drift — 0

## I_badjson — 0
