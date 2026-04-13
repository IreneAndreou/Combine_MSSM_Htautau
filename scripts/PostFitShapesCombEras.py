# Example command:
# python3 scripts/PostFitShapesCombEras.py -w mssm_output/cmb/ws.root --freeze MH=125,r_bbH=1,r_ggH=1
# the script compares against fixed mass MH=125 GeV templates, so the freeze option is needed to get the correct postfit shapes for the signal. The script will print out the yields and uncertainties for each process and also write the postfit shapes to a root file that can be used for plotting. Note that the script assumes a specific naming convention for the input histograms in the workspace, so it may need to be modified if your workspace has a different structure.
import numpy as np
import array
from numpy import arange
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(True)
ROOT.TH1.AddDirectory(False) # avoid memory issues with many histograms
import CombineHarvester.CombineTools.ch as ch
import sys
import argparse
import os
from itertools import groupby

parser = argparse.ArgumentParser()
parser.add_argument('--fitresult', '-f', help= 'Path to a RooFitResult, only needed for postfit')
parser.add_argument('--workspace', '-w', help= 'The input workspace-containing file [REQUIRED]')
parser.add_argument('--datacard', '-d', help= 'The input datacard, only used for rebinning')
parser.add_argument("--postfit", action='store_true', help="Create post-fit histograms in addition to pre-fit")
parser.add_argument('--eras', '-e', help= 'Eras to combine in same plots')
parser.add_argument('--channels', '-c', help= 'Channels to combine in sample plots')
parser.add_argument('--cats', help= 'Categories to combine in same plots')
parser.add_argument('--bin_match', '-b', help= 'String to match bin names to, if specified yields will only be printed for bins that match the string')
parser.add_argument('--output', '-o', help= 'The output name of the root file', default='shapes_output.root')
parser.add_argument('--freeze', help= 'Parameters to freeze to specified values. Format PARAM1,PARAM2=X,PARAM3=Y where the values X and Y are optional.')
parser.add_argument('--plot_dir', help='Optional output directory for quick diagnostic plots')
parser.add_argument('--max_proc_plots', type=int, default=8, help='Maximum number of per-process uncertainty plots per bin')
args = parser.parse_args()

fout = ROOT.TFile(args.output,'UPDATE')

eras=[]
channels=[]
cats=[]
if args.eras: eras=args.eras.split(',')
if args.channels: channels=args.channels.split(',')
if args.cats: cats=args.cats.split(',')


cmb_card = ch.CombineHarvester()
if args.datacard:
  cmb_card.ParseDatacard(args.datacard)

cmb = ch.CombineHarvester()
infile = ROOT.TFile(args.workspace)
ws = infile.Get('w')

cmb.SetFlag('workspaces-use-clone', True)
ch.ParseCombineWorkspace(cmb, ws, "ModelConfig", "data_obs", False)

#cmb.PrintAll()

bins = cmb.cp().bin_set()

def ReplaceEraAndChannels(x):
    for e in eras:
      x=x.replace(e,'')
    for c in channels:
      x=x.replace(c,'')
    for cat in cats:
      x=x.replace(cat,'')
    return x

bins_grouped = [list(g) for k, g in groupby(sorted(bins, key=ReplaceEraAndChannels), key=ReplaceEraAndChannels)]

print(bins_grouped)

def GetBinnings(ref):
  bins=[]
  for i in range(1,ref.GetNbinsX()+2):
    bins.append(ref.GetBinLowEdge(i))

  return bins

def RestoreBinning(src, ref):
  res = ref.Clone(f'{ref.GetName()}_restore')
  res.SetDirectory(0)
  res.Reset()
  for x in range(1, res.GetNbinsX()+1):
    res.SetBinContent(x, src.GetBinContent(x))
    res.SetBinError(x, src.GetBinError(x))
  return res

def ZeroErrors(src):
  out = src.Clone(f'{src.GetName()}_zeroerr')
  out.SetDirectory(0)
  for x in range(1, out.GetNbinsX()+1):
    out.SetBinError(x, 0.)
  return out


def ParseWorkspaceBin(bin_name):
  if not bin_name.startswith('mssm_'):
    return None
  parts = bin_name.split('_')
  if len(parts) < 5:
    return None
  if parts[1] not in ('mt', 'et', 'tt'):
    return None
  if parts[2] not in ('1', '2'):
    return None
  channel = parts[1]
  category = parts[2]
  era = '_'.join(parts[3:])
  cat_label = 'nobtag' if category == '1' else 'btag'
  directory = f'{channel}_{cat_label}'
  return channel, era, cat_label, directory


def GetInputHist(file_cache, bin_name, proc_name, signal_mass='125'):
  parsed = ParseWorkspaceBin(bin_name)
  if not parsed:
    return None
  channel, era, cat_label, directory = parsed
  input_root_file = f'shapes/mssm.datacard.mt_tot.{channel}.{era}.{cat_label}.root'

  if input_root_file not in file_cache:
    file_cache[input_root_file] = ROOT.TFile(input_root_file)
  input_file = file_cache[input_root_file]
  if not input_file or input_file.IsZombie():
    return None

  hist_name = proc_name
  if proc_name in ['ggH_MSSM_htt', 'bbH_MSSM_htt']:
    hist_name = f'{proc_name}{signal_mass}'

  h = input_file.Get(f'{directory}/{hist_name}')
  if not h:
    return None
  return h.Clone()


def GetInputIntegral(file_cache, bin_name, proc_name, signal_mass='125'):
  h = GetInputHist(file_cache, bin_name, proc_name, signal_mass)
  if not h:
    return None
  return h.Integral()


def BuildRelUncHist(src, name):
  out = src.Clone(name)
  out.SetDirectory(0)
  out.Reset()
  for i in range(1, src.GetNbinsX() + 1):
    c = src.GetBinContent(i)
    e = src.GetBinError(i)
    rel = 0.
    if c > 0.:
      rel = e / c
    out.SetBinContent(i, rel)
    out.SetBinError(i, 0.)
  return out


def SaveTotalPlot(data_hist, bkg_hist, sig_hist, out_path, title):
  base = SafeName(title)
  c = ROOT.TCanvas(f'c_total_{base}', '', 800, 700)
  c.cd()

  bkg = bkg_hist.Clone(f'bkg_plot_{base}')
  sig = sig_hist.Clone(f'sig_plot_{base}')
  data = data_hist.Clone(f'data_plot_{base}')
  for h in [bkg, sig, data]:
    h.SetDirectory(0)
    h.SetStats(0)

  bkg.SetTitle(title)
  bkg.GetXaxis().SetTitle('Observable bin')
  bkg.GetYaxis().SetTitle('Events')
  bkg.SetLineColor(ROOT.kBlue + 2)
  bkg.SetFillColorAlpha(ROOT.kBlue, 0.35)
  bkg.SetFillStyle(1001)
  bkg.SetMarkerSize(0)

  sig.SetLineColor(ROOT.kRed + 1)
  sig.SetLineWidth(2)

  data.SetMarkerStyle(20)
  data.SetMarkerSize(0.8)
  data.SetLineColor(ROOT.kBlack)

  bkg.Draw('E2')
  sig.Draw('HIST SAME')
  data.Draw('EP SAME')

  leg = ROOT.TLegend(0.62, 0.72, 0.89, 0.89)
  leg.SetBorderSize(0)
  leg.SetFillStyle(0)
  leg.AddEntry(data, 'Data', 'lep')
  leg.AddEntry(bkg, 'TotalBkg unc', 'f')
  leg.AddEntry(sig, 'TotalSig', 'l')
  leg.Draw()

  c.Modified()
  c.Update()
  c.SaveAs(out_path)
  c.Close()


def SaveProcUncPlot(proc_hist_unc, out_path, title):
  base = SafeName(title)
  c = ROOT.TCanvas(f'c_unc_{base}', '', 800, 600)
  c.cd()

  rel = BuildRelUncHist(proc_hist_unc, f'rel_{base}')
  rel.SetDirectory(0)
  rel.SetStats(0)
  rel.SetTitle(title)
  rel.GetXaxis().SetTitle('Observable bin')
  rel.GetYaxis().SetTitle('Relative unc')
  rel.SetLineColor(ROOT.kGreen + 2)
  rel.SetLineWidth(2)
  rel.SetMinimum(0.)

  maxval = rel.GetMaximum()
  if maxval <= 0.:
    maxval = 1.
  rel.SetMaximum(1.2 * maxval)

  rel.Draw('HIST')

  c.Modified()
  c.Update()
  c.SaveAs(out_path)
  c.Close()


def SafeName(name):
  return name.replace('/', '_')

def PrintMassScan(file_cache, bins, proc_name, masses=('120', '125', '130', '135', '140')):
  print(f'-- Input mass scan for {proc_name}')
  vals = {}
  for m in masses:
    total = 0.
    found = False
    for b in bins:
      val = GetInputIntegral(file_cache, b, proc_name, signal_mass=m)
      if val is not None:
        total += val
        found = True
    if found:
      vals[m] = total
      print(f'   m={m}: {total:.1f}')
    else:
      print(f'   m={m}: missing')

  if '125' in vals and vals['125'] != 0.:
    for m in masses:
      if m in vals:
        print(f'   ratio {m}/125 = {vals[m]/vals["125"]:.3f}')


def BuildCombinedInputHist(file_cache, bins, proc_name, signal_mass, ref=None, common_bins=None):
  hs = []
  for b in bins:
    h = GetInputHist(file_cache, b, proc_name, signal_mass)
    if not h:
      continue
    if ref is not None:
      h = RestoreBinning(h, ref)
    if common_bins is not None:
      h = h.Rebin(len(common_bins)-1, '', common_bins)
    hs.append(h.Clone())

  if len(hs) == 0:
    return None

  out = hs[0].Clone(f'{proc_name}{signal_mass}_combined')
  for h in hs[1:]:
    out.Add(h)
  return out


def SaveMassShapeComparison(file_cache, bins, proc_name, out_path,
                            masses=('120', '125', '130', '135', '140'),
                            ref=None, common_bins=None,
                            normalize=False,
                            x_min=None, x_max=None,
                            y_min=None, y_max=None):
  hs = []
  for m in masses:
    h = BuildCombinedInputHist(file_cache, bins, proc_name, m, ref=ref, common_bins=common_bins)
    if h:
      hs.append((m, h))

  if len(hs) == 0:
    return

  c = ROOT.TCanvas(f'c_{SafeName(proc_name)}_{SafeName(os.path.basename(out_path))}', '', 800, 600)
  leg = ROOT.TLegend(0.62, 0.70, 0.89, 0.89)
  leg.SetBorderSize(0)
  leg.SetFillStyle(0)

  colors = [ROOT.kBlack, ROOT.kRed + 1, ROOT.kBlue + 1, ROOT.kGreen + 2]

  ymax = 0.
  draw_hists = []
  for i, (m, h) in enumerate(hs):
    hh = h.Clone(f'{h.GetName()}_draw_{m}')
    hh.SetDirectory(0)
    if normalize and hh.Integral() > 0:
      hh.Scale(1. / hh.Integral())
    hh.SetLineColor(colors[i % len(colors)])
    hh.SetLineWidth(2)
    hh.SetMarkerSize(0)
    hh.SetStats(0)
    ymax = max(ymax, hh.GetMaximum())
    draw_hists.append((m, hh))

  first = True
  for m, h in draw_hists:
    h.SetTitle(f'{proc_name} mass comparison')
    h.GetXaxis().SetTitle('Observable bin')
    h.GetYaxis().SetTitle('A.U.' if normalize else 'Events')

    if x_min is not None or x_max is not None:
      xmin = x_min if x_min is not None else h.GetXaxis().GetXmin()
      xmax = x_max if x_max is not None else h.GetXaxis().GetXmax()
      h.GetXaxis().SetRangeUser(xmin, xmax)

    if y_min is not None:
      h.SetMinimum(y_min)
    else:
      h.SetMinimum(0.)

    if y_max is not None:
      h.SetMaximum(y_max)
    else:
      h.SetMaximum(1.25 * ymax if ymax > 0 else 1.)

    h.Draw('HIST' if first else 'HIST SAME')
    leg.AddEntry(h, f'{proc_name}{m}', 'l')
    first = False

  leg.Draw()
  c.SaveAs(out_path)
  c.Close()

if args.postfit:
  # print postfit yields and uncertainties
  print('\n------------------------------')
  print('Getting postfit shapes and uncertainties:')
  print('------------------------------')

  f_fit = ROOT.TFile(args.fitresult.split(':')[0])
  res = f_fit.Get(args.fitresult.split(':')[1])

  cmb.UpdateParameters(res) # need this line to get postfit results!!
  params = res.floatParsFinal()
  # store a backup of the fit result before we modified the parameters
  res_backup = res.clone()
else: 
  # print prefit yields and uncertainties
  # this is not the most efficient way to make the prefit plots as it still involves sampling the covariance matrix
  print('\n------------------------------')
  print('Getting prefit shapes and uncertainties:')
  print('------------------------------')


samples=500 


if args.freeze:
  freeze_vec = args.freeze.split(',')
  for item in freeze_vec:
    parts=item.split('=')
    if len(parts) == 1:
      par = cmb.GetParameter(parts[0])
      if par: par.set_frozen(True)
      else: print(f"Requested variable to freeze, {parts[0]}, does not exist in workspace")
    else: 
      if len(parts) == 2: 
        par = cmb.GetParameter(parts[0])
        if par:
          par.set_val(float(parts[1]))
          par.set_frozen(True)
        else: print(f"Requested variable to freeze, {parts[0]}, does not exist in workspace")

if args.plot_dir:
  os.makedirs(args.plot_dir, exist_ok=True)


for bin in bins_grouped:

  if True in ['htt_em_2' in b for b in bin]: continue

  if args.bin_match and True not in [args.bin_match in b for b in bin]: continue

  print('\n------------------------------')
  print('bin = %s' % bin)
  print('------------------------------')

  dirname=ReplaceEraAndChannels(bin[0])
  # new hacky lines just to name the directories a bit more descriptive
  if '__' in dirname and 'em' in dirname and args.cats: dirname=dirname.replace('__','_'+cats[0])
  if dirname[-1] == "_": dirname=dirname[:-1]
  if '__' in dirname and 'mt' in args.channels: dirname=dirname.replace('__','_lt_')
  if not fout.GetDirectory(dirname):
    fout.mkdir(dirname)
  print('directory name = ', dirname)

  cmb_bin = cmb.cp().bin(bin)

  bins=cmb_bin.cp().bin_set()
 
  # first get shapes for data 
  shapes_data = []
  for b in bins:
    shape = cmb_bin.cp().bin([b]).GetObservedShape()
    if args.datacard: 
      ref = cmb_card.cp().bin([b]).GetObservedShape();
      shape = RestoreBinning(shape, ref)
    shapes_data.append(shape.Clone())
  

  # now need to determine common bin boundaries

  common_bins = []
  for s in shapes_data:
    bnew = GetBinnings(s)
    if len(common_bins) ==0: common_bins = bnew
    else: common_bins = list(set(common_bins).intersection(bnew))

  common_bins.sort()
  common_bins = array.array('d',common_bins)
  common_bins = np.array(common_bins)
  print('common binning  = ', common_bins)

  # rebin data to common bins:
  shapes_data = [s.Rebin(len(common_bins)-1, '', common_bins) for s in shapes_data]


  # add contributions together and write them to the file
  for s in shapes_data[1:]: shapes_data[0].Add(s) 
  fout.cd(dirname)
  shapes_data[0].SetName('data_obs')
  shapes_data[0].Write('data_obs')

  # now get shapes for individual processes (note no uncertainties currently added for these)

  procs = cmb_bin.cp().process_set()
  shapes_procs = {}
  shapes_procs_unc = {}
  input_file_cache = {}
  for p in procs:
    shapes_procs[p] = []
    shapes_procs_unc[p] = []
    for b in bins:
      shape_unc = cmb_bin.cp().bin([b]).process([p]).GetShapeWithUncertainty()
      if args.datacard: shape_unc = RestoreBinning(shape_unc, ref)
      shape_unc = shape_unc.Rebin(len(common_bins)-1, '', common_bins)
      shapes_procs_unc[p].append(shape_unc.Clone())

      shape = shape_unc.Clone()
      shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
      shapes_procs[p].append(shape.Clone())

    # add contributions together and write them to the file
    for s in shapes_procs[p][1:]: shapes_procs[p][0].Add(s)
    for s in shapes_procs_unc[p][1:]: shapes_procs_unc[p][0].Add(s)
    proc_cp = cmb_bin.cp().process([p])
    rate = proc_cp.GetRate()
    err = proc_cp.GetUncertainty()

    input_rate = 0.
    found_input = False
    for b in bins:
      val = GetInputIntegral(input_file_cache, b, p)
      if val is not None:
        input_rate += val
        found_input = True

    if rate != 0.:
      print(f'{p} Rate = {rate:.1f} +/- {err:.1f} ({err/rate:.3f})')
    else:
      print(f'{p} Rate = {rate:.1f} +/- {err:.1f}')
    if found_input:
      print(f'Input {p} = {input_rate:.1f}')
      if p in ['ggH_MSSM_htt', 'bbH_MSSM_htt']:
        PrintMassScan(input_file_cache, bins, p, masses=('120', '125', '130', '135', '140'))

    fout.cd(dirname)
    shapes_procs[p][0].SetName(p)
    shapes_procs[p][0].Write(p)
    shapes_procs_unc[p][0].SetName(f'{p}_unc')
    shapes_procs_unc[p][0].Write(f'{p}_unc')


  # get total signal (note no uncertainties currently added for this)

  shapes_sig = []
  for b in bins:
    shape = cmb_bin.cp().bin([b]).signals().GetShape()
    if args.datacard: shape = RestoreBinning(shape, ref)
    shape = shape.Rebin(len(common_bins)-1, '', common_bins)
    shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
    shapes_sig.append(shape.Clone())

  # add contributions together and write them to the file
  for s in shapes_sig[1:]: shapes_sig[0].Add(s)
  fout.cd(dirname)
  shapes_sig[0].SetName('TotalSig')
  shapes_sig[0].Write('TotalSig')

  print('TotalSig = ', shapes_sig[0].Integral())
  sig_input_total = 0.
  found_sig_input = False
  for b in bins:
    for p_sig in ['ggH_MSSM_htt', 'bbH_MSSM_htt']:
      val = GetInputIntegral(input_file_cache, b, p_sig)
      if val is not None:
        sig_input_total += val
        found_sig_input = True
  if found_sig_input:
    print(f'Input TotalSig (m=125 templates) = {sig_input_total:.1f}')

  # get total signal+background (note no uncertainties currently added for this)

  shapes_tot = []
  for b in bins:
    shape = cmb_bin.cp().bin([b]).GetShape()
    print(b, shape.Integral())
    if args.datacard: shape = RestoreBinning(shape, ref)
    shape = shape.Rebin(len(common_bins)-1, '', common_bins)
    shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
    shapes_tot.append(shape.Clone())

  # add contributions together and write them to the file
  for s in shapes_tot[1:]: shapes_tot[0].Add(s)
  fout.cd(dirname)
  shapes_tot[0].SetName('TotalProcs')
  shapes_tot[0].Write('TotalProcs')

  # get total background and propper uncertainty 

  # first get nominal histogram
  shapes_bkg = []
  for b in bins:
    shape = cmb_bin.cp().bin([b]).backgrounds().GetShapeWithUncertainty()
    if args.datacard: shape = RestoreBinning(shape, ref)
    shape = shape.Rebin(len(common_bins)-1, '', common_bins)
    shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
    shapes_bkg.append(shape.Clone())

  # add contributions together and write them to the file
  for s in shapes_bkg[1:]: shapes_bkg[0].Add(s)

  rate = cmb_bin.cp().backgrounds().GetRate() 

  # now get uncertainties

  # zero errors on total background histogram
  shapes_bkg[0] = ZeroErrors(shapes_bkg[0])

  if not args.postfit:
#    # note prefit plots not fully supported
#    # they will work fine as long as no rebinning is performed
#    # if you rebin the uncertainties for merged bins will be treated as being uncorrelated and summed in quadrature which will not be correct in general

    shape = cmb_bin.cp().bin(bins).backgrounds().GetShapeWithUncertainty()
    if args.datacard: shape = RestoreBinning(shape, ref)
    shape = shape.Rebin(len(common_bins)-1, '', common_bins)
    shapes_bkg[0]=shape.Clone()

    print('!!!!', shapes_bkg[0].Integral())
    err = cmb_bin.cp().bin(bins).backgrounds().GetUncertainty()
    print(f'Total Bkg = {rate:.1f} +/- {err:.1f} ({err/rate:.3f})')

  # get total post error on background
  if args.postfit:
  
    rands = res.randomizePars()
    p_vec = [None]*len(rands)
  
    for n in range(0,len(rands)):
      p_vec[n] = cmb_bin.cp().bin([b]).GetParameter(rands[n].GetName())
  
    ave=0.

    for x in range(0, samples):
  
      res.randomizePars()
      for n in range(0,len(rands)):
        if p_vec[n]: p_vec[n].set_val(rands[n].getVal())
  
      shapes_bkg_var = []
      for b in bins:
        shape = cmb_bin.cp().bin([b]).backgrounds().GetShape()
        if args.datacard: shape = RestoreBinning(shape, ref)
        shape = shape.Rebin(len(common_bins)-1, '', common_bins)
        shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
        shapes_bkg_var.append(shape.Clone())
  
      for s in shapes_bkg_var[1:]: shapes_bkg_var[0].Add(s)
      ave+=abs(shapes_bkg_var[0].Integral()-shapes_bkg[0].Integral())**2
  
  
      for i in range(1, shapes_bkg[0].GetNbinsX()+1):
        err = abs(shapes_bkg_var[0].GetBinContent(i)-shapes_bkg[0].GetBinContent(i))
        shapes_bkg[0].SetBinError(i, err*err + shapes_bkg[0].GetBinError(i))
  
    # now need to set parameters back to nominal values
    cmb.UpdateParameters(res_backup)
  
    ave = (ave/float(samples))**.5
    print(
      f'Total Bkg = {shapes_bkg[0].Integral():.1f} +/- '
      f'{ave:.1f} ({ave/shapes_bkg[0].Integral():.3f})'
    )
  
    # to get the final error we need to take the sqrt and divide by the number of samples
    for i in range(1, shapes_bkg[0].GetNbinsX()+1):
      err_total = (shapes_bkg[0].GetBinError(i)/float(samples))**.5
      shapes_bkg[0].SetBinError(i,err_total)

  # now save our total background template with correct uncertainties
  fout.cd(dirname)
  shapes_bkg[0].SetName('TotalBkg')
  shapes_bkg[0].Write('TotalBkg')

  if args.plot_dir:
    bin_plot_dir = os.path.join(args.plot_dir, SafeName(dirname))
    os.makedirs(bin_plot_dir, exist_ok=True)
    for p_sig in ['ggH_MSSM_htt', 'bbH_MSSM_htt']:
      raw_plot_path = os.path.join(
        bin_plot_dir,
        f'massscan_{SafeName(p_sig)}_raw.png'
      )
      norm_plot_path = os.path.join(
        bin_plot_dir,
        f'massscan_{SafeName(p_sig)}_norm.png'
      )

      SaveMassShapeComparison(
        input_file_cache,
        bins,
        p_sig,
        raw_plot_path,
        masses=('120', '125', '130', '135', '140'),
        common_bins=common_bins,
        normalize=False,
        x_min=0,
        x_max=400
      )
      SaveMassShapeComparison(
        input_file_cache,
        bins,
        p_sig,
        norm_plot_path,
        masses=('120', '125', '130', '135', '140'),
        common_bins=common_bins,
        normalize=True,
        x_min=0,
        x_max=400
      )

    total_plot_path = os.path.join(bin_plot_dir, 'total_prefit.png')
    SaveTotalPlot(
      shapes_data[0],
      shapes_bkg[0],
      shapes_sig[0],
      total_plot_path,
      f'{dirname} total'
    )

    proc_plot_count = 0
    for p in sorted(shapes_procs_unc.keys()):
      if proc_plot_count >= args.max_proc_plots:
        break
      if shapes_procs_unc[p][0].Integral() <= 0.:
        continue
      proc_plot_path = os.path.join(
        bin_plot_dir,
        f'unc_{SafeName(p)}.png'
      )
      SaveProcUncPlot(
        shapes_procs_unc[p][0],
        proc_plot_path,
        f'{dirname} {p} relative uncertainty'
      )
      proc_plot_count += 1


fout.Close()
