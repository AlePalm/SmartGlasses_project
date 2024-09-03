#include <stdio.h>
#include "project.h"
#include "FDC1004Q.h"
#include "FDC1004Q_Defs.h"
#include "I2C_Interface.h"
#include "Interrupt_Routines.h"

#define FDC1004Q_I2C_ADDR 0x50
#define LED_ON 1
#define LED_OFF 0

int main(void)
{
    CyGlobalIntEnable; /* Enable global interrupts. */
    I2C_Master_Start();
    CyDelay(100);
    FDC_Start();
    UART_1_Start();
    CyDelay(1000);
    Pin_LED_Write(LED_ON);

    ErrorCode error;
    char message[60] = {'\0'};
    
    // Check if FDC1004Q is connected
    uint32_t rval = I2C_Master_MasterSendStart(FDC1004Q_I2C_ADDR, I2C_Master_WRITE_XFER_MODE);
    if( rval == I2C_Master_MSTR_NO_ERROR ) {
        UART_1_PutString("FDC1004Q found @ address 0xFF\r\n");
    }
    I2C_Master_MasterSendStop();
    
    // String to print out messages over UART
    
    UART_1_PutString("**************\r\n");
    UART_1_PutString("** I2C Scan **\r\n");
    UART_1_PutString("**************\r\n");
    
    CyDelay(10);
    
    // Setup the screen and print the header
	UART_1_PutString("\n\n   ");
	for(uint8_t i = 0; i<0x10; i++)
	{
        sprintf(message, "%02X ", i);
		UART_1_PutString(message);
	}
    
    // SCAN the I2C BUS for slaves
	for( uint8_t i2caddress = 0; i2caddress < 0x80; i2caddress++ ) {
        
		if(i2caddress % 0x10 == 0 ) {
            sprintf(message, "\n%02X ", i2caddress);
		    UART_1_PutString(message);
        }
 
		rval = I2C_Master_MasterSendStart(i2caddress, I2C_Master_WRITE_XFER_MODE);
        
        if( rval == I2C_Master_MSTR_NO_ERROR ) // If you get ACK then print the address
		{
            sprintf(message, "%02X ", i2caddress);
		    UART_1_PutString(message);
		}
		else //  Otherwise print a --
		{
		    UART_1_PutString("-- ");
		}
        I2C_Master_MasterSendStop();
	}
	UART_1_PutString("\n\n");
    
    /******************************************/
    /*            I2C Reading                 */
    /******************************************/
    
    Setup_Channels();
    
    
    
    for (uint8_t reg = 0; reg < 0x15; reg++)
    {
        uint8_t temp[2];
        I2C_Peripheral_ReadRegisterMulti(0x50, reg, 2, temp);
        sprintf(message, "0x%02X: 0x%04x\n", reg, (temp[0] << 8 | temp[1]));
        UART_1_PutString(message);
    }
    
    Setup_Values();
    Timer_Start();
    isr_1_StartEx(Custom_ISR_TIMER);
 
    for(;;)
    {   
    }
 }