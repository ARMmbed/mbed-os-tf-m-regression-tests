# About

This is a fairly minimal Vagrantfile and associated bootstrap scripts for
setting up a GCC-based build environment for
[TrustedFirmware-M](https://www.trustedfirmware.org).

Note that the vagrant virtual machine will contain an independent copy of TF-M
and the mbed-os-tf-m-regression-tests.

Note that by default vagrant shares `/vagrant` in the virtual machine with the
host. You can use this directory to copy binaries from inside the vagrant
machine out to the host for e.g. programming via USB.

# Howto

### TF-M + Mbed OS Regression Tests

The following quickstart instructions will build you the TF-M regression tests
for MUSCA_B1 on Mbed OS.

```
$ cd vagrant
$ vagrant up
$ vagrant ssh
$ cd mbed-os-tf-m-regression-tests
$ mbed deploy
$ python3 build_tfm.py -m ARM_MUSCA_B1 -t GNUARM -c ConfigRegressionIPC.cmake
```

### TF-M Standalone Regression Tests

These quickstart instructions will build you the TF-M regression tests for
MUSCA_B1 standalone (without Mbed OS).

```
$ cd vagrant
$ vagrant up
$ vagrant ssh
$ cd tfm/trusted-firmware-m
$ mkdir cmake_build
$ cd cmake_build
$ cmake -G"Unix Makefiles" -DPROJ_CONFIG=`readlink -f ../configs/ConfigRegressionIPC.cmake` -DTARGET_PLATFORM=MUSCA_B1 -DCOMPILER=GNUARM -DCMAKE_BUILD_TYPE=Release ../
$ cmake --build .
```

After the build completes, you should see output like the following:
```
--- snip 8< ---
[ 91%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/Native_Driver/gpio_cmsdk_drv.o
[ 92%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/common/boot_hal.o
[ 92%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/boot_hal.o
[ 92%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/common/template/tfm_initial_attestation_key_material.o
[ 93%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/common/template/tfm_rotpk.o
[ 93%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/dummy_crypto_keys.o
[ 94%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/common/template/nv_counters.o
[ 94%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/CMSIS_Driver/Driver_USART.o
[ 95%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/CMSIS_Driver/Driver_QSPI_Flash.o
[ 95%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/__/platform/ext/target/musca_b1/CMSIS_Driver/Driver_GFC100_EFlash.o
[ 95%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bl2_main.o
[ 96%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/flash_map_extended.o
[ 96%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/flash_map_legacy.o
[ 97%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/keys.o
[ 97%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/src/flash_map.o
[ 97%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bootutil/src/loader.o
[ 98%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bootutil/src/bootutil_misc.o
[ 98%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bootutil/src/image_validate.o
[ 99%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bootutil/src/image_rsa.o
[ 99%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/bootutil/src/tlv.o
[ 99%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/src/boot_record.o
[100%] Building C object bl2/ext/mcuboot/CMakeFiles/mcuboot.dir/__/__/src/security_cnt.o
[100%] Linking C executable mcuboot.axf
Memory region         Used Size  Region Size  %age Used
           FLASH:       19828 B       128 KB     15.13%
        CODE_RAM:        1164 B       512 KB      0.22%
             RAM:       22560 B       512 KB      4.30%
[100%] Built target mcuboot
```

See [TF-M's documentation](https://ci.trustedfirmware.org/job/tf-m-build-test-nightly/lastSuccessfulBuild/artifact/build-docs/tf-m_documents/install/doc/user_guide/html/index.html) for further details.
