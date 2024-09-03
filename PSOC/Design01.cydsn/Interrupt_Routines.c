#include "Interrupt_Routines.h"
#include "Timer.h"
#include "UART_1.h"
#include "project.h"
#include "FDC1004Q.h"
#include "FDC1004Q_Defs.h"
#include "I2C_Interface.h"

double capacitance_values[4] = {0,0,0,0};
char message[60] = {'\0'};
uint8_t temporary[2];


void Sensors_ProcessCapacitanceData(void);

CY_ISR(Custom_ISR_TIMER)
{
    //I2C_Peripheral_ReadRegisterMulti(0x50, 0x0C, 2, temporary);
    Sensors_ProcessCapacitanceData();
    sprintf(message, "SOS\n");
    UART_1_PutString(message);
    for (uint8_t i = 0; i < 4; i++)
    {
        sprintf(message,"%.2f\n", capacitance_values[i]);
        UART_1_PutString(message);
    }
    sprintf(message, "EOS\n");
    UART_1_PutString(message);      
}


void Sensors_ProcessCapacitanceData(void)
{
    for (uint8_t ch = 0; ch < 4; ch++)
    {
        // Read measurement
        FDC_ReadMeasurement(ch, &capacitance_values[ch]);
    }
}
