import ROOT
import math

def DecomposeUncerts(fitresult, fit):
  # this function decomposes the uncertainties into orthogonal shifts
  shifted_functions = []
  # Decompose the covariance matrix into eigenvectors
  cov = ROOT.TMatrixD(fitresult.GetCovarianceMatrix())
  eig = ROOT.TMatrixDEigen(cov)
  eigenvectors = eig.GetEigenVectors()

  # Estimate uncertainty variations based on the eigenvectors
  pars = ROOT.TVectorD(fit.GetNpar())
  for i in range(fit.GetNpar()):
      pars[i] = fit.GetParameter(i)
  variances = eig.GetEigenValues()
  transposed_eigenvectors = eigenvectors.Clone().T()

  for i in range(fit.GetNpar()):

      temp = ROOT.TVectorD(fit.GetNpar())
      for j in range(fit.GetNpar()):
          temp[j] = transposed_eigenvectors(i, j)


      temp*=variances(i,i)**0.5
      fit_up=fit.Clone()  
      fit_down=fit.Clone() 

      # shift each parameter of the function in turn
      for j in range(fit.GetNpar()): 
        p_uncert = temp[j] 
        nom = fit.GetParameter(j)
        p_up=nom+p_uncert   
        p_down=nom-p_uncert   
        fit_up.SetParameter(j,p_up)
        fit_down.SetParameter(j,p_down)
        fit_up.SetName(fit.GetName()+'_uncert%i_up' %i)
        fit_down.SetName(fit.GetName()+'_uncert%i_down' %i)

      shifted_functions.append(('uncert%i' % i, fit_up, fit_down))

  return shifted_functions

def _crystalballEfficiency(m, m0, sigma, alpha, n, norm):
  
    sqrtPiOver2 = math.sqrt(ROOT.TMath.PiOver2())
    sqrt2       = math.sqrt(2.)
    sig         = abs(sigma)
    t           = (m - m0)/sig * alpha / abs(alpha)
    absAlpha    = abs(alpha/sig)
    a           = ROOT.TMath.Power(n/absAlpha, n) * ROOT.TMath.Exp(-0.5 * absAlpha * absAlpha)
    b           = absAlpha - n/absAlpha
    arg         = absAlpha / sqrt2;
  
    if   arg >  5.: ApproxErf =  1.
    elif arg < -5.: ApproxErf = -1.
    else          : ApproxErf = ROOT.TMath.Erf(arg)
  
    leftArea    = (1. + ApproxErf) * sqrtPiOver2
    rightArea   = ( a * 1./ROOT.TMath.Power(absAlpha-b, n-1) ) / (n - 1)
    area        = leftArea + rightArea
  
    if t <= absAlpha:
        arg = t / sqrt2
        if   arg >  5.: ApproxErf =  1.
        elif arg < -5.: ApproxErf = -1.
        else          : ApproxErf = ROOT.TMath.Erf(arg)
        return norm * (1 + ApproxErf) * sqrtPiOver2 / area
  
    else:
        return norm * (leftArea + a * (1/ROOT.TMath.Power(t-b,n-1) - \
                                       1/ROOT.TMath.Power(absAlpha - b,n-1)) / (1 - n)) / area

def crystalballEfficiency(x, par):
    x     = x[0]
    m0    = par[0]
    sigma = par[1]
    alpha = par[2]
    n     = par[3]
    norm  = par[4]
    return _crystalballEfficiency( x, m0, sigma, alpha, n, norm )

def crystalballEfficiencyCorrParams(x, par):
    x     = x[0]
    m0    = par[0]
    sigma = par[1]
    alpha = par[2]
    n     = par[1]
    norm  = par[3]
    return _crystalballEfficiency( x, m0, sigma, alpha, n, norm )

def FitSF(h,func='erf'):
  h_uncert = ROOT.TH1D(h.GetName()+'_uncert',"",1000,20,200)
  if func == 'erf':
    f2 = ROOT.TF1("f2","[0]*TMath::Erf((x-[1])/[2])+[3]",20.,200.)
    f2.SetParameter(2,40)
    f2.SetParameter(3,0)
  elif func == 'erf_rev':
    f2 = ROOT.TF1("f2","[0]*TMath::Erf((-x-[1])/[2])+[3]",20.,200.)
    f2.SetParameter(0,0.1)
    f2.SetParameter(1,-40)
    f2.SetParameter(2,10)
    f2.SetParameter(3,1)
  elif func == 'erf_extra':
    #error function with additional linear component
    f2 = ROOT.TF1("f2","[0]*(TMath::Erf((x-[1])/[2]) + [3] + [4]*x)",20.,200.) 
    f2.SetParameter(2,40)
    f2.SetParameter(3,0)
  elif func == 'erf_pol':
    #error function with additional constant
    f2 = ROOT.TF1("f2","(TMath::Erf((x/[0])) + [1])",20.,200.)
    f2.SetParameter(0,40)
    f2.SetParameter(2,0)
  elif func == 'logx':
   f2 = ROOT.TF1("f2", "[0] + [1]*TMath::Log(x)", 20., 200.)
  elif 'pol_order' in func:
   order=int(func.split('pol_order')[1])
   f2 = ROOT.TF1("f2", "[0] + [1]*pow(x,%i)" % order, 20., 200.)
   #f2 = ROOT.TF1("f2", "[0] + [1]*x + [2]*x*x + [3]*x*x*x", 20., 200.)
   #f2 = ROOT.TF1("f2", "[0] + [1]*pow(x,%i)" % order, 20., 200.)
  elif func == 'cb_eff':
    par = [10,5,6,2.,1.]
    f2 = ROOT.TF1("f2",crystalballEfficiency,20.,200.,5)
    f2.SetParameter(0,par[0]) # x0 
    f2.SetParameter(1,par[1]) # sigma
    f2.SetParameter(2,par[2]) # alpha
    f2.SetParameter(3,par[3]) # n
    f2.SetParameter(4,par[4]) #[4]
  elif func == 'pol0_gt40':
    f2 = ROOT.TF1("f2",'pol0',40.,200.)
  elif func == 'pol1_gt40':
    f2 = ROOT.TF1("f2",'pol1',40.,200.)
  elif func=='pol1_split':
    f2 = ROOT.TF1("f2",'(x<50)*([0]+[1]*x)+(x>=50)*([2]+[3]*x)',20.,200.)
  elif func=='pol1_split_constrained':
    split=50.
    f2 = ROOT.TF1("f2",'([0]+[1]*min(x,%(split).1f))' % vars(),20.,200.)
  elif 'pol' in func:
    f2 = ROOT.TF1("f2",func,20.,200.)
  else:
    f1 = ROOT.TF1("f1","landau",20,200)
    f2 = ROOT.TF1("f2","[0]*TMath::Landau(x,[1],[2])+[3]",20,200)

  # clone histogram and set all bins with >0 content
  if func=='landau':
    # fit first with landau to get initial values for parameters - pol values set to 0 initially
    h.Fit("f1",'IR')
    f2.SetParameter(0,f1.GetParameter(0)); f2.SetParameter(1,f1.GetParameter(1)); f2.SetParameter(2,f1.GetParameter(2)); f2.SetParameter(3,0)
  # now fit with the full functions
  # repeat fit up to 100 times until the fit converges properly
  rep = True
  count = 0
  maxN = 100
  while rep:
    #fitresult = h.Fit("f2",'SIR')
    fitresult = h.Fit("f2",'SR')
    rep = int(fitresult) != 0
    if not rep or count>maxN:
      ROOT.TVirtualFitter.GetFitter().GetConfidenceIntervals(h_uncert, 0.68)
      fit = f2
      uncerts = DecomposeUncerts(fitresult, fit)
      break
    count+=1
  fit.SetName(h.GetName()+'_fit')

  print(f'Chi2/NDF = {f2.GetChisquare()}.2f/{f2.GetNDF()}.0f, p-value = {f2.GetProb()}.2f')
  return fit, h_uncert, h, uncerts

def PlotSF(f, h, name, title='', output_folder='./'):
  c1 = ROOT.TCanvas()
  f.GetXaxis().SetTitle('p_{T} (GeV)')
  f.GetYaxis().SetTitle('Correction')
  f.SetTitle(title)
  f.SetLineColor(ROOT.kBlack)
  f.Draw('ape')
  h.Draw("e3 same")
  f.Draw('pesame')
  c1.RedrawAxis()
  h.SetStats(0)
  h.SetFillColor(ROOT.kBlue-10)
  latex = ROOT.TLatex()
  latex.SetNDC()
  latex.SetTextFont(42)
  latex.SetTextSize(0.05)
  latex.SetTextAlign(31)
  latex.DrawLatex(0.9, 0.91, "#scale[0.8]{59.7 fb^{-1} (13 TeV)}") #UL
  #latex.DrawLatex(0.9, 0.91, "#scale[0.8]{35.1 fb^{-1} (13.6 TeV)}") #2022
  c1.Print(output_folder+'/'+name+'.pdf')
