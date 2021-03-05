#!/usr/bin/env bash

# ARM GCC
wget -q -O gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2 "https://developer.arm.com/-/media/Files/downloads/gnu-rm/9-2019q4/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2?revision=108bd959-44bd-4619-9c19-26187abf5225&la=en&hash=E788CE92E5DFD64B2A8C246BBA91A249CB8E2D2D"
tar xf gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
mkdir -p ~/.local
mv gcc-arm-none-eabi-9-2019-q4-major/* ~/.local/

# Python environment
python3 -m pip install --user cryptography pyasn1 pyyaml jinja2 cbor mbed-cli mbed-tools
