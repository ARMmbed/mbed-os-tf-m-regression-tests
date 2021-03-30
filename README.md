# mbed-os-tf-m-regression-tests

This is an Mbed-flavored application which enables the user to run the
**TF-M regression test suite (default)** or the **PSA Compliance test suite**
for **TF-M v1.2** integrated with the **Mbed OS**.

## Prerequisites

We have provided a ready-to-use Vagrant virtual machine for building
TF-M tests, see [`vagrant/README.md`](vagrant/README.md) for instructions.

If you prefer to build and run the tests directly on your host machine,
please have the following set up.

### TF-M build environment

The following tools are needed for building TF-M:
* Commands: see [`vagrant/bootstrap.sh`](./vagrant/bootstrap.sh) for Linux,
or install equivalent packages for your operating system.
* Python environment: see [`vagrant/bootstrap-user.sh`](./vagrant/bootstrap-user.sh).
* One of the supported compilers: see "Compiler versions" on
[Arm Mbed tools](https://os.mbed.com/docs/mbed-os/v6.7/build-tools/index.html).
Make sure the compiler has been added to the `PATH` of your environment.

### Mbed OS build tools

#### Mbed CLI 2
Starting with version 6.5, Mbed OS uses Mbed CLI 2. It uses Ninja as a build system,
and CMake to generate the build environment and manage the build process in a
compiler-independent manner. If you are working with Mbed OS version prior to 6.5
then check the section [Mbed CLI 1](#mbed-cli-1).
1. [Install Mbed CLI 2](https://os.mbed.com/docs/mbed-os/latest/build-tools/install-or-upgrade.html).
1. From the command-line, import the example: `mbed-tools import mbed-os-tf-m-regression-tests`
1. Change the current directory to where the project was imported.

#### Mbed CLI 1
1. [Install Mbed CLI 1](https://os.mbed.com/docs/mbed-os/latest/quick-start/offline-with-mbed-cli.html).
1. From the command-line, import the example: `mbed import mbed-os-tf-m-regression-tests`
1. Change the current directory to where the project was imported.

### Mbed initialization

Run `mbed deploy` to obtain Mbed OS for this application. Then run
```
python3 -m pip install -r mbed-os/requirements.txt
```
to install dependencies for the Mbed tools.

## Building TF-M

We are building for the ARM Musca B1 (`ARM_MUSCA_B1`) in our example
below, but other targets can be built for by changing the `-m` option.
This builds the `CoreIPC` config by default.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM
```

**Note**: This step does not build any test suites, but the files and binaries
generated are checked into Mbed OS repository at the time of release, which
further supports the building of [mbed-os-example-psa](https://github.com/ARMmbed/mbed-os-example-psa)
without the user requiring to go through the complex process.

To display help on supported options and targets:

```
python3 build_tfm.py -h
```

## Building the TF-M Regression Test suite

Use the `-c` option to specify the config to override the default.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c RegressionIPC
```

Then follow [Building the Mbed OS application](#Building-the-Mbed-OS-application)
to build an application that runs the test suite.

## Building the PSA Compliance Test suites

**Note**: If you build on macOS, run:
```
export SDKROOT=$(xcrun --sdk macosx --show-sdk-path)
```

Run `build_tfm.py` with the PSA API config to build for a target.
Different suites can be built using the `-s` option.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c PsaApiTestIPC -s CRYPTO
```

Then follow [Building the Mbed OS application](#Building-the-Mbed-OS-application)
to build an application that runs the test suite.

**Notes**:
* To see all available suites, run `python3 build_tfm.py -h`.
* Make sure the TF-M Regression Test suite has **PASSED** on the board before
running any PSA Compliance Test suite to avoid unpredictable behavior.

## Building the Mbed OS application

After building the [TF-M regression](#Building-the-TF-M-Regression-Test) or
[PSA compliance tests](#Building-the-PSA-Compliance-Test) for the target, it should be
followed by building a Mbed OS application. This will execute the test suites previously built.

Configure an appropriate test in the `config` section of `mbed_app.json`. If you want to
*flash and run tests manually*, please set `wait-for-sync` to 0 so that tests start without
waiting.

Run one of the following commands to build the application

* Mbed CLI 2

    ```
    $ mbed-tools compile -m <TARGET> -t <TOOLCHAIN>
    ```

* Mbed CLI 1

    ```bash
    $ mbed compile -m <TARGET> -t <TOOLCHAIN>
    ```

The binary is located at:
* **Mbed CLI 2** - `./cmake_build/<TARGET>/<PROFILE>/<TOOLCHAIN>/mbed-os-tf-m-regression-tests.bin`</br>
* **Mbed CLI 1** - `./BUILD/<TARGET>/<TOOLCHAIN>/mbed-os-tf-m-regression-tests.bin`

## Running the Mbed OS application manually

1. Connect your Mbed Enabled device to the computer over USB.
1. Copy the binary or hex file to the Mbed device.
1. Connect to the Mbed Device using a serial client application of your choice.
1. Press the reset button on the Mbed device to run the program.

**Note:** The default serial port baud rate is 115200 baud.

## Automating all test suites

This will build and execute TF-M regression and PSA compliance tests with
Mbed OS application, using the [Greentea](https://os.mbed.com/docs/mbed-os/v6.7/debug-test/greentea-for-testing-applications.html) test tool. Make sure the device is connected to your local machine.

* Mbed CLI 2 (default)

    ```
    python3 test_psa_target.py -t GNUARM -m ARM_MUSCA_B1
    ```

* Mbed CLI 1

    ```
    python3 test_psa_target.py -t GNUARM -m ARM_MUSCA_B1 --cli=1
    ```

**Notes**:
* The tests cannot be run in the Vagrant
environment, which does not have access to the USB of the host machine to
connect the target. You can use it to build all the tests by running `test_psa_target.py`
with `-b` then copying `BUILD/` and `test_spec.json` to the host.
* To run all tests from an existing build, run `test_psa_target.py` with `-r`.
* If you want to flash and run tests manually instead of automating them with Greentea,
you need to pass `--no-sync` so that tests start without waiting.

To display help on supported options and targets:

```
python3 test_psa_target.py -h
```

## Expected test results

When you automate all tests, the Greentea test tool compares the test results with the logs in [`test/logs`](./test/logs) and prints a test report. *All test suites should pass*, except for the following suites that are currently **excluded** from the run:

* PSA Crypto suite: Some test cases are known to crash and reboot the target. This
causes the Greentea test framework to lose synchronization, and the residual data in the
memory prevents subsequent suites from running.

    **Tip**: You can flash and run the PSA Crypto suite separately. Make sure
    to build the Crypto suite manually with `wait-for-sync` set to 0 in
    `mbed_app.json`, and power cycle the target before and after
    the run to clear the memory. The total number of failures should match
    `CRYPTO.log` in [`test/logs`](./test/logs)`/<your-target>`.
