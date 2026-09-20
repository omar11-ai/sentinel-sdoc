# Official self-check bundle

`scoring.py` is the organizers' official scorer and `ground_truth.json` is the
official answer key for the v2 dataset. The organizers distributed both to ALL
teams inside the participant docker kit **intentionally, for self-checking**
(organizers' clarification, relayed to every team). This bundle powers the
dashboard "Self-Check" button: it grades SENTINEL's own submission live with
the exact code the judges will use. Nothing here influences the pipeline at
run time — iteration never touched ground truth.

## Organizer clarification (Discord, 19 Sep 2026 — "fichera")

> "…the docker zip files in the info pack ground truth is for you to evaluate your models
> to be better ya. The readme part is just that we didnt update it long time ago. No need
> to worry about the content of us should not release to the participants. The whole
> content it is meant for you all to check your own work."

This supersedes any outdated wording in the bundle README and confirms what this folder
already documented: the key is the organizers' sanctioned self-check asset. See
../GROUND-TRUTH-VERIFICATION.md for the field-level verification it enabled.
