# mbed-os-tf-m-regression-tests

This is an Mbed-flavored application which enables one to run the TF-M
regression test suite with Mbed OS.

## Building TF-M

Ensure you've run `mbed deploy` to obtain Mbed OS for this application. Then,
run the following command to build TF-M. We are building for the Cypress PSoC
64 (`CY8CKIT_064S2_4343W`) in our example below, but other targets can be built
for by changing the `-m` option.

```
python3 build_tfm.py -m CY8CKIT_064S2_4343W -t GNUARM
```
