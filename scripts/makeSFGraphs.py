# this script takes the fit result and converts it into a set of TGraphAsymmErrors objects
import json
import ROOT
import math
from array import array
from argparse import ArgumentParser
from CombineHarvester.TauSF.fit_tools import DecomposeUncerts, FitSF, PlotSF
ROOT.gROOT.SetBatch(1)

description = '''This script makes TGraphAsymmErrors objects from tau ID SF measurments.'''
parser = ArgumentParser(prog="makeSFGraphs",description=description,epilog="Success!")
parser.add_argument('--dm-bins', dest='dm_bins', default=False, action='store_true', help="if specified then the mu+tauh channel fits are also split by tau decay-mode")
parser.add_argument('--saveJson', dest='saveJson', default=False, action='store_true', help="if specified then store the scale factors into jsons")
parser.add_argument('--file', '-f', help= 'File containing the output of MultiDimFit')
parser.add_argument('-e', '--eras', dest='eras', type=str, default='UL', help="Eras to make plots of pT dependent SFs for; can be UL, 2022 or specific years")
parser.add_argument('--wp', dest='wp', type=str, default='dummy_wp', help="The WP the SF are produced for (only used for storing json correctly)")
parser.add_argument('--output_folder', type=str, help="path to output folder")
#parser.add_argument('--pt_bins', dest='pt_bins', type=int, default='0', help="The pt bin being fitted")
args = parser.parse_args()
if args.eras == 'UL':
  eras = ['2016_preVFP', '2016_postVFP', '2017', '2018'] # add other eras later
elif args.eras == '2022':
  eras = ['2022_preEE', '2022_postEE']
elif args.eras == 'Run3':
  eras = ['Run3_2022','Run3_2022EE','Run3_2023','Run3_2023BPix']
else:
  eras = args.eras.split(',')

dm_bins=args.dm_bins
wp=args.wp

f = ROOT.TFile(args.file)

fout_name = args.file.replace('.root','.TGraphAsymmErrors.root')

l = f.Get('limit')

vals = {}
if dm_bins:
  #if args.pt_bins == 0:
  if any(era in eras for era in ['2016_preVFP', '2016_postVFP', '2017', '2018']):
    pois = ['rate_tauSF_DM0_pT20to25_2016_preVFP','rate_tauSF_DM0_pT25to30_2016_preVFP','rate_tauSF_DM0_pT30to35_2016_preVFP','rate_tauSF_DM0_pT35to40_2016_preVFP','rate_tauSF_DM0_pT40to50_2016_preVFP','rate_tauSF_DM0_pT50to60_2016_preVFP','rate_tauSF_DM0_pT60to80_2016_preVFP','rate_tauSF_DM0_pT80to100_2016_preVFP','rate_tauSF_DM0_pT100to200_2016_preVFP','rate_tauSF_DM1_pT20to25_2016_preVFP','rate_tauSF_DM1_pT25to30_2016_preVFP','rate_tauSF_DM1_pT30to35_2016_preVFP','rate_tauSF_DM1_pT35to40_2016_preVFP','rate_tauSF_DM1_pT40to50_2016_preVFP','rate_tauSF_DM1_pT50to60_2016_preVFP','rate_tauSF_DM1_pT60to80_2016_preVFP','rate_tauSF_DM1_pT80to100_2016_preVFP','rate_tauSF_DM1_pT100to200_2016_preVFP','rate_tauSF_DM10_pT20to25_2016_preVFP','rate_tauSF_DM10_pT25to30_2016_preVFP','rate_tauSF_DM10_pT30to35_2016_preVFP','rate_tauSF_DM10_pT35to40_2016_preVFP','rate_tauSF_DM10_pT40to50_2016_preVFP','rate_tauSF_DM10_pT50to60_2016_preVFP','rate_tauSF_DM10_pT60to80_2016_preVFP','rate_tauSF_DM10_pT80to100_2016_preVFP','rate_tauSF_DM10_pT100to200_2016_preVFP','rate_tauSF_DM11_pT20to25_2016_preVFP','rate_tauSF_DM11_pT25to30_2016_preVFP','rate_tauSF_DM11_pT30to35_2016_preVFP','rate_tauSF_DM11_pT35to40_2016_preVFP','rate_tauSF_DM11_pT40to50_2016_preVFP','rate_tauSF_DM11_pT50to60_2016_preVFP','rate_tauSF_DM11_pT60to80_2016_preVFP','rate_tauSF_DM11_pT80to100_2016_preVFP','rate_tauSF_DM11_pT100to200_2016_preVFP','rate_tauSF_DM0_pT20to25_2016_postVFP','rate_tauSF_DM0_pT25to30_2016_postVFP','rate_tauSF_DM0_pT30to35_2016_postVFP','rate_tauSF_DM0_pT35to40_2016_postVFP','rate_tauSF_DM0_pT40to50_2016_postVFP','rate_tauSF_DM0_pT50to60_2016_postVFP','rate_tauSF_DM0_pT60to80_2016_postVFP','rate_tauSF_DM0_pT80to100_2016_postVFP','rate_tauSF_DM0_pT100to200_2016_postVFP','rate_tauSF_DM1_pT20to25_2016_postVFP','rate_tauSF_DM1_pT25to30_2016_postVFP','rate_tauSF_DM1_pT30to35_2016_postVFP','rate_tauSF_DM1_pT35to40_2016_postVFP','rate_tauSF_DM1_pT40to50_2016_postVFP','rate_tauSF_DM1_pT50to60_2016_postVFP','rate_tauSF_DM1_pT60to80_2016_postVFP','rate_tauSF_DM1_pT80to100_2016_postVFP','rate_tauSF_DM1_pT100to200_2016_postVFP','rate_tauSF_DM10_pT20to25_2016_postVFP','rate_tauSF_DM10_pT25to30_2016_postVFP','rate_tauSF_DM10_pT30to35_2016_postVFP','rate_tauSF_DM10_pT35to40_2016_postVFP','rate_tauSF_DM10_pT40to50_2016_postVFP','rate_tauSF_DM10_pT50to60_2016_postVFP','rate_tauSF_DM10_pT60to80_2016_postVFP','rate_tauSF_DM10_pT80to100_2016_postVFP','rate_tauSF_DM10_pT100to200_2016_postVFP','rate_tauSF_DM11_pT20to25_2016_postVFP','rate_tauSF_DM11_pT25to30_2016_postVFP','rate_tauSF_DM11_pT30to35_2016_postVFP','rate_tauSF_DM11_pT35to40_2016_postVFP','rate_tauSF_DM11_pT40to50_2016_postVFP','rate_tauSF_DM11_pT50to60_2016_postVFP','rate_tauSF_DM11_pT60to80_2016_postVFP','rate_tauSF_DM11_pT80to100_2016_postVFP','rate_tauSF_DM11_pT100to200_2016_postVFP','rate_tauSF_DM0_pT20to25_2017','rate_tauSF_DM0_pT25to30_2017','rate_tauSF_DM0_pT30to35_2017','rate_tauSF_DM0_pT35to40_2017','rate_tauSF_DM0_pT40to50_2017',
  'rate_tauSF_DM0_pT50to60_2017','rate_tauSF_DM0_pT60to80_2017','rate_tauSF_DM0_pT80to100_2017','rate_tauSF_DM0_pT100to200_2017','rate_tauSF_DM1_pT20to25_2017','rate_tauSF_DM1_pT25to30_2017','rate_tauSF_DM1_pT30to35_2017','rate_tauSF_DM1_pT35to40_2017','rate_tauSF_DM1_pT40to50_2017','rate_tauSF_DM1_pT50to60_2017','rate_tauSF_DM1_pT60to80_2017','rate_tauSF_DM1_pT80to100_2017','rate_tauSF_DM1_pT100to200_2017','rate_tauSF_DM10_pT20to25_2017','rate_tauSF_DM10_pT25to30_2017','rate_tauSF_DM10_pT30to35_2017','rate_tauSF_DM10_pT35to40_2017','rate_tauSF_DM10_pT40to50_2017','rate_tauSF_DM10_pT50to60_2017','rate_tauSF_DM10_pT60to80_2017','rate_tauSF_DM10_pT80to100_2017','rate_tauSF_DM10_pT100to200_2017','rate_tauSF_DM11_pT20to25_2017','rate_tauSF_DM11_pT25to30_2017','rate_tauSF_DM11_pT30to35_2017','rate_tauSF_DM11_pT35to40_2017','rate_tauSF_DM11_pT40to50_2017','rate_tauSF_DM11_pT50to60_2017','rate_tauSF_DM11_pT60to80_2017','rate_tauSF_DM11_pT80to100_2017','rate_tauSF_DM11_pT100to200_2017','rate_tauSF_DM0_pT20to25_2018','rate_tauSF_DM0_pT25to30_2018','rate_tauSF_DM0_pT30to35_2018','rate_tauSF_DM0_pT35to40_2018','rate_tauSF_DM0_pT40to50_2018','rate_tauSF_DM0_pT50to60_2018','rate_tauSF_DM0_pT60to80_2018','rate_tauSF_DM0_pT80to100_2018','rate_tauSF_DM0_pT100to200_2018','rate_tauSF_DM1_pT20to25_2018','rate_tauSF_DM1_pT25to30_2018','rate_tauSF_DM1_pT30to35_2018','rate_tauSF_DM1_pT35to40_2018','rate_tauSF_DM1_pT40to50_2018','rate_tauSF_DM1_pT50to60_2018','rate_tauSF_DM1_pT60to80_2018','rate_tauSF_DM1_pT80to100_2018','rate_tauSF_DM1_pT100to200_2018','rate_tauSF_DM10_pT20to25_2018','rate_tauSF_DM10_pT25to30_2018','rate_tauSF_DM10_pT30to35_2018','rate_tauSF_DM10_pT35to40_2018','rate_tauSF_DM10_pT40to50_2018','rate_tauSF_DM10_pT50to60_2018','rate_tauSF_DM10_pT60to80_2018','rate_tauSF_DM10_pT80to100_2018','rate_tauSF_DM10_pT100to200_2018','rate_tauSF_DM11_pT20to25_2018','rate_tauSF_DM11_pT25to30_2018','rate_tauSF_DM11_pT30to35_2018','rate_tauSF_DM11_pT35to40_2018','rate_tauSF_DM11_pT40to50_2018','rate_tauSF_DM11_pT50to60_2018','rate_tauSF_DM11_pT60to80_2018','rate_tauSF_DM11_pT80to100_2018','rate_tauSF_DM11_pT100to200_2018']
  if any(era in eras for era in ['2022_preEE', '2022_postEE']):
    pois = ['rate_tauSF_DM0_pT20to25_2022_preEE','rate_tauSF_DM0_pT25to30_2022_preEE','rate_tauSF_DM0_pT30to35_2022_preEE','rate_tauSF_DM0_pT35to40_2022_preEE','rate_tauSF_DM0_pT40to50_2022_preEE','rate_tauSF_DM0_pT50to60_2022_preEE','rate_tauSF_DM0_pT60to80_2022_preEE','rate_tauSF_DM0_pT80to100_2022_preEE','rate_tauSF_DM0_pT100to200_2022_preEE','rate_tauSF_DM1_pT20to25_2022_preEE','rate_tauSF_DM1_pT25to30_2022_preEE','rate_tauSF_DM1_pT30to35_2022_preEE','rate_tauSF_DM1_pT35to40_2022_preEE','rate_tauSF_DM1_pT40to50_2022_preEE','rate_tauSF_DM1_pT50to60_2022_preEE','rate_tauSF_DM1_pT60to80_2022_preEE','rate_tauSF_DM1_pT80to100_2022_preEE','rate_tauSF_DM1_pT100to200_2022_preEE','rate_tauSF_DM10_pT20to25_2022_preEE','rate_tauSF_DM10_pT25to30_2022_preEE','rate_tauSF_DM10_pT30to35_2022_preEE','rate_tauSF_DM10_pT35to40_2022_preEE','rate_tauSF_DM10_pT40to50_2022_preEE','rate_tauSF_DM10_pT50to60_2022_preEE','rate_tauSF_DM10_pT60to80_2022_preEE','rate_tauSF_DM10_pT80to100_2022_preEE','rate_tauSF_DM10_pT100to200_2022_preEE','rate_tauSF_DM11_pT20to25_2022_preEE','rate_tauSF_DM11_pT25to30_2022_preEE','rate_tauSF_DM11_pT30to35_2022_preEE','rate_tauSF_DM11_pT35to40_2022_preEE','rate_tauSF_DM11_pT40to50_2022_preEE','rate_tauSF_DM11_pT50to60_2022_preEE','rate_tauSF_DM11_pT60to80_2022_preEE','rate_tauSF_DM11_pT80to100_2022_preEE','rate_tauSF_DM11_pT100to200_2022_preEE','rate_tauSF_DM0_pT20to25_2022_postEE','rate_tauSF_DM0_pT25to30_2022_postEE','rate_tauSF_DM0_pT30to35_2022_postEE','rate_tauSF_DM0_pT35to40_2022_postEE','rate_tauSF_DM0_pT40to50_2022_postEE','rate_tauSF_DM0_pT50to60_2022_postEE','rate_tauSF_DM0_pT60to80_2022_postEE','rate_tauSF_DM0_pT80to100_2022_postEE','rate_tauSF_DM0_pT100to200_2022_postEE','rate_tauSF_DM1_pT20to25_2022_postEE','rate_tauSF_DM1_pT25to30_2022_postEE','rate_tauSF_DM1_pT30to35_2022_postEE','rate_tauSF_DM1_pT35to40_2022_postEE','rate_tauSF_DM1_pT40to50_2022_postEE','rate_tauSF_DM1_pT50to60_2022_postEE','rate_tauSF_DM1_pT60to80_2022_postEE','rate_tauSF_DM1_pT80to100_2022_postEE','rate_tauSF_DM1_pT100to200_2022_postEE','rate_tauSF_DM10_pT20to25_2022_postEE','rate_tauSF_DM10_pT25to30_2022_postEE','rate_tauSF_DM10_pT30to35_2022_postEE','rate_tauSF_DM10_pT35to40_2022_postEE','rate_tauSF_DM10_pT40to50_2022_postEE','rate_tauSF_DM10_pT50to60_2022_postEE','rate_tauSF_DM10_pT60to80_2022_postEE','rate_tauSF_DM10_pT80to100_2022_postEE','rate_tauSF_DM10_pT100to200_2022_postEE','rate_tauSF_DM11_pT20to25_2022_postEE','rate_tauSF_DM11_pT25to30_2022_postEE','rate_tauSF_DM11_pT30to35_2022_postEE','rate_tauSF_DM11_pT35to40_2022_postEE','rate_tauSF_DM11_pT40to50_2022_postEE','rate_tauSF_DM11_pT50to60_2022_postEE','rate_tauSF_DM11_pT60to80_2022_postEE','rate_tauSF_DM11_pT80to100_2022_postEE','rate_tauSF_DM11_pT100to200_2022_postEE']
  if any(era in eras for era in ['Run3_2022','Run3_2022EE','Run3_2023','Run3_2023BPix']):

    pois = []

    for era in eras:
      temp_pois=[
        "rate_tauSF_DM$DM_pT20to25_$YEAR",
        "rate_tauSF_DM$DM_pT25to30_$YEAR",
        "rate_tauSF_DM$DM_pT30to35_$YEAR",
        "rate_tauSF_DM$DM_pT35to40_$YEAR",
        "rate_tauSF_DM$DM_pT40to50_$YEAR",
        "rate_tauSF_DM$DM_pT50to60_$YEAR",
        "rate_tauSF_DM$DM_pT60to80_$YEAR",
        "rate_tauSF_DM$DM_pT80to100_$YEAR",
        "rate_tauSF_DM$DM_pT100to200_$YEAR",
      ]

      pois += [x.replace('$DM', y).replace('$YEAR', era) for y in ['0','1','2','10','11'] for x in temp_pois]

  #if args.pt_bins == 1:
  #   pois = ['rate_tauSF_DM0_pT20to25_2017','rate_tauSF_DM1_pT20to25_2017','rate_tauSF_DM10_pT20to25_2017','rate_tauSF_DM11_pT20to25_2017']
  #if args.pt_bins == 2:
  #   pois = ['rate_tauSF_DM0_pT25to30_2017','rate_tauSF_DM1_pT25to30_2017','rate_tauSF_DM10_pT25to30_2017','rate_tauSF_DM11_pT25to30_2017']
  #if args.pt_bins == 3:
  #   pois = ['rate_tauSF_DM0_pT30to35_2017','rate_tauSF_DM1_pT30to35_2017','rate_tauSF_DM10_pT30to35_2017','rate_tauSF_DM11_pT30to35_2017']
  #if args.pt_bins == 4:
  #   pois = ['rate_tauSF_DM0_pT35to40_2017','rate_tauSF_DM1_pT35to40_2017','rate_tauSF_DM10_pT35to40_2017','rate_tauSF_DM11_pT35to40_2017']
  #if args.pt_bins == 5:
  #   pois = ['rate_tauSF_DM0_pT40to50_2017', 'rate_tauSF_DM1_pT40to50_2017','rate_tauSF_DM10_pT40to50_2017','rate_tauSF_DM11_pT40to50_2017']
  #if args.pt_bins == 6:
  #   pois = ['rate_tauSF_DM0_pT50to60_2017','rate_tauSF_DM1_pT50to60_2017','rate_tauSF_DM10_pT50to60_2017','rate_tauSF_DM11_pT50to60_2017']
  #if args.pt_bins == 7:
  #   pois = ['rate_tauSF_DM0_pT60to80_2017','rate_tauSF_DM1_pT60to80_2017','rate_tauSF_DM10_pT60to80_2017','rate_tauSF_DM11_pT60to80_2017']
  #if args.pt_bins == 8:
  #   pois = ['rate_tauSF_DM0_pT80to100_2017','rate_tauSF_DM1_pT80to100_2017','rate_tauSF_DM10_pT80to100_2017','rate_tauSF_DM11_pT80to100_2017']
  #if args.pt_bins == 9:
  #   pois = ['rate_tauSF_DM0_pT100to200_2017','rate_tauSF_DM1_pT100to200_2017','rate_tauSF_DM10_pT100to200_2017','rate_tauSF_DM11_pT100to200_2017']
else:
  if any(era in eras for era in ['2016_preVFP', '2016_postVFP', '2017', '2018']):
    pois = ['rate_tauSF_DMinclusive_pT20to25_2016_preVFP','rate_tauSF_DMinclusive_pT25to30_2016_preVFP','rate_tauSF_DMinclusive_pT30to35_2016_preVFP','rate_tauSF_DMinclusive_pT35to40_2016_preVFP','rate_tauSF_DMinclusive_pT40to50_2016_preVFP','rate_tauSF_DMinclusive_pT50to60_2016_preVFP','rate_tauSF_DMinclusive_pT60to80_2016_preVFP','rate_tauSF_DMinclusive_pT80to100_2016_preVFP','rate_tauSF_DMinclusive_pT100to200_2016_preVFP','rate_tauSF_DMinclusive_pT20to25_2016_postVFP','rate_tauSF_DMinclusive_pT25to30_2016_postVFP','rate_tauSF_DMinclusive_pT30to35_2016_postVFP','rate_tauSF_DMinclusive_pT35to40_2016_postVFP','rate_tauSF_DMinclusive_pT40to50_2016_postVFP','rate_tauSF_DMinclusive_pT50to60_2016_postVFP','rate_tauSF_DMinclusive_pT60to80_2016_postVFP','rate_tauSF_DMinclusive_pT80to100_2016_postVFP','rate_tauSF_DMinclusive_pT100to200_2016_postVFP','rate_tauSF_DMinclusive_pT20to25_2017','rate_tauSF_DMinclusive_pT25to30_2017','rate_tauSF_DMinclusive_pT30to35_2017','rate_tauSF_DMinclusive_pT35to40_2017','rate_tauSF_DMinclusive_pT40to50_2017','rate_tauSF_DMinclusive_pT50to60_2017','rate_tauSF_DMinclusive_pT60to80_2017','rate_tauSF_DMinclusive_pT80to100_2017','rate_tauSF_DMinclusive_pT100to200_2017','rate_tauSF_DMinclusive_pT20to25_2018','rate_tauSF_DMinclusive_pT25to30_2018','rate_tauSF_DMinclusive_pT30to35_2018','rate_tauSF_DMinclusive_pT35to40_2018','rate_tauSF_DMinclusive_pT40to50_2018','rate_tauSF_DMinclusive_pT50to60_2018','rate_tauSF_DMinclusive_pT60to80_2018','rate_tauSF_DMinclusive_pT80to100_2018','rate_tauSF_DMinclusive_pT100to200_2018']
  if any(era in eras for era in ['2022_preEE', '2022_postEE']):
    pois = ['rate_tauSF_DMinclusive_pT20to25_2022_preEE','rate_tauSF_DMinclusive_pT25to30_2022_preEE','rate_tauSF_DMinclusive_pT30to35_2022_preEE','rate_tauSF_DMinclusive_pT35to40_2022_preEE','rate_tauSF_DMinclusive_pT40to50_2022_preEE','rate_tauSF_DMinclusive_pT50to60_2022_preEE','rate_tauSF_DMinclusive_pT60to80_2022_preEE','rate_tauSF_DMinclusive_pT80to100_2022_preEE','rate_tauSF_DMinclusive_pT100to200_2022_preEE','rate_tauSF_DMinclusive_pT20to25_2022_postEE','rate_tauSF_DMinclusive_pT25to30_2022_postEE','rate_tauSF_DMinclusive_pT30to35_2022_postEE','rate_tauSF_DMinclusive_pT35to40_2022_postEE','rate_tauSF_DMinclusive_pT40to50_2022_postEE','rate_tauSF_DMinclusive_pT50to60_2022_postEE','rate_tauSF_DMinclusive_pT60to80_2022_postEE','rate_tauSF_DMinclusive_pT80to100_2022_postEE','rate_tauSF_DMinclusive_pT100to200_2022_postEE']

# get values and +/- 1 sigma shifts from tree
for poi in pois:
  skip = True
  for era in eras: 
    if era in poi: skip=False
  if skip: continue 
  vals[poi] = set()

  for i in range(0, l.GetEntries()):
    l.GetEntry(i)
    x=getattr(l, poi)
    vals[poi].add(x)

# group x, y values and errors by DM
graph_values = {}

sf_map = {}

for e in eras:

  if dm_bins:
    for dm in [0,1,2,10,11]: graph_values['%i_%s' % (dm,e)] = []
  else: 
    graph_values['inclusive_%s' % e] = []  


bin_boundaries = [20.,25.,30.,35.,40.,50.,60.,80.,100.,200.]

htemp = ROOT.TH1D('htemp','',len(bin_boundaries)-1, array('d',bin_boundaries))

# taking pt bins from average values instead
pt_vals = [23., 28., 32., 37., 44., 54., 68., 89., 125.] 

# taking x errors from RMS values from bin averaging
pt_errs=[2., 2., 2., 2., 3., 3., 6., 6., 22]

def FindBin(hi,lo):

  for i, x in enumerate(pt_vals):
    if x<hi and x>=lo: return x, pt_errs[i] 
  return (hi+lo)/2, (hi-lo)/2

for v in vals: 
  x = list(vals[v])
  # list contains nominal value and +/- 1 sigma shited value
  # sort list and subtract nominal value to obtain up and down errors
  x.sort()
  val = x[1]
  e_up = x[2]-val
  e_down = val-x[0]
  dm_bin = v.split('_')[2][2:]
  pt_bin = v.split('_')[3][2:]
  era='_'.join(v.split('_')[4:])
  pt_lo=float(pt_bin.split('to')[0])
  pt_hi=float(pt_bin.split('to')[1])
  ave_pt = (pt_lo+pt_hi)/2 # can use average pT to define bin centres 
  # but if option is specific then will take the average pT values within each bin instead
  x_val = ave_pt
  x_val,x_err=FindBin(pt_hi,pt_lo)
  graph_values['%s_%s' % (dm_bin,era)].append((x_val, val, e_down, e_up, x_err))

sf_map[wp] = {}

if not dm_bins:

  for era in eras:
    print(f'pT-binned SFs for era {era}:')
    out='((gen_match_2!=5) + (gen_match_2==5)*('
    for i, b in enumerate(bin_boundaries[:-1]):
      x=list(vals['rate_tauSF_DMinclusive_pT%ito%i_%s' % (int(b), int(bin_boundaries[i+1]), era)])
      x.sort()
      val=x[1]
      if b == 100: out+='(pt_2>=%i)*(%.3f)' %(b, val)
      else: out+='(pt_2>=%i&&pt_2<%i)*(%.3f)+' %(b, bin_boundaries[i+1], val) 
    out+='))'
    sf_map[wp][era] = out
    print(out)

print ('Writing to file: %s' % fout_name)
fout = ROOT.TFile(fout_name,'RECREATE')


dm_binned_strings={}

for g_val in graph_values:

  h = htemp.Clone()
  h.SetName('DM%s_hist' % g_val)

  gr = ROOT.TGraphAsymmErrors()
  gr.SetName('DM%s' % g_val)

  for x in graph_values[g_val]:
    nominal_value = x[1]
    y_err_low = x[2]
    y_err_high = x[3]

    if abs(y_err_low) >= abs(nominal_value) or abs(y_err_high) >= abs(nominal_value):
      continue

    n=gr.GetN()
    gr.SetPoint(n, x[0], nominal_value)
    gr.SetPointError(n, x[4], x[4], y_err_low, y_err_high)

    bini = h.FindBin(x[0])
    h.SetBinContent(bini, nominal_value)
    h.SetBinError(bini, max(y_err_low, y_err_high)) # set histogram error to maximum of the up and down

  fout.cd()
  gr.Write()
  h.Write()

  dm=str(gr.GetName()).split('_')[0]
  era=str(gr.GetName()).split('_')[1]
#  if dm=='DM0' or (dm=='DM10') or (dm=='DM11'): fit, h_uncert, h, uncerts = FitSF(gr,func='pol1')
#  else: fit, h_uncert, h, uncerts = FitSF(gr,func='erf_extra')
  fit, h_uncert, h, uncerts = FitSF(gr,func='pol1')
  gr.Write(gr.GetName()+'_fitted')
  fit.Write()
  h_uncert.Write()
  name = fit.GetName()
  for x in uncerts: 
    x[1].SetName(name+'_%s_up' %x[0]) 
    x[2].SetName(name+'_%s_down' %x[0])
    x[1].Write() 
    x[2].Write() 

  dm_binned_strings[gr.GetName()] = str(fit.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
  PlotSF(gr, h_uncert, 'fit_'+gr.GetName(), title=gr.GetName(), output_folder=args.output_folder)


if dm_bins:
  for era in eras:
    print(f'DM-binned SFs for era {era}:')
    out='((gen_match_2!=5) + (gen_match_2==5)*('
    for dm in [0,1,10,11]:
      out+='(tau_decay_mode_2==%i)*(%s)+' % (dm, dm_binned_strings['DM%i_%s' % (dm,era)])
    out=out[:-1]
    out+='))'
    sf_map[wp][era] = out
    print(out)

if args.saveJson:
  if dm_bins: json_out_name = args.output_folder+'tau_SF_strings_dm_binned_%(wp)s.json' % vars()
  else: json_out_name = args.output_folder+'tau_SF_strings_pt_binned_%(wp)s.json' % vars()
  with open(json_out_name, 'w') as fp:
    json.dump(sf_map, fp, sort_keys=True, indent=4)
