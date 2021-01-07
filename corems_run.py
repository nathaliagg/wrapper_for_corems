#!/usr/bin/env python3

# I used a script template created by Ken Youens-Clark
# from the Tiny Python Projects
# (https://github.com/kyclark/tiny_python_projects)


"""
Author : Nathalia Graf Grachet
Date   : 2021-01-06
Purpose: Wrapper for CoreMS
"""

import argparse
from typing import NamedTuple
import os
import errno
import glob
import datetime

import pandas as pd
import numpy as np

from corems.transient.input.brukerSolarix import ReadBrukerSolarix
from corems.encapsulation.factory.parameters import MSParameters
from corems.mass_spectrum.calc.Calibration import MzDomainCalibration
from corems.molecular_id.search.molecularFormulaSearch import SearchMolecularFormulas
from corems.molecular_id.factory.classification import HeteroatomsClassification

import corems


class Args(NamedTuple):
    """ Command-line arguments """
    positional: str
    string_arg: str
    int_arg: int
    calibration: bool

# define Python user-defined exceptions
class NeedCalibrationFile(Exception):
    """Base class for other exceptions"""
    pass


# --------------------------------------------------
def get_args() -> Args:
    """ Get command-line arguments """

    parser = argparse.ArgumentParser(
        description="""
        Wrapper for CoreMS. Limited argumants.
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('data',
                        metavar='str',
                        help='Path to directory where Bruker .d files are located')

    parser.add_argument('-ref',
                        '--reference',
                        metavar='str',
                        type=str,
                        help='Path to calibration file',
                        default=None)

    parser.add_argument('-ppm',
                        '--calib_ppm',
                        help='Calibration threshold in ppm',
                        metavar='int',
                        type=int,
                        default=10)

    parser.add_argument('-c',
                        '--calibration',
                        help='Perform calibration?',
                        metavar='bool',
                        type=str,
                        default='False')

    parser.add_argument('-o',
                        '--outdir',
                        help='Name for output dir',
                        metavar='str',
                        type=str,
                        default='corems_output')

    args = parser.parse_args()

    return args


# --------------------------------------------------
def main() -> None:
    """
    Does it all
    """

    args = get_args()

    # print(args)

    print(timestamp())
    print()

    print("CoreMS version: {}".format(corems.__version__))

    validate_input_files(args.data)

    list_files = glob.glob(args.data+'/*.d')

    ref = args.reference

    validate_calibration_file(ref)

    validate_output_dir()

    # Set parameters for CoreMS
    MSParameters.mass_spectrum.threshold_method = 'signal_noise'
    MSParameters.mass_spectrum.s2n_threshold = 6
    MSParameters.molecular_search.min_ppm_error = -10  # +/- 10 ppm
    MSParameters.molecular_search.max_ppm_error = 10
    MSParameters.molecular_search.mz_error_range = 1.5  # default 1.5
    MSParameters.molecular_search.error_method = None  # default is None
    MSParameters.molecular_search.mz_error_average = 0  # default is 0
    MSParameters.molecular_search.score_method = 'prob_score'  # prob_score
    MSParameters.molecular_search.min_mz = 200
    MSParameters.molecular_search.max_mz = 1000
    MSParameters.molecular_search.usedAtoms['C'] = (1, 90)
    MSParameters.molecular_search.usedAtoms['H'] = (4, 200)
    MSParameters.molecular_search.usedAtoms['O'] = (1, 20)
    MSParameters.molecular_search.usedAtoms['N'] = (0, 3)
    MSParameters.molecular_search.usedAtoms['S'] = (0, 1)
    MSParameters.molecular_search.usedAtoms['P'] = (0, 1)
    print()

    if args.calibration == "True":
        MSParameters.mass_spectrum.do_calibration = True
        MSParameters.mass_spectrum.min_calib_ppm_error = -args.calib_ppm
        MSParameters.mass_spectrum.max_calib_ppm_error = args.calib_ppm
        print('With calibration at {} ppm'.format(args.calib_ppm))
    else:
        MSParameters.mass_spectrum.do_calibration = False
        print('Without calibration')

    print()

    print('Start CoreMS')

    # Start CoreMS run

    # Open variables
    result_SearchMF = []
    df_coreMS = pd.DataFrame()

    # loop over each file in the list_files
    for file in list_files:

        # get just the filename
        filename = file.split('/')[-1]
        print(filename)
        print()

        # import .d
        mass_spectrum = import_d_files(file)
        # print(mass_spectrum)

        # do calibration, or don't
        if args.calibration == 'True':
            MzDomainCalibration(mass_spectrum, ref).run()

        # Formula assignment
        mass_spectrum.molecular_search_settings.url_database = "postgresql+psycopg2://coremsappdb:coremsapppnnl@localhost:5432/coremsapp"
        SearchMolecularFormulas(mass_spectrum,
                                first_hit=True).run_worker_mass_spectrum()

        # Get results from the SearchMolecularFormulas
        result_SearchMF.append(get_searchMF_results(mass_spectrum, filename))

        # get the table from mass spectrum obj
        df = mass_spectrum.to_dataframe()

        # remove formula with 13C
        df = df[df['13C'].isnull()]

        # add sample_id information
        df['SampleID'] = filename

        # concat with the df_coreMS (==final df)
        df_coreMS = pd.concat([df_coreMS, df], axis=0)

        print()
        print()

    # make a df from result_SearchMF
    col_list = [
        'n_peaks_assigned', 'n_peaks_n_assigned', 'p_total', 'rel_abundance',
            'RMS_error_ppm', 'Calibration_points', 'SampleID'
    ]
    df_SearchMF = pd.DataFrame(result_SearchMF, columns = col_list)

    # save it
    df_SearchMF.to_csv(
            os.path.join(args.outdir, "summary_SearchMolecularFormulas.csv"),
            index = False
    )

    # save the corems final df
    df_coreMS.to_csv(
            os.path.join(args.outdir, "CoreMS_report.csv"),
            index = False
    )

    print('CoreMS Concluded!')
    print()
    print(timestamp())


# --------------------------------------------------
def validate_output_dir():
    """
    Validate if path to output exists
    """

    args = get_args()

    if os.path.exists(args.outdir):
        print("\u2713 Output directory {} already exists".format(args.outdir))
    else:
        os.makedirs(args.outdir)
        print("\u2713 Created output directory {}".format(args.outdir))


# --------------------------------------------------
def validate_input_files(directory):
    """
    Validate if path to data directory where .d are exists
    """

    list_files = glob.glob(directory+'/*.d')

    if len(list_files) == 0:
        raise FileNotFoundError(
                                errno.ENOENT,
                                os.strerror(errno.ENOENT),
                                args.outdir
                                )
    else:
        for file in list_files:
            if os.path.exists(file):
                print("\u2713 {}".format(file))
            else:
                raise FileNotFoundError(
                                        errno.ENOENT,
                                        os.strerror(errno.ENOENT),
                                        args.outdir
                                        )


# --------------------------------------------------
def validate_calibration_file(calib_file):
    """
    Validate if path to calibration file exists, if provided
    """

    args = get_args()

    if calib_file == None:
        if args.calibration == 'False':
            pass
        else:
            raise NeedCalibrationFile

    else:
        if os.path.exists(calib_file):
            print("\u2713 {}".format(calib_file))
        else:
            raise FileNotFoundError(errno.ENOENT,
                                  os.strerror(errno.ENOENT),
                                  args.outdir)


# --------------------------------------------------
def import_d_files(file_d):
    """
    Import a .d file as a mass_spectrum object
    """

    bruker_reader = ReadBrukerSolarix(file_d)
    bruker_transient = bruker_reader.get_transient()
    mass_spectrum = bruker_transient.get_mass_spectrum(plot_result=False,
                                                       auto_process=True)

    return mass_spectrum


# --------------------------------------------------
def get_searchMF_results(ms_obj, sample_id):
    """
    Get the results from SearchMolecularFormulas()
    """

    result_list = [
            i for i in ms_obj.percentile_assigned(report_error=True)
        ]

    # append n calibration points
    result_list.append(ms_obj.calibration_points)

    # append sampleid
    result_list.append(sample_id)


    return result_list


# --------------------------------------------------
def timestamp():
    """
    Get date and time right now
    """

    right_now = datetime.datetime.now()

    return right_now.strftime("%b-%d-%Y @ %I:%M %p")

# --------------------------------------------------
if __name__ == '__main__':
    main()
