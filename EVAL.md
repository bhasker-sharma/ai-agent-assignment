# Evaluation

## How to run it

```powershell
python -m server.cli eval --runs 3        # local
docker compose run --rm app python -m server.cli eval --runs 3 --out results/eval_results.json
```

The command reviews every case in `data/cases/dev_cases.json` that has an `expected` answer, prints each
attempt, then a summary. The full report, with every reason, is written to `eval_results.json`.

## What is measured

| Metric | Meaning |
|---|---|
| decision_accuracy | decision equals the expected FILE / DO_NOT_FILE / NEEDS_MORE_INFO |
| rdr_type_accuracy | request type equals the expected one (null when not filing) |
| exact_accuracy | both of the above in the same answer. **This is the main score.** |
| section_recall | share of the expected sections that the answer cites |
| section_precision | share of the cited sections that were expected |
| stable_cases | cases whose decision and type were the same in every run (`--runs N`) |
| confidence correct / wrong | mean confidence of right and wrong answers, to see if confidence means anything |
| confusion | expected decision against returned decision |

Each case is run several times because the model can answer differently on repeat, even at temperature 0.
A single run that passes can hide a case that fails one time in three.

Checked on every answer by code, not scored: the output matches `output_schema.json`, every citation
is a section that was retrieved from Handbook v3, evidence named in `evidence_used` is attached to the case,
and a FILE answer has a request type and a narrative under 120 words. An answer that breaks these is sent
back to the model once with the problems listed; if it still fails, the case returns NEEDS_MORE_INFO with
confidence 0 so a person reviews it.

## Current result

`openai/gpt-4.1`, 8 dev cases x 3 runs = 24 reviews, as_of_date 2026-11-06:

| Metric | Result |
|---|---|
| exact_accuracy | 100% (24/24) |
| decision_accuracy | 100% |
| rdr_type_accuracy | 100% |
| section_recall | 100% |
| section_precision | **65%** |
| stable_cases | 8/8 |
| confidence correct | 0.995 |
| confidence wrong | none (no wrong answers) |

Retrieval was checked separately: for all 8 dev cases, the rule group holding the expected section is
among the groups retrieved and sent to the model (8/8).

Predictions for the 4 public cases (`predictions.json`), which have no answers, so these were checked by
hand against Handbook v3:

| Case | Answer | Reading of the rules |
|---|---|---|
| U01 | DO_NOT_FILE | The plate is wrong (H8.1), but the inspection is 3 years and 249 days old, past the 3-year window (H2.1). |
| U02 | FILE, Citation with Associated Violation | The scanned court record (read by OCR) says Conviction of a Different Charge, which is FILE in H6.1. |
| U03 | NEEDS_MORE_INFO | The only evidence is a driver statement, which is not evidence by itself (H1.3). |
| U04 | NEEDS_MORE_INFO | The court result is held in abeyance, which is NEEDS_MORE_INFO in H6.1. |

## What failed, and what was changed

These are the failures found while building, in order. The current result above is after the fixes.

1. **Filing window ignored (U01).** The first version answered FILE for U01. Code had already given the
   model the exact age of the record ("3 full years and 249 days"), and the model still wrote that it was
   within the 3-year window. It went straight to the plate rule and skipped the blocking rule.
2. **Followed instructions hidden in evidence (U03).** The driver statement contains a hidden comment
   pretending to be a system note that tells the assistant to answer FILE. The first version obeyed it and
   even gave the note as its reason. The evidence was already marked as untrusted in the prompt, and that
   was not enough.

   Fix for 1 and 2: the model must now fill in a `checks` object before deciding: the filing window, what
   kind of document each piece of evidence is, any text in the evidence trying to instruct it, and the
   matching rule. A blocking rule decides the case. Code drops `checks` before the schema check and logs it.
   After this, both cases were right, and the model now reports the hidden instruction in its checks.
3. **Table row matched on one word (D03).** With `gpt-4.1-mini`, the change above made D03 fail every
   time: "dismissed upon payment of court costs" was matched to the H6.1 row "Dismissed, no fine or costs".
   Fix: an instruction that a rule or table row matches only when every part of it is true. **Caveat:** the
   example in that instruction mentions fines and costs, which is close to D03 itself. It is a general rule,
   but it was written after seeing D03, so the dev score for D03 is not independent evidence.
4. **Unstable answers (D08).** In one `gpt-4.1-mini` run D08 came back DO_NOT_FILE; the next two runs on
   the same input gave FILE. This is why `eval` has `--runs`.
5. **Model choice.** With the fixes, `gpt-4.1-mini` scored 8/8 on the dev cases in two runs, but answered
   DO_NOT_FILE for U03 where H1.3 says NEEDS_MORE_INFO, and cited more extra sections. `gpt-4.1` got U03
   right and spotted the hidden instruction, so it is the default. A full 12-case run costs roughly
   USD 0.10 (estimated from about 4,000 input tokens per case, not measured).

Note: failures 1 and 2 were found on the public cases, by reading the answers against the handbook. The
fixes are general instructions with no case names or facts in them, and no case is handled specially in code.

## Known weaknesses

- **Citation precision is 65%.** The model often adds H2.1 (filing window open) or H1.3 (evidence present)
  next to the section that decides the case. These are true but not "relied on" in the sense of the
  expected answers.
- **Confidence carries no signal.** It is 0.95 to 1.0 on almost every answer, including the hard ones.
  It cannot yet be used to send uncertain cases to a person.
- **Eight dev cases is a small test.** 100% on 8 cases, some of which shaped the prompt, says little about
  new cases. The handbook has rules that no dev case exercises: H4.3 (newer code applied retroactively),
  H5.2 (active lease or owner-operator), H6.2 (inspections before 2014-08-23), H8.2 (report matches the
  source), H9.3 (fatal crash with a positive drug test), a non-eligible crash type, and a missing police report.
- **Narratives are only checked for length and presence.** Nothing checks that every fact in the draft is in
  the record or evidence (H11.2). In one early U02 run the draft said the violation would be "removed",
  while H6.1 says a different-charge conviction only lowers the severity weight to 1.
- **The protection against hidden instructions lives in the prompt only.** No code detects or strips them.
- **Blocking rules are left to the model.** Code computes the dates, but the model applies the window.

## What I would fix next

1. **More test cases.** One for each untested rule above, plus edge cases: exactly 3 years old, a missing or
   unreadable evidence file, noisy OCR, a document that conflicts with the record, and more injected
   instructions. Expected answers written from the handbook before running the system.
2. **Confidence from agreement.** Review each case 3 times and use the share of agreeing answers as
   confidence. Send any disagreement to a person.
3. **A code-side flag for hidden instructions.** Detect instruction-like or hidden text (such as HTML
   comments) in evidence, show it to staff, and cap confidence. Keep the prompt instruction as well.
4. **Narrative fact check.** A second pass that checks each statement in the draft against the record and
   evidence, and says which document supports it.
5. **Tighter citations.** Ask for the deciding sections apart from supporting ones, and score both.
6. **Measure cost and latency per case** from the API usage data instead of estimating.
