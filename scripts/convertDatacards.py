import ROOT
import argparse
import os
import numpy as np

# Turn off automatic in-memory directory association for newly created TH1s
ROOT.TH1.AddDirectory(False)

bins = [20., 25., 30., 35., 40., 50., 60., 80., 100., 200.]

def WriteToTFile(obj, file, path):
    '''Writes an object to a root file in the given path. If the directory does not exist it is created.'''
    file.cd()
    as_vec = path.split('/')
    if len(as_vec) >= 1:
        for i in range(0, len(as_vec)-1):
            if not ROOT.gDirectory.GetDirectory(as_vec[i]):
                ROOT.gDirectory.mkdir(as_vec[i])
            ROOT.gDirectory.cd(as_vec[i])
    # Write object with its existing name
    ROOT.gDirectory.WriteTObject(obj, obj.GetName())
    ROOT.gDirectory.cd('/')

def splitHistogramsAndWriteToFile(infile, outfile, dirname):
    '''Split 2D histogram in bins of pT and m_vis into several 1D histograms in bins of m_vis'''
    directory = infile.Get(dirname)
    for key in directory.GetListOfKeys():
        name = key.GetName()
        histo = directory.Get(name)
        # Only process if this key is a TH2
        if isinstance(histo, ROOT.TH2):
            # Loop over each pT bin
            for i, b_lo in enumerate(bins[:-1]):
                b_hi = bins[i+1]
                y1 = histo.GetYaxis().FindBin(b_lo)
                y2 = histo.GetYaxis().FindBin(b_hi) - 1

                # Create projection with a TEMPORARY name
                hnew = histo.ProjectionX("tmp_" + name, y1, y2)
                # Now rename it to match the original 2D name
                hnew.SetName(name)

                # Write into a different subdirectory so it won't clash on disk
                newdirname = '%s_pT_%i_to_%i' % (dirname, int(b_lo), int(b_hi))
                WriteToTFile(hnew, outfile, newdirname + "/" + name)

def findAvepT(infile, dirname):
    '''Find the average pT of the tau in each pT bin'''
    directory = infile.Get(dirname)

    # Make a combined 2D histogram
    name = 'ZTT'
    histo = directory.Get(name).Clone()
    histo.Add(directory.Get('TTT'))
    histo.Add(directory.Get('VVT'))

    if isinstance(histo, ROOT.TH2):
        bin_means = []
        for i, b_lo in enumerate(bins[:-1]):
            b_hi = bins[i+1]
            histo.GetYaxis().SetRangeUser(b_lo, b_hi)
            bin_means.append(round(histo.GetMean(2), 1))
        print("Directory:", dirname, "=> average pT in each bin:", bin_means)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', '-f', help='File from which subdirectories need to be dropped')
    args = parser.parse_args()
    filename = args.file

    if 'pt_2_vs_m_vis' not in filename:
        raise Exception('ERROR: your input file does not appear to have the correct naming')

    newfilename = filename.replace('pt_2_vs_m_vis', 'm_vis')

    original_file = ROOT.TFile.Open(filename, "READ")
    output_file   = ROOT.TFile(newfilename, "RECREATE")

    for key in original_file.GetListOfKeys():
        if isinstance(original_file.Get(key.GetName()), ROOT.TDirectory):
            dirname = key.GetName()
            print('Converting histograms in directory: %s' % dirname)
            splitHistogramsAndWriteToFile(original_file, output_file, dirname)

            # Optionally find mean pTs
            if 'Gt30' in dirname or 'method12' in dirname:
                continue
            findAvepT(original_file, dirname)

    output_file.Close()
    original_file.Close()
