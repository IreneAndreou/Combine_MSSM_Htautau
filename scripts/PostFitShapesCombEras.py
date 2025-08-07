import numpy as np
import array
from numpy import arange
import ROOT; ROOT.PyConfig.IgnoreCommandLineOptions = True
import CombineHarvester.CombineTools.ch as ch
import sys
import argparse
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
  res = ref
  res.Reset()
  for x in range(1,res.GetNbinsX()+1): 
    res.SetBinContent(x, src.GetBinContent(x))
    res.SetBinError(x, src.GetBinError(x))
  
  return res

def ZeroErrors(src):
  for x in range(1,src.GetNbinsX()+1):
    src.SetBinError(x, 0.)
  return src

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
  for p in procs:
    shapes_procs[p] = []
    for b in bins:
      shape = cmb_bin.cp().bin([b]).process([p]).GetShape()
      shape = cmb_bin.cp().bin([b]).process([p]).GetShapeWithUncertainty()
      rate = cmb_bin.cp().process([p]).backgrounds().GetRate() 
      err = cmb_bin.cp().bin(bins).backgrounds().GetUncertainty()
      if p == "ggH_MSSM_htt":
        print(f'{p} Bkg = {rate}.1f +/- {err}.1f')
        input_root_file = "/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root"
        # Get input yields to compare
        input_file = ROOT.TFile(input_root_file)
        input_shape = input_file.Get(f'mt_nobtag/{p}300')
        if input_shape:
          print(f'Input {p} Bkg = {input_shape.Integral()}.1f')
      else:
        print(f'{p} Bkg = {rate}.1f +/- {err}.1f ({err/rate}.3f)')
        input_root_file = "/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root"
        # Get input yields to compare
        input_file = ROOT.TFile(input_root_file)
        input_shape = input_file.Get(f'mt_nobtag/{p}')
        if input_shape:
          print(f'Input {p} Bkg = {input_shape.Integral()}.1f')



      if args.datacard: shape = RestoreBinning(shape, ref)
      shape = shape.Rebin(len(common_bins)-1, '', common_bins)
      shape = ZeroErrors(shape) # zero errors to avoid confusion about what they represent
      shapes_procs[p].append(shape.Clone())

    # add contributions together and write them to the file
    for s in shapes_procs[p][1:]: shapes_procs[p][0].Add(s)
    fout.cd(dirname)
    shapes_procs[p][0].SetName(p)
    shapes_procs[p][0].Write(p)


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
  input_root_file = "/vols/cms/ia2318/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF/shapes/mssm.datacard.mt_tot.mt.Run3_2022EE.nobtag.root"
  # Get input yields to compare
  input_file = ROOT.TFile(input_root_file)
  input_shape = input_file.Get(f'mt_nobtag/ggH_MSSM_htt300')
  if input_shape:
    print(f'Input {p} Bkg = {input_shape.Integral()}.1f')

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
    print(f'Total Bkg = {rate}.1f +/- {err}.1f ({err/rate}.3f)')

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
    print(f'Total Bkg = {shapes_bkg[0].Integral()}.1f +/- {ave}.1f ({ave/shapes_bkg[0].Integral()}.3f)')
  
    # to get the final error we need to take the sqrt and divide by the number of samples
    for i in range(1, shapes_bkg[0].GetNbinsX()+1):
      err_total = (shapes_bkg[0].GetBinError(i)/float(samples))**.5
      shapes_bkg[0].SetBinError(i,err_total)

  # now save our total background template with correct uncertainties
  fout.cd(dirname)
  shapes_bkg[0].SetName('TotalBkg')
  shapes_bkg[0].Write('TotalBkg')


fout.Close()
