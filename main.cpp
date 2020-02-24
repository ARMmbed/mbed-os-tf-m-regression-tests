#include "mbed.h"
#include <stdio.h>

extern "C" int tfm_log_printf(const char *fmt, ...)
{
    return printf(fmt);
}

int main(void)
{
    tfm_log_printf("Starting TF-M regression tests\n");

    return 0;
}
