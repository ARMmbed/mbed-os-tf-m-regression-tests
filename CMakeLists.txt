# Copyright (c) 2021 ARM Limited. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

cmake_minimum_required(VERSION 3.19.0 FATAL_ERROR)

set(MBED_PATH ${CMAKE_CURRENT_SOURCE_DIR}/mbed-os CACHE INTERNAL "")
set(MBED_CONFIG_PATH ${CMAKE_CURRENT_BINARY_DIR} CACHE INTERNAL "")
set(APP_TARGET mbed-os-tf-m-regression-tests)

include(${MBED_PATH}/tools/cmake/app.cmake)

add_subdirectory(${MBED_PATH})

add_executable(${APP_TARGET})

project(${APP_TARGET})

target_sources(${APP_TARGET}
    PRIVATE
        main.cpp
)

# Note: This is needed because TARGET_** is part of a list instead
# of a standalone variable, and it controls the path visibility
# for Mbed CLI 1. Once Mbed CLI 1 is deprecated, we can simplify
# the path to tfm/targets/${APP_TARGET}/device.
if(${MBED_TARGET} STREQUAL "ARM_MUSCA_B1")
    set(TFM_TARGET_INCLUDE tfm/targets/TARGET_ARM_SSG/TARGET_MUSCA_B1/device)
elseif(${MBED_TARGET} STREQUAL "ARM_MUSCA_S1")
    set(TFM_TARGET_INCLUDE tfm/targets/TARGET_ARM_SSG/TARGET_MUSCA_S1/device)
else()
    message(FATAL_ERROR "Unsupported target ${MBED_TARGET}")
endif()

target_include_directories(${APP_TARGET}
    PRIVATE
        tfm/platform/include
        ${TFM_TARGET_INCLUDE}
        test/inc
)

target_link_libraries(${APP_TARGET}
    PRIVATE
        mbed-os
        mbed-psa
        mbed-greentea
)

if ("${MBED_CONFIG_DEFINITIONS}" MATCHES "MBED_CONF_APP_REGRESSION_TEST=1")
    set(TEST_LIBS
        # Note: To link successfully the order is important and reflects dependency.
        # In general: test entry point -> suites -> platform -> utilities.
        tfm_test_suite_core_ns
        tfm_test_suite_attestation_ns
        tfm_test_suite_crypto_ns
        tfm_test_suite_ipc_ns
        tfm_test_suite_its_ns
        tfm_test_suite_platform_ns
        tfm_test_suite_ps_ns
        tfm_test_suite_qcbor_ns
        tfm_test_suite_t_cose_ns
        tfm_qcbor_test
        tfm_t_cose_test
        platform_ns
        tfm_ns_integration_test
        tfm_qcbor
        tfm_t_cose
    )
    # Firmware Update test supports Musca B1 only
    if(${MBED_TARGET} STREQUAL ARM_MUSCA_B1)
        list(APPEND TEST_LIBS
            tfm_test_suite_fwu_ns
            tfm_api_ns
        )
    endif()
elseif ("${MBED_CONFIG_DEFINITIONS}" MATCHES "MBED_CONF_APP_PSA_COMPLIANCE_TEST=1")
    set(TEST_LIBS
        val_nspe
        pal_nspe
        test_combine
    )
else()
    message(FATAL_ERROR "No test enabled in mbed_app.json")
endif()

# Note: The path transformation is required because `.ar` is not
# recognized by `-l<name>` of either toolchains. This extension
# is a legacy of Mbed CLI 1. In the future we should use `.a` for
# both toolchains, and take advantage of target_link_directories()
# so each `lib<name>.a` simply becomes `<name>` in target_link_libraries().
if(${MBED_TOOLCHAIN} STREQUAL "GCC_ARM")
    set(LIB_SUFFIX ".a")
elseif(${MBED_TOOLCHAIN} STREQUAL "ARM")
    set(LIB_SUFFIX ".ar")
else()
    message(FATAL_ERROR "Unsupported toolchain ${MBED_TOOLCHAIN}")
endif()

list(TRANSFORM TEST_LIBS
    PREPEND "${CMAKE_CURRENT_SOURCE_DIR}/test/lib/TOOLCHAIN_${MBED_TOOLCHAIN}/lib"
)

list(TRANSFORM TEST_LIBS
    APPEND "${LIB_SUFFIX}"
)

target_link_libraries(${APP_TARGET}
    PRIVATE
        ${TEST_LIBS}
)

mbed_set_post_build(${APP_TARGET})

option(VERBOSE_BUILD "Have a verbose build process")
if(VERBOSE_BUILD)
    set(CMAKE_VERBOSE_MAKEFILE ON)
endif()
