# mbed-os-tf-m-regression-tests

This is a Mbed-flavored application which enables the user to run
**TF-M regression test suite (default)** or **PSA Compliance test suite**,
with Mbed OS which can be configured in the `config` section of `mbed_app.json`.

## Prerequisite

Run `mbed deploy` to obtain Mbed OS for this application.

## Building TF-M

We are building for the Cypress PSoC64 (`CY8CKIT_064S2_4343W`) in our example
below, but other targets can be built for by changing the `-m` option.

```
python3 build_tfm.py -m CY8CKIT_064S2_4343W -t GNUARM
```

## Building the TF-M Regression Test

Use the `-c` option to specify the config overriding the default
`ConfigCoreIPC.cmake` config.

```
python3 build_tfm.py -m CY8CKIT_064S2_4343W -t GNUARM -c ConfigRegressionIPC.cmake
```

## Building the PSA Compliance Test

First, run `build_psa_compliance.py` to build for a target. Different suites can
be built using the `-s` option.

```
python3 build_psa_compliance.py -m CY8CKIT_064S2_4343W -s CRYPTO -t GNUARM
```

Then run `build_tfm.py` with the PSA API config.

```
python3 build_tfm.py -m CY8CKIT_064S2_4343W -t GNUARM -c ConfigPsaApiTestIPC.cmake -s CRYPTO
```

## Building the Mbed OS application

```
mbed compile -m CY8CKIT_064S2_4343W -t GCC_ARM
```

## Execute all tests for ARM_MUSCA_B1

This will build and execute TF-M regression and PSA compliance tests
for `ARM_MUSCA_B1` target only. Make sure the device is attached to your local
machine. `-d` option sets the disk and `-p` for the port and baudrate.
```
python3 test_psa_target.py -t GNUARM -m ARM_MUSCA_B1 -d D: -p COM8:115200
```
