---
name: add-backend-endpoint
description: Step-by-step checklist for adding a new endpoint to server/main.py, following this codebase's single-file FastAPI conventions. Use this skill when adding or significantly changing a backend API route.
---

# Adding a Backend Endpoint

This codebase keeps all routes, Pydantic models, and filter helpers in one file: `server/main.py`. There is no `models.py` or `routers/` split — don't introduce one. Follow this checklist in order; it mirrors how `/api/restocking/recommendations` was added.

## Checklist

1. **Define Pydantic model(s) near the other models**, above the `# API endpoints` section (not inline in the route). Split into separate models for nested shapes rather than nesting dicts — e.g. `RestockingResponse` contains a `RestockingSummary` and a `List[RestockRecommendation]`, each its own class.

2. **Reuse existing filter helpers instead of writing new filtering logic:**
   - `apply_filters(items, warehouse, category, status)` — warehouse/category/status, all optional, `'all'` means no filter.
   - `filter_by_month(items, month)` — only meaningful for order-dated data; don't apply it to inventory (inventory has no time dimension — see CLAUDE.md "Common Issues").
   - If you need a new cross-cutting computation (like `compute_demand_scores`), add it as its own small function next to `apply_filters`, not inline in the route body.

3. **Add the route with `response_model=` set** to a Pydantic type (or `List[...]`), not a bare dict — this is the established convention for anything with a fixed, typed shape. Place it near related existing routes (e.g. a new inventory-adjacent route goes near `/api/inventory`, not at the end of the file).

4. **Validate inputs explicitly before computing anything:**
   ```python
   if budget < 0:
       raise HTTPException(status_code=400, detail="Budget must be non-negative")
   ```
   - Required query params: just type them without a default (`budget: float`, no `= None`) — FastAPI returns 422 automatically if the client omits them. Don't hand-roll this check.
   - Domain-invalid values (negative budget, etc.): raise `HTTPException(400, ...)` yourself.
   - Not-found lookups: raise `HTTPException(404, ...)`.

5. **Never mutate the module-level data lists** (`inventory_items`, `orders`, etc.). Build new lists/dicts from them; the existing filter helpers already do this correctly — copy that pattern.

6. **Round money fields explicitly** (`round(value, 2)`) at the point you compute them, not just at the response boundary — see how `line_cost` and `remaining` are rounded on every iteration in the restocking endpoint, not only in the final summary.

7. **Write matching tests** in `tests/backend/` using the `backend-api-test` skill — don't skip this step or leave it for later.

## What NOT to do

- Don't add a database, ORM, or persistence layer — this app is intentionally in-memory, load-once-from-JSON (`server/mock_data.py`).
- Don't add auth, rate limiting, or production hardening — out of scope for this demo app (see `server/CLAUDE.md` Security Notes).
- Don't return a raw `dict` from a route with a well-defined, fixed shape — type it with `response_model`.
- Don't duplicate filter logic inline in a new route — extend or call the shared helpers.

## Verification

After adding the endpoint:
1. Hit `http://localhost:8001/docs`, expand the new route, and try it with realistic + edge-case inputs (missing required params, zero/negative values, filters that narrow to empty).
2. Run the full backend suite to confirm no regressions: `cd server && uv run pytest ../tests/backend/ -v -c ../tests/pytest.ini`.
