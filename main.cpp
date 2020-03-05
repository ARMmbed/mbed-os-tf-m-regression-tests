#include "mbed.h"
#include "unity.h"
#include "test_framework_integ_test.h"
#include "tfm_peripherals_def.h"
#include <stdio.h>

extern "C" void TIMER1_Handler(void);

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

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
