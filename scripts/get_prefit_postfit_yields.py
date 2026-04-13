#!/usr/bin/env python3
# Compare prefit and postfit shapes and yields, and produce summary tables and plots.
# Need to run these on 125 GeV MH background fits
#  For prefit plots:
# python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=125,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_prefit
# mv shapes_output.root shapes_output_prefit_125.root

#For postfit plots:
# combine -M FitDiagnostics mssm_output/cmb/combined.txt.cmb --saveShapes --saveWithUncertainties --saveNormalizations
# python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=125,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_postfit --fitresult fitDiagnosticsTest.root:fit_b --postfit
# mv shapes_output.root shapes_output_postfit_125.root
# Example usage:
# python3 scripts/get_prefit_postfit_yields.py --prefit shapes_output_prefit_125.root --postfit shapes_output_postfit_125.root --output-dir mssm_output/shape_comparisons
import os
import argparse
import numpy as np
import pandas as pd
import ROOT

import matplotlib.pyplot as plt
import mplhep as hep

plt.style.use(hep.style.CMS)
plt.rcParams.update({
    "font.size": 16,
    "axes.titlesize": 18,
    "axes.labelsize": 16,
    "legend.fontsize": 13,
    "xtick.labelsize": 12,
    "ytick.labelsize": 12,
})

import matplotlib as mpl
mpl.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}'
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = 'Helvetica'
mpl.rcParams['mathtext.fontset'] = 'custom'
mpl.rcParams['mathtext.rm'] = 'Helvetica'
mpl.rcParams['mathtext.it'] = 'Helvetica:italic'
mpl.rcParams['mathtext.bf'] = 'Helvetica:bold'


# =========================================================
# Definitions
# =========================================================

PLOT_GROUPS = [
    {"label": r"$Z\to\tau\tau$",      "procs": ["ZTT"]},
    {"label": r"$Z\to\ell\ell$",      "procs": ["ZL", "ZJ"]},
    {"label": r"Jet$\to\tau_h$", "procs": ["JetFakes", "JetFakesSublead"]},
    {"label": r"$t\bar{t}$",       "procs": ["TTT", "TTJ"]},
    {"label": "Electroweak",      "procs": ["VVT", "VVJ", "W"]},
]

ALL_PROCESSES = sorted({
    proc
    for group in PLOT_GROUPS
    for proc in group["procs"]
})


# =========================================================
# ROOT helpers
# =========================================================

def is_hist(obj):
    return obj and obj.InheritsFrom("TH1")


def get_hist(directory, name, allow_empty=False):
    if not directory:
        return None
    obj = directory.Get(name)
    if not obj or not is_hist(obj):
        if allow_empty:
            return None
        raise RuntimeError(f"Missing histogram '{name}' in directory '{directory.GetName()}'")
    h = obj.Clone(f"{directory.GetName()}_{name}_clone")
    h.SetDirectory(0)
    return h


def list_categories(root_file):
    cats = []
    for key in root_file.GetListOfKeys():
        obj = key.ReadObj()
        if obj and obj.InheritsFrom("TDirectory"):
            cats.append(key.GetName())
    return sorted(cats)


def sum_histograms(directory, process_names, out_name="hsum"):
    hsum = None
    for proc in process_names:
        h = get_hist(directory, proc, allow_empty=True)
        if h is None:
            continue
        if hsum is None:
            hsum = h.Clone(out_name)
            hsum.SetDirectory(0)
        else:
            hsum.Add(h)
    return hsum


def make_empty_like(hist, name):
    h = hist.Clone(name)
    h.Reset("ICESM")
    h.SetDirectory(0)
    return h


def get_bin_edges(h):
    nbins = h.GetNbinsX()
    return np.array(
        [h.GetBinLowEdge(i + 1) for i in range(nbins)] +
        [h.GetBinLowEdge(nbins + 1)],
        dtype=float,
    )


def hist_to_vals(h):
    return np.array([h.GetBinContent(i + 1) for i in range(h.GetNbinsX())], dtype=float)


# =========================================================
# Metrics
# =========================================================

def normalized_shape(vals):
    total = np.sum(vals)
    if total <= 0:
        return np.zeros_like(vals, dtype=float)
    return vals / total


def compute_hist_metrics(h_prefit, h_postfit):
    vals_pre = hist_to_vals(h_prefit)
    vals_post = hist_to_vals(h_postfit)

    N_prefit = np.sum(vals_pre)
    N_postfit = np.sum(vals_post)

    delta_yield = N_postfit - N_prefit
    yield_ratio = N_postfit / N_prefit if N_prefit > 0 else np.nan
    rel_shift_percent = 100.0 * (yield_ratio - 1.0) if N_prefit > 0 else np.nan

    p_pre = normalized_shape(vals_pre)
    p_post = normalized_shape(vals_post)

    shape_distance = np.sum(np.abs(p_pre - p_post))
    shape_distance_half = 0.5 * shape_distance

    return {
        "N_prefit": float(N_prefit),
        "N_postfit": float(N_postfit),
        "delta_yield": float(delta_yield),
        "yield_ratio": float(yield_ratio) if np.isfinite(yield_ratio) else np.nan,
        "rel_shift_percent": float(rel_shift_percent) if np.isfinite(rel_shift_percent) else np.nan,
        "shape_distance": float(shape_distance),
        "shape_distance_half": float(shape_distance_half),
    }


# =========================================================
# Table building
# =========================================================

def process_per_process(dir_prefit, dir_postfit, category, processes=None):
    if processes is None:
        processes = ALL_PROCESSES

    rows = []
    for proc in processes:
        h_pre = get_hist(dir_prefit, proc, allow_empty=True)
        h_post = get_hist(dir_postfit, proc, allow_empty=True)

        if h_pre is None and h_post is None:
            continue
        if h_pre is None:
            h_pre = make_empty_like(h_post, f"{category}_{proc}_prefit_empty")
        if h_post is None:
            h_post = make_empty_like(h_pre, f"{category}_{proc}_postfit_empty")

        if h_pre.Integral() <= 0 and h_post.Integral() <= 0:
            continue

        rows.append({
            "category": category,
            "process": proc,
            **compute_hist_metrics(h_pre, h_post),
        })
    return rows


def process_groups(dir_prefit, dir_postfit, category, groups=None):
    if groups is None:
        groups = PLOT_GROUPS

    rows = []
    for group in groups:
        label = group["label"]
        procs = group["procs"]

        h_pre = sum_histograms(dir_prefit, procs, out_name=f"{category}_{label}_prefit_sum")
        h_post = sum_histograms(dir_postfit, procs, out_name=f"{category}_{label}_postfit_sum")

        if h_pre is None and h_post is None:
            continue
        if h_pre is None:
            h_pre = make_empty_like(h_post, f"{category}_{label}_prefit_empty")
        if h_post is None:
            h_post = make_empty_like(h_pre, f"{category}_{label}_postfit_empty")

        if h_pre.Integral() <= 0 and h_post.Integral() <= 0:
            continue

        rows.append({
            "category": category,
            "group": label,
            **compute_hist_metrics(h_pre, h_post),
        })
    return rows


# =========================================================
# Plot helpers
# =========================================================

def cms_label(ax, lumi_text=None):
    hep.cms.label(ax=ax, label="Private Work", data=True, lumi=lumi_text, com=13.6)


def savefig(fig, path_base):
    fig.savefig(path_base + ".pdf", bbox_inches="tight")
    fig.savefig(path_base + ".png", bbox_inches="tight", dpi=180)
    plt.close(fig)


def make_matrix(df, row_field, col_field, value_field, row_order=None, col_order=None):
    pivot = df.pivot(index=row_field, columns=col_field, values=value_field)
    if row_order is not None:
        pivot = pivot.reindex(row_order)
    if col_order is not None:
        pivot = pivot.reindex(columns=col_order)
    return pivot


def plot_heatmap(
    pivot,
    outpath,
    xlabel,
    ylabel,
    cbar_label,
    title=None,
    cmap="coolwarm",
    vmin=None,
    vmax=None,
    annotate=False,
    fmt="{:.2f}",
):
    fig, ax = plt.subplots(figsize=(1.4 * max(6, len(pivot.columns)), 0.6 * max(5, len(pivot.index)) + 2))
    data = pivot.values.astype(float)
    im = ax.imshow(data, aspect="auto", cmap=cmap, vmin=vmin, vmax=vmax)

    ax.set_xticks(np.arange(len(pivot.columns)))
    ax.set_xticklabels(pivot.columns, rotation=45, ha="right")
    ax.set_yticks(np.arange(len(pivot.index)))
    ax.set_yticklabels(pivot.index)

    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)

    cbar = fig.colorbar(im, ax=ax)
    cbar.set_label(cbar_label)

    if annotate:
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                val = data[i, j]
                if np.isfinite(val):
                    ax.text(j, i, fmt.format(val), ha="center", va="center", fontsize=8)

    cms_label(ax)
    savefig(fig, outpath)


def plot_top_barh(df, value_col, label_col, outpath, xlabel, title, top_n=15):
    tmp = df.copy().sort_values(value_col, ascending=False).head(top_n)
    labels = tmp[label_col].tolist()
    vals = tmp[value_col].values

    fig, ax = plt.subplots(figsize=(11, max(6, 0.45 * len(tmp))))
    y = np.arange(len(tmp))
    ax.barh(y, vals)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.set_xlabel(xlabel)
    ax.grid(True, axis="x", alpha=0.3)
    cms_label(ax)
    savefig(fig, outpath)


def plot_signed_barh(df, value_col, label_col, outpath, xlabel, title, top_n=15):
    tmp = df.copy()
    tmp["abs_value"] = np.abs(tmp[value_col])
    tmp = tmp.sort_values("abs_value", ascending=False).head(top_n)

    labels = tmp[label_col].tolist()
    vals = tmp[value_col].values

    fig, ax = plt.subplots(figsize=(11, max(6, 0.45 * len(tmp))))
    y = np.arange(len(tmp))
    ax.barh(y, vals)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.invert_yaxis()
    ax.axvline(0.0, color="black", linewidth=1.0)
    ax.set_xlabel(xlabel)
    ax.grid(True, axis="x", alpha=0.3)
    cms_label(ax)
    savefig(fig, outpath)


# =========================================================
# Overlay plots
# =========================================================

def draw_shape_overlay(
    h_prefit,
    h_postfit,
    category,
    process,
    outpath,
    lumi_text=None,
    normalize=False,
    logy=False,
):
    edges = get_bin_edges(h_prefit)
    vals_pre = hist_to_vals(h_prefit)
    vals_post = hist_to_vals(h_postfit)

    if normalize:
        vals_pre = normalized_shape(vals_pre)
        vals_post = normalized_shape(vals_post)
        ylab = "Normalized events"
        ratio_label = "Postfit / Prefit (shape)"
    else:
        ylab = "Events"
        ratio_label = "Postfit / Prefit"

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(10, 8),
        gridspec_kw={"height_ratios": [4, 1]},
        sharex=True,
    )

    ax.step(edges, np.r_[vals_pre, vals_pre[-1] if len(vals_pre) else 0.0], where="post",
            linewidth=2.0, label="Prefit")
    ax.step(edges, np.r_[vals_post, vals_post[-1] if len(vals_post) else 0.0], where="post",
            linewidth=2.0, linestyle="--", label="Postfit")

    ymax = max(np.max(vals_pre) if len(vals_pre) else 0.0, np.max(vals_post) if len(vals_post) else 0.0, 1e-6)
    if logy:
        ax.set_yscale("log")
        ax.set_ylim(1e-5 if normalize else 0.1, max(20.0 * ymax, 10.0 * (1e-5 if normalize else 1.0)))
    else:
        ax.set_ylim(0.0, 1.4 * ymax)

    ax.set_ylabel(ylab)
    ax.legend(frameon=False, loc="upper right")
    ax.grid(True, axis="y", alpha=0.25)
    cms_label(ax, lumi_text=lumi_text)

    ratio = np.divide(vals_post, vals_pre, out=np.full_like(vals_post, np.nan), where=vals_pre > 0)
    axr.axhline(1.0, color="black", linestyle=":")
    axr.step(edges, np.r_[ratio, ratio[-1] if len(ratio) else 1.0], where="post", linewidth=1.8)

    axr.set_ylabel(ratio_label)
    axr.set_xlabel(r"$m_{T}^{\mathrm{tot}}$ (GeV)")
    axr.set_ylim(0.5, 1.5)
    axr.grid(True, axis="y", alpha=0.2)

    ax.set_xlim(edges[0], edges[-1])
    axr.set_xlim(edges[0], edges[-1])

    savefig(fig, outpath)


def plot_top_overlays(
    f_prefit,
    f_postfit,
    df_proc,
    outdir,
    top_n_shift=12,
    top_n_shape=12,
    lumi_text=None,
):
    shift_dir = os.path.join(outdir, "top_overlays_by_shift")
    shape_dir = os.path.join(outdir, "top_overlays_by_shape")
    normshape_dir = os.path.join(outdir, "top_normalized_overlays_by_shape")
    os.makedirs(shift_dir, exist_ok=True)
    os.makedirs(shape_dir, exist_ok=True)
    os.makedirs(normshape_dir, exist_ok=True)

    tmp_shift = df_proc.copy()
    tmp_shift["abs_rel_shift_percent"] = np.abs(tmp_shift["rel_shift_percent"])
    top_shift = tmp_shift.sort_values("abs_rel_shift_percent", ascending=False).head(top_n_shift)

    top_shape = df_proc.sort_values("shape_distance_half", ascending=False).head(top_n_shape)

    for _, row in top_shift.iterrows():
        category = row["category"]
        process = row["process"]
        dir_pre = f_prefit.Get(category)
        dir_post = f_postfit.Get(category)
        if not dir_pre or not dir_post:
            continue

        h_pre = get_hist(dir_pre, process, allow_empty=True)
        h_post = get_hist(dir_post, process, allow_empty=True)
        if h_pre is None and h_post is None:
            continue
        if h_pre is None:
            h_pre = make_empty_like(h_post, f"{category}_{process}_prefit_empty")
        if h_post is None:
            h_post = make_empty_like(h_pre, f"{category}_{process}_postfit_empty")

        safe_name = f"{category}__{process}"
        draw_shape_overlay(
            h_pre, h_post, category, process,
            outpath=os.path.join(shift_dir, safe_name),
            lumi_text=lumi_text,
            normalize=False,
            logy=False,
        )

    for _, row in top_shape.iterrows():
        category = row["category"]
        process = row["process"]
        dir_pre = f_prefit.Get(category)
        dir_post = f_postfit.Get(category)
        if not dir_pre or not dir_post:
            continue

        h_pre = get_hist(dir_pre, process, allow_empty=True)
        h_post = get_hist(dir_post, process, allow_empty=True)
        if h_pre is None and h_post is None:
            continue
        if h_pre is None:
            h_pre = make_empty_like(h_post, f"{category}_{process}_prefit_empty")
        if h_post is None:
            h_post = make_empty_like(h_pre, f"{category}_{process}_postfit_empty")

        safe_name = f"{category}__{process}"
        draw_shape_overlay(
            h_pre, h_post, category, process,
            outpath=os.path.join(shape_dir, safe_name),
            lumi_text=lumi_text,
            normalize=False,
            logy=False,
        )
        draw_shape_overlay(
            h_pre, h_post, category, process,
            outpath=os.path.join(normshape_dir, safe_name),
            lumi_text=lumi_text,
            normalize=True,
            logy=False,
        )


def plot_category_process_overlays(
    f_prefit,
    f_postfit,
    df_proc,
    outdir,
    lumi_text=None,
    top_n_per_category=3,
):
    os.makedirs(outdir, exist_ok=True)

    for category in sorted(df_proc["category"].unique()):
        sub = df_proc[df_proc["category"] == category].copy()
        if sub.empty:
            continue

        sub["rank_metric"] = np.abs(sub["rel_shift_percent"]).fillna(0.0) + 100.0 * sub["shape_distance_half"].fillna(0.0)
        sub = sub.sort_values("rank_metric", ascending=False).head(top_n_per_category)

        cat_dir = os.path.join(outdir, category)
        os.makedirs(cat_dir, exist_ok=True)

        dir_pre = f_prefit.Get(category)
        dir_post = f_postfit.Get(category)
        if not dir_pre or not dir_post:
            continue

        for _, row in sub.iterrows():
            process = row["process"]
            h_pre = get_hist(dir_pre, process, allow_empty=True)
            h_post = get_hist(dir_post, process, allow_empty=True)
            if h_pre is None and h_post is None:
                continue
            if h_pre is None:
                h_pre = make_empty_like(h_post, f"{category}_{process}_prefit_empty")
            if h_post is None:
                h_post = make_empty_like(h_pre, f"{category}_{process}_postfit_empty")

            safe_name = process.replace("/", "_")
            draw_shape_overlay(
                h_pre, h_post, category, process,
                outpath=os.path.join(cat_dir, f"{safe_name}_yield"),
                lumi_text=lumi_text,
                normalize=False,
                logy=False,
            )
            draw_shape_overlay(
                h_pre, h_post, category, process,
                outpath=os.path.join(cat_dir, f"{safe_name}_shape"),
                lumi_text=lumi_text,
                normalize=True,
                logy=False,
            )


# =========================================================
# Summary plots
# =========================================================

def plot_group_summary(group_df, outdir):
    categories = sorted(group_df["category"].unique())
    groups = [g["label"] for g in PLOT_GROUPS]

    pivot_shift = make_matrix(
        group_df, row_field="group", col_field="category", value_field="rel_shift_percent",
        row_order=groups, col_order=categories
    )
    vmax = np.nanmax(np.abs(pivot_shift.values)) if np.isfinite(pivot_shift.values).any() else 1.0
    plot_heatmap(
        pivot_shift,
        os.path.join(outdir, "group_rel_shift_heatmap"),
        xlabel="Category",
        ylabel="Background group",
        cbar_label="Postfit / Prefit shift (%)",
        title="Grouped normalization shifts",
        cmap="coolwarm",
        vmin=-vmax,
        vmax=vmax,
        annotate=True,
        fmt="{:.1f}",
    )

    pivot_shape = make_matrix(
        group_df, row_field="group", col_field="category", value_field="shape_distance_half",
        row_order=groups, col_order=categories
    )
    plot_heatmap(
        pivot_shape,
        os.path.join(outdir, "group_shape_distance_heatmap"),
        xlabel="Category",
        ylabel="Background group",
        cbar_label="Shape change (TV distance)",
        title="Grouped shape changes",
        cmap="viridis",
        vmin=0.0,
        vmax=np.nanmax(pivot_shape.values) if np.isfinite(pivot_shape.values).any() else 1.0,
        annotate=True,
        fmt="{:.3f}",
    )


def plot_process_summary(proc_df, outdir):
    categories = sorted(proc_df["category"].unique())
    processes = sorted(proc_df["process"].unique())

    pivot_shift = make_matrix(
        proc_df, row_field="process", col_field="category", value_field="rel_shift_percent",
        row_order=processes, col_order=categories
    )
    vmax = np.nanmax(np.abs(pivot_shift.values)) if np.isfinite(pivot_shift.values).any() else 1.0
    plot_heatmap(
        pivot_shift,
        os.path.join(outdir, "process_rel_shift_heatmap"),
        xlabel="Category",
        ylabel="Process",
        cbar_label="Postfit / Prefit shift (%)",
        title="Per-process normalization shifts",
        cmap="coolwarm",
        vmin=-vmax,
        vmax=vmax,
        annotate=True,
        fmt="{:.1f}",
    )

    pivot_shape = make_matrix(
        proc_df, row_field="process", col_field="category", value_field="shape_distance_half",
        row_order=processes, col_order=categories
    )
    plot_heatmap(
        pivot_shape,
        os.path.join(outdir, "process_shape_distance_heatmap"),
        xlabel="Category",
        ylabel="Process",
        cbar_label="Shape change (TV distance)",
        title="Per-process shape changes",
        cmap="viridis",
        vmin=0.0,
        vmax=np.nanmax(pivot_shape.values) if np.isfinite(pivot_shape.values).any() else 1.0,
        annotate=True,
        fmt="{:.3f}",
    )

    tmp = proc_df.copy()
    tmp["cat_proc"] = tmp["category"] + " : " + tmp["process"]

    plot_signed_barh(
        tmp,
        value_col="rel_shift_percent",
        label_col="cat_proc",
        outpath=os.path.join(outdir, "largest_rel_shift_barh"),
        xlabel="Relative yield shift (%)",
        title="Largest per-process normalization shifts",
        top_n=15,
    )

    plot_top_barh(
        tmp.sort_values("shape_distance_half", ascending=False),
        value_col="shape_distance_half",
        label_col="cat_proc",
        outpath=os.path.join(outdir, "largest_shape_change_barh"),
        xlabel="Shape change (TV distance)",
        title="Largest per-process shape changes",
        top_n=15,
    )


def plot_category_breakdown(proc_df, outdir):
    for category in sorted(proc_df["category"].unique()):
        sub = proc_df[proc_df["category"] == category].copy()
        if sub.empty:
            continue

        sub = sub.sort_values("rel_shift_percent")
        fig, ax = plt.subplots(figsize=(10, max(5, 0.6 * len(sub))))
        y = np.arange(len(sub))
        ax.barh(y, sub["rel_shift_percent"].values)
        ax.set_yticks(y)
        ax.set_yticklabels(sub["process"].tolist())
        ax.axvline(0.0, color="black", linewidth=1.0)
        ax.set_xlabel("Relative yield shift (%)")
        ax.grid(True, axis="x", alpha=0.3)
        cms_label(ax)
        savefig(fig, os.path.join(outdir, f"{category}_rel_shift"))

        sub2 = sub.sort_values("shape_distance_half", ascending=False)
        fig, ax = plt.subplots(figsize=(10, max(5, 0.6 * len(sub2))))
        y = np.arange(len(sub2))
        ax.barh(y, sub2["shape_distance_half"].values)
        ax.set_yticks(y)
        ax.set_yticklabels(sub2["process"].tolist())
        ax.invert_yaxis()
        ax.set_xlabel("Shape change (TV distance)")
        ax.grid(True, axis="x", alpha=0.3)
        cms_label(ax)
        savefig(fig, os.path.join(outdir, f"{category}_shape_change"))


# =========================================================
# Main
# =========================================================

def main():
    parser = argparse.ArgumentParser(description="Compare prefit and postfit process shapes and yields.")
    parser.add_argument("-p", "--prefit", required=True, help="Prefit ROOT file")
    parser.add_argument("-f", "--postfit", required=True, help="Postfit ROOT file")
    parser.add_argument("-o", "--output-dir", default="prefit_postfit_comparison", help="Output directory")
    parser.add_argument("-c", "--categories", nargs="*", default=None, help="Optional category list")
    parser.add_argument("--lumi-text", default=None, help="Luminosity text passed to mplhep, e.g. '138'")
    parser.add_argument("--top-n-overlays", type=int, default=12, help="Number of global overlay cases")
    parser.add_argument("--top-n-per-category", type=int, default=3, help="Number of process overlays per category")
    args = parser.parse_args()

    ROOT.gROOT.SetBatch(True)

    f_prefit = ROOT.TFile.Open(args.prefit)
    f_postfit = ROOT.TFile.Open(args.postfit)

    if not f_prefit or f_prefit.IsZombie():
        raise RuntimeError(f"Could not open prefit file: {args.prefit}")
    if not f_postfit or f_postfit.IsZombie():
        raise RuntimeError(f"Could not open postfit file: {args.postfit}")

    cats_prefit = set(list_categories(f_prefit))
    cats_postfit = set(list_categories(f_postfit))

    if args.categories:
        categories = sorted(set(args.categories) & cats_prefit & cats_postfit)
    else:
        categories = sorted(cats_prefit & cats_postfit)

    if not categories:
        raise RuntimeError("No common categories found.")

    os.makedirs(args.output_dir, exist_ok=True)
    plot_dir = os.path.join(args.output_dir, "plots")
    os.makedirs(plot_dir, exist_ok=True)
    category_plot_dir = os.path.join(plot_dir, "by_category")
    os.makedirs(category_plot_dir, exist_ok=True)
    overlay_dir = os.path.join(plot_dir, "overlays")
    os.makedirs(overlay_dir, exist_ok=True)
    overlay_cat_dir = os.path.join(plot_dir, "overlays_by_category")
    os.makedirs(overlay_cat_dir, exist_ok=True)

    per_process_rows = []
    group_rows = []

    for cat in categories:
        dir_pre = f_prefit.Get(cat)
        dir_post = f_postfit.Get(cat)

        if not dir_pre or not dir_post:
            print(f"[WARN] Skipping {cat}: missing directory")
            continue

        try:
            per_process_rows.extend(process_per_process(dir_pre, dir_post, cat))
            group_rows.extend(process_groups(dir_pre, dir_post, cat))
        except Exception as e:
            print(f"[WARN] Skipping {cat}: {e}")

    df_proc = pd.DataFrame(per_process_rows)
    df_group = pd.DataFrame(group_rows)

    proc_csv = os.path.join(args.output_dir, "per_process_changes.csv")
    group_csv = os.path.join(args.output_dir, "group_changes.csv")

    df_proc.to_csv(proc_csv, index=False)
    df_group.to_csv(group_csv, index=False)

    print(f"[INFO] Wrote {proc_csv}")
    print(f"[INFO] Wrote {group_csv}")

    if not df_proc.empty:
        plot_process_summary(df_proc, plot_dir)
        plot_category_breakdown(df_proc, category_plot_dir)
        plot_top_overlays(
            f_prefit,
            f_postfit,
            df_proc,
            overlay_dir,
            top_n_shift=args.top_n_overlays,
            top_n_shape=args.top_n_overlays,
            lumi_text=args.lumi_text,
        )
        plot_category_process_overlays(
            f_prefit,
            f_postfit,
            df_proc,
            overlay_cat_dir,
            lumi_text=args.lumi_text,
            top_n_per_category=args.top_n_per_category,
        )

    if not df_group.empty:
        plot_group_summary(df_group, plot_dir)

    if not df_proc.empty:
        print("\n[INFO] Largest normalization shifts:")
        tmp = df_proc.copy()
        tmp["abs_rel_shift_percent"] = np.abs(tmp["rel_shift_percent"])
        print(
            tmp.sort_values("abs_rel_shift_percent", ascending=False)[
                ["category", "process", "N_prefit", "N_postfit", "yield_ratio", "rel_shift_percent", "shape_distance_half"]
            ].head(15).to_string(index=False)
        )

        print("\n[INFO] Largest shape changes:")
        print(
            df_proc.sort_values("shape_distance_half", ascending=False)[
                ["category", "process", "N_prefit", "N_postfit", "yield_ratio", "rel_shift_percent", "shape_distance_half"]
            ].head(15).to_string(index=False)
        )


if __name__ == "__main__":
    main()