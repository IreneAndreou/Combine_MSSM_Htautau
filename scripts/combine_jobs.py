#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
def CreateBatchJob(name,cmd_list):
  if os.path.exists(job_file): os.system('rm %(name)s' % vars())
  os.system('echo "#!/bin/sh" >> %(name)s' % vars())
  os.system('echo "source /vols/grid/cms/setup.sh" >> %(name)s' % vars())
  os.system('echo "export SCRAM_ARCH=slc6_amd64_gcc481" >> %(name)s' % vars())
  os.system('echo "eval \'scramv1 runtime -sh\'" >> %(name)s' % vars())
  os.system('echo "source /vols/cms/ia2318/CMSSW_10_2_19/src/UserCode/ICHiggsTauTau/Analysis/HiggsTauTauRun2/scripts/setup_libs.sh" >> %(name)s' % vars())
  os.system('echo "ulimit -c 0" >> %(name)s' % vars())
  for cmd in cmd_list:
    os.system('echo "%(cmd)s" >> %(name)s' % vars())
  os.system('chmod +x %(name)s' % vars())
  print "Created job:",name

def SubmitBatchJob(name,time=600,memory=24,cores=1):
  error_log = name.replace('.sh','_error.log')
  output_log = name.replace('.sh','_output.log')
  if os.path.exists(error_log): os.system('rm %(error_log)s' % vars())
  if os.path.exists(output_log): os.system('rm %(output_log)s' % vars())
  if cores>1: os.system('qsub -e %(error_log)s -o %(output_log)s -V -q hep.q -pe hep.pe %(cores)s -l h_rt=0:%(time)s:0 -l h_vmem=%(memory)sG -cwd %(name)s' % vars())
  else: os.system('qsub -e %(error_log)s -o %(output_log)s -V -q hep.q -l h_rt=0:%(time)s:0 -l h_vmem=%(memory)sG -cwd %(name)s' % vars())


for wp in ["medium"]:#['loose', 'medium', 'tight', 'vtight', 'vvtight']:
  cmd_1 = 'python /vols/cms/ia2318/CMSSW_10_2_13/src/CombineHarvester/TauSF/scripts/run_all_by_dm_externalTES_floatTES.py -o tauSF_output_v2p5_%(wp)s_dm_2022_TES3 --wp %(wp)s -e 2022'% vars()
  cmd_2 = 'python /vols/cms/ia2318/CMSSW_10_2_13/src/CombineHarvester/TauSF/scripts/run_all_by_dm_externalTES_floatTES.py -o tauSF_output_v2p5_%(wp)s_tightVsEle_dm_2022_TES3 --wp %(wp)s -e 2022 --tightVsEle' % vars() 
  cmds = [cmd_1,cmd_2]
  vsele = ['vvloose', 'tight']
  for i in range(len(cmds)):
    vsel=vsele[i]
    job_file = 'job_%(wp)s_%(vsel)s.sh' % vars()
    CreateBatchJob(job_file, [cmds[i]])  
    SubmitBatchJob(job_file,time=600,memory=24,cores=1)
