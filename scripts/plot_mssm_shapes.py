#!/usr/bin/env python3
# Example command:
# python3 scripts/plot_mssm_shapes.py -i shapes_output.root -b all
#     --blind --dir mssm_output/final_plots --logy --combine-all-bins
# Because of binning, cannot use really high mass point (1 TeV)
#  For prefit plots:
# python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=500,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_prefit
# mv shapes_output.root shapes_output_prefit.root
# python3 scripts/plot_mssm_shapes.py -i shapes_output_prefit.root -b all --blind --dir mssm_output/final_plots_prefit --logy (--combine-all-bins)

#For postfit plots:
# combine -M FitDiagnostics mssm_output/cmb/combined.txt.cmb --saveShapes --saveWithUncertainties --saveNormalizations
# python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=500,r_bbH=1,r_ggH=1 --plot_dir thesis_plots_postfit --fitresult fitDiagnosticsTest.root:fit_b --postfit
# mv shapes_output.root shapes_output_postfit.root
# python3 scripts/plot_mssm_shapes.py -i shapes_output_postfit.root -b all --blind --dir mssm_output/final_plots_postfit --logy (--combine-all-bins)

import argparse
import array
import ctypes
import os

import ROOT
import CombineHarvester.CombineTools.plotting as plot

ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.TH1.AddDirectory(False)

import numpy as np
import matplotlib as mpl
mpl.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}'
mpl.rcParams['font.family'] = 'sans-serif'
mpl.rcParams['font.sans-serif'] = 'Helvetica'
mpl.rcParams['mathtext.fontset'] = 'custom'
mpl.rcParams['mathtext.rm'] = 'Helvetica'
mpl.rcParams['mathtext.it'] = 'Helvetica:italic'
mpl.rcParams['mathtext.bf'] = 'Helvetica:bold'
import matplotlib.ticker as tk
locmaj = tk.LogLocator(base=10.0, subs=(1.0, ), numticks=100)
locmin = tk.LogLocator(base=10.0, subs=np.arange(2, 10) * .1, numticks=100)



COLORS = {
        "yellow": "#ffa90e",
        "red": "#e42536",
        "pink": "#f6b5fd", #facaff",
        "lightblue": "#3f90da",
        "violet": "#882ebd",
        "purple": "#964a8b",
        "brown": "#a96b59",
        "green": "#a0c172", # #b1cf86
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


def list_bin_dirs(root_file):
    out = []
    for key in root_file.GetListOfKeys():
        obj = root_file.Get(key.GetName())
        if obj and obj.InheritsFrom('TDirectory'):
            out.append(key.GetName())
    return sorted(out)


def get_hist(directory, name, allow_empty=False):
    hist = directory.Get(name)
    if hist:
        out = hist.Clone(f'{directory.GetName()}_{name}_clone')
        out.SetDirectory(0)
        return out
    if allow_empty:
        out = ROOT.TH1F(f'{name}_empty', '', 1, 0, 1)
        out.SetDirectory(0)
        return out
    raise RuntimeError(
        f'Failed to find histogram {name} in directory {directory.GetName()}'
    )


def garwood_interval(n, cl=0.683):
    alpha = 1.0 - cl
    if n <= 0:
        low = 0.0
    else:
        low = 0.5 * ROOT.Math.chisquared_quantile(alpha / 2.0, 2.0 * n)
    high = 0.5 * ROOT.Math.chisquared_quantile_c(alpha / 2.0, 2.0 * (n + 1.0))
    return low, high


def data_to_poisson_graph(data_hist):
    graph = ROOT.TGraphAsymmErrors(data_hist)
    graph.SetName(f'{data_hist.GetName()}_graph')
    graph.SetMarkerStyle(20)
    graph.SetMarkerSize(0.9)
    graph.SetLineColor(ROOT.kBlack)

    for i in range(graph.GetN()):
        x = ctypes.c_double(0.0)
        y = ctypes.c_double(0.0)
        graph.GetPoint(i, x, y)
        val = y.value

        exl = graph.GetErrorXlow(i)
        exh = graph.GetErrorXhigh(i)

        if val <= 0:
            graph.SetPoint(i, x.value, 0.0)
            graph.SetPointError(i, exl, exh, 0.0, 0.0)
            continue

        low, high = garwood_interval(int(round(val)), cl=0.683)
        graph.SetPointError(
            i,
            exl,
            exh,
            max(val - low, 0.0),
            max(high - val, 0.0),
        )

    return graph


def make_ratio_graph(graph, denom):
    ratio = graph.Clone(f'{graph.GetName()}_ratio')
    for i in range(ratio.GetN()):
        x = ctypes.c_double(0.0)
        y = ctypes.c_double(0.0)
        ratio.GetPoint(i, x, y)
        bin_idx = denom.FindBin(x.value)
        dval = denom.GetBinContent(bin_idx)
        if dval > 0:
            ratio.SetPoint(i, x.value, y.value / dval)
            ratio.SetPointError(
                i,
                ratio.GetErrorXlow(i),
                ratio.GetErrorXhigh(i),
                ratio.GetErrorYlow(i) / dval,
                ratio.GetErrorYhigh(i) / dval,
            )
        else:
            ratio.SetPoint(i, x.value, 0.0)
            ratio.SetPointError(i, 0.0, 0.0, 0.0, 0.0)
    return ratio


def get_channel(bin_name):
    parts = bin_name.split('_')
    if len(parts) < 3:
        return ''
    return parts[1]


def build_background_scheme(channel, method=None):
    if method is None:
        if channel == 'tt':
            method = 7
        elif channel in ('mt', 'et'):
            method = 6

    if channel == 'tt' and method in (3, 4, 6):
        return [
            (
                'Jet#rightarrow#tau_{h}',
                ['JetFakes', 'JetFakesSublead'],
                ROOT.TColor.GetColor(COLORS['green']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Genuine #tau',
                ['ZTT', 'TTT', 'VVT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'tt' and method in (1, 2):
        return [
            (
                'Jet#rightarrow#tau_{h}',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['green']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Genuine #tau',
                ['ZTT', 'TTT', 'VVT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'tt' and method in (7, 9):
        return [
            (
                'Electroweak',
                ['VVT'],
                ROOT.TColor.GetColor(COLORS['cms_red']),
            ),
            (
                't#bar{t}',
                ['TTT'],
                ROOT.TColor.GetColor(COLORS['cms_violet']),
            ),
            (
                'Jet#rightarrow#tau_{h}',
                ['JetFakes', 'JetFakesSublead'],
                ROOT.TColor.GetColor(COLORS['cms_cyan']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL'],
                ROOT.TColor.GetColor(COLORS['cms_green']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['cms_yellow']),
            ),
        ]
    if channel == 'mt' and method in (6, 8, 10):
        return [
            (
                'Electroweak',
                ['VVT'],
                ROOT.TColor.GetColor(COLORS['cms_red']),
            ),
            (
                't#bar{t}',
                ['TTT'],
                ROOT.TColor.GetColor(COLORS['cms_violet']),
            ),
            (
                'Jet#rightarrow#tau_{h}',
                ['JetFakes'],
                ROOT.TColor.GetColor(COLORS['cms_cyan']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL'],
                ROOT.TColor.GetColor(COLORS['cms_green']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['cms_yellow']),
            ),
        ]
    if channel == 'et' and method in (6, 8, 10):
        return [
            (
                'Electroweak',
                ['VVT'],
                ROOT.TColor.GetColor(COLORS['cms_red']),
            ),
            (
                't#bar{t}',
                ['TTT'],
                ROOT.TColor.GetColor(COLORS['cms_violet']),
            ),
            (
                'Jet#rightarrow#tau_{h}',
                ['JetFakes'],
                ROOT.TColor.GetColor(COLORS['cms_cyan']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL'],
                ROOT.TColor.GetColor(COLORS['cms_green']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['cms_yellow']),
            ),
        ]
    if channel == 'mt' or channel == 'et':
        return [
            (
                'QCD',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['pink']),
            ),
            (
                'Electroweak',
                ['VVJ', 'W', 'VVT'],
                ROOT.TColor.GetColor(COLORS['red']),
            ),
            (
                't#bar{t}',
                ['TTJ', 'TTT'],
                ROOT.TColor.GetColor(COLORS['violet']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL', 'ZJ'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'et':
        return [
            (
                'QCD',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['pink']),
            ),
            (
                'Electroweak',
                ['VVJ', 'W', 'VVT'],
                ROOT.TColor.GetColor(COLORS['red']),
            ),
            (
                't#bar{t}',
                ['TTJ', 'TTT'],
                ROOT.TColor.GetColor(COLORS['violet']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL', 'ZJ'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'em':
        return [
            (
                't#bar{t}',
                ['TTT', 'TTJ'],
                ROOT.TColor.GetColor(COLORS['violet']),
            ),
            (
                'QCD',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['pink']),
            ),
            (
                'Electroweak',
                ['VVT', 'VVJ', 'W'],
                ROOT.TColor.GetColor(COLORS['red']),
            ),
            (
                'Z#rightarrow#ell#ell',
                ['ZL', 'ZJ'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'ee':
        return [
            (
                't#bar{t}',
                ['TTT', 'TTJ'],
                ROOT.TColor.GetColor(COLORS['violet']),
            ),
            (
                'QCD',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['pink']),
            ),
            (
                'Electroweak',
                ['VVT', 'VVJ', 'W'],
                ROOT.TColor.GetColor(COLORS['red']),
            ),
            (
                'Z#rightarrowee',
                ['ZL', 'ZJ'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    if channel == 'mm':
        return [
            (
                't#bar{t}',
                ['TTT', 'TTJ'],
                ROOT.TColor.GetColor(COLORS['violet']),
            ),
            (
                'QCD',
                ['QCD'],
                ROOT.TColor.GetColor(COLORS['pink']),
            ),
            (
                'Electroweak',
                ['VVT', 'VVJ', 'W'],
                ROOT.TColor.GetColor(COLORS['red']),
            ),
            (
                'Z#rightarrow#mu#mu',
                ['ZL', 'ZJ'],
                ROOT.TColor.GetColor(COLORS['lightblue']),
            ),
            (
                'Z#rightarrow#tau#tau',
                ['ZTT'],
                ROOT.TColor.GetColor(COLORS['yellow']),
            ),
        ]
    return []


def create_axis_hists(src):
    axes = []
    for idx in range(2):
        hist = src.Clone(f'axis_{idx}')
        hist.Reset()
        hist.SetTitle('')
        hist.SetStats(0)
        axes.append(hist)
    return axes


def get_bin_edges(hist):
    edges = []
    for i in range(1, hist.GetNbinsX() + 2):
        edges.append(hist.GetBinLowEdge(i))
    return edges


def rebin_to_edges(hist, edges):
    current = get_bin_edges(hist)
    if (
        len(current) == len(edges)
        and all(a == b for a, b in zip(current, edges))
    ):
        out = hist.Clone(f'{hist.GetName()}_samebin')
        out.SetDirectory(0)
        return out

    bins = array.array('d', edges)
    out = hist.Rebin(len(edges) - 1, f'{hist.GetName()}_rebin', bins)
    out.SetDirectory(0)
    return out


def compute_common_edges(root_file, bin_names, ref_hist='TotalBkg'):
    common = None
    for b in bin_names:
        directory = root_file.Get(b)
        if not directory:
            continue
        try:
            h = get_hist(directory, ref_hist)
        except Exception:
            continue
        edges = get_bin_edges(h)
        if common is None:
            common = edges
        else:
            common_set = set(common)
            edges_set = set(edges)
            common = [x for x in common if x in edges_set and x in common_set]

    if not common or len(common) < 2:
        raise RuntimeError('Failed to determine common binning across bins')
    return common


def sum_histograms(root_file, bin_names, hist_name, target_edges=None):
    total = None
    for b in bin_names:
        directory = root_file.Get(b)
        if not directory:
            continue
        try:
            hist = get_hist(directory, hist_name, allow_empty=True)
        except Exception:
            continue
        if hist.GetNbinsX() == 1 and hist.GetEntries() == 0:
            continue
        if target_edges is not None:
            hist = rebin_to_edges(hist, target_edges)
        if total is None:
            total = hist.Clone(f'combined_{hist_name}')
            total.SetDirectory(0)
        else:
            total.Add(hist)
    return total


def draw_combined_bins(
    root_file,
    bin_names,
    output_dir,
    lumi,
    logy=False,
    blind=False,
    method=None,
    fitresult_path=None,
    fitresult_name=None,
):
    # --- Python plotting replacement ---
    import matplotlib.pyplot as plt
    import mplhep as hep
    plt.style.use(hep.style.CMS)
    plt.rcParams.update({
        "font.size": 20,
        "axes.titlesize": 22,
        "axes.labelsize": 20,
        "legend.fontsize": 18,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
    })

    common_edges = compute_common_edges(
        root_file,
        bin_names,
        ref_hist='TotalBkg',
    )
    data = sum_histograms(
        root_file,
        bin_names,
        'data_obs',
        target_edges=common_edges,
    )
    bkg = sum_histograms(
        root_file,
        bin_names,
        'TotalBkg',
        target_edges=common_edges,
    )
    if bkg is None:
        raise RuntimeError('Missing combined TotalBkg histogram')

    # --- Custom stack and legend order ---
    stack_groups = [
        {"label": r"H$\to\tau\tau$", "procs": ["ggH_SM_htt_M125"], "color": COLORS["cms_orange"]},
        {"label": r"$Z\to\tau\tau$", "procs": ["ZTT"], "color": COLORS["cms_yellow"]},
        {"label": r"$Z\to\ell\ell$", "procs": ["ZL", "ZJ"], "color": COLORS["cms_green"]},
        {"label": r"Jet$\to\tau_h$", "procs": ["JetFakes", "JetFakesSublead"], "color": COLORS["cms_cyan"]},
        {"label": r"$t\bar{t}$", "procs": ["TTT", "TTJ"], "color": COLORS["cms_violet"]},
        {"label": "Electroweak", "procs": ["VVT", "VVJ", "W"], "color": COLORS["cms_red"]},
    ]

    # Stacking order: Electroweak (bottom), tbar, JetFakes, ZL, ZTT (top)
    stack_groups = stack_groups[::-1]

    stack_vals = []
    stack_labels = []
    stack_colors = []
    edges = np.array([bkg.GetBinLowEdge(i+1) for i in range(bkg.GetNbinsX())] + [bkg.GetBinLowEdge(bkg.GetNbinsX()+1)])
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)
    for group in stack_groups:
        arr = None
        for proc in group["procs"]:
            h = sum_histograms(
                root_file,
                bin_names,
                proc,
                target_edges=common_edges,
            )
            if h is None or h.Integral() <= 0:
                continue
            vals = np.array([h.GetBinContent(i+1)/widths[i] for i in range(h.GetNbinsX())])
            if arr is None:
                arr = np.zeros_like(vals)
            arr += vals
        if arr is not None and np.sum(arr) > 0:
            stack_vals.append(arr)
            stack_labels.append(group["label"])
            stack_colors.append(group["color"])

    # Data and bkg arrays
    data_arr = np.array([data.GetBinContent(i+1)/widths[i] for i in range(data.GetNbinsX())]) if data else None
    data_err = np.array([data.GetBinError(i+1)/widths[i] for i in range(data.GetNbinsX())]) if data else None
    bkg_arr = np.array([bkg.GetBinContent(i+1)/widths[i] for i in range(bkg.GetNbinsX())])
    bkg_err = np.array([bkg.GetBinError(i+1)/widths[i] for i in range(bkg.GetNbinsX())])

    # --- Covariance-aware uncertainty band ---
    cov_band = None
    if fitresult_path and fitresult_name:
        try:
            import ROOT as _ROOT
            fitf = _ROOT.TFile.Open(fitresult_path)
            fitres = fitf.Get(fitresult_name)
            params = fitres.floatParsFinal()
            npar = params.getSize()
            param_names = [params.at(i).GetName() for i in range(npar)]
            cov = fitres.covarianceMatrix()

            # For each bin in the combined histogram, sum variances of all contributing original bins
            nbins_combined = len(bkg_arr)
            cov_band = np.zeros(nbins_combined)

            # For each bin in the combined histogram
            for icomb in range(nbins_combined):
                # For each category, find the corresponding bin
                for b in bin_names:
                    directory = root_file.Get(b)
                    if not directory:
                        continue
                    h = get_hist(directory, 'TotalBkg')
                    h = rebin_to_edges(h, common_edges)
                    # If this category has this bin, add its variance
                    if icomb < h.GetNbinsX():
                        pname = f"prop_bin{b}_bin{icomb}"
                        if pname in param_names:
                            idx = param_names.index(pname)
                            cov_band[icomb] += cov[idx][idx]
            cov_band = np.sqrt(cov_band)

            if len(cov_band) != len(bkg_arr):
                print(f"[WARN] cov_band length {len(cov_band)} does not match bkg_arr length {len(bkg_arr)}")
                cov_band = None

        except Exception as e:
            print(f"[WARN] Covariance extraction failed: {e}")
            cov_band = None

    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(10, 10), gridspec_kw={"height_ratios": [4, 1]}, sharex=True
    )
    # Stack
    bottoms = np.zeros_like(bkg_arr)
    # Draw stack bars and keep track of cumulative heights for horizontal lines
    cumulative = np.zeros_like(bkg_arr)
    group_tops = []
    for vals, label, color in zip(stack_vals, stack_labels, stack_colors):
        ax.fill_between(
            edges,
            np.append(cumulative, cumulative[-1]),
            np.append(cumulative + vals, (cumulative + vals)[-1]),
            step="post",
            facecolor=color,
            edgecolor="none",
            linewidth=0,
            label=label,
        )
        ax.step(
            edges,
            np.append(cumulative, cumulative[-1]),
            where="post",
            color="black",
            linewidth=0.5,
        )
        cumulative += vals
        group_tops.append(cumulative.copy())

    # Draw background uncertainty band (after stack, before horizontal lines)
    if cov_band is not None:
        ax.fill_between(
            edges,
            np.append(bkg_arr - cov_band, (bkg_arr - cov_band)[-1]),
            np.append(bkg_arr + cov_band, (bkg_arr + cov_band)[-1]),
            step="post",
            facecolor="none",
            hatch='////////',
            edgecolor="grey",
            linewidth=0,
            zorder=10,
            label="Bkg. Uncert."
        )
    else:
        ax.fill_between(
            edges,
            np.append(bkg_arr - bkg_err, (bkg_arr - bkg_err)[-1]),
            np.append(bkg_arr + bkg_err, (bkg_arr + bkg_err)[-1]),
            step="post",
            facecolor="none",
            hatch='////////',
            edgecolor="grey",
            linewidth=0,
            zorder=10,
            label="Bkg. Uncert."
        )

    # Draw horizontal black lines between stack groups (except the topmost)
    for group_top in group_tops[:-1]:
        ax.hlines(
            group_top,
            edges[:-1],
            edges[1:],
            color="black",
            linewidth=1.2,
            zorder=15,
        )
    # Data
    if not blind and data_arr is not None:
        ax.errorbar(
            centers,
            data_arr,
            yerr=data_err,
            xerr=widths / 2.0,
            fmt="o",
            color="black",
            markersize=4,
            linewidth=0.8,
            label="Observed",
        )
    hep.cms.label(
        ax=ax,
        label="Preliminary" if not blind else "Private Work",
        data=True,
        lumi=lumi,
        com=13.6,
    )
    ax.set_ylabel("Events / bin width")
    ax.grid(True, axis="y", alpha=0.25)
    if logy:
        ymax = max(np.max(bottoms), np.max(data_arr) if data_arr is not None else 0.0)
        ax.set_yscale("log")
        ax.set_ylim(0.001, 1000.0 * ymax)
        ax.yaxis.set_major_locator(locmaj)
        ax.yaxis.set_minor_locator(locmin)
        ax.yaxis.set_minor_formatter(tk.NullFormatter())
    # --- Signal lines for selected mass points ---
    signal_masses = [500]  # GeV
    signal_colors = ["#0e0505", "#0c2b41", '#2ca02c']  # red, blue, green
    procs = ['ggH', 'bbH']
    linestyles = ['--', ':']
    legend_labels = [r'gg$\phi$', r'bb$\phi$']
    scales = {'ggH': 1/1000., 'bbH': 1/4000.}
    fbs = {'ggH': 1, 'bbH': 0.5}

    for proc, linestyle,legend_label in zip(procs, linestyles, legend_labels):
        for mass, color in zip(signal_masses, signal_colors):
            sig_name = f'{proc}_MSSM_htt'
            sig_hist = sum_histograms(
                root_file,
                bin_names,
                sig_name,
                target_edges=common_edges,
            )
            print(f"Signal histogram for {sig_name}: {sig_hist.GetName() if sig_hist else 'None'}, integral={sig_hist.Integral() if sig_hist else 'N/A'}")
            if sig_hist and sig_hist.Integral() > 0:
                sig_vals = np.array([sig_hist.GetBinContent(i + 1)/widths[i] for i in range(sig_hist.GetNbinsX())]) * scales[proc]
                ax.stairs(
                    sig_vals,
                    edges,
                    fill=False,
                    color=color,
                    linewidth=2,
                    label=f"{legend_label} @{fbs[proc]} fb\n(m$_{{\phi}}$={mass} GeV)",
                    linestyle=linestyle,
                )
    # Legend: Bkg. unc, ZTT, ZL, JetFakes, tbar, Electroweak
    handles, labels_leg = ax.get_legend_handles_labels()
    order = []
    # Bkg. unc.
    order += [i for i, l in enumerate(labels_leg) if l == "Bkg. Uncert."]
    # HTT
    order += [i for i, l in enumerate(labels_leg) if l == r"H$\to\tau\tau$"]
    # ZTT
    order += [i for i, l in enumerate(labels_leg) if l == r"$Z\to\tau\tau$"]
    # ZL
    order += [i for i, l in enumerate(labels_leg) if l == r"$Z\to\ell\ell$"]
    # JetFakes
    order += [i for i, l in enumerate(labels_leg) if l == r"Jet$\to\tau_h$"]
    # tbar
    order += [i for i, l in enumerate(labels_leg) if l == r"$t\bar{t}$"]
    # Electroweak
    order += [i for i, l in enumerate(labels_leg) if l == "Electroweak"]
    # Observed (if present)
    order += [i for i, l in enumerate(labels_leg) if l == "Observed"]
    order += [i for i, l in enumerate(labels_leg) if l.startswith(legend_labels[0])]
    order += [i for i, l in enumerate(labels_leg) if l.startswith(legend_labels[1])]
    ax.legend([handles[i] for i in order], [labels_leg[i] for i in order], loc="upper right", frameon=False, ncol=2)
    tag = "prefit" if "prefit" in root_file.GetName() else "postfit"
    ax.text(
        0.95, 0.55, rf"All categories {tag}",
         transform=ax.transAxes,
         fontsize=18,         va="top", ha="right",
         fontweight="bold")
    # Ratio panel
    axr.axhline(1.0, color="black", linestyle=":")
    for y in [0.7, 0.8, 1.2, 1.3]:
        axr.axhline(y, color="darkgray", linestyle=":")
    print(cov_band, bkg_arr, bkg_err)
    if cov_band is not None:
        rel = cov_band / bkg_arr
    else:
        rel = np.divide(
            bkg_err,
            bkg_arr,
            out=np.zeros_like(bkg_arr),
            where=bkg_arr > 0,
        )
    axr.fill_between(
        edges,
        np.r_[1.0 - rel, (1.0 - rel)[-1]],
        np.r_[1.0 + rel, (1.0 + rel)[-1]],
        facecolor="none",
        edgecolor="gray",
        hatch="////////",
        linewidth=0.0,
        step=None,
        label="Bkg. Uncert."
    )
    if not blind and data_arr is not None:
        ratio = np.divide(
            data_arr,
            bkg_arr,
            out=np.zeros_like(data_arr),
            where=bkg_arr > 0,
        )
        ratio_err = np.divide(
            data_err,
            bkg_arr,
            out=np.zeros_like(data_err),
            where=bkg_arr > 0,
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
    axr.set_ylim(0.7, 1.3)
    axr.set_xlabel(r'$m_{T}^{tot}$ (GeV)')
    ax.set_xlim(30, edges[-1])
    axr.set_xlim(30, edges[-1])
    axr.set_xscale("log")
    axr.grid(True, axis="y", alpha=0.2)
    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, 'combined_bins.pdf')
    png_path = os.path.join(output_dir, 'combined_bins.png')
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=180)
    plt.close(fig)


def draw_bin(
    root_file,
    bin_name,
    output_dir,
    lumi,
    prefit=False,
    logy=False,
    blind=False,
    method=None,
):
    # --- Python plotting replacement ---
    import os
    import numpy as np
    import matplotlib.pyplot as plt
    import mplhep as hep

    plt.style.use(hep.style.CMS)
    plt.rcParams.update({
        "font.size": 20,
        "axes.titlesize": 22,
        "axes.labelsize": 20,
        "legend.fontsize": 18,
        "xtick.labelsize": 18,
        "ytick.labelsize": 18,
    })

    directory = root_file.Get(bin_name)
    if not directory:
        raise RuntimeError(f"Missing directory {bin_name} in {root_file.GetName()}")

    data = get_hist(directory, "data_obs")
    bkg = get_hist(directory, "TotalBkg")
    if not bkg:
        raise RuntimeError(f"Missing TotalBkg in directory {bin_name}")

    # --- Same stack groups / colours as draw_combined_bins ---
    stack_groups = [
        {"label": r"H$\to\tau\tau$", "procs": ["ggH_SM_htt_M125"], "color": COLORS["cms_orange"]},
        {"label": r"$Z\to\tau\tau$", "procs": ["ZTT"], "color": COLORS["cms_yellow"]},
        {"label": r"$Z\to\ell\ell$", "procs": ["ZL", "ZJ"], "color": COLORS["cms_green"]},
        {"label": r"Jet$\to\tau_h$", "procs": ["JetFakes", "JetFakesSublead"], "color": COLORS["cms_cyan"]},
        {"label": r"$t\bar{t}$", "procs": ["TTT", "TTJ"], "color": COLORS["cms_violet"]},
        {"label": "Electroweak", "procs": ["VVT", "VVJ", "W"], "color": COLORS["cms_red"]},
    ]

    # Same stacking order as combined plot:
    # Electroweak (bottom), ttbar, JetFakes, Zll, Ztt, Htt (top)
    stack_groups = stack_groups[::-1]

    nbins = bkg.GetNbinsX()
    edges = np.array(
        [bkg.GetBinLowEdge(i + 1) for i in range(nbins)]
        + [bkg.GetBinLowEdge(nbins + 1)]
    )
    centers = 0.5 * (edges[:-1] + edges[1:])
    widths = np.diff(edges)

    bkg_arr = np.array([bkg.GetBinContent(i + 1)/widths[i] for i in range(nbins)])
    bkg_err = np.array([bkg.GetBinError(i + 1)/widths[i] for i in range(nbins)])

    data_arr = None
    data_err = None
    if data and not blind:
        data_arr = np.array([data.GetBinContent(i + 1)/widths[i] for i in range(nbins)])
        data_err = np.array([data.GetBinError(i + 1)/widths[i] for i in range(nbins)])

    stack_vals = []
    stack_labels = []
    stack_colors = []

    for group in stack_groups:
        arr = None
        for proc in group["procs"]:
            h = get_hist(directory, proc, allow_empty=True)
            if not h:
                continue
            if h.GetNbinsX() == 1 and h.GetEntries() == 0:
                continue

            vals = np.array([h.GetBinContent(i + 1)/widths[i] for i in range(nbins)])
            if arr is None:
                arr = np.zeros_like(vals)
            arr += vals

        if arr is not None and np.sum(arr) > 0:
            stack_vals.append(arr)
            stack_labels.append(group["label"])
            stack_colors.append(group["color"])

    fig, (ax, axr) = plt.subplots(
        2, 1,
        figsize=(10, 10),
        gridspec_kw={"height_ratios": [4, 1]},
        sharex=True,
    )

    # --- Stack ---
    cumulative = np.zeros_like(bkg_arr)
    group_tops = []

    for vals, label, color in zip(stack_vals, stack_labels, stack_colors):
        ax.fill_between(
            edges,
            np.append(cumulative, cumulative[-1]),
            np.append(cumulative + vals, (cumulative + vals)[-1]),
            step="post",
            facecolor=color,
            edgecolor="none",
            linewidth=0,
            label=label,
        )
        ax.step(
            edges,
            np.append(cumulative, cumulative[-1]),
            where="post",
            color="black",
            linewidth=0.5,
        )
        cumulative += vals
        group_tops.append(cumulative.copy())

    # Background uncertainty band
    ax.fill_between(
        edges,
        np.append(bkg_arr - bkg_err, (bkg_arr - bkg_err)[-1]),
        np.append(bkg_arr + bkg_err, (bkg_arr + bkg_err)[-1]),
        step="post",
        facecolor="none",
        hatch="////////",
        edgecolor="grey",
        linewidth=0,
        zorder=10,
        label="Bkg. Uncert.",
    )

    # Horizontal separators between stack groups
    for group_top in group_tops[:-1]:
        ax.hlines(
            group_top,
            edges[:-1],
            edges[1:],
            color="black",
            linewidth=1.2,
            zorder=15,
        )

    # Data
    if not blind and data_arr is not None:
        ax.errorbar(
            centers,
            data_arr,
            yerr=data_err,
            xerr=widths / 2.0,
            fmt="o",
            color="black",
            markersize=4,
            linewidth=0.8,
            label="Observed",
        )

    hep.cms.label(
        ax=ax,
        label="Preliminary" if not blind else "Private Work",
        data=True,
        lumi=lumi,
        com=13.6,
    )

    ax.set_ylabel("Events / bin width")
    ax.grid(True, axis="y", alpha=0.25)

    ymax_stack = np.max(cumulative) if len(stack_vals) > 0 else np.max(bkg_arr)
    ymax_data = np.max(data_arr) if data_arr is not None else 0.0
    ymax = max(ymax_stack, ymax_data, 1.0)

    if logy:
        ax.set_yscale("log")
        ax.set_ylim(0.00001, 60.0 * ymax)
        ax.yaxis.set_major_locator(locmaj)
        ax.yaxis.set_minor_locator(locmin)
        ax.yaxis.set_minor_formatter(tk.NullFormatter())
    else:
        ax.set_ylim(0.0, max(1.6 * ymax, 1.0))

    # Legend order to match combined plot
    handles, labels_leg = ax.get_legend_handles_labels()
    order = []
    order += [i for i, l in enumerate(labels_leg) if l == "Bkg. Uncert."]
    order += [i for i, l in enumerate(labels_leg) if l == r"H$\to\tau\tau$"]
    order += [i for i, l in enumerate(labels_leg) if l == r"$Z\to\tau\tau$"]
    order += [i for i, l in enumerate(labels_leg) if l == r"$Z\to\ell\ell$"]
    order += [i for i, l in enumerate(labels_leg) if l == r"Jet$\to\tau_h$"]
    order += [i for i, l in enumerate(labels_leg) if l == r"$t\bar{t}$"]
    order += [i for i, l in enumerate(labels_leg) if l == "Electroweak"]
    order += [i for i, l in enumerate(labels_leg) if l == "Observed"]

    ax.legend(
        [handles[i] for i in order],
        [labels_leg[i] for i in order],
        loc="upper right",
        frameon=False,
        ncol=2,
    )
    # Channel label
    if bin_name.startswith("mssm_et_"):
        channel_label = r"e$\boldsymbol{\tau_{h}}$"
    elif bin_name.startswith("mssm_mt_"):
        channel_label = r"$\boldsymbol{\mu}\boldsymbol{\tau_{h}}$"
    elif bin_name.startswith("mssm_tt_"):
        channel_label = r"$\boldsymbol{\tau_{h}}\boldsymbol{\tau_{h}}$"
    elif bin_name.startswith("mssm_em_"):
        channel_label = r"e$\boldsymbol{\mu}$"
    elif bin_name.startswith("mssm_ee_"):
        channel_label = "ee"
    elif bin_name.startswith("mssm_mm_"):
        channel_label = r"$\boldsymbol{\mu}\boldsymbol{\mu}$"
    else:
        channel_label = ""

    if "_1_" in bin_name:
        btag_label = "no b tag"
    elif "_2_" in bin_name:
        btag_label = "b tag"
    else:
        btag_label = ""

    tag = "prefit" if "prefit" in root_file.GetName() else "postfit"

    # Compose label
    extra_label = "  ".join([x for x in [channel_label, btag_label, tag] if x])

    if extra_label:
        ax.text(
        0.95, 0.55, extra_label,
        transform=ax.transAxes,
        fontsize=18,
        va="bottom", ha="right",
        fontweight="bold")

    # --- Ratio panel ---
    axr.axhline(1.0, color="black", linestyle=":")
    for y in [0.7, 0.8, 1.2, 1.3]:
        axr.axhline(y, color="darkgray", linestyle=":")

    rel = np.divide(
        bkg_err,
        bkg_arr,
        out=np.zeros_like(bkg_arr),
        where=bkg_arr > 0,
    )

    axr.fill_between(
        edges,
        np.r_[1.0 - rel, (1.0 - rel)[-1]],
        np.r_[1.0 + rel, (1.0 + rel)[-1]],
        facecolor="none",
        edgecolor="gray",
        hatch="////////",
        linewidth=0.0,
        step="post",
        label="Bkg. Uncert.",
    )

    if not blind and data_arr is not None:
        ratio = np.divide(
            data_arr,
            bkg_arr,
            out=np.zeros_like(data_arr),
            where=bkg_arr > 0,
        )
        ratio_err = np.divide(
            data_err,
            bkg_arr,
            out=np.zeros_like(data_err),
            where=bkg_arr > 0,
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
    axr.set_ylim(0.7, 1.3)
    axr.set_xlabel(r"$m_{T}^{tot}$ (GeV)")
    ax.set_xlim(30, edges[-1])
    axr.set_xlim(30, edges[-1])
    axr.set_xscale("log")
    axr.grid(True, axis="y", alpha=0.2)

    os.makedirs(output_dir, exist_ok=True)
    pdf_path = os.path.join(output_dir, f"{bin_name}.pdf")
    png_path = os.path.join(output_dir, f"{bin_name}.png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, bbox_inches="tight", dpi=180)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(
        description='Plot MSSM shapes from shapes_output.root in CMS style'
    )
    parser.add_argument(
        '--input_file',
        '-i',
        default='shapes_output.root',
        help='Input ROOT file (from PostFitShapesCombEras.py)',
    )
    parser.add_argument(
        '--bin_name',
        '-b',
        default='all',
        help='Directory name to plot, or "all"',
    )
    parser.add_argument(
        '--lumi',
        default='109.08',
        help='Luminosity label',
    )
    parser.add_argument(
        '--dir',
        default='mssm_output/plots',
        help='Output directory for plots',
    )
    parser.add_argument(
        '--blind',
        action='store_true',
        help='Hide observed data points (blinded)',
    )
    parser.add_argument(
        '--combine-all-bins',
        action='store_true',
        help='Produce a single plot by summing all selected bins',
    )
    parser.add_argument(
        '--prefit',
        action='store_true',
        help='Prefit label mode',
    )
    parser.add_argument(
        '--method',
        type=int,
        default=None,
        help='Background-category method selector (e.g. 7, 8, 9, 10)',
    )
    parser.add_argument('--logy', action='store_true', help='Use log y-axis')
    parser.add_argument(
        '--fitresult',
        default=None,
        help='Path:Name to RooFitResult for correlated uncertainties (e.g. mssm_output/cmb/multidimfit.BestFit.root:fit_mdf)',
    )
    args = parser.parse_args()

    f_in = ROOT.TFile.Open(args.input_file)
    if not f_in or f_in.IsZombie():
        raise RuntimeError(f'Cannot open input ROOT file: {args.input_file}')

    fitresult_path = None
    fitresult_name = None
    if args.fitresult:
        if ':' in args.fitresult:
            fitresult_path, fitresult_name = args.fitresult.split(':', 1)
        else:
            fitresult_path = args.fitresult
            fitresult_name = 'fit_mdf'

    if args.bin_name == 'all':
        bins = list_bin_dirs(f_in)
    else:
        bins = [args.bin_name]

    if not bins:
        raise RuntimeError('No directories found to plot.')

    if args.combine_all_bins:
        try:
            draw_combined_bins(
                f_in,
                bins,
                args.dir,
                args.lumi,
                logy=args.logy,
                blind=args.blind,
                method=args.method,
                fitresult_path=fitresult_path,
                fitresult_name=fitresult_name,
            )
            print(f'[OK] Wrote combined plot from {len(bins)} bins')
        except Exception as exc:
            print(f'[WARN] Failed combined plot: {exc}')
    else:
        for b in bins:
            try:
                draw_bin(
                    f_in,
                    b,
                    args.dir,
                    args.lumi,
                    prefit=args.prefit,
                    logy=args.logy,
                    blind=args.blind,
                    method=args.method,
                )
                print(f'[OK] Wrote plot for {b}')
            except Exception as exc:
                print(f'[WARN] Skipping {b}: {exc}')

    f_in.Close()


if __name__ == '__main__':
    main()
