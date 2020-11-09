# mbed-os-tf-m-regression-tests

This is a Mbed-flavored application which enables the user to run
**TF-M regression test suite (default)** or **PSA Compliance test suite**,
with Mbed OS which can be configured in the `config` section of `mbed_app.json`.

## Prerequisite

### Development environment

Please refer to `vagrant/bootstrap.sh` and `vagrant/bootstrap-user.sh` for
details on how to set up a development environment. These scripts can be run
locally on Linux (or macOS with GNU commands, see below), or you may use Vagrant to create a VM suitable for
development (see `vagrant/README.md` for instructions).

To build tests on macOS,

Install GNU coreutils and GCC
```
brew install coreutils
brew install gcc
```

Retarget GNU commands (Note: the `alias` method doesn't work for non-shell)
```
mkdir gnucmd
ln -s $(which greadlink) gnucmd/readlink
ln -s $(which guname) gnucmd/uname
ln -s $(which gcc-10) gnucmd/uname
PATH="$(pwd)/gnucmd:$PATH"
```
Note: `gcc-10` is the current version at the time of writing. `gcc` is Apple clang.

### Mbed initialization

Run `mbed deploy` to obtain Mbed OS for this application.

## Building TF-M

We are building for the ARM Musca B1 (`ARM_MUSCA_B1`) in our example
below, but other targets can be built for by changing the `-m` option.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM
```

## Building the TF-M Regression Test

Use the `-c` option to specify the config overriding the default
`ConfigCoreIPC.cmake` config.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c ConfigRegressionIPC.cmake
```

## Building the PSA Compliance Test

First, run `build_psa_compliance.py` to build for a target. Different suites can
be built using the `-s` option.

```
python3 build_psa_compliance.py -m ARM_MUSCA_B1 -s CRYPTO -t GNUARM
```

Then run `build_tfm.py` with the PSA API config.

```
python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c ConfigPsaApiTestIPC.cmake -s CRYPTO
```

Note: Make sure the TF-M Regression Test suite has PASSED on the board before
running any PSA Compliance Test suite to avoid unpredictable behavior.

## Building the Mbed OS application

```
mbed compile -m ARM_MUSCA_B1 -t GCC_ARM
```

## Execute all tests for ARM_MUSCA_B1

This will build and execute TF-M regression and PSA compliance tests
for `ARM_MUSCA_B1` target only. Make sure the device is attached to your local
machine. `-d` option sets the disk and `-p` for the port and baudrate.
```
python3 test_psa_target.py -t GNUARM -m ARM_MUSCA_B1 -d D: -p COM8:115200
```
