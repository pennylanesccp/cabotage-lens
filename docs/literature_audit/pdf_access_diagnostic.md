# PDF Access Diagnostic

This document records the extraction status and methodology for the local reference PDFs in this repository, to avoid repeated parsing blockers.

## Extraction Method Used
The core papers were analyzed using a local Python script leveraging the `pypdf` library (`py -m pip install pypdf`), which successfully extracted raw text from the PDFs. 

## PDF Status Summary

| File | Status | Readable | Notes & Limitations |
|---|---|---|---|
| `brazilian-cabotage-competitiveness-supernetwork-2024.pdf` | **Readable** | Yes | Full text extracted successfully. Quantitative values and methodology sections parsed. |
| `brazilian-coastal-shipping-decarbonization-2022.pdf` | **Readable** | Yes | Full text extracted successfully. Key emissions comparisons identified. |
| `brazilian-cabotage-decarbonization-pathways-fuels-2024.pdf` | **Readable** | Yes | Full text extracted successfully. Fuel factors and ship consumption data identified. |
| `short-sea-container-co2-efficiency-comparison-2019.pdf` | **Partially Readable** | Yes | Full text was technically extracted, but the review was limited to the abstract and intro level due to its qualitative conclusions regarding Europe. |
| `modal-shift-road-haulage-short-sea-review-2020.pdf` | **Partially Readable** | Yes | Full text was technically extracted, but review was limited to abstract/high-level as it is a broad literature review, not a primary source of new quantitative parameters. |

## Limitations Encountered
* **Encoding Issues**: Standard output (stdout) via python scripts on Windows CMD/PowerShell occasionally crashed with `UnicodeEncodeError` when encountering special characters (e.g., `₂` in CO₂). This was resolved by writing the extracted text directly to UTF-8 encoded text files.
* **Extraction Quality**: `pypdf` sometimes broke paragraphs or headers in ways that required regex-based keyword searches with wide windows (e.g., matching within 250 characters) to read context around keywords like `WTW`, `CO2e`, and `cost`.
