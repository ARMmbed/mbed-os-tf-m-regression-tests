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
from os.path import join, isdir
import logging

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

    def _is_git_lfs_installed():
        """
        Check if git-lfs is installed
        :return: errorcode
        """
        command = ['git', 'config', '--get', 'filter.lfs.required']
        return run_cmd_and_return(command)

    if _is_git_installed() != 0:
        logging.error('"git" is not installed. Exiting...')
        return -1
    elif _is_git_lfs_installed() != 0:
        logging.error('"git-lfs" is not installed. Exiting...')
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
