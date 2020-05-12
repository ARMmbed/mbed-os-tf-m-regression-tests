#!/usr/bin/env python
"""
Copyright (c) 2020 ARM Limited. All rights reserved.

SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from os.path import join, isdir, relpath
import argparse
import sys
import signal
import shutil
import logging
from psa_builder import *

logging.basicConfig(level=logging.INFO,
                    format='[Build-PSA-Compliance-tests] %(asctime)s: %(message)s.',
                    datefmt='%H:%M:%S')

ROOT_TEST_LIB = join(ROOT, "test", "lib")

PSA_API_TARGETS = {
    "ARM_MUSCA_A": ["armv8m_ml", "tgt_dev_apis_tfm_musca_a"],
    "ARM_MUSCA_B1": ["armv8m_ml", "tgt_dev_apis_tfm_musca_b1"],
    "CY8CKIT_064S2_4343W": ["armv7m" , "tgt_dev_apis_tfm_psoc64"]
}

def _clone_psa_compliance_repo(args):
    """
    Clone PSA compliance tests git repos and it's dependencies
    :param args: Command-line arguments
    """
    check_and_clone_repo('psa-arch-tests', dependencies["psa-api-compliance"],
                            TF_M_BUILD_DIR)

    if args.suite == "CRYPTO":
        crypto_dir = join(TF_M_BUILD_DIR, 'psa-arch-tests')
        check_and_clone_repo('mbed-crypto', dependencies["psa-api-compliance"],
                                crypto_dir)
    else:
        # Applicable for INITIAL_ATTESTATION, INTERNAL_TRUSTED_STORAGE
        # PROTECTED_STORAGE and STORAGE suites.
        check_and_clone_repo('trusted-firmware-m', dependencies["tf-m"],
                                TF_M_BUILD_DIR)

def _build_crypto():
    """
    Build crypto library
    """
    folder = join(TF_M_BUILD_DIR, 'psa-arch-tests', 'mbed-crypto')

    command = ['make', '-C', folder, 'clean']
    if run_cmd_and_return(command, True):
        command = ['make', '-C', folder]
        if run_cmd_output_realtime(command, folder):
            logging.critical("Make build failed for crypto")
            sys.exit(1)
    else:
        logging.critical("Make clean failed for crypto")
        sys.exit(1)

def _run_cmake_build(cmake_build_dir, args):
    """
    Run the Cmake build

    :param cmake_build_dir: Base directory for Cmake build
    :param args: Command-line arguments
    """

    cmake_cmd = ['cmake', '../', '-GUnix Makefiles']
    cmake_cmd.append('-DTARGET=' + PSA_API_TARGETS.get(args.mcu)[1])

    cmake_cmd.append('-DCPU_ARCH=' + PSA_API_TARGETS.get(args.mcu)[0])

    cmake_cmd.append('-DSUITE=' + args.suite)

    if args.verbose:
        cmake_cmd.append('-DVERBOSE=' + str(args.verbose))

    if args.include:
        cmake_cmd.append('-DPSA_INCLUDE_PATHS=' + args.include)
    else:
        # Take in defaults
        if args.suite == "CRYPTO":
            crypto_include = join(  TF_M_BUILD_DIR,
                                    'psa-arch-tests', 'mbed-crypto', 'include')
            cmake_cmd.append('-DPSA_INCLUDE_PATHS=' + crypto_include)
        else:
            # Applicable for INITIAL_ATTESTATION, INTERNAL_TRUSTED_STORAGE
            # PROTECTED_STORAGE and STORAGE suites.
            suite_include = join(TF_M_BUILD_DIR,
                                'trusted-firmware-m', 'interface', 'include')
            cmake_cmd.append('-DPSA_INCLUDE_PATHS=' + suite_include)

    if args.range:
        cmake_cmd.append('-DSUITE_TEST_RANGE=' + args.range)

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake configure failed for target %s using toolchain %s" % (
                                                        args.mcu,  args.toolchain)
        logging.critical(msg)
        sys.exit(1)

    cmake_cmd = ['cmake', '--build', '.']

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake build failed for target %s using toolchain %s" % (
                                                        args.mcu,  args.toolchain)
        logging.critical(msg)
        sys.exit(1)

def _copy_psa_libs(source, destination, args):
    """
    Copy TF-M binaries from source to destination

    :param source: directory where TF-M binaries are available
    :param destination: directory to which TF-M binaries are copied to
    :param args: Command-line arguments
    """

    if(destination.endswith('/')):
        output_dir = destination
    else:
        output_dir = destination + '/'

    val_nspe = join(source, 'val', 'val_nspe.a')
    val_nspe_output = output_dir + 'libval_nspe.a'
    logging.info("Copying %s to %s" % (relpath(val_nspe, source),
                                      relpath(val_nspe_output, ROOT)))
    shutil.copy2(val_nspe, val_nspe_output)

    pal_nspe = join(source, 'platform', 'pal_nspe.a')
    pal_nspe_output = output_dir + 'libpal_nspe.a'
    logging.info("Copying %s to %s" % (relpath(pal_nspe, source),
                                      relpath(pal_nspe_output, ROOT)))
    shutil.copy2(pal_nspe, pal_nspe_output)

    if args.suite == "INITIAL_ATTESTATION" or args.suite == "CRYPTO":
        suite_folder = str(args.suite).lower()
    else:
        # Applicable for INTERNAL_TRUSTED_STORAGE, PROTECTED_STORAGE
        # and STORAGE suites.
        suite_folder = 'storage'

    test_combine = join(source, 'dev_apis', suite_folder, 'test_combine.a')
    test_combine_output = output_dir + 'libtest_combine.a'
    logging.info("Copying %s to %s" % (relpath(test_combine, source),
                                      relpath(test_combine_output, ROOT)))
    shutil.copy2(test_combine, test_combine_output)

def _build_psa_compliance(args):
    """
    Build PSA Compliance tests
    :param args: Command-line arguments
    """

    _clone_psa_compliance_repo(args)

    cmake_build_dir = join(TF_M_BUILD_DIR, 'psa-arch-tests', 'api-tests', 'BUILD')

    if isdir(cmake_build_dir):
        shutil.rmtree(cmake_build_dir)

    os.mkdir(cmake_build_dir)

    if "CRYPTO" == args.suite:
        _build_crypto()

    _run_cmake_build(cmake_build_dir, args)
    _copy_psa_libs(cmake_build_dir, ROOT_TEST_LIB, args)

def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mcu",
                        help="Build for the given MCU",
                        required=True,
                        choices=PSA_API_TARGETS,
                        default=None)

    parser.add_argument("-t", "--toolchain",
                        help="Build for the given toolchain (GNUARM)",
                        default="GNUARM",
                        choices=["ARMCLANG", "GNUARM"])

    parser.add_argument("-v", "--verbose",
                        help="Verbose level of the build (default : 3)",
                        choices=range(1,6),
                        type=int,
                        default=None)

    parser.add_argument("-s", "--suite",
                        help="Test suite name",
                        choices=PSA_SUITE_CHOICES,
                        default=None,
                        required=True
                        )

    parser.add_argument("-r", "--range",
                        help="""
                        Test suite range (default : all tests),
                        Format : 'test_start_number;test_end_number'
                        """,
                        default=None)

    parser.add_argument("-i", "--include",
                        help="""
                        Test include path,
                        Format : <include_path1>;<include_path2>;...;<include_pathn>
                        """,
                        default=None)

    return parser

def _main():
    """
    Build PSA Compliance Tests for supported targets
    """
    global TF_M_BUILD_DIR
    signal.signal(signal.SIGINT, exit_gracefully)
    parser = _get_parser()
    args = parser.parse_args()

    if not isdir(TF_M_BUILD_DIR):
        os.mkdir(TF_M_BUILD_DIR)

    logging.info("Using folder %s" % TF_M_BUILD_DIR)
    _build_psa_compliance(args)

if __name__ == '__main__':
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
