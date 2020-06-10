/* mbed Microcontroller Library
* Copyright (c) 2020 ARM Limited
* SPDX-License-Identifier: Apache-2.0
*/

// Toggle only one appropriate test.
#define RUN_REGRESSION_TESTS        1
#define RUN_PSA_COMPLIANCE_TESTS    0

#include "mbed.h"
#include "unity.h"

#if RUN_REGRESSION_TESTS

#include "test_framework_integ_test.h"
#include "tfm_peripherals_def.h"

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

extern "C" void TIMER1_Handler(void);

int main(void)
{
    // Use TF-M regression test TIMER1 IRQ handler for the TIMER1 IRQ. The TF-M
    // IRQ test requires its own handler to be installed.
    NVIC_SetVector(TFM_TIMER1_IRQ, (uint32_t)TIMER1_Handler);

    tfm_log_printf("Starting TF-M regression tests\n");

    // Disable deep sleep to avoid the TF-M IRQ test causing a hang, as the
    // TF-M IRQ test currently uses an interrupt not necessarily capable of
    // waking a target from deep sleep, depending on the target.
    sleep_manager_lock_deep_sleep();
    uint32_t retval = tfm_non_secure_client_run_tests();
    TEST_ASSERT_EQUAL_UINT32(0, retval);

    return 0;
}

#endif //RUN_REGRESSION_TESTS

#if RUN_PSA_COMPLIANCE_TESTS

extern "C" int32_t val_entry(void);

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

int main(void)
{
    // Disable deep sleep
    sleep_manager_lock_deep_sleep();

    tfm_log_printf("Starting TF-M PSA API tests\r\n");

    return val_entry();
}

#endif //RUN_PSA_COMPLIANCE_TESTS
