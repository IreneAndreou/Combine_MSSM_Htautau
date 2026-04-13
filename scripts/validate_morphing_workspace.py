#!/usr/bin/env python3
"""Validate workspace morphing and shape content for MSSM TauSF analyses.

This script is a lightweight sanity checker for the harvested workspace.
It prints signal morphing yields for a few masses, checks that the
expected morph PDFs/observables exist, and flags large yield jumps that can
indicate a morphing or binning problem.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

import ROOT

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)


def parse_csv(values: str) -> List[str]:
    return [v.strip() for v in values.split(",") if v.strip()]


def parse_int_csv(values: str) -> List[int]:
    return [int(v.strip()) for v in values.split(",") if v.strip()]


def get_observable(pdf, ws):
    try:
        obs = pdf.getObservables(ws.allVars())
        if obs and obs.getSize() > 0:
            return obs.first()
    except Exception:
        pass

    for guess in ("CMS_th1x", "x", "m_sv", "mt_tot"):
        var = ws.var(guess)
        if var:
            return var
    return None


def safe_integral(pdf, obs, ws, mh_var, mass):
    if mh_var:
        mh_var.setVal(float(mass))
    if obs:
        return pdf.createIntegral(ROOT.RooArgSet(obs)).getVal()
    return pdf.getVal()


def rel_jump(prev: float, curr: float) -> float:
    denom = max(abs(prev), 1e-12)
    return abs(curr - prev) / denom


def infer_bins(ws, processes: List[str]) -> List[str]:
    for cat_name in ("CMS_channel", "channelCat", "bin"):
        cat = ws.cat(cat_name)
        if cat:
            out = []
            it = cat.typeIterator()
            item = it.Next()
            while item:
                out.append(item.GetName())
                item = it.Next()
            if out:
                return sorted(out)

    funcs = ws.allFunctions()
    it = funcs.createIterator()
    item = it.Next()
    bins = set()
    while item:
        name = item.GetName()
        if name.endswith("_morph"):
            for proc in processes:
                token = f"_{proc}_"
                if token in name:
                    bins.add(name.split(token)[0])
        item = it.Next()

    if bins:
        return sorted(bins)
    return []


def find_shape_object(ws, bin_name: str, proc_name: str):
    candidates = [
        f"{bin_name}_{proc_name}_morph",
        f"shapeSig_{proc_name}_{bin_name}",
        f"shapeBkg_{proc_name}_{bin_name}",
        f"{proc_name}_{bin_name}_morph",
    ]
    for candidate in candidates:
        obj = ws.function(candidate)
        if obj:
            return candidate, obj
        obj = ws.pdf(candidate)
        if obj:
            return candidate, obj
    return None, None


def parse_workspace_bin(bin_name: str):
    if not bin_name.startswith("mssm_"):
        return None
    parts = bin_name.split("_")
    if len(parts) < 5:
        return None
    if parts[1] not in ("mt", "et", "tt"):
        return None
    if parts[2] not in ("1", "2"):
        return None
    channel = parts[1]
    category = parts[2]
    era = "_".join(parts[3:])
    cat_label = "nobtag" if category == "1" else "btag"
    directory = f"{channel}_{cat_label}"
    return channel, era, cat_label, directory


def get_input_integral(file_cache, root_path: Path, hist_path: str):
    handle = file_cache.get(str(root_path))
    if handle is None:
        handle = ROOT.TFile.Open(str(root_path))
        if not handle or handle.IsZombie():
            return None, f"cannot open {root_path}"
        file_cache[str(root_path)] = handle
    hist = handle.Get(hist_path)
    if not hist:
        return None, f"missing {hist_path} in {root_path.name}"
    return hist.Integral(), None


def get_input_hist(file_cache, root_path: Path, hist_path: str):
    handle = file_cache.get(str(root_path))
    if handle is None:
        handle = ROOT.TFile.Open(str(root_path))
        if not handle or handle.IsZombie():
            return None, f"cannot open {root_path}"
        file_cache[str(root_path)] = handle
    hist = handle.Get(hist_path)
    if not hist:
        return None, f"missing {hist_path} in {root_path.name}"
    return hist, None


def list_systematic_pairs(dir_obj, nominal_name: str):
    keys = [k.GetName() for k in dir_obj.GetListOfKeys()]
    systs = {}
    prefix = f"{nominal_name}_"
    for key in keys:
        if ".subnodes" in key:
            continue
        if not key.startswith(prefix):
            continue
        if key.endswith("Up"):
            syst = key[len(prefix):-2]
            systs.setdefault(syst, {})["Up"] = key
        elif key.endswith("Down"):
            syst = key[len(prefix):-4]
            systs.setdefault(syst, {})["Down"] = key
    return systs


def has_negative_bins(hist):
    for idx in range(1, hist.GetNbinsX() + 1):
        if hist.GetBinContent(idx) < 0:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate morphing shapes and workspace content for MSSM TauSF."
        )
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help=(
            "Workspace ROOT file produced by "
            "harvestDatacards_newQCD_uncerts.py"
        ),
    )
    parser.add_argument(
        "--mass-list",
        default="60,125,300,500,1000,1400,2000,3500",
        help="Comma-separated mass points to probe",
    )
    parser.add_argument(
        "--bins",
        default="auto",
        help="Comma-separated bin names to inspect, or 'auto'",
    )
    parser.add_argument(
        "--processes",
        default="bbH_MSSM_htt,ggH_MSSM_htt",
        help="Comma-separated signal processes to validate",
    )
    parser.add_argument(
        "--jump-threshold",
        type=float,
        default=0.50,
        help=(
            "Flag relative yield jumps larger than adjacent masses"
        ),
    )
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="Only print the presence/absence of key workspace objects",
    )
    parser.add_argument(
        "--check-anchors",
        action="store_true",
        help="Compare morph yields to input signal templates at mass anchors",
    )
    parser.add_argument(
        "--input-shapes-dir",
        default="shapes",
        help="Directory with mssm.datacard.mt_tot.* input ROOT files",
    )
    parser.add_argument(
        "--anchor-threshold",
        type=float,
        default=0.05,
        help="Relative mismatch threshold for anchor comparisons",
    )
    parser.add_argument(
        "--check-uncertainties",
        action="store_true",
        help="Check input Up/Down systematic templates for selected masses",
    )
    parser.add_argument(
        "--unc-rel-min",
        type=float,
        default=1e-4,
        help="Minimum relative change to treat a systematic as non-flat",
    )
    parser.add_argument(
        "--unc-max-systs",
        type=int,
        default=0,
        help="Optional cap on checked systematics per proc/mass (0 = all)",
    )
    args = parser.parse_args()

    ws_path = Path(args.workspace)
    if not ws_path.exists():
        print(f"[ERROR] Workspace not found: {ws_path}")
        return 1

    masses = parse_int_csv(args.mass_list)
    bins = parse_csv(args.bins)
    processes = parse_csv(args.processes)

    infile = ROOT.TFile.Open(str(ws_path))
    if not infile or infile.IsZombie():
        print(f"[ERROR] Could not open workspace: {ws_path}")
        return 1

    ws = infile.Get("w")
    if not ws:
        # Some workspaces use a different name; fall back to the first
        # RooWorkspace.
        keys = [k.GetName() for k in infile.GetListOfKeys()]
        for key in keys:
            obj = infile.Get(key)
            if isinstance(obj, ROOT.RooWorkspace):
                ws = obj
                print(f"[INFO] Using workspace object named: {key}")
                break

    if not ws:
        print("[ERROR] No RooWorkspace found in the file.")
        return 1

    if len(bins) == 1 and bins[0].lower() == "auto":
        bins = infer_bins(ws, processes)
        if not bins:
            print("[ERROR] Could not auto-detect bins from workspace.")
            return 1

    mh = ws.var("MH")

    print("==== Workspace validation ====")
    print(f"Workspace: {ws_path}")
    print(f"Mass points: {masses}")
    print(f"Bins: {bins}")
    print(f"Processes: {processes}")
    if not mh:
        print(
            "[WARN] Workspace has no MH variable; "
            "evaluating at nominal state."
        )

    missing = []
    found = {}
    for b in bins:
        for p in processes:
            resolved_name, pdf = find_shape_object(ws, b, p)
            key_name = f"{b}::{p}"
            if not pdf:
                print(f"[MISSING] {key_name}")
                missing.append(key_name)
                continue
            found[key_name] = (resolved_name, pdf)

            obs = get_observable(pdf, ws)

            if args.summary_only:
                print(f"[OK] {key_name} -> {resolved_name}")
                continue

            values = []
            for m in masses:
                try:
                    y = safe_integral(pdf, obs, ws, mh, m)
                    values.append((m, y))
                except Exception as exc:
                    print(f"[ERROR] {resolved_name} mass={m}: {exc}")
                    missing.append(f"{resolved_name}:{m}")
                    values.append((m, None))

            clean = [(m, y) for m, y in values if y is not None]
            if clean:
                y0 = clean[0][1]
                ymin = min(y for _, y in clean)
                ymax = max(y for _, y in clean)
                print(
                    f"[OK] {resolved_name}: y(m0)={y0:.6g}, "
                    f"min={ymin:.6g}, max={ymax:.6g}"
                )
                for (m1, y1), (m2, y2) in zip(clean[:-1], clean[1:]):
                    if rel_jump(y1, y2) > args.jump_threshold:
                        print(
                            f"  [JUMP] {resolved_name}: {m1}->{m2} changed by "
                            f"{rel_jump(y1, y2):.2f}"
                        )

    print("==== Totals ====")
    for b in bins:
        for p in processes:
            key_name = f"{b}::{p}"
            if key_name not in found:
                continue
            pdf_name, pdf = found[key_name]
            obs = get_observable(pdf, ws)
            try:
                integral = safe_integral(pdf, obs, ws, mh, masses[0])
                print(f"{pdf_name}: mass={masses[0]} integral={integral:.6g}")
            except Exception as exc:
                print(f"[ERROR] total integral for {pdf_name}: {exc}")

    infile.Close()

    anchor_issues = 0
    anchor_checks = 0
    file_cache = {}
    if args.check_anchors and not args.summary_only:
        print("==== Anchor comparison ====")
        shapes_dir = Path(args.input_shapes_dir)
        for b in bins:
            info = parse_workspace_bin(b)
            if not info:
                print(f"[WARN] Cannot parse bin naming for anchor check: {b}")
                continue
            channel, era, cat_label, directory = info
            root_name = (
                f"mssm.datacard.mt_tot.{channel}.{era}.{cat_label}.root"
            )
            root_path = shapes_dir / root_name
            for p in processes:
                key_name = f"{b}::{p}"
                if key_name not in found:
                    continue
                resolved_name, pdf = found[key_name]
                obs = get_observable(pdf, ws)
                for mass in masses:
                    anchor_checks += 1
                    morph_val = safe_integral(pdf, obs, ws, mh, mass)
                    hist_path = f"{directory}/{p}{mass}"
                    input_val, err = get_input_integral(
                        file_cache,
                        root_path,
                        hist_path,
                    )
                    if err:
                        print(
                            f"[ANCHOR-MISSING] {resolved_name} "
                            f"m={mass}: {err}"
                        )
                        anchor_issues += 1
                        continue
                    denom = max(abs(input_val), 1e-12)
                    rel = abs(morph_val - input_val) / denom
                    if rel > args.anchor_threshold:
                        print(
                            f"[ANCHOR-MISMATCH] {resolved_name} m={mass}: "
                            f"morph={morph_val:.6g}, input={input_val:.6g}, "
                            f"rel={rel:.3f}"
                        )
                        anchor_issues += 1

        print(
            f"Anchor checks: {anchor_checks}, "
            f"issues: {anchor_issues}, "
            f"threshold: {args.anchor_threshold:.3f}"
        )

    unc_issues = 0
    unc_checks = 0
    if args.check_uncertainties and not args.summary_only:
        print("==== Uncertainty template check ====")
        shapes_dir = Path(args.input_shapes_dir)
        for b in bins:
            info = parse_workspace_bin(b)
            if not info:
                print(
                    f"[WARN] Cannot parse bin naming for "
                    f"uncertainty check: {b}"
                )
                continue
            channel, era, cat_label, directory = info
            root_name = (
                f"mssm.datacard.mt_tot.{channel}.{era}.{cat_label}.root"
            )
            root_path = shapes_dir / root_name
            root_handle = file_cache.get(str(root_path))
            if root_handle is None:
                root_handle = ROOT.TFile.Open(str(root_path))
                if not root_handle or root_handle.IsZombie():
                    print(f"[UNC-ERROR] cannot open {root_path}")
                    unc_issues += 1
                    continue
                file_cache[str(root_path)] = root_handle
            dir_obj = root_handle.Get(directory)
            if not dir_obj:
                print(
                    f"[UNC-ERROR] missing directory {directory} "
                    f"in {root_name}"
                )
                unc_issues += 1
                continue

            for p in processes:
                for mass in masses:
                    nominal_name = f"{p}{mass}"
                    nominal_path = f"{directory}/{nominal_name}"
                    nominal_hist, err = get_input_hist(
                        file_cache,
                        root_path,
                        nominal_path,
                    )
                    if err:
                        print(f"[UNC-SKIP] {b} {nominal_name}: {err}")
                        continue

                    pairs = list_systematic_pairs(dir_obj, nominal_name)
                    if args.unc_max_systs > 0:
                        syst_names = sorted(pairs.keys())[:args.unc_max_systs]
                    else:
                        syst_names = sorted(pairs.keys())

                    for syst in syst_names:
                        unc_checks += 1
                        up_key = pairs[syst].get("Up")
                        down_key = pairs[syst].get("Down")
                        if not up_key or not down_key:
                            print(
                                f"[UNC-MISSING-PAIR] "
                                f"{directory}/{nominal_name} "
                                f"syst={syst}"
                            )
                            unc_issues += 1
                            continue

                        up_hist = dir_obj.Get(up_key)
                        down_hist = dir_obj.Get(down_key)
                        if not up_hist or not down_hist:
                            print(
                                f"[UNC-MISSING-HIST] "
                                f"{directory}/{nominal_name} "
                                f"syst={syst}"
                            )
                            unc_issues += 1
                            continue

                        nom = nominal_hist.Integral()
                        up = up_hist.Integral()
                        down = down_hist.Integral()
                        denom = max(abs(nom), 1e-12)
                        up_rel = (up - nom) / denom
                        down_rel = (down - nom) / denom

                        if (
                            abs(up_rel) > args.unc_rel_min
                            and abs(down_rel) > args.unc_rel_min
                            and up_rel * down_rel > 0
                        ):
                            print(
                                f"[UNC-SAME-DIR] {directory}/{nominal_name} "
                                f"syst={syst} up_rel={up_rel:.3e} "
                                f"down_rel={down_rel:.3e}"
                            )
                            unc_issues += 1

                        if (
                            has_negative_bins(up_hist)
                            or has_negative_bins(down_hist)
                        ):
                            print(
                                f"[UNC-NEGATIVE-BIN] "
                                f"{directory}/{nominal_name} "
                                f"syst={syst}"
                            )
                            unc_issues += 1

        print(
            f"Uncertainty checks: {unc_checks}, "
            f"issues: {unc_issues}, "
            f"rel_min: {args.unc_rel_min:.1e}"
        )

    for _, handle in file_cache.items():
        handle.Close()

    if missing:
        print(f"==== Validation completed with {len(missing)} issues ====")
        return 2

    if args.check_anchors and anchor_issues > 0:
        print("==== Validation completed with anchor mismatches ====")
        return 3

    if args.check_uncertainties and unc_issues > 0:
        print(
            "==== Validation completed with uncertainty "
            "template issues ===="
        )
        return 4

    print("==== Validation passed ====")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
