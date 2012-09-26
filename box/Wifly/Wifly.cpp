#include "Wifly.h"
#include "WiflySerial.h"
static String cmd_mode = "$$$";

int Wifly::init(){
	WiflySerial::init();
}

void Wifly::reboot(){
	String cmd = String("reboot\r");
	WiflySerial::write_string(cmd);
}

int Wifly::tcp_connect(String host){
	String tmp;
	//Serial.print("Connecting to ");
	//Serial.print(host);
	WiflySerial::write_string(cmd_mode);
	delay(275);

	//in case it was already in command mode
	WiflySerial::write('\r');
	delay(100);
	WiflySerial::flush();
	WiflySerial::write('\r');

	String cmd = "open " + host + "\r";
	WiflySerial::write_string(cmd);
	delay(250);
	String s;
	WiflySerial::read_string(s);
	//Serial.println(s);
	WiflySerial::read_string(tmp);
	//Serial.println(tmp);
	if (tmp.equals("*OPEN*")){
		//Serial.println("Connect SUCCESS !");
	}
}

String Wifly::readline(){
	String s = String("");
	byte b;
	bool eol = false;
	if (! WiflySerial::available()){
		//no data available, return an empty string
		return s;
	}
	while (!eol){
		if (WiflySerial::read(b)){
			if (b == '\r'){
				//ignore
			}else if (b == '\n'){
				break;
			}else{
				s = s + String((char)b);
			}
		}else{
			delay(1);
		}
	}
	return s;
}

int Wifly::write(String buff){
	WiflySerial::write_string(buff);
}
