"""Streamlit dashboard for paneer cold-chain and quality data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_quality_data, load_temperature_data
from src.quality_analysis import (
    clean_quality_data,
    daily_quality_summary,
    format_p_value,
    missing_value_summary,
    paired_correlations,
    quality_data_diagnostics,
)
from src.temperature_analysis import analyze_temperature

st.set_page_config(
    page_title="Paneer Cold-Chain Quality Analysis",
    page_icon="🥛",
    layout="wide",
)
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 1.6rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stMetric"] {
        background: #202a31;
        border: 1px solid #34434c;
        border-radius: 0.7rem;
        padding: 0.85rem 1rem;
    }
    div[data-testid="stMetric"] [data-testid="stMetricLabel"] p {
        color: #b6c2ca !important;
    }
    div[data-testid="stMetricValue"],
    div[data-testid="stMetricValue"] > div {
        color: #f2f6f8;
    }
    div[data-testid="stMetricDelta"] {
        color: #59c7b3;
    }
    div[data-testid="stMetricDelta"][data-trend="down"] {
        color: #ff8a80;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Paneer Cold-Chain Quality Analysis")
st.caption(
    "Explore logged refrigerator conditions alongside replicate-level paneer "
    "quality measurements. Analytical references are not food-safety guarantees."
)

st.sidebar.header("Data sources")
st.sidebar.caption(
    "Optional uploads replace the bundled synthetic demonstration data for that dataset."
)
temperature_upload = st.sidebar.file_uploader(
    "Temperature log (CSV)", type=["csv"], key="temperature_upload"
)
quality_upload = st.sidebar.file_uploader(
    "Paneer quality workbook (Excel)", type=["xlsx", "xls"], key="quality_upload"
)
threshold = st.sidebar.number_input(
    "Temperature reference threshold (°C)",
    min_value=-20.0,
    max_value=50.0,
    value=4.0,
    step=0.5,
    help="An analytical reference only; it is not a food-safety determination.",
)
max_gap_minutes = st.sidebar.number_input(
    "Maximum gap for duration estimation (minutes)",
    min_value=1,
    max_value=1440,
    value=30,
    step=5,
    help="Intervals longer than this are treated as unknown, not continuous exposure.",
)

temperature_df: pd.DataFrame | None = None
quality_raw: pd.DataFrame | None = None
quality_df: pd.DataFrame | None = None
temperature_error: str | None = None
quality_error: str | None = None
temperature_sample_fallback = False
quality_sample_fallback = False

try:
    temperature_df = load_temperature_data(temperature_upload)
except Exception as error:
    temperature_error = str(error)
    if temperature_upload is not None:
        try:
            temperature_df = load_temperature_data()
            temperature_sample_fallback = True
        except Exception as fallback_error:
            temperature_error += f" Bundled sample also failed: {fallback_error}"
try:
    quality_raw = load_quality_data(quality_upload)
    if quality_raw is not None:
        quality_df = clean_quality_data(quality_raw)
except Exception as error:
    quality_error = str(error)
    if quality_upload is not None:
        try:
            quality_raw = load_quality_data()
            if quality_raw is not None:
                quality_df = clean_quality_data(quality_raw)
                quality_sample_fallback = True
        except Exception as fallback_error:
            quality_error += f" Bundled sample also failed: {fallback_error}"

if temperature_error:
    message = f"Temperature data could not be loaded: {temperature_error}"
    if temperature_sample_fallback:
        message += " Using the bundled synthetic sample instead."
    st.sidebar.error(message)
if quality_error:
    message = f"Quality workbook could not be loaded: {quality_error}"
    if quality_sample_fallback:
        message += " Using the bundled synthetic sample instead."
    st.sidebar.error(message)
temperature_source = (
    "Synthetic demonstration sample (invalid upload; fallback)"
    if temperature_sample_fallback
    else
    "Uploaded file"
    if temperature_upload is not None and temperature_df is not None
    else "Synthetic demonstration sample"
    if temperature_df is not None
    else "Uploaded file (load failed)"
    if temperature_upload is not None
    else "Demonstration sample (load failed)"
    if temperature_error
    else "Unavailable"
)
quality_source = (
    "Synthetic demonstration sample (invalid upload; fallback)"
    if quality_sample_fallback
    else
    "Uploaded file"
    if quality_upload is not None and quality_df is not None
    else "Synthetic demonstration sample"
    if quality_df is not None
    else "Uploaded file (load failed)"
    if quality_upload is not None
    else "Demonstration sample (load failed)"
    if quality_error
    else "Unavailable"
)
st.sidebar.caption(f"Temperature data source: {temperature_source}")
st.sidebar.caption(f"Quality data source: {quality_source}")
if temperature_df is None and not temperature_error and temperature_upload is not None:
    st.sidebar.warning(
        "Temperature data is unavailable. Check the bundled sample or upload a CSV."
    )
if quality_raw is None and not quality_error and quality_upload is not None:
    st.sidebar.warning(
        "Quality data is unavailable. Check the bundled sample or upload an Excel workbook."
    )

temperature_stats = (
    analyze_temperature(
        temperature_df,
        threshold=threshold,
        max_gap=f"{max_gap_minutes}min",
    )
    if temperature_df is not None
    else None
)
daily_summary = (
    daily_quality_summary(quality_df)
    if quality_df is not None
    else pd.DataFrame()
)
correlations = (
    paired_correlations(quality_df)
    if quality_df is not None and not quality_df.empty
    else None
)
tabs = st.tabs(
    [
        "Overview",
        "Cold-Chain Monitoring",
        "Paneer Quality",
        "Statistical Analysis",
        "Data Explorer",
    ]
)

with tabs[0]:
    if temperature_source == "Synthetic demonstration sample" or quality_source == "Synthetic demonstration sample":
        st.info(
            "**Demonstration Sample Data** — any dataset labelled “Synthetic "
            "demonstration sample” is synthetic example data for exploring the "
            "dashboard, not an experimental finding."
        )
    st.subheader("Dataset status")
    status_columns = st.columns(2)
    status_columns[0].metric(
        "Temperature log",
        "Loaded" if temperature_df is not None else "Unavailable",
        f"{len(temperature_df):,} rows" if temperature_df is not None else None,
    )
    status_columns[1].metric(
        "Paneer workbook",
        "Loaded" if quality_df is not None else "Unavailable",
        f"{len(quality_df):,} replicate observations"
        if quality_df is not None
        else None,
    )

    st.subheader("Cold-chain indicators")
    if temperature_stats is None:
        st.info("Load a valid temperature log to see calculated indicators.")
    elif not temperature_stats["valid_readings"]:
        st.info("The temperature log has no valid timestamped temperature readings.")
    else:
        columns = st.columns(4)
        columns[0].metric(
            "Mean temperature", f"{temperature_stats['mean_temperature']:.2f} °C"
        )
        columns[1].metric(
            f"Above {threshold:g} °C",
            f"{temperature_stats['percent_readings_above_threshold']:.1f}%",
            f"{temperature_stats['readings_above_threshold']:,} readings",
        )
        columns[2].metric(
            "Estimated time above threshold",
            f"{temperature_stats['estimated_time_above_threshold_hours']:.2f} h",
        )
        columns[3].metric("Observed excursions", temperature_stats["excursion_count"])

    st.subheader("Paneer quality indicators")
    if quality_df is None:
        st.info("Load a valid workbook to see quality indicators.")
    elif quality_df.empty:
        st.info("No replicate-level observations were found in the workbook.")
    else:
        available = set(quality_df.columns)
        latest_day = quality_df["Day"].max()
        latest = quality_df.loc[quality_df["Day"].eq(latest_day)]
        indicators = st.columns(4)
        for index, (column, label, unit) in enumerate([
            ("TPC_Log10", "Latest-day mean TPC (log10 CFU/mL)", ""),
            ("Overall_Acceptability", "Latest-day overall acceptability", ""),
            ("pH", "Latest-day mean pH", ""),
            ("Moisture_Percent", "Latest-day mean moisture", "%"),
        ]):
            if column in available and latest[column].notna().any():
                mean_value = latest[column].mean()
                indicators[index].metric(label, f"{mean_value:.2f}{unit}")
            else:
                indicators[index].metric(label, "Not available")

        diagnostics = quality_data_diagnostics(quality_df)
        for message in diagnostics:
            st.warning(message)

    st.caption(
        "Values are computed from the currently loaded files. Threshold time is "
        "estimated only over sufficiently close observations; neither temperature "
        "nor quality indicators alone establish safety, shelf life, or causation."
    )

with tabs[1]:
    st.subheader("Temperature over time")
    if temperature_df is None:
        st.info("Upload or provide a valid temperature CSV to begin.")
    else:
        observations = temperature_stats["observations"]
        if observations.empty:
            st.info("No valid timestamped temperature observations are available.")
        else:
            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=observations["Time_Stamp"],
                    y=observations["Temperature"],
                    mode="lines+markers",
                    name="Temperature",
                    line={"color": "#187a58", "width": 2},
                    marker={"size": 4},
                )
            )
            fig.add_hline(
                y=threshold,
                line_dash="dash",
                line_color="#c04c45",
                annotation_text=f"Reference: {threshold:g} °C",
            )
            fig.update_layout(
                template="plotly_dark",
                height=420,
                title="Temperature readings over time",
                xaxis_title="Timestamp",
                yaxis_title="Temperature (°C)",
                hovermode="x unified",
                paper_bgcolor="#10171c",
                plot_bgcolor="#10171c",
                font={"color": "#e8eef2"},
            )
            st.plotly_chart(fig, width="stretch")

            metric_columns = st.columns(5)
            for container, label, key, suffix in [
                (metric_columns[0], "Minimum", "minimum_temperature", " °C"),
                (metric_columns[1], "Median", "median_temperature", " °C"),
                (metric_columns[2], "Maximum", "maximum_temperature", " °C"),
                (
                    metric_columns[3],
                    "Longest estimated excursion",
                    "longest_excursion_minutes",
                    " min",
                ),
                (
                    metric_columns[4],
                    "Mean recovery duration",
                    "mean_recovery_duration_minutes",
                    " min",
                ),
            ]:
                value = temperature_stats[key]
                container.metric(
                    label,
                    f"{value:.2f}{suffix}" if np.isfinite(value) else "Not estimable",
                )

            st.caption(
                "Estimation method: linear interpolation between valid temperature "
                "observations no farther apart than the configured maximum gap. "
                "Longer intervals are unknown and excluded. Excursion counts are "
                "observed runs; events inside unknown gaps cannot be inferred."
            )
            if temperature_stats["timestamp_gap_count"]:
                st.warning(
                    f"{temperature_stats['timestamp_gap_count']} timestamp gap(s) "
                    f"exceed the {max_gap_minutes}-minute estimation limit. The "
                    "refrigerator state during these gaps is unknown."
                )
            st.dataframe(
                temperature_stats["excursions"],
                width="stretch",
                hide_index=True,
            )

        chart_columns = st.columns(2)
        humidity = observations.dropna(subset=["RH"])
        with chart_columns[0]:
            st.markdown("**Relative humidity**")
            if humidity.empty:
                st.info("No valid relative-humidity readings are available.")
            else:
                humidity_fig = px.line(
                    humidity,
                    x="Time_Stamp",
                    y="RH",
                    title="Relative humidity over time",
                    labels={"Time_Stamp": "Timestamp", "RH": "Relative humidity (%)"},
                )
                humidity_fig.update_layout(
                    template="plotly_dark",
                    height=340,
                    paper_bgcolor="#10171c",
                    plot_bgcolor="#10171c",
                    font={"color": "#e8eef2"},
                )
                humidity_fig.update_traces(connectgaps=False)
                st.plotly_chart(humidity_fig, width="stretch")
                st.caption(
                    f"Mean: {temperature_stats['mean_humidity']:.1f}% · "
                    f"Range: {temperature_stats['minimum_humidity']:.1f}–"
                    f"{temperature_stats['maximum_humidity']:.1f}%"
                )

        with chart_columns[1]:
            st.markdown("**Door and compressor states**")
            state_rows = [
                {"Device": device.replace("_", " "), "State": state, "Readings": count}
                for device, states in temperature_stats["state_counts"].items()
                for state, count in states.items()
            ]
            if not state_rows:
                st.info("No door or compressor state readings are available.")
            else:
                state_fig = px.bar(
                    pd.DataFrame(state_rows),
                    x="Device",
                    y="Readings",
                    color="State",
                    barmode="group",
                    title="Observed state readings",
                )
                state_fig.update_layout(
                    template="plotly_dark",
                    height=340,
                    paper_bgcolor="#10171c",
                    plot_bgcolor="#10171c",
                    font={"color": "#e8eef2"},
                )
                st.plotly_chart(state_fig, width="stretch")
                st.metric(
                    "Observed door-opening transitions",
                    temperature_stats["door_opening_count"],
                )

with tabs[2]:
    st.subheader("Paneer quality over storage")
    if quality_df is None:
        st.info("Upload or provide a valid quality workbook to begin.")
    elif quality_df.empty:
        st.info(
            "No rows with valid Day (0–13) and Replicate (1–5) values were found."
        )
    else:
        diagnostics = quality_data_diagnostics(quality_df)
        for message in diagnostics:
            st.warning(message)

        microbial_columns = [
            ("TPC_Log10", "TPC (log10 CFU/mL)"),
            ("Coliform_Log10", "Coliform (log10 CFU/mL)"),
            ("Yeast_Mold_Log10", "Yeast/mold (log10 CFU/mL)"),
            (
                "Psychrophilic_Log10",
                "Psychrophilic (log10 CFU/mL)",
            ),
        ]
        available_microbes = [
            (column, label)
            for column, label in microbial_columns
            if column in quality_df and quality_df[column].notna().any()
        ]
        st.markdown("**Daily microbial measurements**")
        st.caption(
            "Log10 CFU/mL values are derived by the workbook. A raw count of zero "
            "has no defined logarithm, so its log value is missing; the raw zero "
            "count remains available in the cleaned table."
        )
        if not available_microbes:
            st.info("No microbial measurements are available.")
        else:
            chart_columns = st.columns(2)
            for index, (column, label) in enumerate(available_microbes):
                with chart_columns[index % 2]:
                    metric_summary = daily_summary[
                        ["Day", f"{column}_Mean", f"{column}_N"]
                    ].copy()
                    metric_summary = metric_summary.set_index("Day").reindex(
                        range(int(quality_df["Day"].min()), int(quality_df["Day"].max()) + 1)
                    )
                    fig = px.line(
                        metric_summary.reset_index(),
                        x="Day",
                        y=f"{column}_Mean",
                        markers=True,
                        title=label,
                        labels={
                            "Day": "Storage day",
                            f"{column}_Mean": label,
                        },
                    )
                    fig.update_traces(connectgaps=False)
                    fig.update_layout(
                        template="plotly_dark",
                        height=330,
                        paper_bgcolor="#10171c",
                        plot_bgcolor="#10171c",
                        font={"color": "#e8eef2"},
                    )
                    st.plotly_chart(fig, width="stretch")

        sensory_columns = [
            ("Colour_Appearance", "Colour and appearance"),
            ("Body_Texture", "Body and texture"),
            ("Flavour", "Flavour"),
            ("Overall_Acceptability", "Overall acceptability"),
        ]
        available_sensory = [
            (column, label)
            for column, label in sensory_columns
            if column in quality_df and quality_df[column].notna().any()
        ]
        st.markdown("**Sensory measurements**")
        if not available_sensory:
            st.info("No sensory measurements are available.")
        else:
            sensory_data = daily_summary[["Day"]].copy()
            for column, _ in available_sensory:
                sensory_data[column] = daily_summary[f"{column}_Mean"]
            sensory_data = sensory_data.set_index("Day").reindex(
                range(int(quality_df["Day"].min()), int(quality_df["Day"].max()) + 1)
            ).reset_index()
            sensory_fig = px.line(
                sensory_data,
                x="Day",
                y=[column for column, _ in available_sensory],
                markers=True,
                labels={"Day": "Storage day", "value": "Daily mean score", "variable": "Measure"},
                title="Daily mean sensory scores",
            )
            sensory_fig.update_traces(connectgaps=False)
            sensory_fig.update_layout(
                template="plotly_dark",
                height=400,
                paper_bgcolor="#10171c",
                plot_bgcolor="#10171c",
                font={"color": "#e8eef2"},
            )
            sensory_fig.for_each_trace(
                lambda trace: trace.update(
                    name=dict(available_sensory).get(trace.name, trace.name)
                )
            )
            st.plotly_chart(sensory_fig, width="stretch")
            st.caption(
                "Missing sensory values are left missing; lines do not bridge "
                "unobserved days."
            )

        trend_columns = st.columns(2)
        for container, column, label, unit in [
            (trend_columns[0], "pH", "pH", "pH"),
            (trend_columns[1], "Moisture_Percent", "Moisture", "Moisture (%)"),
        ]:
            with container:
                st.markdown(f"**{label} trend**")
                if column not in quality_df or not quality_df[column].notna().any():
                    st.info(f"No {label.lower()} measurements are available.")
                else:
                    trend = daily_summary[["Day", f"{column}_Mean"]].set_index(
                        "Day"
                    ).reindex(
                        range(int(quality_df["Day"].min()), int(quality_df["Day"].max()) + 1)
                    ).reset_index()
                    fig = px.line(
                        trend,
                        x="Day",
                        y=f"{column}_Mean",
                        markers=True,
                        title=f"Daily mean {label}",
                        labels={
                            "Day": "Storage day",
                            f"{column}_Mean": unit,
                        },
                    )
                    fig.update_traces(connectgaps=False)
                    fig.update_layout(
                        template="plotly_dark",
                        height=330,
                        paper_bgcolor="#10171c",
                        plot_bgcolor="#10171c",
                        font={"color": "#e8eef2"},
                    )
                    st.plotly_chart(fig, width="stretch")

        st.markdown("**Replicate-level and daily-summary data**")
        view = st.radio(
            "Table view",
            ["Replicate observations", "Daily means, SDs, and sample counts"],
            horizontal=True,
            key="quality_table_view",
        )
        st.dataframe(
            quality_df if view == "Replicate observations" else daily_summary,
            width="stretch",
            hide_index=True,
        )

with tabs[3]:
    st.subheader("Microbial count and overall acceptability")
    st.caption(
        "Correlations use rows where both measurements are present. Replicates are "
        "grouped by storage day, and shared day trends may contribute to pooled "
        "association; the reported p-values do not model that clustering. "
        "Association does not establish causation."
    )
    if quality_df is not None and not quality_df.empty:
        observed_days = set(quality_df["Day"].unique())
        sensory_days = set(
            quality_df.loc[
                quality_df["Overall_Acceptability"].notna(), "Day"
            ].unique()
        )
        no_sensory_days = sorted(observed_days - sensory_days)
        if no_sensory_days:
            day_labels = ", ".join(
                str(int(day)) if float(day).is_integer() else str(day)
                for day in no_sensory_days
            )
            st.warning(
                "Overall acceptability is entirely missing for storage day(s) "
                f"{day_labels}; these days cannot contribute to the correlation."
            )
    if quality_df is None:
        st.info("Load a valid quality workbook to calculate correlations.")
    elif correlations is None or correlations["n"] < 2:
        paired_count = 0 if correlations is None else correlations["n"]
        st.info(
            f"At least two complete TPC and overall-acceptability pairs are required; "
            f"found {paired_count}."
        )
    else:
        correlation_columns = st.columns(4)
        correlation_columns[0].metric("Paired observations", correlations["n"])
        correlation_columns[1].metric(
            "Pearson r",
            f"{correlations['pearson_r']:.3f}"
            if np.isfinite(correlations["pearson_r"])
            else "Not estimable",
        )
        correlation_columns[2].metric(
            "Pearson p-value", format_p_value(correlations["pearson_p"])
        )
        correlation_columns[3].metric(
            "Spearman ρ",
            f"{correlations['spearman_r']:.3f}"
            if np.isfinite(correlations["spearman_r"])
            else "Not estimable",
        )
        st.write(f"Spearman p-value: {format_p_value(correlations['spearman_p'])}")
        paired = quality_df[["TPC_Log10", "Overall_Acceptability"]].dropna()
        if len(paired) >= 2:
            scatter = px.scatter(
                paired,
                x="TPC_Log10",
                y="Overall_Acceptability",
                labels={
                    "TPC_Log10": "TPC (log10 CFU/mL)",
                    "Overall_Acceptability": "Overall acceptability score",
                },
                title="Paired replicate measurements",
            )
            scatter.update_layout(
                template="plotly_dark",
                height=430,
                paper_bgcolor="#10171c",
                plot_bgcolor="#10171c",
                font={"color": "#e8eef2"},
            )
            st.plotly_chart(scatter, width="stretch")
        st.info(
            "Pearson measures linear association; Spearman measures rank-based "
            "monotonic association. These pooled statistics do not account for "
            "replicate clustering or shared trends across storage days and do not "
            "establish causation."
        )

with tabs[4]:
    st.subheader("Data Explorer")
    if quality_df is None and temperature_df is None:
        st.info("Load at least one dataset to explore and download cleaned data.")
    else:
        explorer_dataset = st.selectbox(
            "Dataset", ["Paneer quality", "Temperature log"]
            if quality_df is not None and temperature_df is not None
            else ["Paneer quality"]
            if quality_df is not None
            else ["Temperature log"],
        )
        if explorer_dataset == "Paneer quality" and quality_df is not None:
            selected_days = st.multiselect(
                "Storage days",
                options=sorted(quality_df["Day"].unique().tolist()),
                default=sorted(quality_df["Day"].unique().tolist()),
            )
            variable_columns = [
                column
                for column in quality_df.columns
                if column not in {"Source_Row", "Day", "Replicate"}
            ]
            selected_variables = st.multiselect(
                "Variables",
                options=variable_columns,
                default=variable_columns,
            )
            filtered = quality_df.loc[
                quality_df["Day"].isin(selected_days),
                ["Source_Row", "Day", "Replicate", *selected_variables],
            ]
            st.dataframe(filtered, width="stretch", hide_index=True)
            st.download_button(
                "Download cleaned quality data (CSV)",
                data=quality_df.to_csv(index=False).encode("utf-8"),
                file_name="cleaned_paneer_quality.csv",
                mime="text/csv",
            )
            st.download_button(
                "Download daily quality summary (CSV)",
                data=daily_summary.to_csv(index=False).encode("utf-8"),
                file_name="paneer_daily_quality_summary.csv",
                mime="text/csv",
            )
            st.markdown("**Missing measurements**")
            st.dataframe(
                missing_value_summary(quality_df),
                width="stretch",
                hide_index=True,
            )
        elif temperature_df is not None:
            st.dataframe(temperature_df, width="stretch", hide_index=True)
            st.download_button(
                "Download cleaned temperature data (CSV)",
                data=temperature_df.to_csv(index=False).encode("utf-8"),
                file_name="cleaned_temperature_log.csv",
                mime="text/csv",
            )
