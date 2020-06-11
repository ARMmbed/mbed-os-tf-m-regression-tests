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
import sys
import subprocess
from os.path import join, dirname, abspath, isdir
import logging

upstream_tfm = 'https://git.trustedfirmware.org/trusted-firmware-m.git'
mbed_tfm = 'https://github.com/ARMmbed/trusted-firmware-m.git'

dependencies = {
    # If the remote repo is changed, please delete TARGET_IGNORE folder.
    # Quick switch between remotes is not supported.
    "tf-m": {
        "trusted-firmware-m": [mbed_tfm, 'dev/feature-dualcore'],
        "mbed-crypto": ['https://github.com/ARMmbed/mbed-crypto.git',
                        'mbedcrypto-3.0.1'],
        "CMSIS_5": ['https://github.com/ARM-software/CMSIS_5.git',
                        '5.5.0']
    },
    "psa-api-compliance": {
        "psa-arch-tests": ['https://github.com/ARM-software/psa-arch-tests.git',
                            'master'],
        "mbed-crypto": ['https://github.com/ARMmbed/mbed-crypto.git',
                            'mbedcrypto-3.0.1']
    }
}


PSA_SUITE_CHOICES = [
    'CRYPTO',
    'INITIAL_ATTESTATION',
    'PROTECTED_STORAGE',
    'INTERNAL_TRUSTED_STORAGE',
    'STORAGE',
    'IPC']

ROOT = abspath(dirname(__file__))
mbed_path = join(ROOT, "mbed-os")
sys.path.insert(0, mbed_path)
TF_M_BUILD_DIR = join(mbed_path,
    'features/FEATURE_EXPERIMENTAL_API/FEATURE_PSA/TARGET_TFM/TARGET_IGNORE')
POPEN_INSTANCE = None

def are_dependencies_installed():
    def _is_cmake_installed():
        """
        Check if Cmake is installed
        :return: errorcode
        """
        command = ['cmake', '--version']
        return run_cmd_and_return(command)

    def _is_make_installed():
        """
        Check if GNU Make is installed
        :return: errorcode
        """
        command = ['make', '--version']
        return run_cmd_and_return(command)

    def _is_git_installed():
        """
        Check if git is installed
        :return: errorcode
        """
        command = ['git', '--version']
        return run_cmd_and_return(command)

    if _is_git_installed() != 0:
        logging.error('"git" is not installed. Exiting...')
        return -1
    elif _is_cmake_installed() != 0:
        logging.error('"Cmake" is not installed. Exiting...')
        return -1
    elif _is_make_installed() != 0:
        logging.error('"Make" is not installed. Exiting...')
        return -1
    else:
        return 0

def run_cmd_and_return(command, output=False):
    """
    Run the command in the system and return either error code or output.
    Commands are passed as a list of tokens.
    E.g. The command 'git remote -v' would be passed in as:
     ['git', 'remote', '-v']

    :param command: System command as a list of tokens
    :param output: If set to True return output from child process
    :return: Return either output from child process or error code
    """

    global POPEN_INSTANCE
    with open(os.devnull, 'w') as fnull:
        POPEN_INSTANCE = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=fnull)

        std_out, __ = POPEN_INSTANCE.communicate()
        retcode = POPEN_INSTANCE.returncode
        POPEN_INSTANCE = None

        if output:
            return std_out.decode("utf-8")
        else:
            return retcode

def run_cmd_output_realtime(command, cmake_build_dir):
    """
    Run the command in the system and print output in realtime.
    Commands are passed as a list of tokens.
    E.g. The command 'git remote -v' would be passed in as:
     ['git', 'remote', '-v']

    :param command: System command as a list of tokens
    :param cmake_build_dir: Cmake build directory
    :return: Return the error code from child process
    """
    global POPEN_INSTANCE
    POPEN_INSTANCE = subprocess.Popen(command, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, cwd=cmake_build_dir)
    for line in iter(POPEN_INSTANCE.stdout.readline, b''):
        logging.info(line.decode("utf-8").strip('\n'))

    POPEN_INSTANCE.communicate()
    retcode = POPEN_INSTANCE.returncode
    POPEN_INSTANCE = None
    return retcode

def check_and_clone_repo(name, deps, dir):
    """
    Check if the repositories are already cloned. If not clone them
    :param name: Name of the git repository
    :param deps: Dictionary containing dependency details
    :param dir: Directory to perform cloning
    """

    gitref = deps.get(name)[1]
    if not isdir(join(dir, name)):
        logging.info('Cloning %s repo', name)
        cmd = ['git', '-C', dir, 'clone', '-b',
               gitref, deps.get(name)[0]]
        run_cmd_and_return(cmd)
        logging.info('Cloned %s repo successfully', name)
    else:
        logging.info('%s repo exists, fetching latest...', name)
        cmd = ['git', '-C', join(dir, name), 'fetch']
        run_cmd_and_return(cmd)
        logging.info('%s repo exists, checking out %s...', name, gitref)
        head = 'origin/' + gitref
        cmd = ['git', '-C', join(dir, name), 'checkout', head]
        run_cmd_and_return(cmd)
        logging.info('Checked out %s successfully', gitref)

def exit_gracefully(signum, frame):
    """
    Crtl+C signal handler to exit gracefully
    :param signum: Signal number
    :param frame:  Current stack frame object
    """
    logging.info("Received signal %s, exiting..." % signum)
    global POPEN_INSTANCE
    try:
        if POPEN_INSTANCE:
            POPEN_INSTANCE.terminate()
            while not POPEN_INSTANCE.poll():
                continue
    except:
        pass

    sys.exit(0)
