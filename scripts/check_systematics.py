import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

import json
from argparse import ArgumentParser
from collections import Counter
from os import environ

import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombineTools.ch import CombineHarvester
from CombineHarvester.TauSF.systematics import AddMSSMRun3Systematics

# Prevent cppyy's check for the PCH
environ["CLING_STANDARD_PCH"] = "none"

valid_eras = ["Run3_2022", "Run3_2022EE", "Run3_2023", "Run3_2023BPix", "Run3_2024", "Run3"]
all_masses = [
    60, 65, 70, 75, 80, 85, 90, 95, 100, 105, 110, 115, 120, 125, 130, 140,
    160, 180, 200, 250, 300, 350, 400, 450, 500, 600, 700, 800, 900, 1000,
    1100, 1200, 1400, 1600, 1800, 2000, 2300, 2600, 2900, 3200, 3500
]

channels = ["tt", "mt", "et"]

bkg_procs = {
    "tt": ["ggH_SM_htt_M125", "ZTT", "ZL", "VVT", "TTT", "JetFakes", "JetFakesSublead"],
    "et": ["ggH_SM_htt_M125", "ZTT", "ZL", "VVT", "TTT", "JetFakes"],
    "mt": ["ggH_SM_htt_M125", "ZTT", "ZL", "VVT", "TTT", "JetFakes"],
}

sig_procs = ["bbH_MSSM_htt", "ggH_MSSM_htt"]

cats = {
    "mt": [(1, "mt_nobtag"), (2, "mt_btag")],
    "et": [(1, "et_nobtag"), (2, "et_btag")],
    "tt": [(1, "tt_nobtag"), (2, "tt_btag")],
}

ERAS_IN_SYST_FILE = ["2024"]


def green(s):
    return f"\x1b[0;32;40m{s}\033[0m"


def red(s):
    return f"\x1b[0;31;40m{s}\033[0m"


def yellow(s):
    return f"\x1b[0;33;40m{s}\033[0m"


def parse_args():
    parser = ArgumentParser(
        prog="validate_mssm_run3_systematics",
        description="Validate systematic coverage and shape existence for non-morphed MSSM cards."
    )
    parser.add_argument(
        "-e", "--eras", dest="eras", type=str, required=True,
        help="eras to process, e.g. Run3_2024 or Run3"
    )
    parser.add_argument(
        "-m", "--masses", dest="masses", type=str, default="125",
        help="comma-separated masses, or 'all'"
    )
    parser.add_argument(
        "--check-shapes", action="store_true",
        help="also check nominal/Up/Down histograms exist in the ROOT files"
    )
    parser.add_argument(
        "--report-json", dest="report_json", type=str, default="",
        help="optional JSON output path"
    )
    return parser.parse_args()


def resolve_eras(era_tag):
    if era_tag == "Run3":
        eras = ["Run3_2022", "Run3_2022EE", "Run3_2023", "Run3_2023BPix", "Run3_2024"]
    else:
        eras = era_tag.split(",")

    for e in eras:
        if e not in valid_eras:
            raise ValueError(f"Unsupported era {e}. Available: {','.join(valid_eras)}")
    return eras


def resolve_masses(masses_arg):
    if masses_arg == "all":
        return all_masses
    masses = [int(x) for x in masses_arg.split(",")]
    for m in masses:
        if m not in all_masses:
            raise ValueError(f"Unsupported mass {m}")
    return masses


def build_cb(eras, masses):
    cb = CombineHarvester()

    for chn in channels:
        for era in eras:
            cb.AddObservations(["*"], ["mssm"], [era], [chn], cats[chn])
            cb.AddProcesses(["*"], ["mssm"], [era], [chn], bkg_procs[chn], cats[chn], False)
            cb.AddProcesses([str(m) for m in masses], ["mssm"], [era], [chn], sig_procs, cats[chn], True)

    cb = AddMSSMRun3Systematics(cb)
    return cb


def cat_name_without_prefix(full_bin_name):
    for prefix in ["mt_", "et_", "tt_"]:
        if full_bin_name.startswith(prefix):
            return full_bin_name.replace(prefix, "", 1)
    return full_bin_name


def extract_shapes(cb, eras, masses):
    for chn in channels:
        for cat in cats[chn]:
            for era in eras:
                full_bin = cat[1]
                cat_name = cat_name_without_prefix(full_bin)

                filename = f"shapes/mssm.datacard.mt_tot.{chn}.{era}.{cat_name}.root"
                print(f">>> file     {filename}")
                print(f">>> channel  {chn}")
                print(f">>> category {cat_name}")

                cb.cp().channel([chn]).bin([full_bin]).process(bkg_procs[chn]).era([era]).ExtractShapes(
                    filename, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC"
                )
                cb.cp().channel([chn]).bin([full_bin]).process(sig_procs).era([era]).mass(
                    [str(m) for m in masses]
                ).ExtractShapes(
                    filename, "$BIN/$PROCESS$MASS", "$BIN/$PROCESS$MASS_$SYSTEMATIC"
                )


def collect_systs(cb):
    systs = []

    def _collect(s):
        systs.append(s)

    cb.ForEachSyst(_collect)
    return systs


def collect_procs(cb):
    procs = []

    def _collect(p):
        procs.append(p)

    cb.ForEachProc(_collect)
    return procs


def syst_key(s):
    return (
        s.name(),
        s.type(),
        s.era(),
        s.channel(),
        s.bin(),
        s.process(),
        s.mass()
    )


def actual_systs(cb):
    out = []
    for s in collect_systs(cb):
        out.append({
            "name": s.name(),
            "type": s.type(),
            "era": s.era(),
            "channel": s.channel(),
            "bin": s.bin(),
            "process": s.process(),
            "mass": s.mass(),
        })
    return out


def duplicate_systs(cb):
    counts = Counter(syst_key(s) for s in collect_systs(cb))
    dups = [{"key": list(k), "count": c} for k, c in counts.items() if c > 1]
    return dups


def proc_list_for_channel(chn, masses):
    out = []
    for p in bkg_procs[chn]:
        out.append((p, "*"))
    for p in sig_procs:
        for m in masses:
            out.append((p, str(m)))
    return out


def add_expected(expected, name, stype, eras, chns, bins, procs_with_mass):
    for era in eras:
        for chn in chns:
            for b in bins[chn]:
                for proc, mass in procs_with_mass[chn]:
                    expected.add((name, stype, era, chn, b, proc, mass))


def add_expected_for_specific_processes(expected, name, stype, eras, chns, bins, proc_names, masses):
    for era in eras:
        for chn in chns:
            for b in bins[chn]:
                for proc in proc_names:
                    if proc in sig_procs:
                        for m in masses:
                            expected.add((name, stype, era, chn, b, proc, str(m)))
                    else:
                        expected.add((name, stype, era, chn, b, proc, "*"))


def build_expected_assignments(eras, masses):
    expected = set()
    bins = {chn: [x[1] for x in cats[chn]] for chn in channels}
    all_procs = {chn: proc_list_for_channel(chn, masses) for chn in channels}

    # Luminosity, pileup
    add_expected(expected, "lumi_13p6TeV_24", "lnN", eras, channels, bins, all_procs)
    add_expected(expected, "CMS_pileup", "shape", eras, channels, bins, all_procs)

    # Cross sections
    add_expected_for_specific_processes(expected, "cross_section_Z", "lnN", eras, channels, bins, ["ZTT", "ZL"], masses)
    add_expected_for_specific_processes(expected, "cross_section_ttbar", "lnN", eras, channels, bins, ["TTT"], masses)
    add_expected_for_specific_processes(expected, "cross_section_VV", "lnN", eras, channels, bins, ["VVT"], masses)

    # Signal xsec / BR
    add_expected_for_specific_processes(expected, "QCDscale_ggH", "lnN", eras, channels, bins, ["ggH_MSSM_htt"], masses)
    add_expected_for_specific_processes(expected, "QCDscale_ggH_SM", "lnN", eras, channels, bins, ["ggH_SM_htt_M125"], masses)
    add_expected_for_specific_processes(expected, "pdf_Higgs_gg", "lnN", eras, channels, bins, ["ggH_MSSM_htt"], masses)
    add_expected_for_specific_processes(expected, "theory_bbH", "lnN", eras, channels, bins, ["bbH_MSSM_htt"], masses)

    for n in ["BR_htt_THU", "BR_htt_PU_mq", "BR_htt_PU_alphas"]:
        add_expected_for_specific_processes(
            expected, n, "lnN", eras, channels, bins,
            ["ggH_MSSM_htt", "bbH_MSSM_htt", "ggH_SM_htt_M125"], masses
        )

    for n in ["QCDscale_ren_signal_ACCEPT", "QCDscale_fac_signal_ACCEPT", "ps_isr_signal", "ps_fsr_signal"]:
        add_expected_for_specific_processes(
            expected, n, "shape", eras, channels, bins,
            ["ggH_MSSM_htt", "bbH_MSSM_htt", "ggH_SM_htt_M125"], masses
        )

    # DY / top shape
    add_expected_for_specific_processes(
        expected, "CMS_MSSM_Z_pt_reweighting", "shape", eras, channels, bins, ["ZTT", "ZL"], masses
    )
    add_expected_for_specific_processes(
        expected, "CMS_Top_pt_reweighting", "shape", eras, channels, bins, ["TTT"], masses
    )

    # Lepton ID / scale
    add_expected(expected, "CMS_eff_m_id", "shape", eras, ["mt"], bins, {"mt": all_procs["mt"]})
    add_expected(expected, "CMS_eff_m_iso", "shape", eras, ["mt"], bins, {"mt": all_procs["mt"]})

    add_expected(expected, "CMS_eff_e_reco_13p6TeV", "shape", eras, ["et"], bins, {"et": all_procs["et"]})
    add_expected(expected, "CMS_eff_e_id_13p6TeV", "shape", eras, ["et"], bins, {"et": all_procs["et"]})
    add_expected(expected, "CMS_scale_e_13p6TeV", "shape", eras, ["et"], bins, {"et": all_procs["et"]})
    add_expected(expected, "CMS_res_e_13p6TeV", "shape", eras, ["et"], bins, {"et": all_procs["et"]})

    # mu -> tau fakes, ZL only in mt
    for era_short in ERAS_IN_SYST_FILE:
        for eta in ["0p0", "0p4", "0p8", "1p2", "1p7"]:
            name = f"CMS_fake_t_DeepTau2018v2p5_VSmu_{era_short}_eta_{eta}"
            add_expected_for_specific_processes(expected, name, "shape", eras, ["mt"], bins, ["ZL"], masses)

    # e -> tau fakes, ZL only in et
    # Mirrors current code exactly: same nuisance name repeated in the original builder.
    for era_short in ERAS_IN_SYST_FILE:
        for eta in ["0p0", "1p5"]:
            name = f"CMS_fake_t_DeepTau2018v2p5_VSe_{era_short}_eta_{eta}"
            add_expected_for_specific_processes(expected, name, "shape", eras, ["et"], bins, ["ZL"], masses)

    # Genuine tau ID / TES exclude ZL
    non_zl = {
        "tt": [(p, m) for (p, m) in all_procs["tt"] if p != "ZL"],
        "mt": [(p, m) for (p, m) in all_procs["mt"] if p != "ZL"],
        "et": [(p, m) for (p, m) in all_procs["et"] if p != "ZL"],
    }

    for era_short in ERAS_IN_SYST_FILE:
        for u in ["stat1", "stat2"]:
            for dm in ["0", "1", "10", "11"]:
                name = f"CMS_MSSM_eff_t_DeepTau2018v2p5_VSjet_{u}_DM{dm}_{era_short}"
                add_expected(expected, name, "shape", eras, channels, bins, non_zl)

        add_expected(
            expected,
            f"CMS_MSSM_eff_t_DeepTau2018v2p5_VSjet_syst_{era_short}",
            "shape", eras, channels, bins, non_zl
        )

    add_expected(
        expected,
        "CMS_MSSM_eff_t_DeepTau2018v2p5_VSjet_syst_alleras",
        "shape", eras, channels, bins, non_zl
    )

    for hp in ["syst_highpT", "stat_highpT_bin1", "syst_highpT_extrap"]:
        add_expected(
            expected,
            f"CMS_MSSM_eff_t_DeepTau2018v2p5_VSjet_{hp}",
            "shape", eras, channels, bins, non_zl
        )

    # Trigger
    add_expected(expected, "CMS_eff_m_trigger", "shape", eras, ["mt"], bins, {"mt": all_procs["mt"]})
    add_expected(expected, "CMS_eff_e_trigger", "shape", eras, ["et"], bins, {"et": all_procs["et"]})

    for era_short in ERAS_IN_SYST_FILE:
        for trig in ["ditau", "ditaujet", "singletau"]:
            for dm in ["0", "1", "10", "11"]:
                add_expected(
                    expected,
                    f"CMS_MSSM_trig_t_{trig}_Medium_DM{dm}_{era_short}",
                    "shape", eras, ["tt"], bins, {"tt": all_procs["tt"]}
                )
        add_expected(
            expected,
            f"CMS_MSSM_trig_j_ditaujet_{era_short}",
            "shape", eras, ["tt"], bins, {"tt": all_procs["tt"]}
        )

    add_expected(expected, "CMS_MSSM_trig_t_ditau_syst", "lnN", eras, ["tt"], bins, {"tt": all_procs["tt"]})

    # Fake tau energy scales, ZL only
    for era_short in ERAS_IN_SYST_FILE:
        for dm in ["0", "1", "10", "11"]:
            add_expected_for_specific_processes(
                expected,
                f"CMS_scale_e_DeepTau2018v2p5_DM{dm}_{era_short}_genElectron",
                "shape", eras, ["et"], bins, ["ZL"], masses
            )
            add_expected_for_specific_processes(
                expected,
                f"CMS_scale_mu_DeepTau2018v2p5_DM{dm}_{era_short}_genMuon",
                "shape", eras, ["mt"], bins, ["ZL"], masses
            )
            add_expected(
                expected,
                f"CMS_MSSM_scale_t_DeepTau2018v2p5_DM{dm}_{era_short}_genTau",
                "shape", eras, channels, bins, non_zl
            )

    # Jet / MET
    add_expected(expected, "CMS_scale_j_13p6TeV", "shape", eras, channels, bins, all_procs)
    add_expected(expected, "CMS_res_j_13p6TeV", "shape", eras, channels, bins, all_procs)

    recoil_names = ["ZTT", "ZL", "ggH_MSSM_htt", "bbH_MSSM_htt", "ggH_SM_htt_M125"]
    add_expected_for_specific_processes(
        expected, "CMS_MSSM_scale_met", "shape", eras, channels, bins, recoil_names, masses
    )
    add_expected_for_specific_processes(
        expected, "CMS_MSSM_res_met", "shape", eras, channels, bins, recoil_names, masses
    )

    # Fake factors, JetFakes only
    ff_sources = ["BkgSub", "Modelling", "Extrapolation", "Bootstrap", "NonClosure"]
    ff_processes = {
        "tt": ["QCD"],
        "et": ["QCD", "Wjets", "WjetsMC", "ttbarMC"],
        "mt": ["QCD", "Wjets", "WjetsMC", "ttbarMC"],
    }
    for chn, sources in ff_processes.items():
        for ff_proc in sources:
            for source in ff_sources:
                if source == "BkgSub" and ff_proc in ["WjetsMC", "ttbarMC"]:
                    continue
                if source == "Extrapolation":
                    for pt_name in ["pt0to100", "pt100to200", "pt200to300", "pt300plus"]:
                        add_expected_for_specific_processes(
                            expected,
                            f"CMS_MSSM_fake_t_{ff_proc}_{source}_{pt_name}",
                            "shape", eras, [chn], bins, ["JetFakes"], masses
                        )
                else:
                    add_expected_for_specific_processes(
                        expected,
                        f"CMS_MSSM_fake_t_{ff_proc}_{source}",
                        "shape", eras, [chn], bins, ["JetFakes"], masses
                    )

    for era_short in ERAS_IN_SYST_FILE:
        add_expected(
            expected,
            f"CMS_MSSM_btag_correlated_{era_short}",
            "shape", eras, channels, bins, all_procs
        )
        add_expected(
            expected,
            f"CMS_MSSM_btag_uncorrelated_{era_short}",
            "shape", eras, channels, bins, all_procs
        )

    return expected


def compare_expected_actual(cb, eras, masses):
    actual = set(syst_key(s) for s in collect_systs(cb))
    expected = build_expected_assignments(eras, masses)

    missing = sorted(expected - actual)
    unexpected = sorted(actual - expected)

    return missing, unexpected


def get_hist_safe(tfile, path):
    obj = tfile.Get(path)
    if obj is None:
        return None
    if not obj.InheritsFrom("TH1"):
        return None
    return obj


def check_shapes_for_cb(cb, eras, masses):
    problems = []
    open_files = {}

    def file_for(chn, era, full_bin):
        cat_name = cat_name_without_prefix(full_bin)
        key = (chn, era, cat_name)
        if key not in open_files:
            filename = f"shapes/mssm.datacard.mt_tot.{chn}.{era}.{cat_name}.root"
            tf = ROOT.TFile.Open(filename)
            open_files[key] = (filename, tf)
        return open_files[key]

    # Check nominals for processes
    for p in collect_procs(cb):
        filename, tf = file_for(p.channel(), p.era(), p.bin())
        if tf is None or tf.IsZombie():
            problems.append({
                "kind": "file",
                "message": "Could not open ROOT file",
                "file": filename,
                "process": p.process(),
                "channel": p.channel(),
                "era": p.era(),
                "bin": p.bin(),
                "mass": p.mass(),
            })
            continue

        if p.signal():
            nominal_path = f"{p.bin()}/{p.process()}{p.mass()}"
        else:
            nominal_path = f"{p.bin()}/{p.process()}"

        h = get_hist_safe(tf, nominal_path)
        if h is None:
            problems.append({
                "kind": "nominal_missing",
                "file": filename,
                "path": nominal_path,
                "process": p.process(),
                "channel": p.channel(),
                "era": p.era(),
                "bin": p.bin(),
                "mass": p.mass(),
            })

    # Check Up/Down for shape systs
    for s in collect_systs(cb):
        if s.type() != "shape":
            continue

        filename, tf = file_for(s.channel(), s.era(), s.bin())
        if tf is None or tf.IsZombie():
            continue

        if s.mass() != "*" and s.process() in sig_procs:
            nominal_name = f"{s.process()}{s.mass()}"
        else:
            nominal_name = s.process()

        up_path = f"{s.bin()}/{nominal_name}_{s.name()}Up"
        down_path = f"{s.bin()}/{nominal_name}_{s.name()}Down"

        hup = get_hist_safe(tf, up_path)
        hdn = get_hist_safe(tf, down_path)

        if hup is None:
            problems.append({
                "kind": "shape_up_missing",
                "file": filename,
                "path": up_path,
                "name": s.name(),
                "process": s.process(),
                "channel": s.channel(),
                "era": s.era(),
                "bin": s.bin(),
                "mass": s.mass(),
            })
        if hdn is None:
            problems.append({
                "kind": "shape_down_missing",
                "file": filename,
                "path": down_path,
                "name": s.name(),
                "process": s.process(),
                "channel": s.channel(),
                "era": s.era(),
                "bin": s.bin(),
                "mass": s.mass(),
            })

    for _, tf in open_files.values():
        if tf:
            tf.Close()

    return problems


def summarise_by_name(entries):
    counts = Counter()
    for e in entries:
        if isinstance(e, dict):
            if "name" in e:
                counts[e["name"]] += 1
            elif "key" in e and len(e["key"]) > 0:
                counts[e["key"][0]] += 1
        elif isinstance(e, tuple) and len(e) > 0:
            counts[e[0]] += 1
    return dict(sorted(counts.items()))


def main():
    args = parse_args()
    eras = resolve_eras(args.eras)
    masses = resolve_masses(args.masses)

    print(green(f"Building CombineHarvester for eras={eras}, masses={masses}"))
    cb = build_cb(eras, masses)

    print(green("Checking systematic duplicates"))
    dups = duplicate_systs(cb)

    print(green("Checking expected vs actual systematic assignments"))
    missing, unexpected = compare_expected_actual(cb, eras, masses)

    shape_problems = []
    if args.check_shapes:
        print(green("Extracting shapes"))
        extract_shapes(cb, eras, masses)
        print(green("Checking nominal and Up/Down shape existence"))
        shape_problems = check_shapes_for_cb(cb, eras, masses)

    all_systs = collect_systs(cb)

    report = {
        "eras": eras,
        "masses": masses,
        "n_systematics": len(all_systs),
        "n_duplicates": len(dups),
        "n_missing_expected": len(missing),
        "n_unexpected": len(unexpected),
        "n_shape_problems": len(shape_problems),
        "duplicates": dups,
        "missing_expected": [list(x) for x in missing],
        "unexpected": [list(x) for x in unexpected],
        "shape_problems": shape_problems,
        "duplicate_summary_by_name": summarise_by_name(dups),
        "missing_summary_by_name": summarise_by_name(missing),
        "unexpected_summary_by_name": summarise_by_name(unexpected),
    }

    print()
    print(green("========== VALIDATION SUMMARY =========="))
    print(f"Total systematic objects : {report['n_systematics']}")
    print(f"Duplicate assignments    : {report['n_duplicates']}")
    print(f"Missing expected         : {report['n_missing_expected']}")
    print(f"Unexpected assignments   : {report['n_unexpected']}")
    print(f"Shape problems           : {report['n_shape_problems']}")

    if dups:
        print(red("\nDuplicate systematic assignments found:"))
        for d in dups[:20]:
            print(f"  count={d['count']} key={d['key']}")
        if len(dups) > 20:
            print(f"  ... and {len(dups) - 20} more")

    if missing:
        print(red("\nMissing expected systematic assignments:"))
        for x in missing[:20]:
            print(" ", x)
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")

    if unexpected:
        print(yellow("\nUnexpected systematic assignments:"))
        for x in unexpected[:20]:
            print(" ", x)
        if len(unexpected) > 20:
            print(f"  ... and {len(unexpected) - 20} more")

    if shape_problems:
        print(red("\nShape problems:"))
        for x in shape_problems[:20]:
            print(" ", x)
        if len(shape_problems) > 20:
            print(f"  ... and {len(shape_problems) - 20} more")

    if args.report_json:
        with open(args.report_json, "w") as f:
            json.dump(report, f, indent=2)
        print(green(f"\nWrote report to {args.report_json}"))

    n_bad = len(dups) + len(missing) + len(shape_problems)
    if n_bad == 0:
        print(green("\nValidation passed."))
        raise SystemExit(0)
    else:
        print(red(f"\nValidation failed with {n_bad} blocking issues."))
        raise SystemExit(1)


if __name__ == "__main__":
    main()