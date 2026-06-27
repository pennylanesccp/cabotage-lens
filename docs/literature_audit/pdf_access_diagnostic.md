# PDF Access Diagnostic

This document records the extraction status and methodology for the local reference PDFs in this repository, listing all tested files, extraction methods, and limitations.

## Extraction Methodology
* **Tested Methods**:
  1. **Python `pypdf`**: Installed and fully functional (`pypdf` version `6.14.2`). This was the primary tool used for text extraction. All 12 PDF files were successfully read, and raw text could be extracted.
  2. **Python `pdfplumber`**: Tested but not installed/used in the current python environment since `pypdf` was sufficient for text and metadata extraction.
* **Extraction Strategy**: Raw text was extracted per-page and saved to text files or processed directly using regex-based keyword searches (e.g. matching contexts within 250 characters around keywords like `WTW`, `CO2e`, `cost`).

## PDF Readability and Review Status

All 12 local reference PDF files located in `docs/references/core/` were tested for readability using `pypdf`. The results are summarized below:

| File Name | Page Count | Extraction Status | Review Status | Notes & Extraction Details / Snippets |
|---|---|---|---|---|
| `brazilian-cabotage-competitiveness-supernetwork-2024.pdf` | 27 | **Readable** | **Reviewed** | Full text readable. Extracted 1,800 km competitiveness threshold (Page 18) and WTW factors (Page 20, Table 13). |
| `brazilian-coastal-shipping-decarbonization-2022.pdf` | 20 | **Readable** | **Reviewed** | Full text readable. Extracted 8 gCO2/TKU vs 52 gCO2/TKU (Page 12) and 20% fuel cost premium (Page 10). |
| `brazilian-cabotage-decarbonization-pathways-fuels-2024.pdf` | 11 | **Readable** | **Reviewed** | Full text readable. Extracted 3.5 tons/day sea vs 5.0 tons/day port fuel consumption (Page 4), HVO WTW factor of 23.7 gCO2e/MJ (Page 5). |
| `short-sea-container-co2-efficiency-comparison-2019.pdf` | 10 | **Readable** | **Partial** | Text successfully extracted. Review limited to abstract/intro. European context (Norway/North Sea feeder vessel operations). |
| `modal-shift-road-haulage-short-sea-review-2020.pdf` | 26 | **Readable** | **Partial** | Text successfully extracted. Systematic review of global SSS literature (no direct Brazilian inputs). |
| `at-berth-ship-emissions-air-quality-impact-2010.pdf` | 9 | **Readable** | **Pending** | Text successfully extracted. Port air quality and at-berth emissions study. Not yet fully reviewed. |
| `comparative-co2-emissions-short-sea-road-marmara-2021.pdf` | 13 | **Readable** | **Pending** | Text successfully extracted. Short-sea vs road CO2 emissions in Marmara Region. Not yet fully reviewed. |
| `iso-emission-map-short-sea-vs-road-2019.pdf` | 14 | **Readable** | **Pending** | Text successfully extracted. Iso-emission mapping methodology. Not yet fully reviewed. |
| `seagoing-ships-at-berth-fuel-emissions-survey-2009.pdf` | 8 | **Readable** | **Pending** | Text successfully extracted. Fuel/emissions at berth. Not yet fully reviewed. |
| `seagoing-ships-at-berth-fuel-emissions-survey-2009-duplicate-check-needed.pdf` | 8 | **Readable** | **Pending** | Duplicate of the 2009 survey paper. Text successfully extracted. Not yet fully reviewed. |
| `ship-hoteling-loading-unloading-emissions-se-asia-2022.pdf` | 13 | **Readable** | **Pending** | Text successfully extracted. Hoteling emissions in SE Asia ports. Not yet fully reviewed. |
| `ship-hoteling-loading-unloading-emissions-se-asia-2022-duplicate-check-needed.pdf` | 13 | **Readable** | **Pending** | Duplicate of the 2022 hoteling paper. Text successfully extracted. Not yet fully reviewed. |

## Extraction Limitations and Challenges
1. **Unicode/Encoding Output**: When printing extracted text to Windows console, python scripts occasionally failed with `UnicodeEncodeError` due to subscripts (e.g., `₂` in CO₂) and special characters (e.g., `ã` or `é` in Portuguese author names). This was bypassed by outputting directly to UTF-8 text files or logging objects.
2. **Tabular Data Formats**: Tables in some papers (e.g., Table 13 in `competitiveness2024`) had spaces injected in numbers or merged columns when extracted via `pypdf.extract_text()`. Care was taken to manually check and align numbers with their corresponding column headers using context clues.
3. **Qualitative and Contextual Mismatches**: Papers such as `shortsea2019` focus on Northern Europe (feeders vs road), meaning their emissions factors and routing characteristics cannot be directly substituted into a Brazilian cabotage model without careful caveats.
