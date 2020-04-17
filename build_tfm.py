#!/usr/bin/env python
"""
Copyright (c) 2019 ARM Limited. All rights reserved.

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
import json
import sys
import signal
import shutil
import logging
from psa_builder import are_dependencies_installed, check_and_clone_repo, exit_gracefully
from psa_builder import run_cmd_and_return, run_cmd_output_realtime

ROOT = abspath(dirname(__file__))
mbed_path = join(ROOT, "mbed-os")
sys.path.insert(0, mbed_path)
from tools.toolchains import TOOLCHAIN_CLASSES, TOOLCHAIN_PATHS
from tools.targets import Target, TARGET_MAP, TARGET_NAMES

logging.basicConfig(level=logging.INFO,
                    format='[Build-TF-M] %(asctime)s: %(message)s.',
                    datefmt='%H:%M:%S')

TF_M_BUILD_DIR = join(mbed_path, 'features/FEATURE_PSA/TARGET_TFM/TARGET_IGNORE')
VERSION_FILE_PATH = join(mbed_path, 'features/FEATURE_PSA/TARGET_TFM')
TC_DICT = {"ARMCLANG": "ARMC6",
           "GNUARM": "GCC_ARM"}

SUITE_CHOICES = ['CRYPTO',
                 'INITIAL_ATTESTATION',
                 'PROTECTED_STORAGE',
                 'INTERNAL_TRUSTED_STORAGE']
SUPPORTED_TFM_PSA_CONFIGS = ['configs/ConfigPsaApiTestIPC.cmake']
SUPPORTED_TFM_CONFIGS = ['configs/ConfigCoreIPC.cmake', # Default config
                         'configs/ConfigRegressionIPC.cmake'] + SUPPORTED_TFM_PSA_CONFIGS

upstream_tfm = 'https://git.trustedfirmware.org/trusted-firmware-m.git'
mbed_tfm = 'https://github.com/ARMmbed/trusted-firmware-m.git'

dependencies = {
    # If the remote repo is changed, please delete TARGET_IGNORE folder.
    # Quick switch between remotes is not supported.
    "trusted-firmware-m": [mbed_tfm, 'dev/feature-dualcore'],
    "mbed-crypto": ['https://github.com/ARMmbed/mbed-crypto.git',
                    'mbedcrypto-3.0.1'],
    "CMSIS_5": ['https://github.com/ARM-software/CMSIS_5.git', '5.5.0'],
}

def _detect_and_write_tfm_version(tfm_dir, commit):
    """
    Identify the version of TF-M and write it to VERSION.txt
    :param tfm_dir: The filesystem path where TF-M repo is cloned
    :param commit: If True then commmit the VERSION.txt
    """
    cmd = ['git', '-C', tfm_dir, 'describe', '--tags',
           '--abbrev=12', '--dirty', '--always']
    tfm_version = run_cmd_and_return(cmd, True)
    logging.info('TF-M version: %s', tfm_version.strip('\n'))
    if not isdir(VERSION_FILE_PATH):
        os.makedirs(VERSION_FILE_PATH)
    # Write the version to Mbed OS
    with open(join(VERSION_FILE_PATH, 'VERSION.txt'), 'w') as f:
        f.write(tfm_version)
    # Write the version to the current directory
    with open('VERSION.txt', 'w') as f:
        f.write(tfm_version)

    if commit:
        _commit_changes(VERSION_FILE_PATH)

def _clone_tfm_repo(commit):
    """
    Clone TF-M git repos and it's dependencies
    :param commit: If True then commit VERSION.txt
    """
    check_and_clone_repo('trusted-firmware-m', dependencies, TF_M_BUILD_DIR)
    check_and_clone_repo('mbed-crypto', dependencies, TF_M_BUILD_DIR)
    check_and_clone_repo('CMSIS_5', dependencies, TF_M_BUILD_DIR)
    _detect_and_write_tfm_version(join(TF_M_BUILD_DIR, 'trusted-firmware-m'),
                                  commit)

def _get_tfm_secure_targets():
    """
    Creates a list of TF-M secure targets.

    :return: List of TF-M secure targets.
    """
    return [str(t) for t in TARGET_NAMES if
            Target.get_target(t).is_TFM_target]

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
                                                    TARGET_MAP[target].name)
            raise Exception(msg)
        elif toolchain not in TARGET_MAP[target].tfm_supported_toolchains:
            msg = "Toolchain %s is not supported by %s" % (toolchain,
                                                    TARGET_MAP[target].name)
            raise Exception(msg)
        tc = toolchain
    else:
        tc = TARGET_MAP[target].tfm_default_toolchain

    global TC_DICT
    if not TOOLCHAIN_CLASSES[TC_DICT.get(tc)].check_executable():
        msg = "Toolchain %s was not found in PATH" % tc
        raise Exception(msg)

    delivery_dir = join(mbed_path, 'targets',
                        TARGET_MAP[target].tfm_delivery_dir)

    if not os.path.exists(delivery_dir):
        msg = "Delivery directory (delivery_dir) missing for %s" % target
        raise FileNotFoundError(msg)

    return tuple([TARGET_MAP[target].name,
                  TARGET_MAP[target].tfm_target_name,
                  tc,
                  delivery_dir])

def _get_mbed_supported_tfm_targets():
    """
    Returns a generator with every element containing a TF-M target tuple
    (target name, TF-M target name, toolchain, delivery directory)
    """
    tfm_secure_targets = _get_tfm_secure_targets()
    logging.info("Found the following TF-M targets: {}".format(
                                                ', '.join(tfm_secure_targets)))

    return (_get_target_info(t) for t in tfm_secure_targets)

def _commit_changes(directory, target_toolchain=None):
    """
    Check for changes in `directory` and if any then commit them
    :param directory: path to be checked for changes
    :param target_toolchain: List of Tuple (target name, toolchain)
    """
    # Use --intent-to-add option of git status to identify un-tracked files
    cmd = ['git', '-C', mbed_path, 'status', 'N', directory]
    run_cmd_and_return(cmd)

    cmd = ['git', '-C', mbed_path, 'diff', '--exit-code', '--quiet', directory]
    changes_made = run_cmd_and_return(cmd)

    if target_toolchain is None:
        if changes_made:
            logging.info("Committing changes in directory %s" % directory)
            cmd = ['git', '-C', mbed_path, 'add', relpath(directory, mbed_path)]
            run_cmd_and_return(cmd)
            msg = '--message="Updated directory %s "' % directory
            cmd = ['git', '-C', mbed_path, 'commit', msg]
            run_cmd_and_return(cmd)
        else:
            logging.info("No changes detected in %s, skipping commit" %
                                                    relpath(directory,
                                                    mbed_path))
        return

    if changes_made:
        logging.info("Committing image for %s" % target_toolchain)
        cmd = ['git', '-C', mbed_path, 'add', relpath(directory, mbed_path)]
        run_cmd_and_return(cmd)
        msg = '--message="Updated secure binaries for %s"' % target_toolchain
        cmd = ['git', '-C', mbed_path, 'commit', msg]
        run_cmd_and_return(cmd)
    else:
        logging.info("No changes detected for %s, skipping commit" %
                                                            target_toolchain)

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
        msg = "Building TF-M for target %s using toolchain %s in DEBUG mode" % (
                                            tgt[0], tgt[2])
    else:
        msg = "Building TF-M for target %s using toolchain %s" % (tgt[0], tgt[2])
    logging.info(msg)

    cmake_cmd = ['cmake', '-GUnix Makefiles']
    cmake_cmd.append('-DPROJ_CONFIG=' + (join(TF_M_BUILD_DIR,
                        'trusted-firmware-m', tfm_config)))
    cmake_cmd.append('-DTARGET_PLATFORM=' + tgt[1])
    cmake_cmd.append('-DCOMPILER=' + tgt[2])

    if args.debug:
        cmake_cmd.append('-DCMAKE_BUILD_TYPE=Debug')
    else:
        cmake_cmd.append('-DCMAKE_BUILD_TYPE=Release')

    if not TARGET_MAP[tgt[0]].tfm_bootloader_supported:
        cmake_cmd.append('-DBL2=FALSE')
    else:
        cmake_cmd.append('-DBL2=True')

    cmake_cmd.append('-DENABLE_PLATFORM_SERVICE_TESTS=FALSE')

    if args.config in SUPPORTED_TFM_PSA_CONFIGS:
        if args.suite == 'CRYPTO':
            cmake_cmd.append('-DPSA_API_TEST_CRYPTO=ON')
        elif args.suite == 'INITIAL_ATTESTATION':
            cmake_cmd.append('-DPSA_API_TEST_INITIAL_ATTESTATION=ON')
        elif args.suite == 'INTERNAL_TRUSTED_STORAGE':
            cmake_cmd.append('-DPSA_API_TEST_INTERNAL_TRUSTED_STORAGE=ON')
        elif args.suite == 'PROTECTED_STORAGE':
            cmake_cmd.append('-DPSA_API_TEST_PROTECTED_STORAGE=ON')

    cmake_cmd.append('..')

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake configure failed for target %s using toolchain %s" % (
                                                        tgt[0],  tgt[2])
        logging.critical(msg)
        sys.exit(1)

    # install option exports NS APIs to a dedicated folder under
    # cmake build folder
    cmake_cmd = ['cmake', '--build', '.', '--', 'install']

    retcode = run_cmd_output_realtime(cmake_cmd, cmake_build_dir)
    if retcode:
        msg = "Cmake build failed for target %s using toolchain %s" % (
                                                        tgt[0],  tgt[2])
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
    if(destination.endswith('/')):
        output_dir = destination
    else:
        output_dir = destination + '/'

    tfm_secure_axf = join(source, 'tfm_s.axf')
    logging.info("Copying %s to %s" % (relpath(tfm_secure_axf, mbed_path),
                                      relpath(output_dir, mbed_path)))
    shutil.copy2(tfm_secure_axf, output_dir)

    try:
        out_ext = TARGET_MAP[target].TFM_OUTPUT_EXT
    except AttributeError:
        tfm_secure_bin = join(source, 'tfm_s.bin')
        logging.info("Copying %s to %s" % (relpath(tfm_secure_bin, mbed_path),
                                          relpath(output_dir, mbed_path)))
        shutil.copy2(tfm_secure_bin, output_dir)
    else:
        if out_ext == "hex":
            tfm_secure_bin = join(source, 'tfm_s.hex')
            global TC_DICT
            if toolchain == "ARMCLANG":
                elf2bin = join(TOOLCHAIN_PATHS[TC_DICT.get(toolchain)],
                               "fromelf")
                cmd = [elf2bin, "--i32",  "--output=" + tfm_secure_bin,
                    tfm_secure_axf]
            elif toolchain == "GNUARM":
                elf2bin = join(TOOLCHAIN_PATHS[TC_DICT.get(toolchain)],
                            "arm-none-eabi-objcopy")
                cmd = [elf2bin, "-O", "ihex", tfm_secure_axf, tfm_secure_bin]

            run_cmd_and_return(cmd)

            logging.info("Copying %s to %s" % (relpath(tfm_secure_bin, mbed_path),
                                              relpath(output_dir, mbed_path)))
            shutil.copy2(tfm_secure_bin, output_dir)

    if TARGET_MAP[target].tfm_bootloader_supported:
        mcu_bin = join(source, 'mcuboot.bin')
        shutil.copy2(mcu_bin, output_dir)

    if "TFM_V8M" in TARGET_MAP[target].extra_labels:
        install_dir = abspath(join(source, os.pardir, os.pardir))
        tfm_veneer = join(install_dir, "export", "tfm", "veneers",
                          "s_veneers.o")
        shutil.copy2(tfm_veneer, output_dir)

def _copy_tfm_ns_files(source, target):
    """
    Copy TF-M NS API files into Mbed OS
    :param source: Source directory containing TF-M NS API files
    """
    def copy_files(files, path):
        for f in files:
            src_file = join(source, f["src_file"])
            dst_file = join(path, f["dst_file"])
            if not isdir(dirname(dst_file)):
                os.makedirs(dirname(dst_file))
            try:
                shutil.copy2(src_file, dst_file)
            except FileNotFoundError:
                # Workaround: TF-M build process exports all NS API files to
                # cmake build folder. The json file `tfm_ns_import.json` contains
                # list of files and folder relative to cmake build folder.
                # But it doesn't export the OS abstraction layer app/os_wrapper_cmsis_rtos_v2.c
                # which is handled as an exception.
                src_file = join(source, os.pardir, f["src_file"])
                shutil.copy2(src_file, dst_file)

    def copy_folders(folders, path):
        for folder in folders:
            src_folder = join(source, folder["src_folder"])
            dst_folder = join(path, folder["dst_folder"])
            if not isdir(dst_folder):
                os.makedirs(dst_folder)
            for f in os.listdir(src_folder):
                if os.path.isfile(join(src_folder, f)):
                    shutil.copy2(join(src_folder, f), join(dst_folder, f))

    with open(join(dirname(__file__), "tfm_ns_import.json")) as ns_import:
        json_data = json.load(ns_import)
        logging.info("Copying NS API source from TF-M to Mbed OS")
        mbed_os_data = json_data["mbed-os"]
        copy_files(mbed_os_data["files"]["common"], mbed_path)
        if "TFM_V8M" in TARGET_MAP[target].extra_labels:
            copy_files(mbed_os_data["files"]["v8-m"], mbed_path)
        if "TFM_DUALCPU" in TARGET_MAP[target].extra_labels:
            copy_files(mbed_os_data["files"]["dualcpu"], mbed_path)

        copy_folders(mbed_os_data["folders"]["common"], mbed_path)
        if "TFM_DUALCPU" in TARGET_MAP[target].extra_labels:
            copy_folders(mbed_os_data["folders"]["dualcpu"], mbed_path)

        tf_regression_data = json_data["tf-m-regression"]
        copy_files(tf_regression_data["files"]["common"], ROOT)
        if "TFM_V8M" in TARGET_MAP[target].extra_labels:
            copy_files(tf_regression_data["files"]["v8-m"], ROOT)
        if "TFM_DUALCPU" in TARGET_MAP[target].extra_labels:
            copy_files(tf_regression_data["files"]["dualcpu"], ROOT)

        copy_folders(tf_regression_data["folders"], ROOT)

def _build_tfm(args):
    """
    Build TF-M
    :param args: Command-line arguments
    """

    _clone_tfm_repo(args.commit)

    cmake_build_dir = join(TF_M_BUILD_DIR, 'trusted-firmware-m', 'cmake_build')
    if isdir(cmake_build_dir):
        shutil.rmtree(cmake_build_dir)

    os.mkdir(cmake_build_dir)

    tfm_config = args.config

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

        _run_cmake_build(cmake_build_dir, args, tgt, tfm_config)

        source = join(cmake_build_dir, 'install', 'outputs' ,tgt[1])
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
            _run_cmake_build(cmake_build_dir, args, tgt, tfm_config)

            source = join(cmake_build_dir, 'install', 'outputs' ,tgt[1])
            _copy_binaries(source, tgt[3], tgt[2], tgt[0])
            tgt_list.append((tgt[0], tgt[2]))

        if args.commit:
            _commit_changes(tgt[3], tgt_list)

    _copy_tfm_ns_files(cmake_build_dir, tgt[0])

def _get_parser():
    parser = argparse.ArgumentParser()

    parser.add_argument("-c", "--config",
                        help="Use the specified TF-M configuration",
                        default=SUPPORTED_TFM_CONFIGS[0],
                        choices=SUPPORTED_TFM_CONFIGS)
    parser.add_argument("-m", "--mcu",
                        help="Build for the given MCU",
                        default=None,
                        choices=_get_tfm_secure_targets())
    hmsg = "Build for the given toolchain (default is tfm_default_toolchain)"
    parser.add_argument("-t", "--toolchain",
                        help=hmsg,
                        default=None,
                        choices=["ARMCLANG", "GNUARM"])

    parser.add_argument("-d", "--debug",
                        help="Set build profile to debug",
                        action="store_true",
                        default=False)

    parser.add_argument('-l', '--list',
                        help="Print supported TF-M secure targets",
                        action="store_true",
                        default=False)

    parser.add_argument("--commit",
                        help="""
                        Commit secure binaries (TF-M) and
                        features/FEATURE_PSA/TARGET_TFM/VERSION.txt
                        """,
                        action="store_true",
                        default=False)

    parser.add_argument("-s", "--suite",
                        help="Suite name for PSA API Tests",
                        choices=SUITE_CHOICES,
                        default=None)

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
        logging.info("Supported TF-M targets are: {}".format(
                            ', '.join([t for t in _get_tfm_secure_targets()])))
        return

    if args.config not in SUPPORTED_TFM_CONFIGS:
        logging.info("Supported TF-M configs are: {}".format(
                            ', '.join([t for t in SUPPORTED_TFM_CONFIGS])))
        return

    if args.config in SUPPORTED_TFM_PSA_CONFIGS:
        if not args.suite:
            logging.info("Test suite required for supplied config: {}".format(
                            ', '.join([t for t in SUITE_CHOICES])))
            return

    if not isdir(TF_M_BUILD_DIR):
        os.mkdir(TF_M_BUILD_DIR)

    logging.info("Using folder %s" % TF_M_BUILD_DIR)
    _build_tfm(args)

if __name__ == '__main__':
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
