from __future__ import annotations

import re
from pathlib import Path

MRV_FILE_GLOB = "*EU MRV Publication of information.xlsx"
_REPORTING_YEAR_PATTERN = re.compile(
    r"^(?P<year>\d{4})-.*EU MRV Publication of information\.xlsx$",
    re.IGNORECASE,
)


def discover_mrv_workbooks(raw_dir: Path) -> list[Path]:
    """Return one MRV publication workbook per reporting year, oldest first."""

    workbooks_by_year: dict[int, list[Path]] = {}
    for path in raw_dir.glob(MRV_FILE_GLOB):
        match = _REPORTING_YEAR_PATTERN.match(path.name)
        if match is None:
            continue
        workbooks_by_year.setdefault(int(match.group("year")), []).append(path)

    duplicates = {
        year: sorted(paths)
        for year, paths in workbooks_by_year.items()
        if len(paths) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{year}: {', '.join(path.name for path in paths)}"
            for year, paths in sorted(duplicates.items())
        )
        raise ValueError(
            "More than one EU MRV workbook was found for the same reporting "
            f"year: {details}"
        )

    return [
        workbooks_by_year[year][0]
        for year in sorted(workbooks_by_year)
    ]
