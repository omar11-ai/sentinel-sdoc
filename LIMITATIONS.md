# LIMITATIONS

Stated plainly. A system that names its own boundaries is more deployable
than one that implies it has none.

## Scope

- **Seven fields only.** Shipper, consignee, notify party, port of loading,
  port of discharge, container count, gross weight (kg). This is the brief's
  scope; the architecture generalises but is untested beyond these seven.
- **Preliminary-round scope decisions.** No authentication and a single
  free-text reviewer identity (`demo-reviewer`) — the audit trail records the
  actor without an auth system. Multi-reviewer approval chains are final-round
  work (see ARCHITECTURE.md → Production path).
- **One dataset.** Every threshold (entity similarity, ambiguity confidence,
  escalation ordering) is tuned on this 520-email corpus and may not transfer
  unchanged to another carrier's paperwork.

## Engine

- **OCR is out of scope.** All binary attachments in this corpus carry
  readable text layers; the reader interface accommodates an OCR lane but the
  shipped pipeline never needed it.
- **The alias dictionary is corpus-derived.** Labels harvested from this
  dataset (including the bilingual English/Chinese labels) are covered; a
  genuinely novel label on unseen paperwork depends on the LLM fallback lane
  and is surfaced as low confidence rather than silently dropped.
- **Entity similarity thresholds are measured on this corpus.** A different
  defect-injection distribution would need the same one-variable-at-a-time
  re-tuning (see EVALUATION.md).
- **Model self-reported confidence is uncalibrated.** It orders the review
  queue and gates escalation; it is never presented as a probability.

## Process

- **No competitor benchmark.** We make no comparative accuracy claim against
  other teams or commercial document-AI products.
- **The reviewer overlay is session + store local.** Corrections recompute
  verdicts and persist to an append-only audit store, but multi-user conflict
  resolution beyond version checks is out of scope for this round.
- **Cost figures are our own measurements only.** No industry cost-of-error
  or vendor pricing figures are quoted anywhere in this repo, the deck, or
  the video, because none of them can be verified from here.
