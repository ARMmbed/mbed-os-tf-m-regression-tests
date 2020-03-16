/* We don't use platform_irq.h from TF-M here, because Mbed OS's MUSCA A1
 * target support already defines everything we need. We do however need a file
 * named "platform_irq.h" in order to avoid missing header warnings as
 * "tfm_peripherals_def.h" attempts to include "platform_irq.h". */
