# Hoteling and Port-Ops Validation Rerun Summary

Run label: `20260630_portops_hoteling`

Generated at: `2026-06-30T18:04:27-03:00`

Git SHA: `4d900b401bc591bdec59b9868777e80265ae52b4`

Methodology reflected: current checkout rerun with explicit hoteling and port-operation component export, fallback/source-level flags, and component-total checks.

## Output Files

- Input `batch001b_csv`: `docs\validation\portops_hoteling_rerun_20260630\tf_validation_batch_001b_sensitivity_20260630_portops_hoteling.csv`
- Input `batch001b_previous_csv`: `docs\validation\tf_validation_batch_001b_sensitivity_output.csv`
- Input `batch002_csv`: `docs\validation\portops_hoteling_rerun_20260630\tf_validation_batch_002_gustavo_20260630_portops_hoteling.csv`
- Input `batch002_previous_csv`: `data\processed\cabotage_data\gustavo_excel_benchmark.csv`

## Aggregate Results

- Route rows: 29
- Executed/model rows with emissions: 24
- Mean road emissions: 6258.34 kg CO2e
- Mean cabotage/multimodal emissions: 467.43 kg CO2e
- Mean cabotage savings: 91.97%
- Sum navigation emissions over executed rows: 8586.80 kg CO2e
- Sum hoteling emissions over executed rows: 0.00 kg CO2e
- Sum port-ops emissions over executed rows: 309.72 kg CO2e

These aggregate values are unweighted over the rows present in the generated validation outputs; Batch 002 rows are per-container benchmark rows.

## Validation Checks

- Checked executed rows: 24
- Passed: `True`

## Routes Most Affected

| Route | Batch | New hoteling+port-ops kg CO2e | Cabotage delta kg CO2e | Modal change |
| --- | --- | ---: | ---: | --- |
| Porto Alegre, RS -> Recife, PE | Batch 001B sensitivity | 12.91 | 49.25 | False |
| Sao Paulo, SP -> Manaus, AM | Batch 001B sensitivity | 12.91 | -24.97 | False |
| Manaus, AM -> Fortaleza, CE | Batch 001B sensitivity | 12.91 | -24.36 | False |
| Manaus -> Fortaleza | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Manaus -> Recife | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Manaus -> Rio de Janeiro | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Manaus -> Sao Paulo | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Fortaleza -> Manaus | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Fortaleza -> Rio de Janeiro | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |
| Fortaleza -> Sao Paulo | Batch 002 Gustavo/Costa benchmark | 12.91 | 0.00 | False |

## Modal Conclusion Changes

- No route changed road-vs-cabotage emissions winner in the available previous-vs-new comparison.

## Warnings And Limits

- Previous comparison files did not expose hoteling/port-ops component columns for every row; component deltas are therefore unavailable for those rows.
- Some rows explicitly exclude separate hoteling because transport-work intensity is used; this prevents double counting rather than silently zeroing hoteling.
- Port-ops rows using literature_default reflect the documented moves-based scenario because no observed per-port records were supplied in the active artifact.
