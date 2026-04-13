#!/usr/bin/env python3
"""
Pure Python MSSM shape plotter (uproot + matplotlib + mplhep)
Mimics the ROOT-based style and legend/axis conventions.
"""
import argparse
import os
import numpy as np
import matplotlib.pyplot as plt
import mplhep as hep
import uproot

plt.style.use(hep.style.CMS)
plt.rcParams.update({
    "font.size": 20,
    "axes.titlesize": 22,
    "axes.labelsize": 20,
    "legend.fontsize": 18,
    "xtick.labelsize": 18,
    "ytick.labelsize": 18,
})

COLORS = {
    "yellow": "#ffa90e",
    "red": "#e42536",
    "pink": "#f6b5fd",
    "lightblue": "#3f90da",
    "violet": "#882ebd",
    "purple": "#964a8b",
    "brown": "#a96b59",
    "green": "#a0c172",
    "grey": "#94a4a2",
    "ash": "#717581",
    "cms_blue": "#3f90da",
    "cms_yellow": "#ffa90e",
    "cms_red": "#bd1f01",
    "cms_grey": "#94a4a2",
    "cms_violet": "#832db6",
    "cms_brown": "#a96b59",
    "cms_orange": "#e76300",
    "cms_green": "#b9ac70",
    "cms_ash": "#717581",
    "cms_cyan": "#92dadd",
}

PROCESS_ORDER = [
    "TTT", "TTJ", "VVT", "VVJ", "W", "ZL", "ZJ", "ZTT", "QCD", "JetFakes", "JetFakesSublead"
]
PROCESS_LABELS = {
    "TTT": r"$t\bar{t}$",
    "TTJ": r"$t\bar{t}$",
    "VVT": "Electroweak",
    "VVJ": "Electroweak",
    "W": "Electroweak",
    "ZL": r"$Z\to\ell\ell$",
    "ZJ": r"$Z\to\ell\ell$",
    "ZTT": r"$Z\to\tau\tau$",
    "QCD": "QCD",
    "JetFakes": r"Jet$\to\tau_h$",
    "JetFakesSublead": r"Jet$\to\tau_h$",
}
PROCESS_COLORS = {
    "TTT": COLORS["violet"],
    "TTJ": COLORS["violet"],
    "VVT": COLORS["red"],
    "VVJ": COLORS["red"],
    "W": COLORS["red"],
    "ZL": COLORS["lightblue"],
    "ZJ": COLORS["lightblue"],
    "ZTT": COLORS["yellow"],
    "QCD": COLORS["pink"],
    "JetFakes": COLORS["green"],
    "JetFakesSublead": COLORS["green"],
}

def list_bin_dirs(root_file):
    return sorted([
        key.split(";")[0]
        for key, classname in root_file.classnames().items()
        if classname.startswith("TDirectory")
    ])

def get_hist(file_handle, directory, name):
    key = f"{directory}/{name}"
    if key not in file_handle:
        return None, None, None
    hist = file_handle[key]
    values, edges = hist.to_numpy(flow=False)
    variances = hist.variances(flow=False)
    errors = np.sqrt(np.clip(variances, 0.0, None)) if variances is not None else np.sqrt(np.clip(values, 0.0, None))
    return values.astype(float), errors.astype(float), edges.astype(float)

def sum_histograms(file_handle, bin_names, hist_name, target_edges=None):
    total = None
    total_var = None
    for b in bin_names:
        vals, errs, edges = get_hist(file_handle, b, hist_name)
        if vals is None:
            continue
        if target_edges is not None and not np.allclose(edges, target_edges):
            # Rebin to target_edges
            import hist
            h = hist.Hist.new.Reg(len(edges)-1, edges[0], edges[-1]).Double()
            h[...] = vals
            vals = h.project().values()
            errs = np.sqrt(vals)
            edges = target_edges
        if total is None:
            total = np.zeros_like(vals)
            total_var = np.zeros_like(errs)
        total += vals
        total_var += errs**2
    if total is None:
        return None, None, None
    return total, np.sqrt(total_var), edges

def plot_stack_main_ratio(
    stack,
    total_bkg,
    total_bkg_err,
    edges,
    data_vals,
    data_err,
    x_label,
    lumi,
    outbase,
    logy=False,
    blind=False,
    title_right="",
):
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(10, 8), gridspec_kw={"height_ratios": [4, 1]}, sharex=True
    )
    running = np.zeros_like(centers)
    handles = []
    labels = []
    for comp in stack:
        h = ax.bar(
            centers,
            comp["values"],
            width=widths,
            bottom=running,
            color=comp["color"],
            edgecolor="black",
            linewidth=0.5,
            align="center",
            label=comp["label"],
        )
        running += comp["values"]
        handles.append(h)
        labels.append(comp["label"])
    band = ax.fill_between(
        edges,
        np.r_[total_bkg - total_bkg_err, (total_bkg - total_bkg_err)[-1]],
        np.r_[total_bkg + total_bkg_err, (total_bkg + total_bkg_err)[-1]],
        step="post",
        facecolor="none",
        edgecolor="gray",
        hatch="////////",
        linewidth=0.0,
        label="TotalBkg unc.",
    )
    if not blind and data_vals is not None:
        data_handle = ax.errorbar(
            centers,
            data_vals,
            yerr=data_err,
            xerr=widths / 2.0,
            fmt="o",
            color="black",
            markersize=4,
            linewidth=0.8,
            label="Observed",
        )
        handles.append(data_handle)
        labels.append("Observed")
    handles.append(band)
    labels.append("TotalBkg unc.")
    hep.cms.label(
        ax=ax,
        label="Preliminary" if not blind else "Private Work",
        data=True,
        lumi=lumi,
        com=13.6,
    )
    if title_right:
        ax.set_title(title_right, loc="right")
    ax.set_ylabel("Events")
    ax.grid(True, axis="y", alpha=0.25)
    if logy:
        ymax = max(np.max(running), np.max(data_vals) if data_vals is not None else 0.0)
        ax.set_yscale("log")
        ax.set_ylim(0.1, max(10.0 * ymax, 100.0))
    else:
        ymax = max(np.max(running), np.max(data_vals) if data_vals is not None else 0.0)
        ax.set_ylim(0.0, max(1.6 * ymax, 1.0))
    axr.axhline(1.0, color="black", linestyle=":")
    for y in [0.7, 0.8, 1.2, 1.3]:
        axr.axhline(y, color="darkgray", linestyle=":")
    rel = np.divide(
        total_bkg_err,
        total_bkg,
        out=np.zeros_like(total_bkg),
        where=total_bkg > 0,
    )
    axr.fill_between(
        edges,
        np.r_[1.0 - rel, (1.0 - rel)[-1]],
        np.r_[1.0 + rel, (1.0 + rel)[-1]],
        step="post",
        facecolor="none",
        edgecolor="gray",
        hatch="////////",
        linewidth=0.0,
    )
    if not blind and data_vals is not None:
        ratio = np.divide(
            data_vals,
            total_bkg,
            out=np.zeros_like(data_vals),
            where=total_bkg > 0,
        )
        ratio_err = np.divide(
            data_err,
            total_bkg,
            out=np.zeros_like(data_err),
            where=total_bkg > 0,
        )
        axr.errorbar(
            centers,
            ratio,
            yerr=ratio_err,
            xerr=widths / 2.0,
            fmt="o",
            color="black",
            markersize=4,
            linewidth=0.8,
        )
    axr.set_ylabel("Obs./Exp.")
    axr.set_ylim(0.5, 1.5)
    axr.set_xlabel(x_label)
    axr.grid(True, axis="y", alpha=0.2)
    ax.legend(
        handles[::-1],
        labels[::-1],
        loc="upper right",
        frameon=False,
        ncol=2,
    )
    os.makedirs(os.path.dirname(outbase), exist_ok=True)
    fig.savefig(f"{outbase}.pdf", bbox_inches="tight")
    fig.savefig(f"{outbase}.png", bbox_inches="tight", dpi=180)
    plt.close(fig)

def draw_bin(file_handle, bin_name, output_dir, lumi, logy=False, blind=False):
    stack = []
    for proc in PROCESS_ORDER:
        vals, errs, edges = get_hist(file_handle, bin_name, proc)
        if vals is None or np.sum(vals) == 0:
            continue
        stack.append({
            "label": PROCESS_LABELS.get(proc, proc),
            "values": vals,
            "errors": errs,
            "edges": edges,
            "color": PROCESS_COLORS.get(proc, "#cccccc"),
        })
    data_vals, data_err, edges = get_hist(file_handle, bin_name, "data_obs")
    bkg_vals, bkg_err, _ = get_hist(file_handle, bin_name, "TotalBkg")
    if bkg_vals is None:
        raise RuntimeError(f"Missing TotalBkg for {bin_name}")
    plot_stack_main_ratio(
        stack=stack,
        total_bkg=bkg_vals,
        total_bkg_err=bkg_err,
        edges=edges,
        data_vals=data_vals,
        data_err=data_err,
        x_label="Bin number",
        lumi=lumi,
        outbase=os.path.join(output_dir, bin_name),
        logy=logy,
        blind=blind,
        title_right=bin_name,
    )

def draw_combined_bins(file_handle, bin_names, output_dir, lumi, logy=False, blind=False):
    # Try to find common binning; if not possible, unroll all bins
    edges_list = []
    nbins_list = []
    for b in bin_names:
        _, _, e = get_hist(file_handle, b, "TotalBkg")
        if e is not None:
            edges_list.append(e)
            nbins_list.append(len(e) - 1)

    # Check if all edges are identical
    all_same = all(np.array_equal(edges_list[0], e) for e in edges_list)

    if all_same:
        edges = edges_list[0]
        stack = []
        for proc in PROCESS_ORDER:
            vals_sum = None
            errs_sum = None
            for b in bin_names:
                vals, errs, _ = get_hist(file_handle, b, proc)
                if vals is None:
                    continue
                if vals_sum is None:
                    vals_sum = np.zeros_like(vals)
                    errs_sum = np.zeros_like(errs)
                vals_sum += vals
                errs_sum += errs**2
            if vals_sum is not None and np.sum(vals_sum) > 0:
                stack.append({
                    "label": PROCESS_LABELS.get(proc, proc),
                    "values": vals_sum,
                    "errors": np.sqrt(errs_sum),
                    "edges": edges,
                    "color": PROCESS_COLORS.get(proc, "#cccccc"),
                })
        data_vals_sum = None
        data_err_sum = None
        bkg_vals_sum = None
        bkg_err_sum = None
        for b in bin_names:
            dvals, derr, _ = get_hist(file_handle, b, "data_obs")
            bvals, berr, _ = get_hist(file_handle, b, "TotalBkg")
            if dvals is not None:
                if data_vals_sum is None:
                    data_vals_sum = np.zeros_like(dvals)
                    data_err_sum = np.zeros_like(derr)
                data_vals_sum += dvals
                data_err_sum += derr**2
            if bvals is not None:
                if bkg_vals_sum is None:
                    bkg_vals_sum = np.zeros_like(bvals)
                    bkg_err_sum = np.zeros_like(berr)
                bkg_vals_sum += bvals
                bkg_err_sum += berr**2
        if bkg_vals_sum is None:
            raise RuntimeError("Missing combined TotalBkg")
        plot_stack_main_ratio(
            stack=stack,
            total_bkg=bkg_vals_sum,
            total_bkg_err=np.sqrt(bkg_err_sum),
            edges=edges,
            data_vals=data_vals_sum,
            data_err=np.sqrt(data_err_sum),
            x_label="Bin number",
            lumi=lumi,
            outbase=os.path.join(output_dir, "combined_bins"),
            logy=logy,
            blind=blind,
            title_right="",
        )
    else:
        # Unroll all bins into a single 1D array
        total_bins = sum(nbins_list)
        combined_edges = np.arange(total_bins + 1, dtype=float)
        # Build stack
        stack = []
        for proc in PROCESS_ORDER:
            vals_chunks = []
            errs_chunks = []
            for b in bin_names:
                vals, errs, _ = get_hist(file_handle, b, proc)
                if vals is None:
                    continue
                vals_chunks.append(vals)
                errs_chunks.append(errs**2)
            if vals_chunks:
                vals_cat = np.concatenate(vals_chunks)
                errs_cat = np.sqrt(np.concatenate(errs_chunks))
                if np.sum(vals_cat) > 0:
                    stack.append({
                        "label": PROCESS_LABELS.get(proc, proc),
                        "values": vals_cat,
                        "errors": errs_cat,
                        "edges": combined_edges,
                        "color": PROCESS_COLORS.get(proc, "#cccccc"),
                    })
        # Data and bkg
        data_chunks = []
        data_err_chunks = []
        bkg_chunks = []
        bkg_err_chunks = []
        for b in bin_names:
            dvals, derr, _ = get_hist(file_handle, b, "data_obs")
            bvals, berr, _ = get_hist(file_handle, b, "TotalBkg")
            if dvals is not None:
                data_chunks.append(dvals)
                data_err_chunks.append(derr**2)
            if bvals is not None:
                bkg_chunks.append(bvals)
                bkg_err_chunks.append(berr**2)
        data_vals_cat = np.concatenate(data_chunks) if data_chunks else None
        data_err_cat = np.sqrt(np.concatenate(data_err_chunks)) if data_err_chunks else None
        bkg_vals_cat = np.concatenate(bkg_chunks) if bkg_chunks else None
        bkg_err_cat = np.sqrt(np.concatenate(bkg_err_chunks)) if bkg_err_chunks else None
        if bkg_vals_cat is None:
            raise RuntimeError("Missing combined TotalBkg")
        plot_stack_main_ratio(
            stack=stack,
            total_bkg=bkg_vals_cat,
            total_bkg_err=bkg_err_cat,
            edges=combined_edges,
            data_vals=data_vals_cat,
            data_err=data_err_cat,
            x_label="Combined bin number",
            lumi=lumi,
            outbase=os.path.join(output_dir, "combined_bins"),
            logy=logy,
            blind=blind,
            title_right="",
        )
def main():
    parser = argparse.ArgumentParser(description="Plot MSSM shapes in pure Python (uproot + mplhep)")
    parser.add_argument("--input_file", "-i", default="shapes_output.root")
    parser.add_argument("--bin_name", "-b", default="all")
    parser.add_argument("--lumi", default="109.08 fb^{-1} (13.6 TeV)")
    parser.add_argument("--dir", default="mssm_output/plots")
    parser.add_argument("--blind", action="store_true")
    parser.add_argument("--combine-all-bins", action="store_true")
    parser.add_argument("--logy", action="store_true")
    args = parser.parse_args()
    file_handle = uproot.open(args.input_file)
    if args.bin_name == "all":
        bins = list_bin_dirs(file_handle)
    else:
        bins = [args.bin_name]
    if not bins:
        raise RuntimeError("No directories found to plot")
    os.makedirs(args.dir, exist_ok=True)
    if args.combine_all_bins:
        draw_combined_bins(
            file_handle,
            bins,
            args.dir,
            args.lumi,
            logy=args.logy,
            blind=args.blind,
        )
        print(f"[OK] Wrote combined plot from {len(bins)} bins")
        return
    for bname in bins:
        try:
            draw_bin(
                file_handle,
                bname,
                args.dir,
                args.lumi,
                logy=args.logy,
                blind=args.blind,
            )
            print(f"[OK] Wrote plot for {bname}")
        except Exception as exc:
            print(f"[WARN] Skipping {bname}: {exc}")
if __name__ == "__main__":
    main()
