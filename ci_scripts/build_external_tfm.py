#!/usr/bin/env python3
"""
Copyright (c) 2021 ARM Limited. All rights reserved.

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

from os.path import join, isdir
import argparse
import sys
import signal
import logging
import shutil

sys.path.append("../")
from psa_builder import *

logging.basicConfig(
    level=logging.INFO,
    format="[Build-external-TF-M] %(asctime)s: %(message)s.",
    datefmt="%H:%M:%S",
)


def _copy_tfm_binaries(args, suite):
    """
    Copy TF-M binaries from source to destination
    :param args: Command-line arguments
    :param suite: Test suite for PSA compliance
    """

    src_folder = join(
        TF_M_BUILD_DIR, "trusted-firmware-m", "cmake_build", "bin"
    )
    dst_folder = join(
        ROOT, "BUILD", args.mcu, TC_DICT[args.toolchain], "TFM", suite
    )

    logging.info("Copying folder: " + src_folder + " - to - " + dst_folder)
    if not isdir(dst_folder):
        os.makedirs(dst_folder)
    for f in os.listdir(src_folder):
        if os.path.isfile(join(src_folder, f)):
            shutil.copy2(join(src_folder, f), join(dst_folder, f))


def _build_tfm(args, config, suite):
    """
    Build TF-M regression test
    :param args: Command-line arguments
    :param config: Config type
    :param suite: Test suite for PSA compliance
    """
    cmd = [
        "python3",
        "build_tfm.py",
        "-m",
        args.mcu,
        "-t",
        args.toolchain,
        "-c",
        config,
        "--skip-clone",
        "--skip-copy",
    ]

    if config in SUPPORTED_TFM_PSA_CONFIGS:
        cmd.append("-s")
        cmd.append(suite)

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        logging.critical("Unable to build TF-M for target - %s", args.mcu)
        sys.exit(1)

    _copy_tfm_binaries(args, suite)


def _build_regression_test(args):
    """
    Build TF-M regression test for the target
    :param args: Command-line arguments
    """
    logging.info("Build TF-M regression tests for %s", args.mcu)

    _build_tfm(args, "RegressionIPC", "REGRESSION")


def _build_compliance_test(args):
    """
    Build PSA Compliance test for the target
    :param args: Command-line arguments
    """

    for suite in PSA_SUITE_CHOICES:

        # Issue : https://github.com/ARMmbed/mbed-os-tf-m-regression-tests/issues/49
        # There is no support for this target to run Firmware Framework tests
        if suite == "IPC" and args.mcu == "ARM_MUSCA_S1":
            logging.info(
                "%s config is not supported for %s target" % (suite, args.mcu)
            )
            continue

        logging.info("Build PSA Compliance - %s suite for %s", suite, args.mcu)

        _build_tfm(args, "PsaApiTestIPC", suite)


def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-m",
        "--mcu",
        help="Build for the given MCU",
        choices=["ARM_MUSCA_S1"],
        default=None,
    )

    parser.add_argument(
        "-t",
        "--toolchain",
        help="Build for the given toolchain",
        default=None,
        choices=["ARMCLANG", "GNUARM"],
    )

    return parser


def _main():
    """
    Build and run Regression, PSA compliance for suported targets
    """
    signal.signal(signal.SIGINT, exit_gracefully)
    parser = _get_parser()
    args = parser.parse_args()

    logging.info("Target - %s", args.mcu)

    _build_regression_test(args)
    _build_compliance_test(args)

    logging.info("Target built succesfully - %s", args.mcu)


if __name__ == "__main__":
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
