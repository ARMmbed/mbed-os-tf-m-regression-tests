#!/usr/bin/env python3
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
from os.path import join, relpath
import argparse
import sys
import signal
import logging
import json
import shutil
from psa_builder import *

logging.basicConfig(level=logging.INFO,
                    format='[Test-Target] %(asctime)s: %(message)s.',
                    datefmt='%H:%M:%S')

test_results = {}

def _set_json_param(regression, compliance):
    """
    Set json parameter required for Mbed OS build
    :param regression: set regression build
    :param compliance: set compliance build
    """
    with open('mbed_app.json', 'r') as json_file:
        json_object = json.load(json_file)
        json_file.close()

    json_object['config']['regression-test'] = regression
    json_object['config']['psa-compliance-test'] = compliance

    with open('mbed_app.json', 'w') as json_file:
        json.dump(json_object, json_file, indent=4)
        json_file.close()

def _build_mbed_os(args):
    """
    Build Mbed OS
    :param args: Command-line arguments
    """
    cmd = [ 'mbed', 'compile', '-m', args.mcu, '-t',
            TC_DICT.get(args.toolchain)]

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        msg = "Unable to build Mbed OS target - %s" % args.mcu
        logging.critical(msg)
        sys.exit(1)

def _build_psa_compliance(args, suite):
    """
    Build PSA compliance test
    :param args: Command-line arguments
    :param suite: Test suite for PSA compliance
    """
    cmd = [ 'python3', 'build_psa_compliance.py', '-m', args.mcu, '-t',
            args.toolchain, '-s', suite]

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        msg = "Unable to build PSA compliance tests for target - %s" % args.mcu
        logging.critical(msg)
        sys.exit(1)

def _build_tfm(args, config, suite=None):
    """
    Build TF-M regression test
    :param args: Command-line arguments
    :param config: Config type
    :param suite: Test suite for PSA compliance
    """
    cmd = [ 'python3', 'build_tfm.py', '-m', args.mcu, '-t', args.toolchain,
            '-c', config]

    if config in SUPPORTED_TFM_PSA_CONFIGS:
        cmd.append('-s')
        cmd.append(suite)

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        msg = "Unable to build TF-M for target - %s" % args.mcu
        logging.critical(msg)
        sys.exit(1)

def _execute_test(args, suite):
    """
    Execute test by using the mbed host test runner
    :param args: Command-line arguments
    :param suite: Test suite
    """
    logging.info("Executing tests for - %s suite..." % suite)

    mbed_os_dir = join( ROOT, 'BUILD', args.mcu,
                        TC_DICT.get(args.toolchain))
    log_dir = join(ROOT, 'test', 'logs', args.mcu, (suite + '.log'))

    cmd = [ 'mbedhtrun', '--sync=0', '-p', args.port, '--compare-log', log_dir,
            '--polling-timeout', '300', '-d', args.disk, '-f',
            'mbed-os-tf-m-regression-tests.bin', '--skip-reset', '-C', '1']

    retcode = run_cmd_output_realtime(cmd, mbed_os_dir)
    if retcode:
        msg = "Test **FAILED** for target %s, suite %s" % (args.mcu, suite)
        logging.critical(msg)
        test_results[suite] = False

def _run_regression_test(args):
    """
    Run TF-M regression test for the target
    :param args: Command-line arguments
    """
    logging.info("Test TF-M regression...")

    _set_json_param(1,0)
    _build_tfm(args, 'ConfigRegressionIPC.cmake')
    _build_mbed_os(args)

    _execute_test(args, 'REGRESSION')

def _run_compliance_test(args):
    """
    Run PSA Compliance test for the target
    :param args: Command-line arguments
    """
    _set_json_param(0,1)

    for suite in PSA_SUITE_CHOICES:
        logging.info("Test PSA Compliance - %s suite..." % suite)

        _build_psa_compliance(args, suite)
        _build_tfm(args, 'ConfigPsaApiTestIPC.cmake', suite)
        _build_mbed_os(args)

        _execute_test(args, suite)

def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("-m", "--mcu",
                        help="Build for the given MCU",
                        required=True,
                        choices=["ARM_MUSCA_B1"],
                        default=None)

    parser.add_argument("-t", "--toolchain",
                        help="Build for the given toolchain (GNUARM)",
                        default="GNUARM",
                        choices=["ARMCLANG", "GNUARM"])

    parser.add_argument("-d", "--disk",
                        help="""
                        Target disk (mount point) path
                        """,
                        default=None)

    parser.add_argument("-p", "--port",
                        help="""
                        Target port for connection
                        """,
                        default=None)

    return parser

def _init_results_dict():
    """
    Initialize the results dictionary for target to track ongoing progress
    """
    global test_results
    test_results = {}
    complete_list = ['REGRESSION'] + PSA_SUITE_CHOICES
    for index in complete_list:
        test_results[index] = True

def _print_results_and_exit():
    """
    Print results summary for the target and exit if any error
    """
    err = False
    print("*** Test execution status ***")

    for key in test_results:
        if test_results.get(key):
            result = "PASSED"
        else:
            result = "FAILED"
            err = True
        print (key + " suite : " + result)

    print ("*** End Report ***")

    if err == True:
        sys.exit(1)

def _main():
    """
    Build and run Regression, PSA compliance for suported targets
    """
    signal.signal(signal.SIGINT, exit_gracefully)
    parser = _get_parser()
    args = parser.parse_args()

    logging.info("Testing target - %s" % args.mcu)

    _init_results_dict()

    _run_regression_test(args)
    _run_compliance_test(args)

    _print_results_and_exit()

if __name__ == '__main__':
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
