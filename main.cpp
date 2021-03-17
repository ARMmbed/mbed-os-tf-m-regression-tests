/* mbed Microcontroller Library
* Copyright (c) 2020 ARM Limited
* SPDX-License-Identifier: Apache-2.0
*/

#include "mbed.h"
#include "unity.h"
#include "greentea-client/test_env.h"

#if MBED_CONF_APP_REGRESSION_TEST

#include "test_framework_integ_test.h"
#include "tfm_peripherals_def.h"

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

extern "C" void TIMER1_Handler(void);

int main(void)
{
#if MBED_CONF_APP_WAIT_FOR_SYNC
    tfm_log_printf("Waiting for Greentea host\n");
    GREENTEA_SETUP(90, "default_auto");
#endif

    tfm_log_printf("Starting TF-M regression tests\n");

    // Disable deep sleep to avoid the TF-M IRQ test causing a hang, as the
    // TF-M IRQ test currently uses an interrupt not necessarily capable of
    // waking a target from deep sleep, depending on the target.
    sleep_manager_lock_deep_sleep();
    uint32_t retval = tfm_non_secure_client_run_tests();
    TEST_ASSERT_EQUAL_UINT32(0, retval);

    return 0;
}

#endif //MBED_CONF_APP_REGRESSION_TEST

#if MBED_CONF_APP_PSA_COMPLIANCE_TEST

extern "C" int32_t val_entry(void);

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

int main(void)
{
#if MBED_CONF_APP_WAIT_FOR_SYNC
    tfm_log_printf("Waiting for Greentea host\n");
    GREENTEA_SETUP(90, "default_auto");
#endif

    // Disable deep sleep
    sleep_manager_lock_deep_sleep();

    tfm_log_printf("Starting TF-M PSA API tests\r\n");

    return val_entry();
}

#endif //MBED_CONF_APP_PSA_COMPLIANCE_TEST
