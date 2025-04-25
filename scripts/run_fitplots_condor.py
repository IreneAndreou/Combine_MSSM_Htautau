import os
import sys


import argparse
import subprocess



def get_args():
    parser = argparse.ArgumentParser(description="Run pre or post fit plotting")
    parser.add_argument('--fit_dir', required=True, help='Desired classifier channel')
    parser.add_argument('--era', required=False, default="Run3_2022", help='Era')
    parser.add_argument('--postfit', action='store_true', help="plot postfit")
    return parser.parse_args()




def create_condor_submission_file(fit_dir, bin_name, log_dir, is_postfit=False):

    if is_postfit:
        executable_file_path = os.path.join(log_dir, f'{bin_name}_postfit.sh')
        executable_file_content = f"""
#!/bin/bash
source /vols/grid/cms/setup.sh
cd /vols/cms/lcr119/offline/HiggsCP/IDSFs/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF
cmsenv
echo "Environment activated..."
python3 scripts/PostFitShapesCombEras.py -f {fit_dir}/cmb/multidimfit.ztt.bestfit.singles.robustHesse.root:fit_mdf -w {fit_dir}/cmb/ws.root -d {fit_dir}/cmb/combined.txt.cmb --output {os.path.join(args.fit_dir, 'postfit')}/{bin_name}_postfit.root -b {bin_name} --postfit
python3 scripts/postFitPlots.py --file {os.path.join(args.fit_dir, 'postfit')}/{bin_name}_postfit.root --file_dir {bin_name} --ratio --ratio_range 0.5,1.5 --mode postfit
"""
        submission_file_content = f"""
executable = {executable_file_path}
output = {log_dir}/{bin_name}_postfit.out
error = {log_dir}/{bin_name}_postfit.err
log = {log_dir}/{bin_name}_postfit.log
request_memory = 8000
request_cpus = 1
+MaxRuntime = 2800
queue
"""
        submission_file_path = os.path.join(log_dir, f'condor_submit_{bin_name}_postfit.sub')

    else:
        executable_file_path = os.path.join(log_dir, f'{bin_name}_prefit.sh')
        executable_file_content = f"""
#!/bin/bash
source /vols/grid/cms/setup.sh
cd /vols/cms/lcr119/offline/HiggsCP/IDSFs/CMSSW_14_1_0_pre4/src/CombineHarvester/TauSF
cmsenv
echo "Environment activated..."
python3 scripts/PostFitShapesCombEras.py -f {fit_dir}/cmb/multidimfit.ztt.bestfit.singles.robustHesse.root:fit_mdf -w {fit_dir}/cmb/ws.root -d {fit_dir}/cmb/combined.txt.cmb --output {os.path.join(args.fit_dir, 'prefit')}/{bin_name}_prefit.root -b {bin_name}
python3 scripts/postFitPlots.py --file {os.path.join(args.fit_dir, 'prefit')}/{bin_name}_prefit.root --file_dir {bin_name} --ratio --ratio_range 0.5,1.5 --mode prefit
"""
        submission_file_content = f"""
executable = {executable_file_path}
output = {log_dir}/{bin_name}_prefit.out
error = {log_dir}/{bin_name}_prefit.err
log = {log_dir}/{bin_name}_prefit.log
request_memory = 8000
request_cpus = 1
+MaxRuntime = 2800
queue
"""
        submission_file_path = os.path.join(log_dir, f'condor_submit_{bin_name}_prefit.sub')


    with open(submission_file_path, 'w') as f:
        f.write(submission_file_content)
    with open(executable_file_path, 'w') as f:
        f.write(executable_file_content)
    os.system(f'chmod u+x {executable_file_path}')

    return submission_file_path

#


def submit_to_condor(submission_file_path):
    subprocess.run(['condor_submit', submission_file_path])


def main(args):

    # Create directories
    log_dir = os.path.join(args.fit_dir, "condor_logs")
    os.makedirs(log_dir, exist_ok=True)
    if args.postfit:
        os.makedirs(os.path.join(args.fit_dir, 'postfit'), exist_ok=True)
    else:
        os.makedirs(os.path.join(args.fit_dir, 'prefit'), exist_ok=True)

    # Run mt:
    mt_name_base = "ztt_mt_"
    for b in range(101, 120):
        if b not in [110, 120]:
            bin_name = mt_name_base + str(b) + "_" +  args.era
            print(f"Submitting bin: {bin_name}")
            sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
            submit_to_condor(sub_file)

    for b in range(201, 220):
        if b not in [210, 220]:
            bin_name = mt_name_base + str(b) + "_" +  args.era
            print(f"Submitting bin: {bin_name}")
            sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
            submit_to_condor(sub_file)

    for b in range(301, 320):
        if b not in [310, 320]:
            bin_name = mt_name_base + str(b) + "_" +  args.era
            print(f"Submitting bin: {bin_name}")
            sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
            submit_to_condor(sub_file)

    for b in range(401, 420):
        if b not in [410, 420]:
            bin_name = mt_name_base + str(b) + "_" +  args.era
            print(f"Submitting bin: {bin_name}")
            sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
            submit_to_condor(sub_file)

    for b in range(501, 520):
        if b not in [510, 520]:
            bin_name = mt_name_base + str(b) + "_" +  args.era
            print(f"Submitting bin: {bin_name}")
            sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
            submit_to_condor(sub_file)

    # Run mm:
    bin_name = 'ztt_mm_0_' + args.era
    sub_file = create_condor_submission_file(args.fit_dir, bin_name, log_dir, args.postfit)
    submit_to_condor(sub_file)



if __name__ == "__main__":
    args= get_args()

    main(args)

