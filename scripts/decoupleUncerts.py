from os import remove
import re
import ROOT
import math
from array import array
from argparse import ArgumentParser
import json
from CombineHarvester.TauSF.fit_tools import DecomposeUncerts, FitSF, PlotSF
import ctypes
ROOT.gROOT.SetBatch(1)

# HI
description = '''This script makes the graphs containing the split uncertainties.'''
parser = ArgumentParser(prog="decoupleUncerts",description=description,epilog="Success!")
parser.add_argument('--dm-bins', dest='dm_bins', default=False, action='store_true', help="if specified then the mu+tauh channel fits are also split by tau decay-mode")
parser.add_argument('--split-fit', dest='split_fit', default=False, action='store_true', help="if specified then split the pT dependent fits into 2 regions < 50 GeV and > 50 GeV")
parser.add_argument('--split-fit-join', dest='split_fit_join', default=False, action='store_true', help="if specified then split the pT dependent fits into 2 regions < 50 GeV and > 50 GeV but the functions are constrained to join at pT=50")
parser.add_argument('--saveJson', dest='saveJson', default=False, action='store_true', help="if specified then store the scale factors into jsons")
parser.add_argument('--wp', dest='wp', type=str, default='dummy_wp', help="The WP the SF are produced for (only used for storing json correctly)")
parser.add_argument('--file_total', '-f1', help= 'File containing the output of MultiDimFit with all uncertainties floating')
parser.add_argument('--file_comb1', '-f2', help= 'File containing the output of MultiDimFit with by eras uncertainties fixed')
parser.add_argument('--file_comb2', '-f3', help= 'File containing the output of MultiDimFit with by eras and by pT-bins uncertainties fixed')
parser.add_argument('--file_comb3', '-f4', help= 'File containing the output of MultiDimFit with by eras, by pT-bins, and by DM-bins uncertainties fixed')
parser.add_argument('--file_comb4', '-f5', help= 'File containing the output of MultiDimFit for +1-sigma TES shift', default=None)
parser.add_argument('--file_comb5', '-f6', help= 'File containing the output of MultiDimFit for -1-sigma TES shift', default=None)
parser.add_argument('-e', '--eras', dest='eras', type=str, default='UL', help="Eras to make plots of pT dependent SFs for; can be UL or 2022")
parser.add_argument('-o', '--output_folder', dest='output_folder', type=str, default='./', help="Name of the output folder to save the root files and plots")
args = parser.parse_args()

if args.eras == 'UL':
  eras = ['2016_preVFP', '2016_postVFP', '2017', '2018'] # add other eras later
elif args.eras == '2022':
  eras = ['2022_preEE', '2022_postEE']
elif args.eras == 'Run3':
  eras = ['Run3_2022','Run3_2022EE','Run3_2023','Run3_2023BPix']
else:
  eras = args.eras.split(',')

output_folder=args.output_folder

def checkBins(graph, remove_bins=[]):
    n_points = graph.GetN()
    if n_points == 0:
        print("Graph is empty, returning.")
        return graph

    # Step 1: Collect bin indices to remove
    bins_to_remove = []
    for i in range(n_points):
        if graph.GetErrorYhigh(i) == graph.GetY()[i] or graph.GetErrorYlow(i) == graph.GetY()[i]:
            bins_to_remove.append(i)

    # Step 2: Append to remove_bins and remove duplicates
    remove_bins.extend(bins_to_remove)
    remove_bins = sorted(set(remove_bins))  # Remove duplicates and sort

    return remove_bins


def checkErrors(graph, remove_bins):
    n_points = graph.GetN()
    if n_points == 0:
        print("Graph is empty, returning.")
        return graph

    for i in sorted(remove_bins, reverse=True):  # Reverse order to avoid index shifting
        if i < graph.GetN():  # Ensure index is still valid after removals
            graph.RemovePoint(i)
            print(f'Removed point {i}')
        else:
            print(f'Skipping index {i}, out of bounds')

    return graph


def symmetriseBins(graph):
    n_points = graph.GetN()
    if n_points == 0:
        print("Graph is empty, returning.")
        return graph

    # check the error of each bin, if the up error is the same as the central value, but the down error is not, then set the up error to be the same as the down error and vice versa
    for i in range(n_points):
        if graph.GetErrorYhigh(i) >= graph.GetY()[i] and graph.GetErrorYlow(i) < graph.GetY()[i]:
            graph.SetPointEYhigh(i, graph.GetErrorYlow(i))

        if graph.GetErrorYlow(i) >= graph.GetY()[i] and graph.GetErrorYhigh(i) < graph.GetY()[i]:
            graph.SetPointEYlow(i, graph.GetErrorYhigh(i))

    return graph


def GraphDivideErrors(num, den):
    res = num.Clone()
    n_res = res.GetN()
    n_den = den.GetN()
    print("Number of points in res:", n_res)
    print("Number of points in den:", n_den)
    for i in range(num.GetN()):
        if type(res) is ROOT.TGraphAsymmErrors:
          if den.Eval(res.GetX()[i]) == 0:
              res.GetEYhigh()[i] = 0
              res.GetEYlow()[i] = 0
          else:
              if res.GetY()[i] < 1e-100 or den.GetY()[i] < 1e-100:
                res.GetEYhigh()[i] = 0
                res.GetEYlow()[i] = 0
              else:
                res.GetEYhigh()[i] = math.sqrt((res.GetEYhigh()[i]/res.GetY()[i])**2 + (den.GetEYhigh()[i]/den.GetY()[i])**2)
                res.GetEYlow()[i] = math.sqrt((res.GetEYlow()[i]/res.GetY()[i])**2 + (den.GetEYlow()[i]/den.GetY()[i])**2)
        if den.Eval(res.GetX()[i]) == 0: res.GetY()[i] = 0
        else: res.GetY()[i] = res.GetY()[i]/den.Eval(res.GetX()[i])
    return res



def SplitUncerts(g1,g2,g3,era,dm=None,g4=None):

  gout1=g1.Clone()
  gout2=g1.Clone()
  gout3=g1.Clone()
  name = g1.GetName()
  gout1.SetName(name+'_stat') 
  gout2.SetName(name+'_syst_alleras') 
  gout3.SetName(name+'_syst_%(era)s' % vars()) 
  if dm is not None: 
    gout4=g1.Clone()
    gout4.SetName(name+'_syst_dm%(dm)i_%(era)s' % vars()) 
    #gout5 will combine uncerts for syst_dm_era with syst_era as for split TES scheme the syst_dm_era component is very small anyway so finer splitting is not very well motivated 
    gout5=g1.Clone()
    gout5.SetName(name+'_syst_alldms_%(era)s' % vars()) 

  for i in range(0,g1.GetN()):
    up_total=g1.GetErrorYhigh(i)
    down_total=g1.GetErrorYlow(i)
  
    up_no_era=g2.GetErrorYhigh(i)
    down_no_era=g2.GetErrorYlow(i)
  
    up_no_era_ptbins=g3.GetErrorYhigh(i)
    down_no_era_ptbins=g3.GetErrorYlow(i)

    up_no_era_ptbins_dmbins=0.
    down_no_era_ptbins_dmbins=0.


    if dm is not None:

      up_no_era_ptbins_dmbins=g4.GetErrorYhigh(i)
      down_no_era_ptbins_dmbins=g4.GetErrorYlow(i)

      up_stat = up_no_era_ptbins_dmbins
      down_stat = down_no_era_ptbins_dmbins

      up_dmbins = max(up_no_era_ptbins**2-up_stat**2,0.)**.5
      down_dmbins = max(down_no_era_ptbins**2-down_stat**2,0.)**.5

      up_era = max(up_total**2-up_no_era**2,0.)**.5
      down_era= max(down_total**2-down_no_era**2,0.)**.5

      up_ptbins = max(up_no_era**2-up_no_era_ptbins**2,0.)**.5
      down_ptbins = max(down_no_era**2-down_no_era_ptbins**2,0.)**.5

    else: 

      up_stat = up_no_era_ptbins
      down_stat = down_no_era_ptbins

      up_ptbins = max(up_no_era**2-up_stat**2,0.)**.5
      down_ptbins = max(down_no_era**2-down_stat**2,0.)**.5

      up_era = max(up_total**2-up_no_era**2,0.)**.5
      down_era = max(down_total**2-down_no_era**2,0.)**.5

    gout1.SetPointEYhigh(i,up_stat)
    gout1.SetPointEYlow(i,down_stat)
    gout2.SetPointEYhigh(i,up_era) 
    gout2.SetPointEYlow(i,down_era)
    gout3.SetPointEYhigh(i,up_ptbins)  
    gout3.SetPointEYlow(i,down_ptbins)   

    #for uncertainty variations we just store the errors and set the nominal values to 0 
    x=ctypes.c_double(0.0)
    y=ctypes.c_double(0.0)

    g1.GetPoint(i,x,y)
 
    gout1.SetPoint(i,x,0.)
    gout2.SetPoint(i,x,0.)
    gout3.SetPoint(i,x,0.)
    if dm is not None:
      gout4.SetPointEYhigh(i,up_dmbins)
      gout4.SetPointEYlow(i,down_dmbins) 
      gout4.SetPoint(i,x,0.)
     
      gout5.SetPointEYhigh(i,(up_dmbins**2+up_ptbins**2)**.5)
      gout5.SetPointEYlow(i,(down_dmbins**2+down_ptbins**2)**.5)
      gout5.SetPoint(i,x,0.)

  if dm is not None:
    return(gout1,gout2,gout3,gout4,gout5)
  else:
    return(gout1,gout2,gout3)


f1 = ROOT.TFile(args.file_total)
f2 = ROOT.TFile(args.file_comb1)
f3 = ROOT.TFile(args.file_comb2)

if args.dm_bins:
  f4 = ROOT.TFile(args.file_comb3)

sepTES=(args.file_comb4 and args.file_comb5)
if sepTES:
  f5 = ROOT.TFile(args.file_comb4)
  f6 = ROOT.TFile(args.file_comb5)

if args.dm_bins: out_file='split_uncertainties_dmbins.root'
else: out_file='split_uncertainties.root'

if args.split_fit: 
  out_file=out_file.replace('.root','_split_fit.root')
elif args.split_fit_join: 
  out_file=out_file.replace('.root','_split_fit_join.root')

fout = ROOT.TFile(output_folder+'/'+out_file,'RECREATE')

for era in eras:
  dms = ['inclusive']
  if args.dm_bins: 
    dms = [0,1,2,10,11]

  for dm in dms:
 
    graph_name = 'DM%(dm)s_%(era)s' % vars()
    
    h1 = f1.Get(graph_name+'_hist') 
    g1 = f1.Get(graph_name)
    g2 = f2.Get(graph_name)
    g3 = f3.Get(graph_name)
    g4=None
    g5=None
    g6=None 
   
    if sepTES:
      g5 = f5.Get(graph_name)
      g6 = f6.Get(graph_name)
      g5.SetName(graph_name+'_TESUp')
      g6.SetName(graph_name+'_TESDown')
      g5.Write()
      g6.Write()
    if args.dm_bins:
      g4 = f4.Get(graph_name)
      gout1,gout2,gout3,gout4,gout5 = SplitUncerts(g1,g2,g3,era,dm,g4)
      fout.cd()
      gout4.Write() 
      gout5.Write() 
    else:
      gout1,gout2,gout3 = SplitUncerts(g1,g2,g3,era)
  
    fout.cd()
    g1.Write() 
    h1.Write() 
    gout1.Write() 
    gout2.Write() 
    gout3.Write()

# for dm-binned SF we now want to construct up and down shifted templates for the systematic variations
# then we fit these with the same functions we use for the nominal SFs
# the fitted distributions then correspond to our uncertainty variations


def MakeUpAndDownVariations(g,guncert):

  x = ctypes.c_double(0.0)
  y = ctypes.c_double(0.0)

  x_uncert = ctypes.c_double(0.0)
  y_uncert = ctypes.c_double(0.0)

  gout_up = g.Clone()
  gout_down = g.Clone()


  for i in range(0,g.GetN()):
    g.GetPoint(i,x,y) 
    guncert.GetPoint(i,x_uncert,y_uncert)

    print(g.GetN(), guncert.GetN())
    print('x: %f, x_uncert: %f' % (x.value,x_uncert.value))
    if x_uncert.value != x.value:
      print('ERRROR: x bins values don\'t match!')
      exit() 

    up=y.value+guncert.GetErrorYhigh(i)
    down=y.value-guncert.GetErrorYlow(i)
   
    gout_up.SetPoint(i,x,up) 
    gout_down.SetPoint(i,x,down) 

    gout_up.SetName(guncert.GetName()+'_up')
    gout_down.SetName(guncert.GetName()+'_down')

  return (gout_up,gout_down)

def PlotpTBinned(nom, systs,output_name):

  colors = [2,3]

  c1=ROOT.TCanvas()

  nom.GetXaxis().SetTitle('p_{T} (GeV)')
  nom.GetYaxis().SetTitle('Correction')
  nom.SetTitle('')
  nom.SetMarkerStyle(20)
  nom.Draw('ape')
  leg = ROOT.TLegend(0.15,0.92,0.9,0.96)
  leg.SetNColumns(4)
  leg.SetBorderSize(0)
  leg.AddEntry(nom,'total uncert.' ,'ep')
  for i, syst in enumerate(systs):
    syst.SetLineColor(colors[i]) 
    leg.AddEntry(syst,'_'.join(str(syst.GetName()).split('_')[2:]),'e')
    for j in range(0,nom.GetN()):
      x=ctypes.c_double(0.0)
      y=ctypes.c_double(0.0)
      nom.GetPoint(j,x,y)
      syst.SetPoint(j,x,y)
    syst.Draw('pep') 
  leg.Draw() 
 
  c1.Print(output_name+'.pdf')


def CompareSystsPlot(nom, systs,output_name):

  colors = [1,2,4,6,3,7,9,8]

  c1=ROOT.TCanvas()

  to_draw = []
 
  for i, syst in enumerate(systs):
    up=syst[0]
    down=syst[1]
    up_r=ROOT.TF1('%s_ratio' % up.GetName(),'(%s)/(%s)' % (up.GetExpFormula('p'), nom.GetExpFormula('p')),20,140)
    down_r=ROOT.TF1('%s_ratio' % down.GetName(),'(%s)/(%s)' % (down.GetExpFormula('p'), nom.GetExpFormula('p')),20,140)

    up_r.SetLineColor(colors[i]) 
    down_r.SetLineColor(colors[i]) 
    down_r.SetLineStyle(2)

    to_draw.append(up_r)
    to_draw.append(down_r)
 
    up_r.Draw('same')
    down_r.Draw('same')

  nom_r=ROOT.TF1('nom_ratio','0',20,140)
  nom_r.GetXaxis().SetTitle('p_{T} (GeV)')
  nom_r.GetYaxis().SetTitle('relative uncertainty')
  nom_r.SetTitle('')
  nom_r.SetMaximum(1.15)
  nom_r.SetMinimum(0.85)
  nom_r.Draw() 
  leg = ROOT.TLegend(0.15,0.92,0.9,0.96)
  leg.SetNColumns(4)
  leg.SetBorderSize(0)
  for p in to_draw: 
    p.Draw('same')
    leg.AddEntry(p,'_'.join(str(p.GetName()).split('_')[2:-1]),'l')
  leg.Draw()
  c1.Print(output_name+'.pdf')

dm_binned_strings={}

tot_chi2=0.
tot_ndf=0.

print("-"*50)
if args.dm_bins:
  for era in eras:
    for dm in [0,1,2,10,11]:

      if args.split_fit:
        fit_func='pol1_split'
      elif args.split_fit_join: fit_func='pol1_split_constrained'
      else: fit_func='pol_order-2'

#      if dm==1 and era != '2016_preVFP': fit_func='erf'
      graph_name = 'DM%(dm)s_%(era)s' % vars()

      if not gout5: systs = ['_syst_alleras', '_syst_%(era)s' % vars(),  '_syst_dm%(dm)s_%(era)s' % vars()]
      else: systs = ['_syst_alleras', '_syst_alldms_%(era)s' % vars()]
      systs_to_plot = []

      g = fout.Get(graph_name)

      remove_bins = []
      remove_bins = checkBins(g,remove_bins)

      for syst in systs:
        guncert = fout.Get(graph_name+syst)
        remove_bins = checkBins(guncert,remove_bins)


      # now remove the bins from g
      # g = checkErrors(g,remove_bins)
      #g = symmetriseBins(g)
      for syst in systs:
        guncert=fout.Get(graph_name+syst)
        # guncert = checkErrors(guncert,remove_bins)
        gr_up,gr_down=MakeUpAndDownVariations(g,guncert)

        fout.cd()
        gr_up.Write()
        gr_down.Write()

        fit_up, h_uncert_up, h_up, uncerts_up = FitSF(gr_up,func=fit_func)
        fit_down, h_uncert_down, h_down, uncerts_down = FitSF(gr_down,func=fit_func)

        fit_up.Write()
        fit_down.Write()
        systs_to_plot.append((fit_up.Clone(), fit_down.Clone()))

      print('\nfitting nominal: '+g.GetName() )
      # we also fit the nominal SFs again, just to make sure everything is consistent with the uncertainties
      fit_nom, h_uncert_nom, h_nom, uncerts_nom = FitSF(g,func=fit_func)
      tot_chi2+=fit_nom.GetChisquare()
      tot_ndf+=fit_nom.GetNDF()
      print('finished fitting nominal\n')

      extra_name=''
      if args.split_fit: extra_name='_split_fit'
      elif args.split_fit_join: extra_name='_split_fit_join'

      if sepTES:
        # TES shifts are not described very well by pol1 fit so we use a different procedure
        # We divide the shifts by the nominal, then fit with unless the split fit option is used
        # if split fit option is not used we use a different procedure whereby we fit relative uncertainties using 
        # an error function + pol0 and then to get final function we multiply this by the pol1 fit for the nominal SFs
        gr_up=fout.Get(graph_name+'_TESUp').Clone()
        gr_down=fout.Get(graph_name+'_TESDown').Clone()
        if (args.split_fit or args.split_fit_join):
          fit_up, h_uncert_up, h_up, uncerts_up = FitSF(gr_up,func=fit_func)
          fit_down, h_uncert_down, h_down, uncerts_down = FitSF(gr_down,func=fit_func)
          PlotSF(gr_up, h_uncert_up, 'TESUp_DM%(dm)s_%(era)s' % vars()+ extra_name, title='DM%(dm)s, %(era)s' % vars(), output_folder=output_folder)
          PlotSF(gr_down, h_uncert_down, 'TESDown_DM%(dm)s_%(era)s' % vars()+extra_name, title='DM%(dm)s, %(era)s' % vars(), output_folder=output_folder)
        else:
          gr_nom=fout.Get(graph_name)
          gr_up.SetName(graph_name+'_TESUp_relative')
          gr_down.SetName(graph_name+'_TESDown_relative')
          gr_up=GraphDivideErrors(gr_up,gr_nom)
          gr_down=GraphDivideErrors(gr_down,gr_nom)
          gr_up.Write()
          gr_down.Write()
# erf works well for pol1 fits but for pol_order-2 can use same function
#          fit_rel_up, h_uncert_up, h_up, uncerts_up = FitSF(gr_up,func='erf_rev')
#          fit_rel_down, h_uncert_down, h_down, uncerts_down = FitSF(gr_down,func='erf')
          fit_rel_up, h_uncert_up, h_up, uncerts_up = FitSF(gr_up,func=fit_func)
          fit_rel_down, h_uncert_down, h_down, uncerts_down = FitSF(gr_down,func=fit_func)
          func_rel_up = str(fit_rel_up.GetExpFormula('p'))
          func_rel_down = str(fit_rel_down.GetExpFormula('p'))
          func_nom=str(fit_nom.GetExpFormula('p'))
          if func_nom[0]!='(': func_nom='('+func_nom+')'
          if func_rel_up[0]!='(': func_rel_up='('+func_rel_up+')'
          if func_rel_down[0]!='(': func_rel_down='('+func_rel_down+')'
          PlotSF(gr_up, h_uncert_up, 'TESUp_relative_DM%(dm)s_%(era)s' % vars()+ extra_name, title='DM%(dm)s, %(era)s' % vars(), output_folder=output_folder)
          PlotSF(gr_down, h_uncert_down, 'TESDown_relative_DM%(dm)s_%(era)s' % vars()+extra_name, title='DM%(dm)s, %(era)s' % vars(), output_folder=output_folder)
          fit_rel_up.Write()
          fit_rel_down.Write()
          fit_up = ROOT.TF1(graph_name+'_TESUp_fit',func_rel_up+'*'+func_nom,20,200)       
          fit_down = ROOT.TF1(graph_name+'_TESDown_fit',func_rel_down+'*'+func_nom,20,200)       

        fit_up.Write()
        fit_down.Write()
        systs_to_plot.append((fit_up.Clone(), fit_down.Clone()))

      g.Write(g.GetName()+'_fitted')
      fit_nom.Write()
      h_uncert_nom.Write()

      # # we also fit the nominal SFs with a pol0 function for pT>40 to match the old prescription
      # g_pol0 = g.Clone()
      # g_pol0.SetName(g.GetName()+'_pol0_gt40')
      # # g_pol0
      # # loop over bins and print bin contents and errors
      # n_points = g_pol0.GetN()  # Number of points in the graph

      # for i in range(n_points):
      #     x = ctypes.c_double(0.0)
      #     y = ctypes.c_double(0.0)
      #     g_pol0.GetPoint(i, x, y)
      #     err_x_low = g_pol0.GetErrorXlow(i)
      #     err_x_high = g_pol0.GetErrorXhigh(i)
      #     err_y_low = g_pol0.GetErrorYlow(i)
      #     err_y_high = g_pol0.GetErrorYhigh(i)

      #     print(f"Point {i}: X = {x.value:.4f} (+{err_x_high:.4f}, -{err_x_low:.4f}), "
      #           f"Y = {y.value:.4f} (+{err_y_high:.4f}, -{err_y_low:.4f})")
      # # TODO: DANNY WHY? :(
      # fit_pol0, h_uncert_pol0, h_pol0, uncerts_pol0 = FitSF(g_pol0,func='pol1_gt40')

      # fit_pol0.Write()
      # h_uncert_pol0.Write()

      name = fit_nom.GetName()

      stats_to_plot = []
      for x in uncerts_nom:
        x[1].SetName(name+'_%s_up' %x[0])
        x[2].SetName(name+'_%s_down' %x[0])
        stats_to_plot.append((x[1].Clone(), x[2].Clone()))
        x[1].Write()
        x[2].Write()

      # make some plots of SFs and uncertainties
      # PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='DM%(dm)s, %(era)s' % vars(), output_folder=output_folder)
      # CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
      # CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
      # dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
      if dm==0:
        PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='#tau^{ #pm} #rightarrow #pi^{ #pm} #nu_{#tau}, %(era)s' % vars(), output_folder=output_folder)
        CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
      if dm==1:
        PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='#tau^{ #pm} #rightarrow #pi^{ #pm} #pi^{ 0} #nu_{#tau}, %(era)s' % vars(), output_folder=output_folder)
        CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
      if dm==2:
        PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='#tau^{ #pm} #rightarrow #pi^{ #pm} #pi^{ 0} #pi^{ 0} #nu_{#tau}, %(era)s' % vars(), output_folder=output_folder)
        CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
      if dm==10:
        PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='#tau^{ #pm} #rightarrow #pi^{ #pm} #pi^{ #mp} #pi^{ #pm} #nu_{#tau}, %(era)s' % vars(), output_folder=output_folder)
        CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')
      if dm==11:
        PlotSF(g, h_uncert_nom, 'tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name, title='#tau^{ #pm} #rightarrow #pi^{ #pm} #pi^{ #mp} #pi^{ #pm} #pi^{ 0} #nu_{#tau}, %(era)s' % vars(), output_folder=output_folder)
        CompareSystsPlot(fit_nom,systs_to_plot,output_folder+'/'+'uncerts_systs_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        CompareSystsPlot(fit_nom,stats_to_plot,output_folder+'/'+'uncerts_stats_tau_sf_DM%(dm)s_%(era)s' % vars()+extra_name)
        dm_binned_strings[g.GetName()] = str(fit_nom.GetExpFormula('p')).replace('x','min(max(pt_2,20.),140.)')

# make plots of pT-dependent SFs
if not args.dm_bins:
  for era in eras:
    systs=[fout.Get('DMinclusive_%(era)s_syst_alleras' % vars()).Clone(), fout.Get('DMinclusive_%(era)s_syst_%(era)s' % vars()).Clone()]
    PlotpTBinned(fout.Get('DMinclusive_%(era)s' % vars()),systs,output_folder+'/'+'tau_sf_DMinclusive_%(era)s' % vars())

if args.dm_bins and args.saveJson:
  wp=args.wp
  sf_map = {}
  sf_map[wp] = {}
  for era in eras:
    print(f'DM-binned SFs for era {era}:')
    out='((gen_match_2!=5) + (gen_match_2==5)*('
    for dm in [0,1,2,10,11]:
      out+='(tau_decay_mode_2==%i)*(%s)+' % (dm, dm_binned_strings['DM%i_%s' % (dm,era)])
    out=out[:-1]
    out+='))'
    sf_map[wp][era] = out
    print(out)

  json_out_name = output_folder+'tau_SF_strings_dm_binned_%(wp)s' % vars() + extra_name+'.json'
  with open(json_out_name, 'w') as fp:
    json.dump(sf_map, fp, sort_keys=True, indent=4)


def compute_p_value(chi2, ndf):
    p_value = ROOT.TMath.Prob(chi2, int(ndf))

    return p_value

p_value = ROOT.TMath.Prob(tot_chi2, int(tot_ndf))
file_name = "chi_2_values_polynomials.txt"
print(f'\nTotal chi2/NDF, p-value = {tot_chi2}.2f/{tot_ndf}.0f, {p_value}.6f ')
with open(file_name, 'a') as file:
    # Write the formatted string to the file
    if args.split_fit:
       file.write("\n%(wp)s_splitfit" %vars())
    else:
       file.write("\n%(wp)s" %vars())
    file.write('\nTotal chi2/NDF, p-value = %.2f/%.0f, %.10f ' % (tot_chi2, tot_ndf, p_value))

