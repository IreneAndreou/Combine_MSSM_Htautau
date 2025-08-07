import ROOT
from argparse import ArgumentParser
ROOT.gROOT.SetBatch(1)

# HI
description = '''This script makes plots of the pT-dependent SFs.'''
parser = ArgumentParser(prog="harvesterDatacards",description=description,epilog="Success!")
parser.add_argument('-e', '--eras', dest='eras', type=str, default='UL', help="Eras to make plots of pT dependent SFs for; can be UL, 2022 or specific years")
parser.add_argument('-o', '--output_folder', dest='output_folder', type=str, default='./', help="Specify the output directory where the plots will be saved")
parser.add_argument('--file', '-f', help= 'File containing the TGraphAsymmErrors objects')
args = parser.parse_args()

output_folder = args.output_folder
if args.eras == 'UL': eras = ['2016_preVFP', '2016_postVFP', '2017', '2018']
if args.eras == '2022': eras = ['2022_preEE', '2022_postEE']
else: eras=args.eras.split(',')

f1 = ROOT.TFile(args.file)

for era in eras:

  graph_name = 'DMinclusive_%s' % era
  
  
  
  g1 = f1.Get(graph_name)
  
  c1 = ROOT.TCanvas()
  
  g1.SetMarkerStyle(8)
  g1.GetXaxis().SetTitle('p_{T} (GeV)')
  g1.GetYaxis().SetTitle('SF')
  g1.Draw('ape')
  
  c1.Print(output_folder+'/graph_pTdep_%s.pdf' % graph_name)
