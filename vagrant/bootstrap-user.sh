#!/usr/bin/env bash

# ARM GCC
wget -q -O gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2 "https://developer.arm.com/-/media/Files/downloads/gnu-rm/9-2019q4/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2?revision=108bd959-44bd-4619-9c19-26187abf5225&la=en&hash=E788CE92E5DFD64B2A8C246BBA91A249CB8E2D2D"
tar xf gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
mkdir -p ~/.local
mv gcc-arm-none-eabi-9-2019-q4-major/* ~/.local/

# Python environment
python3 -m pip install --user cryptography pyasn1 pyyaml jinja2 cbor

# TrustedFirmware-M and dependencies
mkdir tfm
cd ~/tfm
git clone https://git.trustedfirmware.org/TF-M/trusted-firmware-m.git
git clone https://github.com/ARMmbed/mbed-crypto.git -b mbedcrypto-3.0.1
git clone https://github.com/ARM-software/CMSIS_5.git -b 5.5.0
cd ~/tfm/CMSIS_5
wget -q https://github.com/ARM-software/CMSIS_5/releases/download/5.5.0/ARM.CMSIS.5.5.0.pack
unzip -o ARM.CMSIS.5.5.0.pack
cd ~/tfm/trusted-firmware-m
git remote add ARMmbed https://github.com/ARMmbed/trusted-firmware-m.git
git fetch --all

# Mbed tools
python3 -m pip install mbed-cli

# Regression tests
cd
git clone https://github.com/ARMmbed/mbed-os-tf-m-regression-tests.git
cd ~/mbed-os-tf-m-regression-tests
git clone https://github.com/ARMmbed/mbed-os.git
