# Pass 72 — cleanup/refactor handoff

This pass intentionally avoids gameplay changes. It only moves self-contained code out of `openagent/runtime.py` so future reverse-engineering passes are easier to review.

## Extracted HUD/UI renderer

Moved the status-bar and 8x8 text helpers from `openagent/runtime.py` into:

```text
openagent/hud.py
```

The new module owns:

- `STATUS_BAR_H`
- `UI_TEXT_PAGE_0`, `UI_TEXT_PAGE_1`, `UI_HUD_PAGE`
- the fallback-only `HUD_GLYPHS`
- `HUDMixin`, which provides `draw_status_bar()`, `draw_hud_digit_string()`, `draw_hud_icon()`, and `draw_ui_text_8x8()`

Gameplay state still lives in `OpenAgentApp`; the mixin only reads it for drawing. This keeps the refactor low-risk and preserves the current HUD behavior from pass 61/70.

## Extracted player state dataclass

Moved the `Player` dataclass into:

```text
openagent/player.py
```

`runtime.py` now imports `Player` instead of defining it inline. Movement behavior is not moved yet; only the data shape was separated.

## Runtime size

`openagent/runtime.py` went from roughly 3062 lines to roughly 2834 lines. It is still too large, but now the next refactors have clearer boundaries.

## Recommended next cleanup targets

1. Extract projectile update/collision helpers into `openagent/projectiles.py`.
2. Extract damage/death helpers into `openagent/damage.py` or `openagent/player_lifecycle.py`.
3. Extract interaction dispatch for pickups/doors/teleports into `openagent/interactions.py`.
4. Keep actual ASM-derived constants in small factual modules instead of adding more magic numbers to runtime.

## Validation

```bash
python tools/audit_project.py
PYTHONDONTWRITEBYTECODE=1 python -c "import openagent.runtime, openagent.hud, openagent.player; print('imports ok')"
```
