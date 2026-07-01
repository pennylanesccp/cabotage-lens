# Literature Reference Audit

This audit records the final citation pass for the LaTeX report and companion technical article. It uses the local sources in `docs/references/`, the existing bibliography in `docs/references.bib`, and the audit notes in `docs/literature_audit/` plus `docs/tf_support/writing/tf_literature_citation_map.md`.

Scope reviewed:

- `docs/report/main.tex`
- `docs/report/chapters/`
- `docs/report/appendices/`
- `docs/article/cabotagelens_technical_article.tex`
- `docs/references.bib`
- `docs/references/`
- `docs/literature_audit/`

## Citation/source matrix

| Report/article section | Claim or idea | Source/paper | How the source is used | Citation key/reference | Status |
| --- | --- | --- | --- | --- | --- |
| Report ch. 1 introduction | Brazilian freight is road-heavy and cabotage is policy-relevant, but route-level comparison is still required. | Brazilian coastal shipping: New prospects for growth with decarbonization | National cabotage context and BR do Mar/policy framing. | `icct2022` | cited |
| Report ch. 1, ch. 3, ch. 4; article introduction/methodology | Road-only versus road-cabotage-road comparisons must be door-to-door rather than ship-only versus truck-only. | The comparative CO2 efficiency of short sea container transport; Brazilian maritime containerized cabotage competitiveness assessment based on a multimodal super network; Modal shift from road haulage to short sea shipping | Supports corridor-specific and chain-level comparison; warns against isolated-mode comparisons. | `shortsea2019`; `competitiveness2024`; `modalshiftreview2020` | cited / wording adjusted |
| Report ch. 3, ch. 4, ch. 8, ch. 9; article context/methodology/limitations | Operational TTW CO2e must remain separate from WTW, LCA, CO2-only, and external benchmark notation. | Brazilian coastal shipping; Decarbonization pathways in Brazilian maritime cabotage; maritime fuels LCA review | Boundary contrast and caution against mixing scopes. | `icct2022`; `decarb2024`; `maritimelca2024` | cited / wording adjusted |
| Report ch. 3, ch. 4, ch. 8, ch. 9; article context/methodology/discussion | Cost output is a modeled operational proxy, not freight rate, tariff, booking, contract, or commercial feasibility. | Brazilian cabotage competitiveness supernetwork study; modal-shift systematic review | Supports broader commercial/network factors that CabotageLens intentionally excludes. | `competitiveness2024`; `modalshiftreview2020` | cited / wording adjusted |
| Report ch. 3, ch. 4, ch. 9; article context/methodology | Port operations and hoteling can affect multimodal emissions/cost interpretation but need provenance and boundary alignment. | Fuel consumption at berth survey; ship hoteling/loading/unloading emissions study; at-berth air-quality study; Brazilian cabotage decarbonization pathways | Justifies treating port/berth operations as relevant components while keeping factors bounded and non-calibrating. | `berth2009`; `shipops2022`; `berthairquality2010`; `decarb2024` | cited / wording adjusted |
| Report ch. 4, ch. 9, ch. 10; article methodology/implementation/limitations | CabotageLens is not a complete supernetwork, schedule, frequency, slot, or service-availability model. | Brazilian cabotage competitiveness supernetwork study; modal-shift systematic review | Supports the limitation that real modal choice includes service network, frequency, inventory, reliability, and commercial terms. | `competitiveness2024`; `modalshiftreview2020` | cited / wording adjusted |
| Report ch. 4, ch. 6, ch. 7, ch. 9; appendices; article route/provenance/results | Haversine fallback, same-port, alternate-port, and reference-needed cases must remain sensitivity/limitation material. | Project validation artifacts and citation map, not a literature paper | Uses tracked CabotageLens validation evidence to define use categories. Literature only supports general route/network caution. | `docs/validation/*`; `docs/tf_support/writing/tf_literature_citation_map.md` | project assumption / cited where literature supports general issue |
| Report ch. 6, ch. 7, ch. 8, ch. 9; article evidence/results/discussion | Gustavo/Costa benchmark provides directional plausibility, not calibrated reproduction or ground truth. | Brazilian cabotage competitiveness and decarbonization papers plus local workbook benchmark artifacts | Literature/workbook family anchors the external benchmark; project artifacts define the interpretation limits. | `competitiveness2024`; `decarb2024`; `docs/validation/tf_validation_batch_002_gustavo_benchmark.md` | cited / project evidence |
| Report ch. 7; article results | Rerun and portops/hoteling closure results are validation outputs, not new literature claims. | Tracked validation artifacts | Used as internal evidence only; no external citation added because the source is the project run record. | `docs/validation/portops_hoteling_rerun_20260630/*` | project evidence |
| Report ch. 10; article future work | Future work may include WTW/LCA, HVO, port operations refinement, service networks, and commercial layers only with compatible data. | Decarbonization pathways; maritime LCA review; supernetwork and modal-shift literature; port/hoteling literature | Supports future-work categories without importing factors into the current model. | `decarb2024`; `maritimelca2024`; `competitiveness2024`; `modalshiftreview2020`; `berth2009`; `shipops2022` | cited / wording adjusted |

## Bibliography consistency

Used citation keys found in the report/article sources and present in `docs/references.bib`:

- `berth2009`
- `berthairquality2010`
- `competitiveness2024`
- `decarb2024`
- `icct2022`
- `maritimelca2024`
- `modalshiftreview2020`
- `shipops2022`
- `shortsea2019`

No used citation key was found without a bibliography entry during this audit pass.

## Unused bibliography entries for human review

The report and article use a selective subset of `docs/references.bib`. The following bibliography entries remain unused in those two LaTeX targets. They were not removed because the repository does not clearly follow a strict cited-only bibliography convention and several are support/future-work references:

- `isoemission2019`
- `marmara2021`
- `berth2009duplicatecheck`
- `shipops2022duplicatecheck`
- `eumrv2025`
- `drybulk2019`
- `seahub2021`
- `porttime2015`
- `eupolicy2011`
- `lowcarbonroute2025`
- `rtg2017`
- `hybridrtg2021`
- `external2023`
- `lifecycle2020`
- `portemissions2014`
- `waterways2025`
- `sssfactors2018`
- `hubcarbon2023`
- `users2022`
- `biodiesel2017`
- `shapley2025`
- `ppo2025`
- `sadc2019`
- `emep2023`
- `workbookdados`
- `antaq2025`
- `anp2026`

## Claims still needing human citation review

These gaps come from `docs/literature_audit/citation_gap_register.md` and remain unresolved by the local audit materials. They should not be silently converted into stronger claims:

- Brazilian truck emission factors and heavy-duty fleet baseline.
- Average capacity utilization for Brazilian cabotage container vessels.
- Brazilian port dwell time, berth productivity, and terminal efficiency data.
- Commercial freight margins and full market-rate formation.
- A stronger methodological standard citation for TTW/TtW as the operational comparison boundary.

## Duplicate or near-duplicate local PDFs noticed

The local reference folder contains duplicate-check candidates that were not moved, deleted, renamed, or cited as separate sources:

- `docs/references/core/seagoing-ships-at-berth-fuel-emissions-survey-2009.pdf`
- `docs/references/core/seagoing-ships-at-berth-fuel-emissions-survey-2009-duplicate-check-needed.pdf`
- `docs/references/core/ship-hoteling-loading-unloading-emissions-se-asia-2022.pdf`
- `docs/references/core/ship-hoteling-loading-unloading-emissions-se-asia-2022-duplicate-check-needed.pdf`

## Cleanup performed in this pass

- Added paragraph-level citations to repeated methodology, boundary, port-operations, supernetwork, and commercial-cost claims in the report and article.
- Added port/hoteling bibliography use to the article where it discusses terminal, auxiliary-energy, at-berth, and missing-data treatment.
- Removed a stale article comment that still described `../references.bib` as preliminary.
- Left unused and duplicate-check bibliography entries in place for human review instead of deleting them.
