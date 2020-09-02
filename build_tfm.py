#!/usr/bin/env python3
"""
Copyright (c) 2019-2020 ARM Limited. All rights reserved.

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
from os.path import join, abspath, dirname, isdir, relpath
import argparse
import sys
import signal
import shutil
import logging
from psa_builder import *

try:
    import yaml
except ImportError as e:
    print(str(e) + " To install it, type:")
    print("python3 -m pip install PyYAML")
    exit(1)

from tools.toolchains import TOOLCHAIN_CLASSES, TOOLCHAIN_PATHS
from tools.targets import Target, TARGET_MAP, TARGET_NAMES

logging.basicConfig(
    level=logging.INFO,
    format="[Build-TF-M] %(asctime)s: %(message)s.",
    datefmt="%H:%M:%S",
)

VERSION_FILE_PATH = join(mbed_path, TF_M_RELATIVE_PATH)


def _detect_and_write_tfm_version(tfm_dir, commit):
    """
    Identify the version of TF-M and write it to VERSION.txt
    :param tfm_dir: The filesystem path where TF-M repo is cloned
    :param commit: If True then commmit the VERSION.txt
    """
    cmd = [
        "git",
        "-C",
        tfm_dir,
        "describe",
        "--tags",
        "--abbrev=12",
        "--dirty",
        "--always",
    ]
    tfm_version = run_cmd_and_return(cmd, True)
    logging.info("TF-M version: %s", tfm_version.strip("\n"))
    if not isdir(VERSION_FILE_PATH):
        os.makedirs(VERSION_FILE_PATH)
    # Write the version to Mbed OS
    with open(join(VERSION_FILE_PATH, "VERSION.txt"), "w") as f:
        f.write(tfm_version)
    # Write the version to the current directory
    with open("VERSION.txt", "w") as f:
        f.write(tfm_version)

    if commit:
        _commit_changes(VERSION_FILE_PATH)


def _clone_tfm_repo(commit):
    """
    Clone TF-M git repos and it's dependencies
    :param commit: If True then commit VERSION.txt
    """
    check_and_clone_repo(
        "trusted-firmware-m", dependencies["tf-m"], TF_M_BUILD_DIR
    )
    check_and_clone_repo("mbed-crypto", dependencies["tf-m"], TF_M_BUILD_DIR)
    check_and_clone_repo("mcuboot", dependencies["tf-m"], TF_M_BUILD_DIR)
    check_and_clone_repo("tf-m-tests", dependencies["tf-m"], TF_M_BUILD_DIR)
    _detect_and_write_tfm_version(
        join(TF_M_BUILD_DIR, "trusted-firmware-m"), commit
    )


def _get_tfm_secure_targets():
    """
    Creates a list of TF-M secure targets.

    :return: List of TF-M secure targets.
    """
    return [str(t) for t in TARGET_NAMES if Target.get_target(t).is_TFM_target]


def _get_target_info(target, toolchain=None):
    """
    Creates a TF-M target tuple (target name, TF-M target name, toolchain,
    delivery directory)

    :param target: Target name.
    :param toolchain: Toolchain
    :return: tuple (target name, TF-M target name, toolchain, delivery directory)
    """
    if toolchain:
        if not TARGET_MAP[target].tfm_supported_toolchains:
            msg = "Supported Toolchains is not configured for target %s" % (
                TARGET_MAP[target].name
            )
            raise Exception(msg)
        elif toolchain not in TARGET_MAP[target].tfm_supported_toolchains:
            msg = "Toolchain %s is not supported by %s" % (
                toolchain,
                TARGET_MAP[target].name,
            )
            raise Exception(msg)
        tc = toolchain
    else:
        tc = TARGET_MAP[target].tfm_default_toolchain

    global TC_DICT
    if not TOOLCHAIN_CLASSES[TC_DICT.get(tc)].check_executable():
        msg = "Toolchain %s was not found in PATH" % tc
        raise Exception(msg)

    delivery_dir = join(
        mbed_path, "targets", TARGET_MAP[target].tfm_delivery_dir
    )

    if not os.path.exists(delivery_dir):
        msg = "Delivery directory (delivery_dir) missing for %s" % target
        raise FileNotFoundError(msg)

    return tuple(
        [
            TARGET_MAP[target].name,
            TARGET_MAP[target].tfm_target_name,
            tc,
            delivery_dir,
        ]
    )


def _get_mbed_supported_tfm_targets():
    """
    Returns a generator with every element containing a TF-M target tuple
    (target name, TF-M target name, toolchain, delivery directory)
    """
    tfm_secure_targets = _get_tfm_secure_targets()
    logging.info(
        "Found the following TF-M targets: {}".format(
            ", ".join(tfm_secure_targets)
        )
    )

    return (_get_target_info(t) for t in tfm_secure_targets)


def _commit_changes(directory, target_toolchain=None):
    """
    Check for changes in `directory` and if any then commit them
    :param directory: path to be checked for changes
    :param target_toolchain: List of Tuple (target name, toolchain)
    """
    # Use --intent-to-add option of git status to identify un-tracked files
    cmd = ["git", "-C", mbed_path, "status", "N", directory]
    run_cmd_and_return(cmd)

    cmd = ["git", "-C", mbed_path, "diff", "--exit-code", "--quiet", directory]
    changes_made = run_cmd_and_return(cmd)

    if target_toolchain is None:
        if changes_made:
            logging.info("Committing changes in directory %s" % directory)
            cmd = [
                "git",
                "-C",
                mbed_path,
                "add",
                relpath(directory, mbed_path),
            ]
            run_cmd_and_return(cmd)
            msg = '--message="Updated directory %s "' % directory
            cmd = ["git", "-C", mbed_path, "commit", msg]
            run_cmd_and_return(cmd)
        else:
            logging.info(
                "No changes detected in %s, skipping commit"
                % relpath(directory, mbed_path)
            )
        return

    if changes_made:
        logging.info("Committing image for %s" % target_toolchain)
        cmd = ["git", "-C", mbed_path, "add", relpath(directory, mbed_path)]
        run_cmd_and_return(cmd)
        msg = '--message="Updated secure binaries for %s"' % target_toolchain
        cmd = ["git", "-C", mbed_path, "commit", msg]
        run_cmd_and_return(cmd)
    else:
        logging.info(
            "No changes detected for %s, skipping commit" % target_toolchain
        )


def _run_cmake_build(cmake_build_dir, args, tgt, tfm_config):
    """
    Run the Cmake build

    :param cmake_build_dir: Base directory for Cmake build
    :param args: Command-line arguments
    :param tgt[]:
    0: Target name
    1: TF-M target name
    2: Toolchain
    3: Delivery directory
    :return Error code returned by Cmake build
    """
    if args.debug:
        msg = (
            "Building TF-M for target %s using toolchain %s in DEBUG mode"
            % (tgt[0], tgt[2],)
        )
    else:
        msg = "Building TF-M for target %s using toolchain %s" % (
            tgt[0],
            tgt[2],
        )
    logging.info(msg)

    cmake_cmd = ["cmake", "-GUnix Makefiles"]
    cmake_cmd.append(
        "-DPROJ_CONFIG="
        + (join(TF_M_BUILD_DIR, "trusted-firmware-m", "configs", tfm_config))
    )
    cmake_cmd.append("-DTARGET_PLATFORM=" + tgt[1])
    cmake_cmd.append("-DCOMPILER=" + tgt[2])

    if args.debug:
        cmake_cmd.append("-DCMAKE_BUILD_TYPE=Debug")
    else:
        cmake_cmd.append("-DCMAKE_BUILD_TYPE=Release")

    if not TARGET_MAP[tgt[0]].tfm_bootloader_supported:
        cmake_cmd.append("-DBL2=FALSE")
    else:
        cmake_cmd.append("-DBL2=True")

    cmake_cmd.append("-DENABLE_PLATFORM_SERVICE_TESTS=FALSE")

    if args.config in SUPPORTED_TFM_PSA_CONFIGS:
        if args.suite == "CRYPTO":
            cmake_cmd.append("-DPSA_API_TEST_CRYPTO=ON")
        elif args.suite == "INITIAL_ATTESTATION":
            cmake_cmd.append("-DPSA_API_TEST_INITIAL_ATTESTATION=ON")
        elif args.suite == "INTERNAL_TRUSTED_STORAGE":
            cmake_cmd.append("-DPSA_API_TEST_INTERNAL_TRUSTED_STORAGE=ON")
        elif args.suite == "PROTECTED_STORAGE":
            cmake_cmd.append("-DPSA_API_TEST_PROTECTED_STORAGE=ON")
        elif args.suite == "STORAGE":
            cmake_cmd.append("-DPSA_API_TEST_STORAGE=ON")
        elif args.suite == "IPC":
            cmake_cmd.append("-DPSA_API_TEST_IPC=ON")

    cmake_cmd.append("..")

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake configure failed for target %s using toolchain %s" % (
            tgt[0],
            tgt[2],
        )
        logging.critical(msg)
        sys.exit(1)

    # install option exports NS APIs to a dedicated folder under
    # cmake build folder
    cmake_cmd = ["cmake", "--build", ".", "--", "install"]

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake build failed for target %s using toolchain %s" % (
            tgt[0],
            tgt[2],
        )
        logging.critical(msg)
        sys.exit(1)


def _copy_binaries(source, destination, toolchain, target):
    """
    Copy TF-M binaries from source to destination

    :param source: directory where TF-M binaries are available
    :param destination: directory to which TF-M binaries are copied to
    :param toolchain: build toolchain
    :param target: target name
    """
    if destination.endswith("/"):
        output_dir = destination
    else:
        output_dir = destination + "/"

    tfm_secure_axf = join(source, "tfm_s.axf")
    logging.info(
        "Copying %s to %s"
        % (relpath(tfm_secure_axf, mbed_path), relpath(output_dir, mbed_path))
    )
    shutil.copy2(tfm_secure_axf, output_dir)

    try:
        out_ext = TARGET_MAP[target].TFM_OUTPUT_EXT
    except AttributeError:
        tfm_secure_bin = join(source, "tfm_s.bin")
        logging.info(
            "Copying %s to %s"
            % (
                relpath(tfm_secure_bin, mbed_path),
                relpath(output_dir, mbed_path),
            )
        )
        shutil.copy2(tfm_secure_bin, output_dir)
    else:
        if out_ext == "hex":
            tfm_secure_bin = join(source, "tfm_s.hex")
            global TC_DICT
            if toolchain == "ARMCLANG":
                elf2bin = join(
                    TOOLCHAIN_PATHS[TC_DICT.get(toolchain)], "fromelf"
                )
                cmd = [
                    elf2bin,
                    "--i32",
                    "--output=" + tfm_secure_bin,
                    tfm_secure_axf,
                ]
            elif toolchain == "GNUARM":
                elf2bin = join(
                    TOOLCHAIN_PATHS[TC_DICT.get(toolchain)],
                    "arm-none-eabi-objcopy",
                )
                cmd = [elf2bin, "-O", "ihex", tfm_secure_axf, tfm_secure_bin]

            run_cmd_and_return(cmd)

            logging.info(
                "Copying %s to %s"
                % (
                    relpath(tfm_secure_bin, mbed_path),
                    relpath(output_dir, mbed_path),
                )
            )
            shutil.copy2(tfm_secure_bin, output_dir)

    if TARGET_MAP[target].tfm_bootloader_supported:
        mcu_bin = join(source, "mcuboot.bin")
        shutil.copy2(mcu_bin, output_dir)

    if "TFM_V8M" in TARGET_MAP[target].extra_labels:
        install_dir = abspath(join(source, os.pardir, os.pardir))
        tfm_veneer = join(
            install_dir, "export", "tfm", "veneers", "s_veneers.o"
        )
        shutil.copy2(tfm_veneer, output_dir)


def _copy_tfm_ns_files(source, target):
    """
    Copy TF-M NS API files into Mbed OS
    :param source: Source directory containing TF-M NS API files
    """

    mbed_os_excluded_files = []

    def _is_excluded(filename):
        for f in mbed_os_excluded_files:
            if filename in f:
                return True
        return False

    def _copy_file(fname, path):
        src_file = join(source, fname["src"])
        dst_file = join(path, fname["dst"])
        if not isdir(dirname(dst_file)):
            os.makedirs(dirname(dst_file))
        try:
            if not _is_excluded(src_file):
                shutil.copy2(src_file, dst_file)
        except FileNotFoundError:
            # Workaround: TF-M build process exports all NS API files to
            # cmake build folder. The yaml file `tfm_ns_import.yaml` contains
            # list of files and folder relative to cmake build folder.
            # However, both mbed-os and regression tests needs some
            # files/folders which are not exported (the path names in
            # `tfm_ns_import.yaml` which don't begin with `install`). These
            # are handled as exceptions.
            src_file = join(source, os.pardir, fname["src"])
            shutil.copy2(src_file, dst_file)

    def _copy_folder(folder, path):
        src_folder = join(source, folder["src"])
        dst_folder = join(path, folder["dst"])
        if not isdir(dst_folder):
            os.makedirs(dst_folder)
        for f in os.listdir(src_folder):
            if os.path.isfile(join(src_folder, f)):
                if not _is_excluded(f):
                    shutil.copy2(join(src_folder, f), join(dst_folder, f))

    def _check_and_copy(list_of_items, path):
        for item in list_of_items:
            if isdir(join(source, item["src"])):
                _copy_folder(item, path)
            else:
                _copy_file(item, path)

    with open(join(dirname(__file__), "tfm_ns_import.yaml")) as ns_import:
        yaml_data = yaml.safe_load(ns_import)
        logging.info("Copying files/folders from TF-M to Mbed OS")
        mbed_os_data = yaml_data["mbed-os"]
        mbed_os_excluded_files = mbed_os_data["excluded_files"]
        if target in mbed_os_data:
            _check_and_copy(mbed_os_data[target], mbed_path)
        if "common" in mbed_os_data:
            _check_and_copy(mbed_os_data["common"], mbed_path)
        if "TFM_V8M" in TARGET_MAP[target].extra_labels:
            if "v8-m" in mbed_os_data:
                _check_and_copy(mbed_os_data["v8-m"], mbed_path)
        if "TFM_DUALCPU" in TARGET_MAP[target].extra_labels:
            if "dualcpu" in mbed_os_data:
                _check_and_copy(mbed_os_data["dualcpu"], mbed_path)

        logging.info("Copying files/folders from TF-M to regression test")
        tf_regression_data = yaml_data["tf-m-regression"]
        if target in tf_regression_data:
            _check_and_copy(tf_regression_data[target], ROOT)
        if "common" in tf_regression_data:
            _check_and_copy(tf_regression_data["common"], ROOT)
        if "TFM_V8M" in TARGET_MAP[target].extra_labels:
            if "v8-m" in tf_regression_data:
                _check_and_copy(tf_regression_data["v8-m"], ROOT)
        if "TFM_DUALCPU" in TARGET_MAP[target].extra_labels:
            if "dualcpu" in tf_regression_data:
                _check_and_copy(tf_regression_data["dualcpu"], ROOT)


def _copy_library(source, toolchain):
    dest_lib_name = (
        "libtfm_non_secure_tests.ar"
        if toolchain == "ARMCLANG"
        else "libtfm_non_secure_tests.a"
    )
    regression_lib_src = join(
        source, "install", "export", "tfm", "test", "lib"
    )
    global TC_DICT
    regression_lib_dest = join(
        ROOT, "test", "lib", "TOOLCHAIN_" + TC_DICT[toolchain]
    )
    if not isdir(regression_lib_dest):
        os.makedirs(regression_lib_dest)
    shutil.copy2(
        join(regression_lib_src, "libtfm_non_secure_tests.a"),
        join(regression_lib_dest, dest_lib_name),
    )


def _build_tfm(args):
    """
    Build TF-M
    :param args: Command-line arguments
    """

    _clone_tfm_repo(args.commit)

    cmake_build_dir = join(TF_M_BUILD_DIR, "trusted-firmware-m", "cmake_build")
    if isdir(cmake_build_dir):
        shutil.rmtree(cmake_build_dir)

    os.mkdir(cmake_build_dir)

    if args.mcu:
        if args.toolchain:
            """
            _get_target_info() returns a tuple:
            0: Target name
            1: TF-M target name
            2: Toolchain
            3: Delivery directory
            """
            tgt = _get_target_info(args.mcu, args.toolchain)
        else:
            tgt = _get_target_info(args.mcu)

        _run_cmake_build(cmake_build_dir, args, tgt, args.config)

        source = join(cmake_build_dir, "install", "outputs", tgt[1])
        _copy_binaries(source, tgt[3], tgt[2], tgt[0])

        if args.commit:
            _commit_changes(tgt[3], [(tgt[0], tgt[2])])
    else:
        tgt_list = []
        for tgt in _get_mbed_supported_tfm_targets():
            """
            _get_mbed_supported_tfm_targets() returns a generator and each
            element contains a tuple:
            0: Target name
            1: TF-M target name
            2: Toolchain
            3: Delivery directory
            """
            _run_cmake_build(cmake_build_dir, args, tgt, args.config)

            source = join(cmake_build_dir, "install", "outputs", tgt[1])
            _copy_binaries(source, tgt[3], tgt[2], tgt[0])
            tgt_list.append((tgt[0], tgt[2]))

        if args.commit:
            _commit_changes(tgt[3], tgt_list)

    _copy_library(cmake_build_dir, tgt[2])
    _copy_tfm_ns_files(cmake_build_dir, tgt[0])


def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-c",
        "--config",
        help="Use the specified TF-M configuration",
        default=SUPPORTED_TFM_CONFIGS[0],
        choices=SUPPORTED_TFM_CONFIGS,
    )

    parser.add_argument(
        "-m",
        "--mcu",
        help="Build for the given MCU",
        default=None,
        choices=_get_tfm_secure_targets(),
    )

    hmsg = "Build for the given toolchain (default is tfm_default_toolchain)"
    parser.add_argument(
        "-t",
        "--toolchain",
        help=hmsg,
        default=None,
        choices=["ARMCLANG", "GNUARM"],
    )

    parser.add_argument(
        "-d",
        "--debug",
        help="Set build profile to debug",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-l",
        "--list",
        help="Print supported TF-M secure targets",
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "--commit",
        help="""
            Commit secure binaries (TF-M) and
            features/FEATURE_PSA/TARGET_TFM/VERSION.txt
            """,
        action="store_true",
        default=False,
    )

    parser.add_argument(
        "-s",
        "--suite",
        help="Suite name for PSA API Tests",
        choices=PSA_SUITE_CHOICES,
        default=None,
    )

    return parser


def _main():
    """
    Build TrustedFirmware-M (TF-M) image for supported targets
    """
    global TF_M_BUILD_DIR
    signal.signal(signal.SIGINT, exit_gracefully)
    parser = _get_parser()
    args = parser.parse_args()

    if args.list:
        logging.info(
            "Supported TF-M targets are: {}".format(
                ", ".join([t for t in _get_tfm_secure_targets()])
            )
        )
        return

    if args.config not in SUPPORTED_TFM_CONFIGS:
        logging.info(
            "Supported TF-M configs are: {}".format(
                ", ".join([t for t in SUPPORTED_TFM_CONFIGS])
            )
        )
        return

    if args.config in SUPPORTED_TFM_PSA_CONFIGS:
        if not args.suite:
            logging.info(
                "Test suite required for supplied config: {}".format(
                    ", ".join([t for t in PSA_SUITE_CHOICES])
                )
            )
            return

    if not isdir(TF_M_BUILD_DIR):
        os.mkdir(TF_M_BUILD_DIR)

    logging.info("Using folder %s" % TF_M_BUILD_DIR)
    _build_tfm(args)


if __name__ == "__main__":
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
