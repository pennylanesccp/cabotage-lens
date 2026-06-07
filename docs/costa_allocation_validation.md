# Costa Papers Validation Note (Allocation Update)

## Sources Reviewed

- `references/core/brazilian-cabotage-competitiveness-supernetwork-2024.pdf`
- `references/core/brazilian-cabotage-decarbonization-pathways-fuels-2024.pdf`

## Assumptions Used in Code

1. Speed-power / fuel relation for VLSFO (both papers):
- Formula: `F = k1 * V^3 + k2`
- Units stated in papers: `F` in tons/day, `V` in knots.
- Coefficients adopted by papers: `k1 = 0.006754`, `k2 = 37.23`.
- Paper locations:
  - Competitiveness paper, section 4.3 (pages 6-7 in extracted text).
  - Decarbonization paper, section 4.2 / model equations (pages 4 and 6 in extracted text).

2. Operational TEU utilization assumption:
- Competitiveness paper states operational capacity is `80%` of nominal TEU capacity for slot-cost/emissions allocation.
- Implemented default: `load_factor = 0.8` for `teu_share` mode.

3. Fair road vs cabotage comparison guidance:
- Competitiveness paper compares both modes using freight cost + in-transit inventory cost + CO2eq cost, with pre/on-carriage included in multimodal paths.
- This supports transparent, like-for-like door-to-door comparison framing.

4. Additional maritime parameter sanity from decarbonization paper:
- Fuel-based (top-down) method explicitly preferred when detailed per-vessel operation data is limited.
- Channel navigation assumption: 2 hours at 10 knots.
- MDO reference rates used in paper equations: 3.5 t/day (voyage) and 5.0 t/day (port).

## Why TEU-share Is Preferred for Container Cargo

- `dwt_share` (`cargo_t / size_proxy_t_median`) is mass-only and can under-allocate for containerized cargo where slot/cube constraints bind before deadweight.
- `teu_share` (`cargo_teu_resolved / (teu_capacity * load_factor)`) aligns allocation with the operational bottleneck used in liner planning and with Costa's operational-capacity framing.
- For compatibility and auditability, code now computes both (`share_old_dwt`, `share_new_teu`) and exposes `ratio_new_vs_old`.

## Unit Checks Performed

- `cargo_teu_resolved`: integer TEU via `ceil(cargo_teu)` or `ceil(cargo_t / t_per_teu_default)`.
- `teu_loaded = teu_capacity * load_factor` (TEU), then `share_new_teu = cargo_teu_resolved / teu_loaded` (dimensionless), clamped to `[0, 1]`.
- Legacy share remains dimensionless (`cargo_t / size_proxy_t_median`).
- Existing sailing-fuel branches preserved:
  - `fuel_g_per_tnm` branch: `g/(t*nm) * t * nm -> g -> kg`.
  - Fallback branch: `kg/nm * nm * share`.
