#ifndef _WIFLY_SERIAL_H_
#define _WIFLY_SERIAL_H_

//for 'byte' definition
#include <WProgram.h>

/**


Note on communication with SPI to UART
 - When reading data from register
   set first bit to 1, followed by 4 bit of register address, followed by 000
 - When writing data to register
   set first bit to 0, followed by 4 bit of register address, followed by 000
*/
class WiflySerial{
public:
	/** intializes the SPI device, and the Wifly SPI to UART device */
	static int init();

	/** @return 1 if some data is available to read, 0 else */
	static int available();

	static void flush();

	/** read one byte from Wifly Tx
	@param the byte read
	@return 1 if success, 0 else */
	static int read(byte &b);

	/** write one char (byte) to Wifly Rx */
	static void write(byte c);

	/** read a string
	@param s the string where read data is written to
	@param length the number of byte to read
	@param timeout in millisec, default 200
	@return the number of byte read
	*/
	//static int read_string(char* s, int length, int timeout);
	static int read_string(String &s);

	/** write a string  of length length */
	//static void write_string(char* s, int length);
	static void write_string(String s);
private:
	
};

#endif
