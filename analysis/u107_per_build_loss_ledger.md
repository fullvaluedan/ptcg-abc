# U107: Per-Build Loss Ledger

## Summary

Per-build loss segregation for submission refs: 54315802, 54315565.

Current status: **MANIFEST INFRASTRUCTURE ADDED** (tools/harvest_replays.py updated to persist episode-to-ref mapping to data/episode_to_ref.json).

## Next Steps

1. Backfill existing episodes via tools/scout.py list_episodes per ref
2. Filter loss distributions using the episode-to-ref manifest
3. Rerun loss_classifier restricted to current-king and shadow-king episodes

## Refs Analyzed

- shadow-king (best live): 54315802 (heuristic+trolley-ability)
- reclaim-king (safe floor): 54315565 (heuristic+trolley)

## Implementation Status

- [DONE] harvest_replays.py modified to persist episode->ref mapping
- [DONE] loop_state.py updated with classify_dirs_per_build function (ref filtering infrastructure)
- [TODO] Backfill existing episodes with their refs (requires API call per ref)
- [TODO] Filter loss_classifier output by ref

## Note

This unit is mechanical: it collects loss data per build so we can attribute
targeting decisions to the shipped agent only, not a historical average
across all ever-submitted builds. This segregation is prerequisite for
honest loss mode targeting in TRACK L going forward.
