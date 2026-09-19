# Official self-check bundle

`scoring.py` is the organizers' official scorer and `ground_truth.json` is the
official answer key for the v2 dataset. The organizers distributed both to ALL
teams inside the participant docker kit **intentionally, for self-checking**
(organizers' clarification, relayed to every team). This bundle powers the
dashboard "Self-Check" button: it grades SENTINEL's own submission live with
the exact code the judges will use. Nothing here influences the pipeline at
run time — iteration never touched ground truth.
