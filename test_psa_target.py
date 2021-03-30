#!/usr/bin/env python3
"""
Copyright (c) 2020-2021 ARM Limited. All rights reserved.

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
from os.path import join, relpath, normpath
import argparse
import sys
import signal
import logging
import json
import shutil
from psa_builder import *

logging.basicConfig(
    level=logging.INFO,
    format="[Test-Target] %(asctime)s: %(message)s.",
    datefmt="%H:%M:%S",
)


def _get_baud_rate():
    """
    return baud rate from mbed_app.json
    """
    with open("mbed_app.json", "r") as json_file:
        json_object = json.load(json_file)
        json_file.close()

    return json_object["target_overrides"]["*"]["platform.stdio-baud-rate"]


def _set_json_param(regression, compliance, sync):
    """
    Set json parameter required for Mbed OS build
    :param regression: set regression build
    :param compliance: set compliance build
    :param sync: set waiting for sync from Greentea host
    """
    with open("mbed_app.json", "r") as json_file:
        json_object = json.load(json_file)
        json_file.close()

    json_object["config"]["regression-test"] = regression
    json_object["config"]["psa-compliance-test"] = compliance
    json_object["config"]["wait-for-sync"] = sync

    with open("mbed_app.json", "w") as json_file:
        json.dump(json_object, json_file, indent=4)
        json_file.close()


def _build_mbed_os(args):
    """
    Build Mbed OS
    :param args: Command-line arguments
    """
    build_tool = "mbed" if args.cli == 1 else "mbedtools"
    cmd = [
        build_tool,
        "compile",
        "-m",
        args.mcu,
        "-t",
        TC_DICT.get(args.toolchain),
    ]

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        logging.critical("Unable to build Mbed OS target - %s", args.mcu)
        sys.exit(1)


def _build_tfm(args, config, suite=None):
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
    ]

    if config in SUPPORTED_TFM_PSA_CONFIGS:
        cmd.append("-s")
        cmd.append(suite)

    if args.clean:
        cmd.append("--clean")

    if args.skip_clone:
        cmd.append("--skip-clone")

    retcode = run_cmd_output_realtime(cmd, ROOT)
    if retcode:
        logging.critical("Unable to build TF-M for target - %s", args.mcu)
        sys.exit(1)


def _erase_flash_storage(args, suite):
    """
    Creates a target specific binary which has its ITS erased
    :param args: Command-line arguments
    :param suite: Test suite
    :return: return binary name generated
    """
    if args.cli == 1:
        mbed_os_dir = join(
            ROOT, "BUILD", args.mcu, TC_DICT.get(args.toolchain)
        )
    else:
        mbed_os_dir = join(
            ROOT,
            "cmake_build",
            args.mcu,
            "develop",
            TC_DICT.get(args.toolchain),
        )

    cmd = []

    binary_name = "mbed-os-tf-m-regression-tests-reset-flash-{}.hex".format(
        suite
    )

    if args.mcu == "ARM_MUSCA_B1":
        cmd = [
            "srec_cat",
            "mbed-os-tf-m-regression-tests.bin",
            "-Binary",
            "-offset",
            "0xA000000",
            "-fill",
            "0xFF",
            "0xA1F0000",
            "0XA1FC000",
            "-o",
            binary_name,
            "-Intel",
        ]

    if args.mcu == "ARM_MUSCA_S1":
        # Note: The erase range is different from https://git.trustedfirmware.org/TF-M/trusted-firmware-m.git/tree/platform/ext/target/musca_s1/partition/flash_layout.h?h=TF-Mv1.2.0#n29
        # ARM_MUSCA_S1's DAPLink only permits 64K-aligned flashing for compatibility with QSPI even though MRAM (which we use) has a 4K granularity.
        cmd = [
            "srec_cat",
            "mbed-os-tf-m-regression-tests.bin",
            "-Binary",
            "-offset",
            "0xA000000",
            "-fill",
            "0xFF",
            "0xA1E0000",
            "0xA1F0000",
            "-o",
            binary_name,
            "-Intel",
        ]

    retcode = run_cmd_output_realtime(cmd, mbed_os_dir)
    if retcode:
        logging.critical(
            "Unable to create a binary with ITS erased for target %s, suite %s",
            args.mcu,
            suite,
        )
        sys.exit(1)

    return binary_name


def _execute_test():
    """
    Execute greentea runs test as specified in test_spec.json
    """
    if not os.path.isfile("test_spec.json"):
        logging.critical(
            "test_spec.json is not found, please build the tests first"
        )
        sys.exit(1)

    cmd = ["mbedgt", "--polling-timeout", "600", "-V"]

    run_cmd_output_realtime(cmd, os.getcwd())


def _init_test_spec(args):
    """
    initialize test specification
    :param args: Command-line arguments
    :return: test specification dictionary with initial contents
    """
    target = args.mcu
    toolchain = TC_DICT.get(args.toolchain)
    test_group = _get_test_group(args)
    baud_rate = _get_baud_rate()

    return {
        "builds": {
            test_group: {
                "platform": target,
                "toolchain": toolchain,
                "base_path": ".",
                "baud_rate": baud_rate,
                "tests": {},
            }
        }
    }


def _get_test_group(args):
    """
    make a unique test group name
    :param args: Command-line arguments
    :return: return test group name
    """
    target = args.mcu
    toolchain = TC_DICT.get(args.toolchain)
    baud_rate = _get_baud_rate()
    return "{}-{}-{}".format(target, toolchain, baud_rate)


def _get_test_spec(args, suite, binary_name):
    """
    return test specification for the suite name
    :param args: Command-line arguments
    :param suite: test suite
    :param binary_name: name of the binary
    :return: return test spec dictionary for the suite name
    """
    target = args.mcu
    toolchain = TC_DICT.get(args.toolchain)
    log_path = join("test", "logs", target, "{}.log".format(suite))

    if args.cli == 1:
        image_path = join("BUILD", target, toolchain, binary_name)
    else:
        image_path = join(
            "cmake_build", target, "develop", toolchain, binary_name
        )

    return {
        "binaries": [
            {
                "binary_type": "bootable",
                "path": normpath(image_path),
                "compare_log": log_path,
            }
        ]
    }


def _build_regression_test(args, test_spec):
    """
    Build TF-M regression test for the target
    :param args: Command-line arguments
    """
    logging.info("Build TF-M regression tests for %s", args.mcu)
    suite = "REGRESSION"
    _set_json_param(1, 0, 0 if args.no_sync else 1)

    # build stuff
    _build_tfm(args, "RegressionIPC")
    _build_mbed_os(args)
    binary_name = _erase_flash_storage(args, suite)

    # update the test_spec
    test_group = _get_test_group(args)
    test_spec["builds"][test_group]["tests"][suite.lower()] = _get_test_spec(
        args, suite, binary_name
    )


def _build_compliance_test(args, test_spec):
    """
    Build PSA Compliance test for the target
    :param args: Command-line arguments
    """
    _set_json_param(0, 1, 0 if args.no_sync else 1)

    test_group = _get_test_group(args)

    for suite in PSA_SUITE_CHOICES:

        logging.info("Build PSA Compliance - %s suite for %s", suite, args.mcu)

        _build_tfm(args, "PsaApiTestIPC", suite)
        _build_mbed_os(args)
        binary_name = _erase_flash_storage(args, suite)

        # Issue: https://github.com/ARM-software/psa-arch-tests/issues/252
        # The Crypto suite is known to crash and reset the target during runs.
        # This causes the Greentea test framework to lose synchronization, and
        # messes up the memory and prevents subsequent suites from running.
        # The PSA tests currently provide no option to skip known failures.
        # Users can still run the Crypto suite manually without automation.
        if suite != "CRYPTO":
            test_spec["builds"][test_group]["tests"][
                suite.lower()
            ] = _get_test_spec(args, suite, binary_name)


def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-m",
        "--mcu",
        help="Build for the given MCU",
        choices=get_tfm_regression_targets(),
        default=None,
    )

    parser.add_argument(
        "-t",
        "--toolchain",
        help="Build for the given toolchain",
        default=None,
        choices=["ARMCLANG", "GNUARM"],
    )

    parser.add_argument(
        "-b",
        "--build",
        help="Build the target only",
        action="store_true",
    )

    parser.add_argument(
        "-r",
        "--run",
        help="Run on the target only",
        action="store_true",
    )

    parser.add_argument(
        "--no-sync",
        help="Tests start without waiting for sync from Greentea host",
        action="store_true",
    )

    parser.add_argument(
        "-l",
        "--list",
        help="Print supported TF-M secure targets",
        action="store_true",
    )

    parser.add_argument(
        "--clean",
        help="Clean the cloned dependencies",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--skip-clone",
        help="Skip cloning/checkout of TF-M dependencies",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--cli",
        help="Build with the specified version of Mbed CLI",
        type=int,
        default=2,
        choices=[1, 2],
    )

    return parser


def _main():
    """
    Build and run Regression, PSA compliance for suported targets
    """
    signal.signal(signal.SIGINT, exit_gracefully)
    parser = _get_parser()
    args = parser.parse_args()

    if args.list:
        logging.info(
            "Supported TF-M regression and PSA compliance targets are: {}".format(
                ", ".join([t for t in get_tfm_regression_targets()])
            )
        )
        return

    logging.info("Target - %s", args.mcu)

    build = args.build
    run = args.run

    # Default to build and run
    if not args.build and not args.run:
        build = True
        run = True

    if build:
        test_spec = _init_test_spec(args)
        _build_regression_test(args, test_spec)
        _build_compliance_test(args, test_spec)

        with open("test_spec.json", "w") as f:
            f.write(json.dumps(test_spec, indent=2))

        logging.info("Target built succesfully - %s", args.mcu)

    if run:
        _execute_test()


if __name__ == "__main__":
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
