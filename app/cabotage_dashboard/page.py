from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st

from app.cabotage_dashboard.service import (
    CabotageDashboardDataError,
    CabotageDashboardDataset,
    filter_dashboard_dataset,
    load_dashboard_dataset,
)
from app.main.styles import inject_css
from app.main.utils.state import attach_streamlit_logging, init_state

_PAGE_TITLE = "Dashboard"
_TOP_N_DEFAULT = 10
_CHART_HEIGHT = 340


@st.cache_data(ttl=600, show_spinner=False)
def _load_dashboard_dataset_cached() -> CabotageDashboardDataset:
    return load_dashboard_dataset()


def _render_header(dataset: CabotageDashboardDataset) -> None:
    del dataset
    st.markdown(
        f"""
        <section style='padding: 1.1rem 1.35rem; border-radius: 24px; background: linear-gradient(135deg, rgba(234, 244, 255, 0.97), rgba(241, 248, 233, 0.94)); border: 1px solid rgba(15, 23, 42, 0.10); margin-bottom: 0.8rem;'>
            <h1 style='margin: 0; font-size: 2rem; color: #102a43;'>Cabotage {_PAGE_TITLE}</h1>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_filters(dataset: CabotageDashboardDataset) -> tuple[list[int], str | None, list[str], int]:
    years = sorted(int(value) for value in dataset.voyages["reference_year"].dropna().astype(int).unique().tolist())
    closure_modes = sorted(str(value) for value in dataset.voyages["closure_label"].dropna().unique().tolist())
    all_ports = sorted(
        {
            str(value).strip()
            for value in pd.concat(
                [
                    dataset.voyages["origin_port_label"],
                    dataset.voyages["destination_port_label"],
                    dataset.stops["port_label"],
                    dataset.segments["from_port_label"],
                    dataset.segments["to_port_label"],
                ],
                ignore_index=True,
            ).tolist()
            if str(value).strip()
        }
    )

    col_years, col_port, col_closure, col_topn = st.columns([1.1, 1.2, 1.1, 0.7])
    with col_years:
        selected_years = st.multiselect("Years", options=years, default=years)
    with col_port:
        port_options = ["All observed ports"] + all_ports
        selected_port = st.selectbox("Focus port", options=port_options, index=0)
    with col_closure:
        selected_closure_modes = st.multiselect("Voyage closure", options=closure_modes, default=closure_modes)
    with col_topn:
        top_n = st.slider("Top N", min_value=5, max_value=20, value=_TOP_N_DEFAULT, step=1)

    return selected_years, (None if selected_port == "All observed ports" else selected_port), selected_closure_modes, top_n


def _abbr_number(value: float | int | None, *, decimals: int = 1) -> str:
    if value is None:
        return "0"
    number = float(value)
    abs_number = abs(number)
    if abs_number >= 1_000_000_000:
        scaled = number / 1_000_000_000
        suffix = "B"
    elif abs_number >= 1_000_000:
        scaled = number / 1_000_000
        suffix = "M"
    elif abs_number >= 1_000:
        scaled = number / 1_000
        suffix = "k"
    else:
        if number.is_integer():
            return f"{int(number)}"
        return f"{number:,.{decimals}f}".rstrip("0").rstrip(".")

    text = f"{scaled:,.{decimals}f}".rstrip("0").rstrip(".")
    return f"{text}{suffix}"


def _metric_text(value: float | int | None, *, suffix: str = "", decimals: int = 1) -> str:
    return f"{_abbr_number(value, decimals=decimals)}{suffix}"


def _top_departure_ports(segments: pd.DataFrame, top_n: int) -> pd.DataFrame:
    grouped = (
        segments.groupby("from_port_label", dropna=False)
        .agg(
            voyage_count=("voyage_id", "nunique"),
            segment_count=("voyage_id", "size"),
            cargo_weight_t=("cargo_weight_t", "sum"),
            cargo_teu=("cargo_teu", "sum"),
        )
        .reset_index()
        .rename(columns={"from_port_label": "port"})
        .sort_values(
            ["cargo_weight_t", "segment_count", "voyage_count", "port"],
            ascending=[False, False, False, True],
            kind="stable",
        )
    )
    total = float(grouped["cargo_weight_t"].sum()) or 0.0
    grouped["share_pct"] = (grouped["cargo_weight_t"] / total * 100.0) if total > 0 else 0.0
    return grouped.head(top_n)


def _top_arrival_ports(segments: pd.DataFrame, top_n: int) -> pd.DataFrame:
    grouped = (
        segments.groupby("to_port_label", dropna=False)
        .agg(
            voyage_count=("voyage_id", "nunique"),
            segment_count=("voyage_id", "size"),
            cargo_weight_t=("cargo_weight_t", "sum"),
            cargo_teu=("cargo_teu", "sum"),
        )
        .reset_index()
        .rename(columns={"to_port_label": "port"})
        .sort_values(
            ["cargo_weight_t", "segment_count", "voyage_count", "port"],
            ascending=[False, False, False, True],
            kind="stable",
        )
    )
    total = float(grouped["cargo_weight_t"].sum()) or 0.0
    grouped["share_pct"] = (grouped["cargo_weight_t"] / total * 100.0) if total > 0 else 0.0
    return grouped.head(top_n)


def _top_segment_pairs(segments: pd.DataFrame, top_n: int) -> pd.DataFrame:
    grouped = (
        segments.groupby(["from_port_label", "to_port_label"], dropna=False)
        .agg(
            segment_count=("voyage_id", "size"),
            voyage_count=("voyage_id", "nunique"),
            cargo_weight_t=("cargo_weight_t", "sum"),
            cargo_teu=("cargo_teu", "sum"),
        )
        .reset_index()
        .rename(columns={"from_port_label": "from_port", "to_port_label": "to_port"})
        .sort_values(
            ["cargo_weight_t", "segment_count", "voyage_count", "from_port", "to_port"],
            ascending=[False, False, False, True, True],
            kind="stable",
        )
    )
    grouped["corridor"] = grouped["from_port"] + " -> " + grouped["to_port"]
    return grouped.head(top_n)


def _top_intermediate_ports(stops: pd.DataFrame, top_n: int) -> pd.DataFrame:
    intermediate = stops[stops["stop_type"] == "intermediate"].copy()
    if intermediate.empty:
        return pd.DataFrame(
            columns=["port", "stop_count", "voyage_count", "moved_weight_t", "avg_port_stay_hours"]
        )
    grouped = (
        intermediate.groupby("port_label", dropna=False)
        .agg(
            stop_count=("voyage_id", "size"),
            voyage_count=("voyage_id", "nunique"),
            moved_weight_t=("moved_weight_t", "sum"),
            avg_port_stay_hours=("port_stay_hours", "mean"),
        )
        .reset_index()
        .rename(columns={"port_label": "port"})
        .sort_values(
            ["moved_weight_t", "stop_count", "voyage_count", "port"],
            ascending=[False, False, False, True],
            kind="stable",
        )
    )
    return grouped.head(top_n)


def _top_vessels(segments: pd.DataFrame, top_n: int) -> pd.DataFrame:
    filtered = segments[segments["imo"].astype(str).str.strip() != ""].copy()
    if filtered.empty:
        return pd.DataFrame(columns=["imo", "voyage_count", "segment_count", "cargo_weight_t", "cargo_teu"])
    grouped = (
        filtered.groupby("imo", dropna=False)
        .agg(
            voyage_count=("voyage_id", "nunique"),
            segment_count=("voyage_id", "size"),
            cargo_weight_t=("cargo_weight_t", "sum"),
            cargo_teu=("cargo_teu", "sum"),
        )
        .reset_index()
        .sort_values(
            ["cargo_weight_t", "segment_count", "voyage_count", "imo"],
            ascending=[False, False, False, True],
            kind="stable",
        )
    )
    return grouped.head(top_n)


def _monthly_segment_flow(segments: pd.DataFrame) -> pd.DataFrame:
    if segments.empty:
        return pd.DataFrame(columns=["month", "segment_count", "cargo_weight_t"])
    base = segments.copy()
    reference_ts = base["departed_at"].combine_first(base["arrived_at"])
    base["month"] = pd.to_datetime(reference_ts, utc=True, errors="coerce").dt.strftime("%Y-%m").fillna("")
    base = base[base["month"].astype(str).str.strip() != ""].copy()
    if base.empty:
        return pd.DataFrame(columns=["month", "segment_count", "cargo_weight_t"])
    return (
        base.groupby("month", dropna=False)
        .agg(
            segment_count=("voyage_id", "size"),
            cargo_weight_t=("cargo_weight_t", "sum"),
        )
        .reset_index()
        .sort_values("month", kind="stable")
    )


def _port_stay_profile(stops: pd.DataFrame, top_n: int) -> pd.DataFrame:
    grouped = (
        stops.groupby("port_label", dropna=False)
        .agg(
            call_count=("call_count", "sum"),
            voyage_count=("voyage_id", "nunique"),
            avg_port_stay_hours=("port_stay_hours", "mean"),
            avg_operation_hours=("operation_hours", "mean"),
            moved_weight_t=("moved_weight_t", "sum"),
        )
        .reset_index()
        .rename(columns={"port_label": "port"})
        .sort_values(
            ["avg_port_stay_hours", "moved_weight_t", "port"],
            ascending=[False, False, True],
            kind="stable",
        )
    )
    return grouped.head(top_n)


def _render_overview_metrics(voyages: pd.DataFrame, stops: pd.DataFrame, segments: pd.DataFrame) -> None:
    total_voyages = int(voyages["voyage_id"].nunique())
    total_loaded_weight_t = float(voyages["loaded_weight_t_total"].sum())
    carried_weight_t = float(segments["cargo_weight_t"].sum()) if not segments.empty else 0.0
    segment_count = int(len(segments))
    unique_imos = int(voyages["imo"].astype(str).str.strip().replace("", pd.NA).dropna().nunique())
    unique_ports = int(stops["port_label"].nunique())

    row_one = st.columns(3)
    row_one[0].metric("Observed voyages", _metric_text(total_voyages, decimals=0))
    row_one[1].metric("Loaded weight", _metric_text(total_loaded_weight_t, suffix=" t"))
    row_one[2].metric("Carried on legs", _metric_text(carried_weight_t, suffix=" t"))

    row_two = st.columns(3)
    row_two[0].metric("Observed legs", _metric_text(segment_count, decimals=0))
    row_two[1].metric("Unique vessels", _metric_text(unique_imos, decimals=0))
    row_two[2].metric("Observed ports", _metric_text(unique_ports, decimals=0))

def _render_ranked_bar_chart(
    df: pd.DataFrame,
    *,
    label_col: str,
    value_col: str,
    title: str,
    color: str,
    tooltip_cols: list[str] | None = None,
) -> None:
    if df.empty:
        st.info("No data for this chart in the current filter.")
        return

    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopRight=6, cornerRadiusBottomRight=6, color=color)
        .encode(
            x=alt.X(f"{value_col}:Q", title="", axis=alt.Axis(format="~s")),
            y=alt.Y(f"{label_col}:N", sort="-x", title=""),
            tooltip=tooltip_cols or [label_col, value_col],
        )
        .properties(title=title, height=_CHART_HEIGHT)
    )
    st.altair_chart(chart, width="stretch")


def _render_monthly_chart(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("No monthly segment timestamps are available in the current filter.")
        return

    cargo = (
        alt.Chart(df)
        .mark_bar(color="#0f766e", opacity=0.75)
        .encode(
            x=alt.X("month:N", title=""),
            y=alt.Y("cargo_weight_t:Q", title="Carried weight", axis=alt.Axis(format="~s")),
            tooltip=["month", "cargo_weight_t", "segment_count"],
        )
    )
    segments = (
        alt.Chart(df)
        .mark_line(color="#b45309", point=True, strokeWidth=2.6)
        .encode(
            x=alt.X("month:N", title=""),
            y=alt.Y("segment_count:Q", title="Observed legs"),
            tooltip=["month", "cargo_weight_t", "segment_count"],
        )
    )
    chart = alt.layer(cargo, segments).resolve_scale(y="independent").properties(
        title="Monthly carried weight and observed legs",
        height=_CHART_HEIGHT,
    )
    st.altair_chart(chart, width="stretch")


def _format_compact_table(
    df: pd.DataFrame,
    *,
    compact_cols: list[str] | None = None,
    pct_cols: list[str] | None = None,
    decimal_cols: list[str] | None = None,
) -> pd.DataFrame:
    out = df.copy()
    for column in compact_cols or []:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").map(
                lambda value: _metric_text(value) if pd.notna(value) else ""
            )
    for column in pct_cols or []:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").map(
                lambda value: f"{value:.1f}%" if pd.notna(value) else ""
            )
    for column in decimal_cols or []:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").map(
                lambda value: f"{value:.1f}" if pd.notna(value) else ""
            )
    return out


def _display_table(df: pd.DataFrame) -> None:
    st.dataframe(df, hide_index=True, width="stretch")


def render_page() -> None:
    init_state()
    inject_css()
    attach_streamlit_logging(
        level=str(st.session_state.log_level),
        archive_to_storage=bool(st.session_state.archive_logs),
    )

    header_cols = st.columns([0.82, 0.18])
    with header_cols[1]:
        if st.button("Refresh data", width="stretch"):
            _load_dashboard_dataset_cached.clear()
            st.rerun()

    try:
        dataset = _load_dashboard_dataset_cached()
    except CabotageDashboardDataError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"Failed to load cabotage dashboard data: {exc}")
        return

    _render_header(dataset)
    selected_years, selected_port, selected_closure_modes, top_n = _render_filters(dataset)
    view = filter_dashboard_dataset(
        dataset,
        years=selected_years,
        focus_port=selected_port,
        closure_modes=selected_closure_modes,
    )

    voyages = view.voyages
    stops = view.stops
    segments = view.segments
    if voyages.empty:
        st.warning("No voyages match the current filters.")
        return

    departures = _top_departure_ports(segments, top_n)
    arrivals = _top_arrival_ports(segments, top_n)
    segment_pairs = _top_segment_pairs(segments, top_n)
    hubs = _top_intermediate_ports(stops, top_n)
    vessels = _top_vessels(segments, top_n)
    monthly = _monthly_segment_flow(segments)
    dwell = _port_stay_profile(stops, top_n)

    _render_overview_metrics(voyages, stops, segments)
    overview_tab, ports_tab, segments_tab, details_tab = st.tabs(
        ["Overview", "Ports", "Segments", "Details"]
    )

    with overview_tab:
        _render_monthly_chart(monthly)
        chart_left, chart_right = st.columns(2)
        with chart_left:
            _render_ranked_bar_chart(
                departures,
                label_col="port",
                value_col="cargo_weight_t",
                title="Ports where cargo most departs",
                color="#2563eb",
                tooltip_cols=["port", "cargo_weight_t", "segment_count", "voyage_count", "share_pct"],
            )
        with chart_right:
            _render_ranked_bar_chart(
                arrivals,
                label_col="port",
                value_col="cargo_weight_t",
                title="Ports where cargo most arrives",
                color="#0f766e",
                tooltip_cols=["port", "cargo_weight_t", "segment_count", "voyage_count", "share_pct"],
            )

    with ports_tab:
        left, right = st.columns(2)
        with left:
            _render_ranked_bar_chart(
                hubs,
                label_col="port",
                value_col="moved_weight_t",
                title="Intermediate hubs by moved cargo",
                color="#7c3aed",
                tooltip_cols=["port", "moved_weight_t", "stop_count", "voyage_count", "avg_port_stay_hours"],
            )
        with right:
            _render_ranked_bar_chart(
                dwell,
                label_col="port",
                value_col="avg_port_stay_hours",
                title="Ports with the longest average stay",
                color="#b45309",
                tooltip_cols=["port", "avg_port_stay_hours", "avg_operation_hours", "moved_weight_t", "voyage_count"],
            )

    with segments_tab:
        left, right = st.columns(2)
        with left:
            _render_ranked_bar_chart(
                segment_pairs,
                label_col="corridor",
                value_col="cargo_weight_t",
                title="Observed corridors by carried cargo",
                color="#dc2626",
                tooltip_cols=["corridor", "cargo_weight_t", "segment_count", "voyage_count", "cargo_teu"],
            )
        with right:
            _render_ranked_bar_chart(
                vessels,
                label_col="imo",
                value_col="cargo_weight_t",
                title="Vessels with more carried cargo",
                color="#1d4ed8",
                tooltip_cols=["imo", "cargo_weight_t", "segment_count", "voyage_count", "cargo_teu"],
            )
    with details_tab:
        _display_table(
            _format_compact_table(
                segment_pairs[["corridor", "cargo_weight_t", "cargo_teu", "segment_count", "voyage_count"]],
                compact_cols=["cargo_weight_t", "cargo_teu", "segment_count", "voyage_count"],
            )
        )

        _display_table(
            _format_compact_table(
                departures[["port", "cargo_weight_t", "cargo_teu", "segment_count", "voyage_count", "share_pct"]],
                compact_cols=["cargo_weight_t", "cargo_teu", "segment_count", "voyage_count"],
                pct_cols=["share_pct"],
            )
        )


def main() -> None:
    render_page()


if __name__ == "__main__":
    render_page()
