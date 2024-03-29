#include "WiflySerial.h"
#include </usr/share/arduino/libraries/SPI/SPI.h>

#include "pins_arduino.h"

//WiFly SPI <-> UART interface (750) sc16is740_750_760.pdf
#define RHR 0x0
#define THR 0x0
#define EFR 0x2
#define FCR 0x2
#define LCR 0x3
#define SPR 0x7
#define TXLVL 0x8
#define RXLVL 0x9

#define DLL 0x0
#define DLM 0x1

#define READ_REGISTER_MASK 0b10000000

inline void write_register(byte registerAddr, byte data){
  digitalWrite(SS, LOW);
  SPI.transfer(registerAddr << 3);
  SPI.transfer(data);
  digitalWrite(SS, HIGH);
}

inline byte read_register(byte registerAddr){
  byte result;
  digitalWrite(SS, LOW);
  //acces the register
  SPI.transfer(READ_REGISTER_MASK | (registerAddr << 3));
  //send dummy data, only to read a byte
  result = SPI.transfer(0xFF);
  //result = spi_transfer(0xFF);
  digitalWrite(SS, HIGH);
  return result;
}

int WiflySerial::init(){
  //it also init the SS slave control pin as output
  SPI.begin();
  SPI.setBitOrder(MSBFIRST);
  SPI.setDataMode(SPI_MODE0);
  
  //disable WiFly
  digitalWrite(SS, HIGH);
  
  //set SPI clock (this one work, for some reason...)
  SPI.setClockDivider(SPI_CLOCK_DIV2);

  //set SPI-UART baud rate
  //divisor = crystal_freq / (baudrate*16)
  unsigned long divisor = 14745600UL / (9600*16UL);
  //Serial.println(divisor);// = 96
  write_register(LCR, 0b10000000);
  write_register(DLL, lowByte(divisor));
  write_register(DLM, highByte(divisor));

  //Enable access to EFR register...
  //...by setting LCR (0x3) to 0xBF (as specified in doc)
  write_register(LCR, 0xBF);
  
  //EFR (0x2) is used to set HW flow control
  //HW flow control enabled (CTS and RTS set)
  write_register(EFR, 0xD0);

  //set UART to 8 data bit, 1 stop bit, no parity
  //reset LCR to normal
  write_register(LCR, 0x03);

  //reset TXFIFO and RXFIFO, non FIFO mode
  write_register(FCR, 0x06);
  
  // enable FIFO mode
  write_register(FCR, 0x01);
  
  ////Test by writing to Scratch Pad Register
  //0x51 Q is used as test char
  write_register(SPR, 0x51);
  //read from SPR
  byte res = read_register(SPR);

  //test success if the byte read is the same as the one written
  if (0x51 != res){
    //Serial.println("WiFly startup ERROR");
	return -1;
  }
  //Serial.println("WiFly is up & running");
  return 0;
}

int WiflySerial::read(byte &b){
	if (read_register(RXLVL) > 0){
		b = read_register(RHR);
		return 1;
	}
	return 0;
}

void WiflySerial::write(byte data){
	//ensure that there's enough space to write
    while (read_register(TXLVL) == 0){
      //retry...
    }
    write_register(THR, data);
}

int WiflySerial::available(){
	return (int)read_register(RXLVL);
}

void WiflySerial::flush(){
	byte b;
	while(read(b)){};
}

//read max possible
int WiflySerial::read_string(String &s){
	int cnt = 0;
	byte b;
	while (read(b)){
		s = s + String((char)b);
		cnt ++;
	}
	return cnt;
}

void WiflySerial::write_string(String s){
	for (int i=0; i<s.length(); i++){
		write(s.charAt(i));
	}
}

#if 0

int WiflySerial::read_string(char* s, int length, int timeout=200){
	unsigned long t0 = millis();
	int cnt = 0;
	byte b;
	while (cnt < length){
		if (read(b)){
			s[cnt] = b;
			cnt ++;
		}else{
			if (millis() - t0 > timeout){
				break;
			}else{
				delay(1);
			}
		}
	}
	return cnt;
}

void WiflySerial::write_string(char* s, int length){
	for (int i=0; i<length; i++){
		write(s[i]);
	}
}
#endif
