#!/usr/bin/env python3
"""
Make one overarching fit-stability summary plot using mplhep.

Figure layout:
    - Top pad: median expected limit vs mass for all minimizer variants
    - Bottom pad: ratio to baseline for each variant, plus variant envelope

The styling and labels follow the plotMSSM convention closely:
    - CMS / Internal header
    - Process-aware y-axis title
    - m_phi x-axis label
    - ROOT-like color ordering for the minimizer variants

Inputs expected in outdir:
    - asymptotic_summary.csv

Outputs:
    - fit_stability_summary_<poi>.pdf
    - fit_stability_summary_<poi>.png

Usage:
    python make_fit_validation_plots.py \
            --outdir mssm_output/cmb/thesis_fit_validation \
            --poi r_ggH \
            --process gg#phi \
            --cms-sub Internal

    python make_fit_validation_plots.py \
            --outdir mssm_output/cmb/thesis_fit_validation \
            --poi r_bbH \
            --process bb#phi \
            --title-right "137 fb$^{-1}$ (13.6 TeV)"
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
import pandas as pd


VARIANT_ORDER = ["baseline", "strategy1", "tol0p1", "noanalytic"]
VARIANT_LABELS = {
    "strategy1": "Higher minimiser strategy",
    "tol0p1": "Looser convergence tolerance",
    "noanalytic": "No analytic minimisation",
    "baseline": "Nominal fit",
}
VARIANT_STYLES = {
    "baseline": {
        "color": "#000000",
        "linewidth": 2.0,
        "marker": "",
        "linestyle": "--",
    },
    "strategy1": {
        "color": "#d62728",
        "linewidth": 2.0,
        "marker": "s",
    },
    "tol0p1": {
        "color": "#1f77b4",
        "linewidth": 2.0,
        "marker": "^",
    },
    "noanalytic": {
        "color": "#2ca02c",
        "linewidth": 2.0,
        "marker": "D",
    }
}
PROCESS_LABELS = {
    "r_ggH": (
        r"95% CL limit on $\sigma(\mathrm{gg}\phi)\,"
        r"\mathcal{B}(\phi\to\tau\tau)$ (pb)"
    ),
    "r_bbH": (
        r"95% CL limit on $\sigma(\mathrm{bb}\phi)\,"
        r"\mathcal{B}(\phi\to\tau\tau)$ (pb)"
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outdir",
        required=True,
        help="Directory containing asymptotic_summary.csv",
    )
    parser.add_argument("--poi", required=True, choices=["r_ggH", "r_bbH"])
    parser.add_argument(
        "--process",
        choices=["gg#phi", "bb#phi"],
        default="gg#phi",
        help="Process label used in the y-axis title",
    )
    parser.add_argument(
        "--label",
        "--cms-sub",
        dest="cms_sub",
        default="Internal",
        help="Text below the CMS logo",
    )
    parser.add_argument(
        "--title-right",
        default="",
        help="Right header text above the frame",
    )
    parser.add_argument(
        "--title-left",
        default="",
        help="Left header text above the frame",
    )
    parser.add_argument(
        "--x-title",
        default=r"$m_{\phi}$ (GeV)",
        help="Title for the x-axis",
    )
    parser.add_argument(
        "--y-title",
        default=None,
        help="Override the top-panel y-axis title",
    )
    parser.add_argument(
        "--spread-threshold",
        type=float,
        default=0.05,
        help="Reference line for spread",
    )
    parser.add_argument("--ymin-ratio", type=float, default=0.97)
    parser.add_argument("--ymax-ratio", type=float, default=1.03)
    return parser.parse_args()


def prepare_dataframe(csv_path: Path, poi: str) -> pd.DataFrame:
    if not csv_path.exists():
        raise FileNotFoundError(f"Missing file: {csv_path}")

    df = pd.read_csv(csv_path)
    df = df[df["poi"] == poi].copy()
    if df.empty:
        raise RuntimeError(f"No rows found for POI = {poi}")

    df["mass_num"] = pd.to_numeric(df["mass"], errors="coerce")
    df["exp50_num"] = pd.to_numeric(df["exp50"], errors="coerce")
    df["exp16_num"] = pd.to_numeric(df["exp16"], errors="coerce")
    df["exp84_num"] = pd.to_numeric(df["exp84"], errors="coerce")
    df = df.dropna(subset=["mass_num", "exp50_num"])
    if df.empty:
        raise RuntimeError(f"No valid mass/exp50 rows found for POI = {poi}")

    # Keep one row per (mass, variant).
    # If multiple tags exist for the same pair, take the first.
    df = df.sort_values(["mass_num", "variant", "tag"])
    df = df.drop_duplicates(subset=["mass_num", "variant"])
    return df


def build_pivot(df: pd.DataFrame) -> pd.DataFrame:
    pivot = df.pivot(index="mass_num", columns="variant", values="exp50_num")
    # Keep masses where baseline exists
    if "baseline" not in pivot.columns:
        raise RuntimeError(
            "No baseline variant found in asymptotic_summary.csv"
        )
    pivot = pivot.sort_index()
    pivot = pivot[pivot["baseline"].notna()].copy()
    return pivot


def save_plot(fig: plt.Figure, outbase: Path) -> None:
    fig.savefig(outbase.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(outbase.with_suffix(".png"), bbox_inches="tight", dpi=220)
    plt.close(fig)


def get_process_ylabel(args: argparse.Namespace) -> str:
    if args.y_title is not None:
        return args.y_title
    return PROCESS_LABELS[args.poi]


def add_header_text(ax: plt.Axes, args: argparse.Namespace) -> None:
    if args.title_left:
        ax.text(
            0.02,
            1.02,
            args.title_left,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=12,
        )
    if args.title_right:
        ax.text(
            0.98,
            1.02,
            args.title_right,
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=12,
        )


def pretty_variant_label(variant: str) -> str:
    return VARIANT_LABELS.get(variant, variant)


def reorder_top_legend(ax: plt.Axes) -> None:
    handles, labels = ax.get_legend_handles_labels()
    pairs = list(zip(handles, labels))

    wanted = ["Nominal fit", r"Nominal fit $\pm1\sigma$"]
    ordered = [pair for key in wanted for pair in pairs if pair[1] == key]
    ordered.extend(pair for pair in pairs if pair[1] not in wanted)

    if ordered:
        ax.legend(
            [handle for handle, _ in ordered],
            [label for _, label in ordered],
            frameon=True,
            fontsize=20,
            loc="best",
        )


def main() -> None:
    args = parse_args()

    hep.style.use("CMS")

    outdir = Path(args.outdir)
    csv_path = outdir / "asymptotic_summary.csv"

    df = prepare_dataframe(csv_path, args.poi)
    pivot = build_pivot(df)
    pivot16 = df.pivot(index="mass_num", columns="variant", values="exp16_num")
    pivot84 = df.pivot(index="mass_num", columns="variant", values="exp84_num")
    pivot16 = pivot16.sort_index()
    pivot84 = pivot84.sort_index()

    masses = pivot.index.to_numpy(dtype=float)
    baseline = pivot["baseline"].to_numpy(dtype=float)
    baseline_exp16 = pivot16["baseline"].reindex(pivot.index)
    baseline_exp16 = baseline_exp16.to_numpy(dtype=float)
    baseline_exp84 = pivot84["baseline"].reindex(pivot.index)
    baseline_exp84 = baseline_exp84.to_numpy(dtype=float)

    ratio_map: dict[str, np.ndarray] = {}
    available_variants = [v for v in VARIANT_ORDER if v in pivot.columns]

    for variant in available_variants:
        ratio_map[variant] = pivot[variant].to_numpy(dtype=float) / baseline

    fig = plt.figure(figsize=(12, 12))
    gs = fig.add_gridspec(2, 1, height_ratios=[4, 1], hspace=0.1)
    ax_top = fig.add_subplot(gs[0])
    ax_bot = fig.add_subplot(gs[1], sharex=ax_top)

    # --------------------------
    # Top pad: expected limits
    # --------------------------
    ax_top.fill_between(
        masses,
        baseline_exp16,
        baseline_exp84,
        color="#747171",
        alpha=0.35,
        label=r"Nominal fit $\pm1\sigma$",
        zorder=1,
    )

    # ax_top.fill_between(
    #     masses,
    #     pivot[available_variants].min(axis=1).to_numpy(dtype=float),
    #     pivot[available_variants].max(axis=1).to_numpy(dtype=float),
    #     color="#d0d0d0",
    #     alpha=0.35,
    #     label="Variant envelope",
    #     zorder=1,
    # )

    # Plot non-baseline variants first
    for variant in available_variants:
        if variant == "baseline":
            continue
        y = pivot[variant].to_numpy(dtype=float)
        style = VARIANT_STYLES.get(variant, {})
        ax_top.plot(
            masses,
            y,
            markersize=8,
            label=pretty_variant_label(variant),
            zorder=2,
            **style,
        )
    
    # Plot baseline last so it appears on top
    if "baseline" in available_variants:
        y = pivot["baseline"].to_numpy(dtype=float)
        style = VARIANT_STYLES.get("baseline", {})
        ax_top.plot(
            masses,
            y,
            markersize=8,
            label=pretty_variant_label("baseline"),
            zorder=3,
            **style,
        )

    ax_top.set_ylabel(get_process_ylabel(args))
    ax_top.set_yscale("log")
    ax_top.set_ylim(10**-4, 10**3)
    ax_top.grid(True, which="both", alpha=0.25)
    reorder_top_legend(ax_top)
    ax_top.tick_params(axis="x", labelbottom=False)

    add_header_text(ax_top, args)

    hep.cms.label(
        ax=ax_top,
        data=True,
        label=args.cms_sub,
        lumi=109.08,
        com=13.6,
    )

    # --------------------------
    # Bottom pad: ratios + spread
    # --------------------------
    # ax_bot.fill_between(
    #     masses,
    #     ratio_min,
    #     ratio_max,
    #     color="#d0d0d0",
    #     alpha=0.35,
    #     label="Envelope / baseline",
    #     zorder=1,
    # )

    for variant in available_variants:
        if variant == "baseline":
            continue
        variant_style = dict(VARIANT_STYLES.get(variant, {}))
        variant_style["linewidth"] = 1.8
        ax_bot.plot(
            masses,
            ratio_map[variant],
            markersize=8,
            label=f"{VARIANT_LABELS.get(variant, variant)} / baseline",
            linestyle="none",
            zorder=2,
            **variant_style,
        )

    # ax_bot.plot(
    #     masses,
    #     1.0 + spread,
    #     marker="s",
    #     linewidth=1.8,
    #     markersize=4,
    #     color="#555555",
    #     label="1 + max relative spread",
    #     zorder=3,
    # )

    ax_bot.axhline(1.0, linestyle="--", linewidth=1.2, color="#000000")
    ax_bot.axhline(
        1.0 + args.spread_threshold,
        linestyle=":",
        linewidth=1.2,
        color="#000000",
    )
    ax_bot.axhline(
        1.0 - args.spread_threshold,
        linestyle=":",
        linewidth=1.2,
        color="#000000",
    )

    ax_bot.set_xlabel(args.x_title)
    ax_bot.set_ylabel("Ratio to nominal")
    ax_bot.set_ylim(0.99, 1.01)
    ax_bot.grid(True, alpha=0.25)

    # Make x-axis nicer
    ax_bot.set_xscale("log")
    ax_bot.set_xlim(60, 3500)

    ticks = [70, 100, 200, 300, 1000, 2000]
    ax_bot.set_xticks(ticks)
    ax_bot.set_xticklabels([str(t) for t in ticks])  # force visible labels
    ax_bot.tick_params(axis="x", labelbottom=True)

    outbase = outdir / f"fit_stability_summary_{args.poi}"
    save_plot(fig, outbase)

    print(f"[OK] Wrote {outbase.with_suffix('.pdf')}")
    print(f"[OK] Wrote {outbase.with_suffix('.png')}")


if __name__ == "__main__":
    main()
