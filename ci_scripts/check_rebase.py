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
import sys
import signal
import shutil
import logging

sys.path.append("../")
from psa_builder import *

logging.basicConfig(
    level=logging.INFO,
    format="[Rebase-Check] %(asctime)s: %(message)s.",
    datefmt="%H:%M:%S",
)


def _add_remote_repo(repo, remote, dir):
    """
    Add a new remote to a cloned repository
    :param repo: Name of the git repository
    :param remote: Dictionary containing dependency details
    :param dir: Directory to perform operation
    """

    gitref = dependencies[remote].get(repo)[0]
    gitbranch = dependencies[remote].get(repo)[1]

    logging.info(
        "Checking if remote name %s exists for %s repo, if not add it..",
        remote,
        repo,
    )

    cmd = ["git", "-C", join(dir, repo), "remote", "show", remote]
    ret = run_cmd_and_return(cmd)
    if ret != 0:
        # Add remote name
        cmd = ["git", "-C", join(dir, repo), "remote", "add", remote, gitref]
        ret = run_cmd_and_return(cmd)
        if ret != 0:
            logging.critical(
                "Failed to add remote name - %s, error: %d", remote, ret
            )
            sys.exit(1)

        logging.info(
            "Remote name %s added successfully for %s repo", remote, repo
        )
    else:
        logging.info("Remote name %s exists for %s repo", remote, repo)


def _checkout_branch(repo, dir, branch_name):
    """
    Create a local branch for rebasing
    :param repo: Name of the git repository
    :param dir: Directory to perform operation
    """

    cmd = ["git", "-C", join(dir, repo), "checkout", "-B", branch_name]
    ret = run_cmd_and_return(cmd)
    if ret != 0:
        logging.critical("Failed to checkout %s, error: %d", branch_name, ret)
        sys.exit(1)

    logging.info("Checkout of %s complete..", branch_name)


def _perform_rebase(repo, remote_1, remote_2, dir):
    """
    Perform a rebase using 2 remotes, remote_2 is rebased on remote_1
    :param repo: Name of the git repository
    :param remote_1: Dictionary containing dependency details
    :param remote_2: Dictionary containing dependency details
    :param dir: Directory to perform operation
    """

    gitbranch_1 = dependencies[remote_1].get(repo)[1] + "-rebase"
    gitbranch_2 = dependencies[remote_2].get(repo)[1]

    check_and_clone_repo(repo, remote_1, TF_M_BUILD_DIR)
    _checkout_branch(repo, TF_M_BUILD_DIR, gitbranch_1)

    cmd = ["git", "-C", repo, "rebase", gitbranch_2]
    ret = run_cmd_output_realtime(cmd, dir)
    if ret != 0:
        logging.critical(
            "Failed to rebase %s on %s, error: %d",
            (remote_2 + "/" + gitbranch_2),
            (remote_1 + "/" + gitbranch_1),
            ret,
        )
        sys.exit(1)

    logging.info(
        "Rebase of %s on %s successfull..",
        (remote_2 + "/" + gitbranch_2),
        (remote_1 + "/" + gitbranch_1),
    )


def _setup_and_rebase_tfm_repositories():
    """
    Setup TF-M git repo and its dependencies while performing a rebase
    """
    check_and_clone_repo("trusted-firmware-m", "upstream-tfm", TF_M_BUILD_DIR)
    _add_remote_repo("trusted-firmware-m", "mbed-tfm", TF_M_BUILD_DIR)
    _perform_rebase(
        "trusted-firmware-m", "mbed-tfm", "upstream-tfm", TF_M_BUILD_DIR
    )

    check_and_clone_repo("tf-m-tests", "upstream-tfm", TF_M_BUILD_DIR)
    _add_remote_repo("tf-m-tests", "mbed-tfm", TF_M_BUILD_DIR)
    _perform_rebase("tf-m-tests", "mbed-tfm", "upstream-tfm", TF_M_BUILD_DIR)


def _main():
    """
    Perform rebase of TrustedFirmware-M (TF-M) for supported targets
    """
    signal.signal(signal.SIGINT, exit_gracefully)

    logging.info("Using folder %s" % TF_M_BUILD_DIR)

    if isdir(TF_M_BUILD_DIR):
        shutil.rmtree(TF_M_BUILD_DIR)

    os.mkdir(TF_M_BUILD_DIR)

    _setup_and_rebase_tfm_repositories()


if __name__ == "__main__":
    if are_dependencies_installed() != 0:
        sys.exit(1)
    else:
        _main()
