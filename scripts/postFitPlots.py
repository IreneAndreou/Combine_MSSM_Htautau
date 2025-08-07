import ROOT
import re
import math
import argparse
import json
import numpy as np
import sys
import os
import fnmatch
from array import array
import CombineHarvester.CombineTools.plotting as plot

ROOT.gROOT.SetBatch(ROOT.kTRUE)
ROOT.TH1.AddDirectory(False)

#example commands:

#unrolled prefit plot for nobtag category with blinded bins
#python scripts/postFitPlotJetFakes.py --mode prefit --file_dir htt_mt_32_2018 -f shapes_mt_32_2018.root --ratio  --log_y --manual_blind
#1D prefit plot for btag category with blinded bins
#python scripts/postFitPlotJetFakes.py --mode prefit --file_dir htt_mt_35_2018 -f shapes_mt_35_2018.root --ratio  --manual_blind

def DrawCMSLogo(pad, cmsText, extraText, iPosX, relPosX, relPosY, relExtraDY, extraText2='', cmsTextSize=0.8,relExtraDX=0.0):
    """Blah

    Args:
        pad (TYPE): Description
        cmsText (TYPE): Description
        extraText (TYPE): Description
        iPosX (TYPE): Description
        relPosX (TYPE): Description
        relPosY (TYPE): Description
        relExtraDY (TYPE): Description
        extraText2 (str): Description
        cmsTextSize (float): Description

    Returns:
        TYPE: Description
    """
    pad.cd()
    cmsTextFont = 62  # default is helvetic-bold

    writeExtraText = len(extraText) > 0
    writeExtraText2 = len(extraText2) > 0
    extraTextFont = 52

    # text sizes and text offsets with respect to the top frame
    # in unit of the top margin size
    lumiTextOffset = 0.2
    # cmsTextSize = 0.8
    # float cmsTextOffset    = 0.1;  // only used in outOfFrame version

    # ratio of 'CMS' and extra text size
    extraOverCmsTextSize = 0.76

    outOfFrame = False
    if iPosX / 10 == 0:
        outOfFrame = True

    alignY_ = 3
    alignX_ = 2
    if (iPosX / 10 == 0):
        alignX_ = 1
    if (iPosX == 0):
        alignX_ = 1
    if (iPosX == 0):
        alignY_ = 1
    if (iPosX / 10 == 1):
        alignX_ = 1
    if (iPosX / 10 == 2):
        alignX_ = 2
    if (iPosX / 10 == 3):
        alignX_ = 3
    # if (iPosX == 0): relPosX = 0.14
    align_ = 10 * alignX_ + alignY_

    l = pad.GetLeftMargin()
    t = pad.GetTopMargin()
    r = pad.GetRightMargin()
    b = pad.GetBottomMargin()

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextAngle(0)
    latex.SetTextColor(ROOT.kBlack)

    extraTextSize = extraOverCmsTextSize * cmsTextSize
    pad_ratio = (float(pad.GetWh()) * pad.GetAbsHNDC()) / \
        (float(pad.GetWw()) * pad.GetAbsWNDC())
    if (pad_ratio < 1.):
        pad_ratio = 1.

    if outOfFrame:
        latex.SetTextFont(cmsTextFont)
        latex.SetTextAlign(11)
        latex.SetTextSize(cmsTextSize * t * pad_ratio)
        latex.DrawLatex(l, 1 - t + lumiTextOffset * t, cmsText)

    posX_ = 0
    if iPosX % 10 <= 1:
        posX_ = l + relPosX * (1 - l - r)
    elif (iPosX % 10 == 2):
        posX_ = l + 0.5 * (1 - l - r)
    elif (iPosX % 10 == 3):
        posX_ = 1 - r - relPosX * (1 - l - r)

    posY_ = 1 - t - relPosY * (1 - t - b)
    if not outOfFrame:
        latex.SetTextFont(cmsTextFont)
        latex.SetTextSize(cmsTextSize * t * pad_ratio)
        latex.SetTextAlign(align_)
        latex.DrawLatex(posX_, posY_, cmsText)
        if writeExtraText:
            latex.SetTextFont(extraTextFont)
            latex.SetTextAlign(align_)
            latex.SetTextSize(extraTextSize * t * pad_ratio)
            latex.DrawLatex(
                posX_- relExtraDX, posY_ - relExtraDY * cmsTextSize * t, extraText)
            if writeExtraText2:
                latex.DrawLatex(
                    posX_, posY_ - 1.8 * relExtraDY * cmsTextSize * t, extraText2)
    elif writeExtraText:
        if iPosX == 0:
            posX_ = l + relPosX * (1 - l - r) + relExtraDX
            posY_ = 1 - t + lumiTextOffset * t
        latex.SetTextFont(extraTextFont)
        latex.SetTextSize(extraTextSize * t * pad_ratio)
        latex.SetTextAlign(align_)
        latex.DrawLatex(posX_, posY_, extraText)


def getHistogram(fname, histname, dirname='', postfitmode='prefit', allowEmpty=False, logx=False):
  
    outname = fname.GetName()

    if isinstance(dirname,list) or isinstance(histname,list):
      if not isinstance(dirname,list): dirname = [dirname]
      if not isinstance(histname,list): histname = [histname]

      firstHist=True
      for d in dirname: 
        for h in histname: 
          htemp = getHistogram(fname, h, d, postfitmode, allowEmpty, logx)[0]
          if firstHist: 
            histo=htemp.Clone()
            firstHist=False
          else: histo.Add(htemp)
      return [histo,outname]
    
    for key in fname.GetListOfKeys():
        histo = fname.Get(key.GetName())
        dircheck = False
        if dirname == '' : dircheck=True
        elif dirname in key.GetName(): dircheck=True
        #print histo
        #print key.GetName()
        #print histname
        #print isinstance(histo,ROOT.TH1F)
        #print key.GetName()==histname
        #print postfitmode in key.GetName()
        #print dircheck
        if isinstance(histo,ROOT.TH1F) and key.GetName()==histname:
            if logx:
                bin_width = histo.GetBinWidth(1)
                xbins = []
                xbins.append(bin_width - 1)
                axis = histo.GetXaxis()
                for i in range(1,histo.GetNbinsX()+1):
                    xbins.append(axis.GetBinUpEdge(i))
                rethist = ROOT.TH1F(histname,histname,histo.GetNbinsX(),array('d',xbins))
                rethist.SetBinContent(1,histo.GetBinContent(1)*(histo.GetBinWidth(1)-(bin_width - 1))/(histo.GetBinWidth(1)))
                rethist.SetBinError(1,histo.GetBinError(1)*(histo.GetBinWidth(1)-(bin_width - 1))/(histo.GetBinWidth(1)))
                for i in range(2,histo.GetNbinsX()+1):
                    rethist.SetBinContent(i,histo.GetBinContent(i))
                    rethist.SetBinError(i,histo.GetBinError(i))
                histo = rethist
            return [histo,outname]
        elif isinstance(histo,ROOT.TDirectory) and dircheck:
            return getHistogram(histo,histname, allowEmpty=allowEmpty, logx=logx)
    print('Failed to find %(postfitmode)s histogram with name %(histname)s in file %(fname)s in directory %(dirname)s '%vars())
    if allowEmpty:
        return [ROOT.TH1F('empty', '', 1, 0, 1), outname]
    else:
        return None


def signalComp(leg,plots,colour,stacked):
    return dict([('leg_text',leg),('plot_list',plots),('colour',colour),('in_stack',stacked)])

def backgroundComp(leg,plots,colour):
    return dict([('leg_text',leg),('plot_list',plots),('colour',colour)])

def createAxisHists(n,src,xmin=0,xmax=499):
    result = []
    for i in range(0,n):
        res = src.Clone()
        res.Reset()
        res.SetTitle("")
        res.SetName("axis%(i)d"%vars())
        res.SetAxisRange(xmin,xmax)
        res.SetStats(0)
        result.append(res)
    return result

def PositionedLegendUnrolled(width, height, pos, offset):
    o = offset
    w = width
    h = height
    l = ROOT.gPad.GetLeftMargin()
    t = ROOT.gPad.GetTopMargin()
    b = ROOT.gPad.GetBottomMargin()
    r = ROOT.gPad.GetRightMargin()
    if pos == 1:
        return ROOT.TLegend(l + o, 1 - t - o - h, l + o + w, 1 - t - o, '', 'NBNDC')
    if pos == 2:
        c = l + 0.5 * (1 - l - r)
        return ROOT.TLegend(c - 0.5 * w, 1 - t - o - h, c + 0.5 * w, 1 - t - o, '', 'NBNDC')
    if pos == 3:
        return ROOT.TLegend(1 - r - o - w, 1 - t - o - h, 1 - r - o, 1 - t - o, '', 'NBNDC')
    if pos == 4:
        return ROOT.TLegend(l + o, b + o, l + o + w, b + o + h, '', 'NBNDC')
    if pos == 5:
        c = l + 0.5 * (1 - l - r)
        return ROOT.TLegend(c - 0.5 * w, b + o, c + 0.5 * w, b + o + h, '', 'NBNDC')
    if pos == 6:
        return ROOT.TLegend(1 - r - o - w, b + o, 1 - r - o, b + o + h, '', 'NBNDC')
    if pos == 7:
        return ROOT.TLegend(1 - o - w, 1 - t - o - h, 1 - o, 1 - t - o, '', 'NBNDC')

def DrawTitleUnrolled(pad, text, align, scale=1):
    pad_backup = ROOT.gPad
    pad.cd()
    t = pad.GetTopMargin()
    l = pad.GetLeftMargin()
    r = pad.GetRightMargin()

    pad_ratio = (float(pad.GetWh()) * pad.GetAbsHNDC()) / \
        (float(pad.GetWw()) * pad.GetAbsWNDC())
    if pad_ratio < 1.:
        pad_ratio = 1.

    textSize = 0.6
    textOffset = 0.2

    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextAngle(0)
    latex.SetTextColor(ROOT.kBlack)
    latex.SetTextFont(42)
    latex.SetTextSize(textSize * t * pad_ratio * scale)

    y_off = 1 - t + textOffset * t + 0.01
    if align == 1:
        latex.SetTextAlign(11)
        latex.DrawLatex(l, y_off, text)
    if align == 2:
        latex.SetTextAlign(21)
        latex.DrawLatex(l + (1 - l - r) * 0.5, y_off, text)
    if align == 3:
        latex.SetTextAlign(31)
        latex.DrawLatex(1 - r, y_off, text)
    pad_backup.cd()

    
def parse_arguments():
    parser = argparse.ArgumentParser()
    #Ingredients when output of PostFitShapes is already provided
    parser.add_argument('--file', '-f',
                    help='Input file if shape file has already been created')
    parser.add_argument('--channel',default='',
                    help='Option to specify channel in case it is not obtainable from the shape file name')
    parser.add_argument('--file_dir',default='',
                    help='Name of TDirectory inside shape file')
    parser.add_argument('--mode',default='',
                    help='Prefit or postfit')
    #Blinding options
    parser.add_argument('--manual_blind', action='store_true',
                    default=False,help='Blind data with hand chosen range')
    parser.add_argument('--x_blind_min',default=70,
                    help='Minimum x for manual blinding')
    parser.add_argument('--x_blind_max',default=110,
                    help='Maximum x for manual blinding')
    parser.add_argument('--empty_bin_error',action='store_true',
                    default=False, help='Draw error bars for empty bins')
    #General plotting options
    parser.add_argument('--ratio', default=False,action='store_true',
                    help='Draw ratio plot')
    parser.add_argument('--custom_x_range', action='store_true', 
                    default=False, help='Fix x axis range')
    parser.add_argument('--x_axis_min', default=0.0,
                    help='Fix x axis minimum')
    parser.add_argument('--x_axis_max', default=1000.0, 
                    help='Fix x axis maximum')
    parser.add_argument('--custom_y_range', action='store_true', 
                    default=False, help='Fix y axis range')
    parser.add_argument('--y_axis_min', action='store', default=1., 
                    help='Fix y axis minimum')
    parser.add_argument('--y_axis_max', action='store', default=100.0,
                    help='Fix y axis maximum')
    parser.add_argument('--log_y', action='store_true',
                    help='Use log for y axis')
    parser.add_argument('--log_x', action='store_true',
                    help='Use log for x axis')
    parser.add_argument('--extra_pad', default=0.0, 
                    help='Fraction of extra whitespace at top of plot')
    parser.add_argument('--outname',default='',
                    help='Optional string for start of output filename')
    parser.add_argument('--ratio_range',  default="", 
                    help='y-axis range for ratio plot in format MIN,MAX')
    parser.add_argument('--use_asimov', default=False, 
                    action='store_true', help='')
    parser.add_argument('--proper_errors_uniform', default=False, 
                    action='store_true', help='')
    parser.add_argument('--cms_label',default='',
                    help='Optional additional string for CMs label')
    return parser.parse_args()

def main(args):

    fitvars='m_sv_vs_pt_tt'
    fitvars='m_sv'

    if len(args.file_dir.split("_"))>=4: era = args.file_dir.split("_")[3]
    else: era='all'
    if era == "2016":
        lumi = "36.3 fb^{-1} (13 TeV)"
    elif era == "2017":
        lumi = "41.5 fb^{-1} (13 TeV)"
    elif era == "2018":
        lumi = "59.7 fb^{-1} (13 TeV)"
    elif era == "all":
        lumi = "138 fb^{-1} (13 TeV)"
    elif era == "2022_preEE":
        lumi = "8.08 fb^{-1} (13.6 TeV)"
    elif era == "2022_postEE":
        lumi = "27.0 fb^{-1} (13.6 TeV)"
    elif era == "2022":
        lumi = "35.08 fb^{-1} (13.6 TeV)"
    else:
        lumi = era
    plot.ModTDRStyle(width=1800, height=700, r=0.4, l=0.16, t=0.12,b=0.15)
    ROOT.TGaxis.SetExponentOffset(-0.06, 0.01, "y")
    # Channel & Category label

    if args.channel == '':
        args.channel = args.file_dir.split("_")[1]
    if args.channel == "tt":
        channel_label = "#tau_{h}#tau_{h}"
    if args.channel == 'mm':
        channel_label = "#mu_{}#mu_{}"
    if args.channel == "lt":
        channel_label = "#mu_{}#tau_{h}+e_{}#tau_{h}"
    if args.channel == "mt":
        channel_label = "#mu_{}#tau_{h}"
    if args.channel == "et":
        channel_label = "e_{}#tau_{h}"
    if args.channel == "em":
        channel_label = "e_{}#mu_{}"

    #bin_number = args.file_dir.split("_")[2]
    plot.ModTDRStyle(r=0.04, l=0.18)
    x_title = "m_{#tau#tau} (GeV)"

    file_dir = args.file_dir
    mode = args.mode
    manual_blind = args.manual_blind
    x_blind_min = args.x_blind_min
    x_blind_max = args.x_blind_max
    cms_label = args.cms_label
    empty_bin_error = args.empty_bin_error
    extra_pad = float(args.extra_pad)
    custom_x_range = args.custom_x_range
    custom_y_range = args.custom_y_range
    x_axis_min = float(args.x_axis_min)
    x_axis_max = float(args.x_axis_max)
    y_axis_min = float(args.y_axis_min)
    y_axis_max = float(args.y_axis_max)
    log_y=args.log_y
    log_x=args.log_x
    if(args.outname != ''):
        outname=args.outname + '_'
    else:
        outname=''
  
    if args.file:
        print("Providing shape file: ", args.file, ", with specified subdir name: ", file_dir)
        shape_file=args.file
        shape_file_name=args.file
    
    histo_file = ROOT.TFile(shape_file)
 
    #Store plotting information for different backgrounds 
    background_schemes = {
#        'mt':[
#                backgroundComp("t#bar{t}",["TTT","TTJ"],ROOT.TColor.GetColor(155,152,204)),
#                backgroundComp("QCD", ["QCD"], ROOT.TColor.GetColor(250,202,255)),
#                backgroundComp("Electroweak",["VVT","VVJ","W"],ROOT.TColor.GetColor(222,90,106)),
#                backgroundComp("Z#rightarrow#mu#mu",["ZL","ZJ"],ROOT.TColor.GetColor(100,192,232)),
#                backgroundComp("Z#rightarrow#tau#tau",["ZTT"],ROOT.TColor.GetColor(248,206,104)),
#                ],

        'mt':[
                backgroundComp("t#bar{t}",["TTJ"],ROOT.TColor.GetColor(155,152,204)),
                backgroundComp("QCD", ["QCD"], ROOT.TColor.GetColor(250,202,255)),
                backgroundComp("Electroweak",["VVJ","W"],ROOT.TColor.GetColor(222,90,106)),
                backgroundComp("Z#rightarrow#mu#mu",["ZL","ZJ"],ROOT.TColor.GetColor(100,192,232)),
                backgroundComp("Genuine #tau_{h}",["ZTT","TTT","VVT"],ROOT.TColor.GetColor(248,206,104)),
                ],
        'lt':[
                backgroundComp("t#bar{t}",["TTJ"],ROOT.TColor.GetColor(155,152,204)),
                backgroundComp("QCD", ["QCD"], ROOT.TColor.GetColor(250,202,255)),
                backgroundComp("Electroweak",["VVJ","W"],ROOT.TColor.GetColor(222,90,106)),
                backgroundComp("Z#rightarrow#mu#mu",["ZL","ZJ"],ROOT.TColor.GetColor(100,192,232)),
                backgroundComp("Genuine #tau_{h}",["ZTT","TTT","VVT"],ROOT.TColor.GetColor(248,206,104)),
                ],
        'mm':[
                backgroundComp("QCD", ["QCD"], ROOT.TColor.GetColor(250,202,255)),
                backgroundComp("t#bar{t}",["TTL","TTJ"],ROOT.TColor.GetColor(155,152,204)),
                backgroundComp("Electroweak",["VVL","VVJ","W"],ROOT.TColor.GetColor(222,90,106)),
                backgroundComp("Z#rightarrow#tau#tau",["ZTT"],ROOT.TColor.GetColor(248,206,104)),
                backgroundComp("Z#rightarrow#mu#mu",["ZL","ZJ"],ROOT.TColor.GetColor(100,192,232)),
                ],
        }




    file_dir_list = []
    file_dir_list = [file_dir]
    print("%(log_x)s" %vars())
    bkghist = getHistogram(histo_file,'TotalBkg',file_dir, mode, logx=log_x)[0]
    
    if not args.use_asimov:
        total_datahist = getHistogram(histo_file,"data_obs",file_dir, mode, logx=log_x)[0]
    else:
        total_datahist = getHistogram(histo_file,"TotalProcs",file_dir, mode, logx=log_x)[0].Clone()
        for bin_ in range(1,total_datahist.GetNbinsX()+1):
            content = total_datahist.GetBinContent(bin_)
            total_datahist.SetBinError(bin_, np.sqrt(content))


    blind_datahist = total_datahist.Clone()
    total_datahist.SetMarkerStyle(20)
    blind_datahist.SetMarkerStyle(20)
    blind_datahist.SetLineColor(1)

    total_bkg = getHistogram(histo_file,"TotalBkg",file_dir, mode, logx=log_x)[0].Clone()
    azimov_datahist = blind_datahist.Clone()
    for i in range(0, azimov_datahist.GetNbinsX()+1):
      azimov_datahist.SetBinContent(i,-0.1)
      azimov_datahist.SetBinError(i,0)

    azimov_datahist.SetLineColor(ROOT.kRed)
    azimov_datahist.SetMarkerColor(ROOT.kRed)

    #Blinding by hand using requested range, set to 70-110 by default
    # for 0jet category
    if manual_blind:
        for i in range(0,total_datahist.GetNbinsX()):
            low_edge = total_datahist.GetBinLowEdge(i+1)
            high_edge = low_edge+total_datahist.GetBinWidth(i+1)
            if ((low_edge > float(x_blind_min) and low_edge < float(x_blind_max)) 
                    or (high_edge > float(x_blind_min) and high_edge<float(x_blind_max))):
                blind_datahist.SetBinContent(i+1, -0.1)
                blind_datahist.SetBinError(i+1,0)
                c = total_bkg.GetBinContent(i+1)
                azimov_datahist.SetBinContent(i+1,c)
                azimov_datahist.SetBinError(i+1,c**.5)

    #Set bin errors for empty bins if required:
    if empty_bin_error:
        for i in range (1,blind_datahist.GetNbinsX()+1):
            if blind_datahist.GetBinContent(i) == 0:
                blind_datahist.SetBinError(i,1.8)
    #Set uniform bin errors properly for Content < 10 bins
    if args.proper_errors_uniform:
        proper_errs_dict = {
                0: 1.29, 1: 2.38, 2: 3.51, 3: 4.20, 4: 4.44, 5: 5.06,
                6: 5.46, 7: 6.05, 8: 6.02, 9: 6.46 
                }
        for i in range (1,blind_datahist.GetNbinsX()+1):
            if blind_datahist.GetBinContent(i) < 9.5 and blind_datahist.GetBinContent(i) >= 0:
                new_err = proper_errs_dict[round(blind_datahist.GetBinContent(i))]
                blind_datahist.SetBinError(i, new_err)

    #Normalise by bin width 
    scale=1.0
    bkghist.Scale(scale,"width")

    blind_datahist.Scale(scale,"width")
    azimov_datahist.Scale(scale,"width")

    blind_datagraph = ROOT.TGraphAsymmErrors(blind_datahist)
    azimov_datagraph = ROOT.TGraphAsymmErrors(azimov_datahist)

    channel = args.channel
    
    #Create stacked plot for the backgrounds
    bkg_histos = []

    integral_raw = {}
    for i,t in enumerate(background_schemes[channel]):
        plots = t['plot_list']
        isHist = False
        h = ROOT.TH1F()
        for j,k in enumerate(plots):
            if h.GetEntries()==0 and getHistogram(histo_file,k, file_dir,mode,False,logx=log_x) is not None:
                isHist = True
                h = getHistogram(histo_file,k, file_dir,mode, logx=log_x)[0]
                h.SetName(k)
            else:
                if getHistogram(histo_file,k, file_dir,mode, False, logx=log_x) is not None:
                    isHist = True
                    h.Add(getHistogram(histo_file,k, file_dir,mode,logx=log_x)[0])
        print(h.GetName())
        integral_raw[h.GetName()] = h.Integral()
        print(f"Integral KSVAVAASADV: {h.Integral()}")
        h.SetFillColor(t['colour'])
        h.SetLineColor(ROOT.kBlack)
        h.SetMarkerSize(0)
        
        h.Scale(scale,"width")
        if isHist:
            bkg_histos.append(h)
    
    stack = ROOT.THStack("hs","")
    for hists in bkg_histos:
        stack.Add(hists)
    
    #Setup style related things
    c2 = ROOT.TCanvas()
    c2.cd()
    
    if args.ratio:
        pads=plot.TwoPadSplit(0.35,0.01,0.01)
    else:
        pads=plot.OnePad()

    for p in pads: p.SetFrameLineWidth(1)

    pads[0].cd()
    if(log_y):
        pads[0].SetLogy(1)
    if(log_x):
        pads[0].SetLogx(1)
    
    if custom_x_range:
            if x_axis_max > bkghist.GetXaxis().GetXmax(): x_axis_max = bkghist.GetXaxis().GetXmax()
    if args.ratio:
        if(log_x): 
            pads[1].SetLogx(1)
        axish = createAxisHists(2,bkghist,bkghist.GetXaxis().GetXmin(),bkghist.GetXaxis().GetXmax()-0.01)
        axish[1].GetXaxis().SetTitle(x_title)
        axish[1].GetYaxis().SetNdivisions(4)
        axish[1].GetYaxis().SetLabelSize(0.033)
        axish[1].GetXaxis().SetLabelSize(0.033)
        axish[0].GetYaxis().SetTitleSize(0.048)
        axish[0].GetYaxis().SetLabelSize(0.033)
        axish[0].GetYaxis().SetTitleOffset(0.5)
        axish[0].GetXaxis().SetTitleSize(0)
        axish[0].GetXaxis().SetLabelSize(0)
        axish[0].GetYaxis().SetTitleSize(axish[1].GetXaxis().GetTitleSize())
        axish[0].GetXaxis().SetRangeUser(x_axis_min,bkghist.GetXaxis().GetXmax()-0.01)
        axish[1].GetXaxis().SetRangeUser(x_axis_min,bkghist.GetXaxis().GetXmax()-0.01)
        axish[0].GetXaxis().SetMoreLogLabels()
        axish[0].GetXaxis().SetNoExponent()
        axish[1].GetXaxis().SetMoreLogLabels()
        axish[1].GetXaxis().SetNoExponent()
        axish[1].GetXaxis().SetTitleOffset(0.85)

        axish[0].GetXaxis().SetRangeUser(0.,bkghist.GetXaxis().GetXmax()-0.01)
        axish[1].GetXaxis().SetRangeUser(0.,bkghist.GetXaxis().GetXmax()-0.01)
 
        if custom_x_range:
            axish[0].GetXaxis().SetRangeUser(x_axis_min,x_axis_max-0.01)
            axish[1].GetXaxis().SetRangeUser(x_axis_min,x_axis_max-0.01)
        if custom_y_range:
            axish[0].GetYaxis().SetRangeUser(y_axis_min,y_axis_max)
            axish[1].GetYaxis().SetRangeUser(y_axis_min,y_axis_max)
    else:
        axish = createAxisHists(1,bkghist,bkghist.GetXaxis().GetXmin(),bkghist.GetXaxis().GetXmax()-0.01)
        if custom_x_range:
            axish[0].GetXaxis().SetRangeUser(x_axis_min,x_axis_max-0.01)
        if custom_y_range:
            axish[0].GetYaxis().SetRangeUser(y_axis_min,y_axis_max)
    axish[0].GetYaxis().SetTitleOffset(0.5)
    axish[1].GetYaxis().SetTitleOffset(0.5)
    axish[0].GetYaxis().SetTitle("dN/dm_{#tau#tau} (1/GeV)")
    axish[0].GetYaxis().SetTitleOffset(1.5)
    axish[1].GetYaxis().SetTitleOffset(1.5)

    axish[0].GetXaxis().SetTitle(x_title)
        
    if not custom_y_range: axish[0].SetMaximum(extra_pad*bkghist.GetMaximum())
    if not custom_y_range: 
        if(log_y): 
            ymin = 0.1
            axish[0].SetMinimum(ymin)
        else: 
            axish[0].SetMinimum(0)
    
    hist_indices = [0] 
    for i in hist_indices:
        pads[i].cd()
        axish[i].Draw("AXIS")

        bkghist.SetMarkerSize(0)
        bkghist.SetFillColor(2001)
        bkghist.SetLineColor(1)
        bkghist.SetLineWidth(1)
        bkghist.SetFillColor(plot.CreateTransparentColor(12,0.4))
        bkghist.SetLineColor(0)    

        stack.Draw("histsame")

        integrals = []
        integral_names = []
        stack_hist_list = stack.GetHists()
        for rip in range(stack_hist_list.GetSize()):
            h = stack_hist_list.At(rip)
            print(f"{h.GetName()} → {h.Integral():.2f}")
            integrals.append(h.Integral())
            if h.GetName() == "VVJ":
                integral_names.append("EWK")
            else:
                integral_names.append(h.GetName())


        bkghist.Draw("e2same")
        blind_datagraph_extra = blind_datagraph.Clone()
        blind_datagraph_extra.Draw("P Z 0 same")
        blind_datagraph.SetMarkerSize(0.)
        blind_datagraph.Draw("P Z 0 same")

        azimov_datagraph_extra = azimov_datagraph.Clone()
        azimov_datagraph_extra.Draw("P Z 0 same")
        azimov_datagraph.SetMarkerSize(0.)
        azimov_datagraph.Draw("P Z 0 same")

        axish[i].Draw("axissame")
    
    pads[0].cd()
    pads[0].SetTicks(1)
    pads[1].SetTicks(1)
    #Setup legend
    legend = plot.PositionedLegend(0.45,0.33,3,0.02,0.02)
    legend.SetTextSize(0.030)
    legend.SetTextFont(42)
    legend.SetFillStyle(0)
    
    legend.AddEntry(total_datahist,"Observed","PEl")
    #Drawn on legend in reverse order looks better
    bkg_histos.reverse()

    background_schemes[channel].reverse()
    leg_hists = [None]*len(bkg_histos)
    for legi,hists in enumerate(bkg_histos):
        legend.AddEntry(hists,background_schemes[channel][legi]['leg_text'],"f")
    #legend.AddEntry(bkghist,"Background uncertainty","f")
    # Retrieve the bin contents
    bin_contents = [bkghist.GetBinError(bin) for bin in range(1, bkghist.GetNbinsX() + 1)]

    # Print the bin contents
    for bin, content in enumerate(bin_contents): print("Bin {}: {}".format(bin+1, content))
    bkghist.SetLineWidth(0)
    legend.AddEntry(bkghist,"Bkg. unc.","f")
    legend.Draw("same")

    latex2 = ROOT.TLatex()
    latex2.SetNDC()
    latex2.SetTextAngle(0)
    latex2.SetTextColor(ROOT.kBlack)
    latex2.SetTextFont(42)
    textsize=0.033#0.027
    begin_left=None
    ypos = 0.955
    latex2 = ROOT.TLatex()
    latex2.SetNDC()
    latex2.SetTextAngle(0)
    latex2.SetTextColor(ROOT.kBlack)
    latex2.SetTextSize(textsize)
    if begin_left == None:
        #begin_left = 0.145
        begin_left = 0.180
    latex2.SetTextFont(42)
    latex2.DrawLatex(begin_left, 0.960, channel_label)
    latex2.DrawLatex(begin_left + 0.075, 0.960, mode.upper())
    top = 0.86


    for key, integ in integral_raw.items():
        if key == 'VVJ':
            key ==  "EWK"

        latex2.SetTextSize(0.025)  # Set smaller font size
        latex2.DrawLatex(begin_left + 0.05, top, f"{key}: {integ:.2f}")
        top -= 0.03

    # for name, integ in zip(integral_names, integrals):
    #     latex2.SetTextSize(0.025)  # Set smaller font size
    #     latex2.DrawLatex(begin_left + 0.05, top, f"{name}: {integ:.2f}")
    #     top -= 0.03



    # print('\n\nGET QCD AND W YIELDS...')
    # for i, histo in enumerate(bkg_histos):
    #     print(f"Background {i + 1}: {histo.GetName()}, Integral: {histo.Integral()}")



    #CMS and lumi labels
    plot.FixTopRange(pads[0], plot.GetPadYMax(pads[0]), extra_pad if extra_pad>0 else 0.5)
    extra=cms_label
    #extra='Preliminary'
    #DrawCMSLogo(pads[0], 'CMS', extra, 0, 0.07, -0.0, 2.0, '', 0.85, relExtraDX=0.05)
    # cms_scale=1.0
    # DrawCMSLogo(pads[0], 'CMS', extra, 11, 0.045, 0.05, 1.0, '', cms_scale)

    plot.DrawTitle(pads[0], lumi, 3, textSize=0.6)
    
    #Add ratio plot if required
    axish[1].GetYaxis().SetTitle("Obs./Exp.")
    if args.ratio:
        ratio_bkghist = plot.MakeRatioHist(bkghist,bkghist,True,False)
        #print bkghist.GetMeanError()


        bkghist_errors = bkghist.Clone()
        #for i in range(1,bkghist_errors.GetNbinsX()+1): bkghist_errors.SetBinContent(i,bkghist.GetBinError(i))
        for i in range(1,bkghist_errors.GetNbinsX()+1): bkghist_errors.SetBinContent(i,1.)
        ratio_datahist_ = plot.MakeRatioHist(blind_datahist,bkghist,True,False)
        azimov_ratio_datahist_ = plot.MakeRatioHist(azimov_datahist,bkghist,True,False)

        ratio_datahist = ROOT.TGraphAsymmErrors(ratio_datahist_)
        azimov_ratio_datahist = ROOT.TGraphAsymmErrors(azimov_ratio_datahist_)

        pads[1].cd()
        #pads[1].SetGrid(0,1)
        axish[1].Draw("axis")
        axish[1].SetMinimum(float(args.ratio_range.split(',')[0]))
        axish[1].SetMaximum(float(args.ratio_range.split(',')[1]))
        ratio_bkghist.SetMarkerSize(0)

        ratio_bkghist.Draw("e2same")
        ratio_datahist.Draw("P Z 0 same")

        if args.manual_blind: azimov_ratio_datahist.Draw("P Z 0 same")
        pads[1].RedrawAxis("G")

    pads[0].cd()
    pads[0].GetFrame().Draw()
    pads[0].RedrawAxis()
    
    #Save as pdf with some semi sensible filename

    shape_file_name = shape_file_name.replace(".root","")
    shape_file_name = shape_file_name.replace("_shapes","")
    outname += shape_file_name+"_"+file_dir.strip("htt").strip("_")
    if(log_x): 
        outname+="_logx"
    c2.SaveAs("%(outname)s.pdf"%vars())

    del c2
    histo_file.Close()

if __name__ == "__main__":
    args = parse_arguments()
    main(args)
    

