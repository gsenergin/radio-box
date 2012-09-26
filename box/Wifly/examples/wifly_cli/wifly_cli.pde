#include <SPI.h>
#include <WiflySerial.h>

void setup() {
  Serial.begin(9600);
  Serial.println("WiFly CLI gives access to WiFly UART interface from Serial Monitor");

  WiflySerial::init();
}

byte b;
void loop() {
  //read
  while (WiflySerial::read(b)){
    Serial.print(b, BYTE);
  }
  
  //write
  if (Serial.available()){
    WiflySerial::write(Serial.read());
  }
}
