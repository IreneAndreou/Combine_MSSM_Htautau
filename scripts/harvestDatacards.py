import ROOT; ROOT.PyConfig.IgnoreCommandLineOptions = True
import CombineHarvester.CombineTools.ch as ch
from CombineHarvester.CombineTools.ch import CombineHarvester, CardWriter, SetStandardBinNames, AutoRebin
from argparse import ArgumentParser
import yaml
#import os

# specify with eras to fit or combine all eras together by specifying "all"
valid_eras = ['2016_preVFP', '2016_postVFP', '2017', '2018', 'UL', '2022_preEE', '2022_postEE', '2022']

# HI
description = '''This script makes datacards with CombineHarvester for performing tau ID SF measurments.'''
parser = ArgumentParser(prog="harvesterDatacards",description=description,epilog="Success!")
parser.add_argument('-c', '--config', dest='config', type=str, default='config/harvestDatacards.yml', action='store', help="set config file")
parser.add_argument('-o', '--output_folder', dest='output_folder', type=str, default='', help="set output folder name")
parser.add_argument('--dm-bins', dest='dm_bins', default=False, action='store_true', help="if specified then the mu+tauh channel fits are also split by tau decay-mode")
parser.add_argument('--wp', dest='wp', default='medium', help="The vs jet WP to measure SFs for")
parser.add_argument('--tightVsEle', dest='tightVsEle', default=False, action='store_true', help="if specified then use the tight WP of the vs electron ID, otherwise the vvloose WP is used")
parser.add_argument('--useCRs', dest='useCRs', default=False, action='store_true', help="if specified then add seperate QCD and W rate params for each pT bin and use high mT and lepton aiso CRs to constrain them")
args = parser.parse_args()
dm_bins=args.dm_bins
tightVsEle=args.tightVsEle
wp=args.wp
useCRs=args.useCRs

vsele_wp = 'VVLoose'
if tightVsEle: vsele_wp='Tight'
print('Making datacards for %(wp)s VsJet WP and %(vsele_wp)s VsEle WP' % vars())

with open(args.config, 'r') as file:
   setup = yaml.safe_load(file)

output_folder = setup["output_folder"]
era_tag = setup["eras"]

if args.output_folder: output_folder = args.output_folder

if era_tag == 'UL': eras = ['2016_preVFP', '2016_postVFP', '2017', '2018'] # add other eras later
if era_tag == '2022': eras = ['2022_preEE', '2022_postEE']
else: eras = era_tag.split(',')

for e in eras: 
  if e not in valid_eras: raise Exception("ERROR: one or more of the eras you specified is not supported, available options are: %s" % ",".join(valid_eras)) 

def green(string,**kwargs):
    '''Displays text in green text inside a black background'''
    return kwargs.get('pre',"")+"\x1b[0;32;40m%s\033[0m"%string

def NegativeBins(p):
  '''Replaces negative bins in hists with 0'''
  hist = p.shape()
  has_negative = False
  for i in range(1,hist.GetNbinsX()+1):
    if hist.GetBinContent(i) < 0:
       has_negative = True
       print("Process: ",p.process()," has negative bins.")
  if (has_negative):
    for i in range(1,hist.GetNbinsX()+1):
       if hist.GetBinContent(i) < 0:
          hist.SetBinContent(i,0)
  p.set_shape(hist,False)

def NegativeYields(p):
  '''If process has negative yield then set to 0'''
  if (p.process() == "QCD"):
     if p.rate()<0:
        hist = p.shape()
        #error = 0.0
        for i in range(1,hist.GetNbinsX()+1):
           bin_i = hist.GetBinContent(i)
           error = hist.GetBinError(i)
           bins = [hist.GetXaxis().GetBinLowEdge(i), hist.GetXaxis().GetBinUpEdge(i)]
           print("Process: ",p.process()," has negative yields.", p.channel(), p.bin(), p.rate(), bins, bin_i, error) 
        p.set_rate(0.)

channels = ['zmm','mt']
bkg_procs = {}
# procs for the dimuon channel
bkg_procs['zmm'] = ['ZL', 'ZTT','VVL', 'VVJ', 'TTL', 'TTJ','W','ZJ']
# procs for the mu+tauh channel
bkg_procs['mt'] = ['ZL', 'ZJ', 'W', 'VVJ', 'TTJ', 'QCD']

# signal processes are defined as any with genuine hadronic taus in the mt channel
sig_procs = ['ZTT','VVT','TTT']
cats = {}
cats['zmm'] = [(0, 'zmm_inclusive')]

if tightVsEle: cat_extra='_tightVsEle'
else: cat_extra=''


cr_bins=[]
qcd_cr_bins=[]

if dm_bins:
  cats['mt'] = []
  for i, dm in enumerate([0,1,10,11]):
    cats['mt'] += [
     ((i+1)*100+1,  'mt_dm%i_mTLt65%s_pT_20_to_25'   % (dm,cat_extra)),
     ((i+1)*100+2,  'mt_dm%i_mTLt65%s_pT_25_to_30'   % (dm,cat_extra)),
     ((i+1)*100+3,  'mt_dm%i_mTLt65%s_pT_30_to_35'   % (dm,cat_extra)),
     ((i+1)*100+4,  'mt_dm%i_mTLt65%s_pT_35_to_40'   % (dm,cat_extra)),
     ((i+1)*100+5,  'mt_dm%i_mTLt65%s_pT_40_to_50'   % (dm,cat_extra)),
     ((i+1)*100+6,  'mt_dm%i_mTLt65%s_pT_50_to_60'   % (dm,cat_extra)),
     ((i+1)*100+7,  'mt_dm%i_mTLt65%s_pT_60_to_80'   % (dm,cat_extra)),
     ((i+1)*100+8,  'mt_dm%i_mTLt65%s_pT_80_to_100'  % (dm,cat_extra)),
     ((i+1)*100+9,  'mt_dm%i_mTLt65%s_pT_100_to_200' % (dm,cat_extra)),
    ]

    if useCRs:
      cats['mt'] += [
       ((i+1)*100+11,  'mt_dm%i_mTGt70%s_pT_20_to_25'   % (dm,cat_extra)),
       ((i+1)*100+12,  'mt_dm%i_mTGt70%s_pT_25_to_30'   % (dm,cat_extra)),
       ((i+1)*100+13,  'mt_dm%i_mTGt70%s_pT_30_to_35'   % (dm,cat_extra)),
       ((i+1)*100+14,  'mt_dm%i_mTGt70%s_pT_35_to_40'   % (dm,cat_extra)),
       ((i+1)*100+15,  'mt_dm%i_mTGt70%s_pT_40_to_50'   % (dm,cat_extra)),
       ((i+1)*100+16,  'mt_dm%i_mTGt70%s_pT_50_to_60'   % (dm,cat_extra)),
       ((i+1)*100+17,  'mt_dm%i_mTGt70%s_pT_60_to_80'   % (dm,cat_extra)),
       ((i+1)*100+18,  'mt_dm%i_mTGt70%s_pT_80_to_100'  % (dm,cat_extra)),
       ((i+1)*100+19,  'mt_dm%i_mTGt70%s_pT_100_to_200' % (dm,cat_extra)),
       ((i+1)*100+21,  'mt_dm%i_mTLt65%s_aiso_pT_20_to_25'   % (dm,cat_extra)),
       ((i+1)*100+22,  'mt_dm%i_mTLt65%s_aiso_pT_25_to_30'   % (dm,cat_extra)),
       ((i+1)*100+23,  'mt_dm%i_mTLt65%s_aiso_pT_30_to_35'   % (dm,cat_extra)),
       ((i+1)*100+24,  'mt_dm%i_mTLt65%s_aiso_pT_35_to_40'   % (dm,cat_extra)),
       ((i+1)*100+25,  'mt_dm%i_mTLt65%s_aiso_pT_40_to_50'   % (dm,cat_extra)),
       ((i+1)*100+26,  'mt_dm%i_mTLt65%s_aiso_pT_50_to_60'   % (dm,cat_extra)),
       ((i+1)*100+27,  'mt_dm%i_mTLt65%s_aiso_pT_60_to_80'   % (dm,cat_extra)),
       ((i+1)*100+28,  'mt_dm%i_mTLt65%s_aiso_pT_80_to_100'  % (dm,cat_extra)),
       ((i+1)*100+29,  'mt_dm%i_mTLt65%s_aiso_pT_100_to_200' % (dm,cat_extra)),
    ]
 
      cr_bins+=[(i+1)*100+j+10 for j in range(1,10) ] 
      cr_bins+=[(i+1)*100+j+20 for j in range(1,10) ] 
      qcd_cr_bins+=[(i+1)*100+j+20 for j in range(1,10) ] 

    
else:

  cats['mt'] = [
               (1, 'mt_inclusive_mTLt65%s_pT_20_to_25'   % cat_extra),
               (2, 'mt_inclusive_mTLt65%s_pT_25_to_30'   % cat_extra),
               (3, 'mt_inclusive_mTLt65%s_pT_30_to_35'   % cat_extra),
               (4, 'mt_inclusive_mTLt65%s_pT_35_to_40'   % cat_extra),
               (5, 'mt_inclusive_mTLt65%s_pT_40_to_50'   % cat_extra),
               (6, 'mt_inclusive_mTLt65%s_pT_50_to_60'   % cat_extra),
               (7, 'mt_inclusive_mTLt65%s_pT_60_to_80'   % cat_extra),
               (8, 'mt_inclusive_mTLt65%s_pT_80_to_100'  % cat_extra),
               (9, 'mt_inclusive_mTLt65%s_pT_100_to_200' % cat_extra), 
  ]
  if useCRs:
    cats['mt'] += [
                 (11, 'mt_inclusive_mTGt70%s_pT_20_to_25'   % cat_extra),
                 (12, 'mt_inclusive_mTGt70%s_pT_25_to_30'   % cat_extra),
                 (13, 'mt_inclusive_mTGt70%s_pT_30_to_35'   % cat_extra),
                 (14, 'mt_inclusive_mTGt70%s_pT_35_to_40'   % cat_extra),
                 (15, 'mt_inclusive_mTGt70%s_pT_40_to_50'   % cat_extra),
                 (16, 'mt_inclusive_mTGt70%s_pT_50_to_60'   % cat_extra),
                 (17, 'mt_inclusive_mTGt70%s_pT_60_to_80'   % cat_extra),
                 (18, 'mt_inclusive_mTGt70%s_pT_80_to_100'  % cat_extra),
                 (19, 'mt_inclusive_mTGt70%s_pT_100_to_200' % cat_extra),
  
                 (21, 'mt_inclusive_mTLt65%s_aiso_pT_20_to_25'   % cat_extra),
                 (22, 'mt_inclusive_mTLt65%s_aiso_pT_25_to_30'   % cat_extra),
                 (23, 'mt_inclusive_mTLt65%s_aiso_pT_30_to_35'   % cat_extra),
                 (24, 'mt_inclusive_mTLt65%s_aiso_pT_35_to_40'   % cat_extra),
                 (25, 'mt_inclusive_mTLt65%s_aiso_pT_40_to_50'   % cat_extra),
                 (26, 'mt_inclusive_mTLt65%s_aiso_pT_50_to_60'   % cat_extra),
                 (27, 'mt_inclusive_mTLt65%s_aiso_pT_60_to_80'   % cat_extra),
                 (28, 'mt_inclusive_mTLt65%s_aiso_pT_80_to_100'  % cat_extra),
                 (29, 'mt_inclusive_mTLt65%s_aiso_pT_100_to_200' % cat_extra),
    ]
    cr_bins+=range(11,20)+range(21,30)
    qcd_cr_bins+=range(21,30)

#for i in range(0,len(cats['mt'])):
#  cats['mt'][i]=list(cats['mt'][i])
#  cats['mt'][i][1] = cats['mt'][i][1].replace('Lt65','Lt60')
#  cats['mt'][i]=tuple(cats['mt'][i])

# Create an empty CombineHarvester instance
cb = CombineHarvester()

# Add processes and observations
for chn in channels:
  for era in eras:
    # Adding Data,Signal Processes and Background processes to the harvester instance
    cb.AddObservations(['*'], ['ztt'], [era], [chn], cats[chn])
    cb.AddProcesses(['*'], ['ztt'], [era], [chn], bkg_procs[chn], cats[chn], False)
    if chn == 'mt': cb.AddProcesses(['*'], ['ztt'], [era], [chn], sig_procs, cats[chn], False)


# Add systematics

inclusive_bins = [1,2,3,4,5,6,7,8,9, 11,12,13,14,15,16,17,18,19, 21,22,23,24,25,26,27,28,29]
dm0_bins = [101,102,103,104,105,106,107,108,109, 111,112,113,114,115,116,117,118,119, 121,122,123,124,125,126,127,128,129]
dm1_bins = [201,202,203,204,205,206,207,208,209, 211,212,213,214,215,216,217,218,219, 221,222,223,224,225,226,227,228,229]
dm10_bins = [301,302,303,304,305,306,307,308,309, 311,312,313,314,315,316,317,318,319, 321,322,323,324,325,326,327,328,329]
dm11_bins = [401,402,403,404,405,406,407,408,409, 411,412,413,414,415,416,417,418,419, 421,422,423,424,425,426,427,428,429]

# muon selection efficiency for second muon in di-muon dataset
# better to shift the muon efficiency to the mt channel processes (will effectivly shift these in the opposite direction)
cb.cp().channel(['mt']).process(['ZTT','TTT','TTL','VVT','VVL']).AddSyst(cb, "CMS_eff_m", "lnN", ch.SystMap()(0.98))

# for jet->mu in dimuon data the second muon is a fake so add a seperate uncertainty for this - as this uncertainty is so large we don't need to add another uncertainty for the cross section or the lumi
cb.cp().channel(['zmm']).process(['W','TTJ','VVJ','ZJ']).AddSyst(cb, "CMS_j_fake_m", "lnN", ch.SystMap()(1.3))

# uncertainty on VV cross-section - set to 10% to cover missing higher order terms which are typically this large
cb.cp().process(['VVL','VVJ','VVT']).AddSyst(cb, "CMS_htt_vvXsec", "lnN", ch.SystMap()(1.1))

# uncertainty on ttbar cross-section - set to 6% to cover missing higher orders
cb.cp().process(['TTL','TTJ','TTT']).AddSyst(cb, "CMS_htt_tjXsec", "lnN", ch.SystMap()(1.06))

# uncertainty on the DY cross section does not affect Z because the rate parameter includes this effect but it will inversely affect the VV and TT since we assumed these scaled with the same rate parameter as the DY
cb.cp().process(['TTL','TTT','VVL','VVT']).AddSyst(cb, "CMS_htt_zXsec", "lnN", ch.SystMap()(0.96))

# DY shape uncertainty from re-weighting pT-mass to data (100% variation taked as the uncertainty)
cb.cp().process(['ZTT','ZL','ZJ']).AddSyst(cb, "CMS_htt_dyShape", "shape", ch.SystMap()(1.0))
# ttbar shape uncertainty from re-weighting pT-mass to data (100% variation taked as the uncertainty)
cb.cp().process(['TTL','TTJ','TTT']).AddSyst(cb, "CMS_htt_ttbarShape", "shape", ch.SystMap()(1.0))

# TES uncertainties
cb.cp().channel(['mt']).process(['ZTT','TTT','TTL','VVT','VVL']).bin_id(dm0_bins+inclusive_bins).AddSyst(cb, "CMS_scale_t_1prong_$ERA","shape", ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(['ZTT','TTT','TTL','VVT','VVL']).bin_id(dm1_bins+inclusive_bins).AddSyst(cb, "CMS_scale_t_1prong1pizero_$ERA","shape", ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(['ZTT','TTT','TTL','VVT','VVL']).bin_id(dm10_bins+inclusive_bins).AddSyst(cb, "CMS_scale_t_3prong_$ERA", "shape", ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(['ZTT','TTT','TTL','VVT','VVL']).bin_id(dm11_bins+inclusive_bins).AddSyst(cb, "CMS_scale_t_3prong1pizero_$ERA", "shape", ch.SystMap()(1.0))

# mu->tauh energy scale split by decay mode (might want to eventually make sure these don't get added for dm 10 and 11)
cb.cp().channel(['mt']).process(['ZL']).bin_id(dm0_bins+inclusive_bins).AddSyst(cb, "CMS_ZLShape_$CHANNEL_1prong_$ERA", "shape", ch.SystMap()(1.00))

cb.cp().channel(['mt']).process(['ZL']).bin_id(dm1_bins+inclusive_bins).AddSyst(cb, "CMS_ZLShape_$CHANNEL_1prong1pizero_$ERA", "shape", ch.SystMap()(1.00))

#MET related uncertainties
cb.cp().channel(['mt']).process(['QCD'],False).AddSyst(cb, "CMS_res_j_$ERA", "shape", ch.SystMap()(1.00))
cb.cp().channel(['mt']).process(['QCD'],False).AddSyst(cb, "CMS_scale_met_unclustered_$ERA", "shape", ch.SystMap()(1.00))

# single JES parameter
#cb.cp().channel(['mt']).process(['QCD'],False).AddSyst(cb, "CMS_scale_j_$ERA", "shape", ch.SystMap()(1.00))
# split JES into regrouped uncertainties
jes_uncert_names = ["Absolute", "Absolute_year", "BBEC1", "BBEC1_year",
            "EC2", "EC2_year", "FlavorQCD", "HF", "HF_year",
            "RelativeBal", "RelativeSample_year"]

for u in jes_uncert_names:
  if 'year' not in u:
    cb.cp().channel(['mt']).process(['QCD'],False).AddSyst(cb, "CMS_scale_j_%(u)s" % vars(), "shape", ch.SystMap()(1.00))
  else: 
    for era in eras: cb.cp().channel(['mt']).era([era]).process(['QCD'],False).AddSyst(cb, "CMS_scale_j_%s" % u.replace('year',era.split('_')[0]), "shape", ch.SystMap()(1.00))


# jet-tau fake-rate in MC - not for W as this will float in the fit
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).bin_id(inclusive_bins).AddSyst(cb, "CMS_j_fake_t", "lnN", ch.SystMap()(1.2))
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).bin_id(dm0_bins).AddSyst(cb, "CMS_j_fake_t_DM0", "lnN", ch.SystMap()(1.2))
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).bin_id(dm1_bins).AddSyst(cb, "CMS_j_fake_t_DM1", "lnN", ch.SystMap()(1.2))
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).bin_id(dm10_bins).AddSyst(cb, "CMS_j_fake_t_DM10", "lnN", ch.SystMap()(1.2))
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).bin_id(dm11_bins).AddSyst(cb, "CMS_j_fake_t_DM11", "lnN", ch.SystMap()(1.2))
# add a part decoupled by pT/DM bin
cb.cp().channel(['mt']).process(['TTJ','VVJ','ZJ']).AddSyst(cb, "CMS_j_fake_t_$BIN_$ERA", "lnN", ch.SystMap()(1.2))


cb.cp().channel(['mt']).process(['ZL']).bin_id(inclusive_bins).AddSyst(cb, "CMS_l_fake_t", "lnN", ch.SystMap()(1.3))
cb.cp().channel(['mt']).process(['ZL']).bin_id(dm0_bins).AddSyst(cb, "CMS_l_fake_t_DM0", "lnN", ch.SystMap()(1.3))
cb.cp().channel(['mt']).process(['ZL']).bin_id(dm0_bins).AddSyst(cb, "CMS_l_fake_t_DM1", "lnN", ch.SystMap()(1.3))
cb.cp().channel(['mt']).process(['ZL']).bin_id(dm10_bins).AddSyst(cb, "CMS_l_fake_t_DM10", "lnN", ch.SystMap()(1.3))
cb.cp().channel(['mt']).process(['ZL']).bin_id(dm11_bins).AddSyst(cb, "CMS_l_fake_t_DM11", "lnN", ch.SystMap()(1.3))
# add a part decoupled by pT/DM bin
cb.cp().channel(['mt']).process(['ZL']).AddSyst(cb, "CMS_l_fake_t_$BIN_$ERA", "lnN", ch.SystMap()(1.3))

# now add unconstrained rate parameters

# a common rate parameter that scales all MC processes in the di-muon channel with 2 genuine muons and the the ZTT, TTT, and VVT in the mu+tauh channel
cb.cp().channel(['zmm']).process(['ZTT','VVT','VVL','TTT','TTL','ZL']).AddSyst(cb, "rate_DY_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT","VVT",'VVL',"TTT",'TTL']).AddSyst(cb, "rate_DY_$ERA","rateParam",ch.SystMap()(1.0))

# now add the POIs
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([1,11,21]).AddSyst(cb, "rate_tauSF_DMinclusive_pT20to25_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([2,12,22]).AddSyst(cb, "rate_tauSF_DMinclusive_pT25to30_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([3,13,23]).AddSyst(cb, "rate_tauSF_DMinclusive_pT30to35_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([4,14,24]).AddSyst(cb, "rate_tauSF_DMinclusive_pT35to40_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([5,15,25]).AddSyst(cb, "rate_tauSF_DMinclusive_pT40to50_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([6,16,26]).AddSyst(cb, "rate_tauSF_DMinclusive_pT50to60_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([7,17,27]).AddSyst(cb, "rate_tauSF_DMinclusive_pT60to80_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([8,18,28]).AddSyst(cb, "rate_tauSF_DMinclusive_pT80to100_$ERA","rateParam",ch.SystMap()(1.0))
cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([9,19,29]).AddSyst(cb, "rate_tauSF_DMinclusive_pT100to200_$ERA","rateParam",ch.SystMap()(1.0))

for i, dm in enumerate([0,1,10,11]):
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+1+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT20to25_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+2+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT25to30_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+3+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT30to35_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+4+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT35to40_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+5+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT40to50_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+6+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT50to60_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+7+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT60to80_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+8+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT80to100_$ERA" % dm,"rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["ZTT", "TTT", 'TTL', "VVT", 'VVL']).bin_id([(i+1)*100+9+x for x in [0,10,20]]).AddSyst(cb, "rate_tauSF_DM%i_pT100to200_$ERA" % dm,"rateParam",ch.SystMap()(1.0))

if useCRs:
  # add single rate params for each pT/DM bin

  for p in ['QCD','W']:

    cb.cp().channel(['mt']).process([p]).bin_id([1,11,21]).AddSyst(cb, "rate_%s_pT20to25_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    cb.cp().channel(['mt']).process([p]).bin_id([2,12,22]).AddSyst(cb, "rate_%s_pT25to30_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    cb.cp().channel(['mt']).process([p]).bin_id([3,13,23]).AddSyst(cb, "rate_%s_pT30to35_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    cb.cp().channel(['mt']).process([p]).bin_id([4,14,24]).AddSyst(cb, "rate_%s_pT35to40_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    #cb.cp().channel(['mt']).process([p]).bin_id([5,15,25]).AddSyst(cb, "rate_%s_pT40to50_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    #cb.cp().channel(['mt']).process([p]).bin_id([6,16,26]).AddSyst(cb, "rate_%s_pT50to60_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    #cb.cp().channel(['mt']).process([p]).bin_id([7,17,27]).AddSyst(cb, "rate_%s_pT60to80_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    #cb.cp().channel(['mt']).process([p]).bin_id([8,18,28]).AddSyst(cb, "rate_%s_pT80to100_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    #cb.cp().channel(['mt']).process([p]).bin_id([9,19,29]).AddSyst(cb, "rate_%s_pT100to200_$ERA" %p,"rateParam",ch.SystMap()(1.0))

    cb.cp().channel(['mt']).process([p]).bin_id([5,15,25]+[6,16,26]+[7,17,27]+[8,18,28]+[9,19,29]).AddSyst(cb, "rate_%s_pT40to200_$ERA" %p,"rateParam",ch.SystMap()(1.0))
    
    for i, dm in enumerate([0,1,10,11]):
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+1+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT20to25_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+2+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT25to30_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+3+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT30to35_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+4+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT35to40_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
#      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+5+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to50_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
#      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+6+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT50to60_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
#      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+7+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT60to80_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0)) 
#      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+8+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT80to100_$ERA" % (p,dm),"rateParam",ch.SystMap()(1.0))
#      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+9+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT100to200_$ERA" % (p,dm),"rateParam",ch.SystMap()(1.0))

      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+5+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to200_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+6+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to200_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+7+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to200_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+8+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to200_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
      cb.cp().channel(['mt']).process([p]).bin_id([(i+1)*100+9+x for x in [0,10,20]]).AddSyst(cb, "rate_%s_DM%i_pT40to200_$ERA" % (p,dm) ,"rateParam",ch.SystMap()(1.0))
 
  # additional rate uncertainties to account for extrapolations from CRs to SRs
  cb.cp().channel(['mt']).process(['W']).bin_id(cr_bins,False).AddSyst(cb, "CMS_W_extrap", "lnN", ch.SystMap()(1.2))
  cb.cp().channel(['mt']).process(['W']).bin_id(qcd_cr_bins).AddSyst(cb, "CMS_W_extrap", "lnN", ch.SystMap()(1.2))
  cb.cp().channel(['mt']).process(['QCD']).bin_id(qcd_cr_bins,False).AddSyst(cb, "CMS_QCD_extrap", "lnN", ch.SystMap()(1.2))
 
  # for QCD CR the SF for MC were not derived for aiso events so introduce a new uncertainty for the MC processes in this region
  cb.cp().channel(['mt']).process(['QCD'],False).bin_id(qcd_cr_bins).AddSyst(cb, "CMS_aiso_eff", "lnN", ch.SystMap()(1.2))
else:
  #single rate parameters for QCD and W+jets
  cb.cp().channel(['mt']).process(["QCD"]).bin_id(inclusive_bins).AddSyst(cb, "rate_QCD_$ERA","rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["W"]).bin_id(inclusive_bins).AddSyst(cb, "rate_W_$ERA","rateParam",ch.SystMap()(1.0))
  
  cb.cp().channel(['mt']).process(["QCD"]).bin_id(dm0_bins).AddSyst(cb, "rate_QCD_DM0_$ERA","rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["W"]).bin_id(dm0_bins).AddSyst(cb, "rate_W_DM0_$ERA","rateParam",ch.SystMap()(1.0))
  
  cb.cp().channel(['mt']).process(["QCD"]).bin_id(dm1_bins).AddSyst(cb, "rate_QCD_DM1_$ERA","rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["W"]).bin_id(dm1_bins).AddSyst(cb, "rate_W_DM1_$ERA","rateParam",ch.SystMap()(1.0))
  
  cb.cp().channel(['mt']).process(["QCD"]).bin_id(dm10_bins).AddSyst(cb, "rate_QCD_DM10_$ERA","rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["W"]).bin_id(dm10_bins).AddSyst(cb, "rate_W_DM10_$ERA","rateParam",ch.SystMap()(1.0))
  
  cb.cp().channel(['mt']).process(["QCD"]).bin_id(dm11_bins).AddSyst(cb, "rate_QCD_DM11_$ERA","rateParam",ch.SystMap()(1.0))
  cb.cp().channel(['mt']).process(["W"]).bin_id(dm11_bins).AddSyst(cb, "rate_W_DM11_$ERA","rateParam",ch.SystMap()(1.0))

  # additional uncorrelated rate uncertainties to account for different extrapolations per pT/mT bin
  cb.cp().channel(['mt']).process(['W']).bin_id(cr_bins,False).AddSyst(cb, "CMS_W_extrap_$BIN_$ERA", "lnN", ch.SystMap()(1.2))
  cb.cp().channel(['mt']).process(['QCD']).bin_id(cr_bins,False).AddSyst(cb, "CMS_QCD_extrap_$BIN_$ERA", "lnN", ch.SystMap()(1.2))

#shape uncertainties affecting W+jets:
# for W+jets a shape uncertainty due to the energy scale of the j->tauh fakes, we assume a 50% correlation for this syst so we add it scaled by 1/sqrt(2) and then we will clone it later for each era so that adding the correlated and uncorrelated parts in quadrature will equal 1 
cb.cp().channel(['mt']).process(['W']).AddSyst(cb, "CMS_scale_jfake", "shape", ch.SystMap()(0.707))

# set sensible ranges for all rate params
for era in eras:
  cb.GetParameter("rate_DY_%s" % era).set_range(0.5,1.5)

# Populating Observation, Process and Systematic entries in the harvester instance
for chn in channels:
  for era in eras:
    if chn=='zmm': filename = 'shapes_CR/ztt.datacard.m_vis.%s.%s.%s.root' % (chn,era,wp)
    else: filename = 'shapes_CR/ztt.datacard.m_vis.%s.%s.%s.PFMet.root' % (chn,era,wp)
    print ">>>   file %s" % (filename)
    print('%s, %s' % (chn, era))
    cb.cp().channel([chn]).process(bkg_procs[chn]).era([era]).ExtractShapes(filename, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC")
    if chn == 'mt': cb.cp().channel([chn]).process(sig_procs).era([era]).ExtractShapes(filename, "$BIN/$PROCESS", "$BIN/$PROCESS_$SYSTEMATIC")

# now we clone the j->tauh energy scale uncertainties for each era to ensure they are correlated and uncorrelated components of equal magnitudes (i.e a 50% correlation between eras)

for era in eras:
  cb_syst = cb.cp().era([era]).syst_name(['CMS_scale_jfake'])
  ch.CloneSysts(cb_syst, cb, lambda x: x.set_name('CMS_scale_jfake_'+era))

# split j->tauh energy scale uncertainties by dm-bins
if dm_bins:
  cb.cp().bin_id(dm0_bins).RenameSystematic(cb,'CMS_scale_jfake','CMS_scale_jfake_DM0') 
  cb.cp().bin_id(dm1_bins).RenameSystematic(cb,'CMS_scale_jfake','CMS_scale_jfake_DM1')
  cb.cp().bin_id(dm10_bins).RenameSystematic(cb,'CMS_scale_jfake','CMS_scale_jfake_DM10')
  cb.cp().bin_id(dm11_bins).RenameSystematic(cb,'CMS_scale_jfake','CMS_scale_jfake_DM11')
  
  for era in eras:
    cb.cp().bin_id(dm0_bins).RenameSystematic(cb,'CMS_scale_jfake_%s' % era,'CMS_scale_jfake_DM0_%s' % era) 
    cb.cp().bin_id(dm1_bins).RenameSystematic(cb,'CMS_scale_jfake_%s' % era,'CMS_scale_jfake_DM1_%s' % era)
    cb.cp().bin_id(dm10_bins).RenameSystematic(cb,'CMS_scale_jfake_%s' % era,'CMS_scale_jfake_DM10_%s' % era)
    cb.cp().bin_id(dm11_bins).RenameSystematic(cb,'CMS_scale_jfake_%s' % era,'CMS_scale_jfake_DM11_%s' % era)

  
# Merge to one bin for Z->mumu CRs
for b in cb.cp().channel(['zmm']).bin_set():
  print("Rebinning Z->mumu CRs into 1-bin categories")
  cb.cp().bin([b]).VariableRebin([50.,150,]);

# Rebin histograms for mt channel using Auto Rebinning

print(green("Zeroing NegativeYields"))
cb.ForEachProc(NegativeYields)


rebin = AutoRebin()
#rebin.SetBinThreshold(100)
rebin.SetBinUncertFraction(0.2)
rebin.SetRebinMode(1)
rebin.SetPerformRebin(True)
rebin.SetVerbosity(1) 
rebin.Rebin(cb,cb)

# Convert any shapes in CRs to lnN
cb.cp().channel(['zmm']).syst_type(["shape"]).ForEachSyst(lambda sys: sys.set_type('lnN'))
cb.cp().channel(['mt']).bin_id(cr_bins).syst_type(["shape"]).ForEachSyst(lambda sys: sys.set_type('lnN'))
for era in eras:
  cb.cp().channel(['mt']).syst_name(['CMS_scale_j_%s' % era,'CMS_res_j_%s' % era, 'CMS_scale_met_unclustered_%s' % era]).syst_type(["shape"]).ForEachSyst(lambda sys: sys.set_type('lnN'))

for u in jes_uncert_names:
  if 'year' not in u:
    cb.cp().channel(['mt']).syst_name(['CMS_scale_j_%s' % u]).syst_type(["shape"]).ForEachSyst(lambda sys: sys.set_type('lnN'))
  else:
    for era in eras: cb.cp().channel(['mt']).syst_name(["CMS_scale_j_%s" % u.replace('year',era.split('_')[0])]).syst_type(["shape"]).ForEachSyst(lambda sys: sys.set_type('lnN'))


def SetSystToOne(syst):
  if syst.value_u()<=0.: syst.set_value_u(1.)
  if syst.asymm() and syst.value_d() <=0: syst.set_value_d(1.)

cb.cp().syst_type(["lnN"]).ForEachSyst(SetSystToOne)

# Zero negetive bins
print(green("Zeroing NegativeBins"))
cb.ForEachProc(NegativeBins)

print(green("Zeroing NegativeYields"))
cb.ForEachProc(NegativeYields)

#filter procs with 0 or negative yields
#cb.FilterProcs(lambda p : p.rate() <=0.)

SetStandardBinNames(cb)
# Add bbb uncerts using autoMC stats
cb.SetAutoMCStats(cb, 0., 1, 1)

# define groups - this will help determine correlated uncertainties later on
# add a group for systematics that are correlated by bins and by eras

if useCRs: extra_systs = ' CMS_aiso_eff CMS_QCD_extrap CMS_W_extrap'
else: extra_systs = ''

if not dm_bins:
  cb.AddDatacardLineAtEnd("byErasAndBins group = CMS_eff_m CMS_scale_j_Absolute CMS_scale_j_BBEC1 CMS_scale_j_EC2 CMS_scale_j_FlavorQCD CMS_scale_j_HF CMS_scale_j_RelativeBal CMS_j_fake_m CMS_htt_vvXsec CMS_htt_tjXsec CMS_htt_dyShape CMS_htt_ttbarShape CMS_j_fake_t CMS_l_fake_t CMS_scale_jfake"+extra_systs) 
  # add a group for systematics that are correlated by bins (excluding the uncertainties from the bins and eras group)
  systs_for_group = ["CMS_scale_t_1prong", "CMS_scale_t_1prong1pizero", "CMS_scale_t_3prong", "CMS_scale_t_3prong1pizero", "CMS_ZLShape_mt_1prong", "CMS_ZLShape_mt_1prong1pizero", "CMS_res_j", "CMS_scale_met_unclustered", "CMS_scale_j_Absolute_year", "CMS_scale_j_BBEC1_year", "CMS_scale_j_EC2_year", "CMS_scale_j_HF_year", "CMS_scale_j_RelativeSample_year", "rate_DY", "CMS_scale_jfake"]
  if not useCRs: systs_for_group+=["rate_QCD", "rate_W"]
else:
  cb.AddDatacardLineAtEnd("byErasAndBins group = CMS_eff_m CMS_scale_j_Absolute CMS_scale_j_BBEC1 CMS_scale_j_EC2 CMS_scale_j_FlavorQCD CMS_scale_j_HF CMS_scale_j_RelativeBal CMS_j_fake_m CMS_htt_vvXsec CMS_htt_tjXsec CMS_htt_dyShape CMS_htt_ttbarShape CMS_j_fake_t_DM0 CMS_j_fake_t_DM1 CMS_j_fake_t_DM10 CMS_j_fake_t_DM11 CMS_l_fake_t_DM0 CMS_l_fake_t_DM1 CMS_l_fake_t_DM10 CMS_l_fake_t_DM11 CMS_scale_jfake_DM0 CMS_scale_jfake_DM1 CMS_scale_jfake_DM10 CMS_scale_jfake_DM11"+extra_systs)
  # add a group for systematics that are correlated by bins (excluding the uncertainties from the bins and eras group)
  systs_for_group = ["CMS_res_j", "CMS_scale_met_unclustered", "CMS_scale_j_Absolute_year", "CMS_scale_j_BBEC1_year", "CMS_scale_j_EC2_year", "CMS_scale_j_HF_year", "CMS_scale_j_RelativeSample_year", "rate_DY"]
  
  for dm in [0,1,10,11]:
    if dm==0:  systs = ['CMS_scale_t_1prong','CMS_ZLShape_mt_1prong']
    if dm==1:  systs = ['CMS_scale_t_1prong1pizero','CMS_ZLShape_mt_1prong1pizero']
    if dm==10: systs = ['CMS_scale_t_3prong']
    if dm==11: systs = ['CMS_scale_t_3prong1pizero']

    if not useCRs:
      systs.append('rate_QCD_DM%(dm)s' % vars())
      systs.append('rate_W_DM%(dm)s' % vars())
    systs.append('CMS_scale_jfake_DM%(dm)s' % vars())
    group_str = 'byDM%(dm)s group =' % vars()
    for s in systs:
      for era in eras: group_str+=' %s_%s' % (s,era)
    cb.AddDatacardLineAtEnd(group_str)

group_str = 'byBins group ='
for s in systs_for_group:
  if s.endswith('_year'): 
    for era in eras: 
      year = era.split('_')[0]
      if s.replace('year',year) not in group_str: group_str+=' %s' % s.replace('year',year)
  else: 
    for era in eras: group_str+=' %s_%s' % (s,era)

print group_str
cb.AddDatacardLineAtEnd(group_str)

# Write datacards
print green(">>> writing datacards...")
datacardtxt  = "%s/cmb/$BIN.txt"%(output_folder)
datacardroot = "%s/cmb/common/$BIN_input.root"%(output_folder)
writer = CardWriter(datacardtxt,datacardroot)
writer.SetVerbosity(1)
writer.SetWildcardMasses([ ])
writer.WriteCards("cmb", cb)
