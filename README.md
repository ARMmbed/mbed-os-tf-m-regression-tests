# mbed-os-tf-m-regression-tests

This is a Mbed-flavored application which enables the user to run
**TF-M regression test suite (default)** or **PSA Compliance test suite**
with the Mbed OS.

**Note**: This repository supports regression and PSA compliance tests for
**TF-M v1.1** which is currently integrated by Mbed OS.

## Prerequisite

### Development environment

Please refer to `vagrant/bootstrap.sh` and `vagrant/bootstrap-user.sh` for
details on how to set up a development environment. These scripts can be run
locally on Linux, or you may use Vagrant to create a VM suitable for
development (see `vagrant/README.md` for instructions).

### Mbed initialization

Run `mbed deploy` to obtain Mbed OS for this application.

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

## Building the TF-M Regression Test

Use the `-c` option to specify the config to override the default.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c RegressionIPC
```

## Building the PSA Compliance Test

**Note**: If you build on macOS, run:
```
export SDKROOT=$(xcrun --sdk macosx --show-sdk-path)
```

Run `build_tfm.py` with the PSA API config to build for a target.
Different suites can be built using the `-s` option.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c PsaApiTestIPC -s CRYPTO
```

**Note**: Make sure the TF-M Regression Test suite has **PASSED** on the board before
running any PSA Compliance Test suite to avoid unpredictable behavior.

## Building the Mbed OS application

After building the [TF-M regression](#Building-the-TF-M-Regression-Test) or
[PSA compliance tests](#Building-the-PSA-Compliance-Test) for the target, it should be
followed by building a Mbed OS application. This will execute the test suites previously built.

Configure an appropriate test in the `config` section of `mbed_app.json`. If you want to
flash and run tests manually, please set `wait-for-sync` to 0 so that tests start without
waiting.

```
mbed compile -m ARM_MUSCA_B1 -t GCC_ARM
```

## Running the Mbed OS application

1. Connect your Mbed Enabled device to the computer over USB.
1. Copy the binary or hex file to the Mbed device. The binary is located at `./BUILD/<TARGET>/<TOOLCHAIN>/mbed-os-tf-m-regression-tests.hex`.
1. Connect to the Mbed Device using a serial client application of your choice.
1. Press the reset button on the Mbed device to run the program.

**Note:** The default serial port baud rate is 115200 baud.

## Execute all tests suites

This will build and execute TF-M regression and PSA compliance tests with
Mbed OS application. Make sure the device is connected to your local machine.

```
python3 test_psa_target.py -t GNUARM -m ARM_MUSCA_B1
```

**Notes**:
* This script cannot be executed in the vagrant
environment because it does not have access to the USB of the host machine to
connect the target and therefore cannot run the tests, except it can only be
used to build all the tests by `-b` option.
* If you want to flash and run tests manually instead of automating them with Greentea,
you need to pass `--no-sync` so that tests start without waiting.
* The PSA Crypto test suite is currently excluded from the automated run of all
tests, because some Crypto tests are known to crash and reboot the target. This
causes the Greentea test framework to lose synchronization, and messes up the memory
and prevents subsequent suites from running.
You can flash and run the Crypto suite standalone. Make sure to either pass `--no-sync`
to `test_psa_target.py` when building tests, or build the Crypto suite manually with
`wait-for-sync` set to 0 in `mbed_app.json`. And power cycle the target before and after
the run to clear the memory.

To display help on supported options and targets:

```
python3 test_psa_target.py -h
```
