#include <SPI.h>
#include <WiflySerial.h>
#include <Wifly.h>

#include <Wire.h>
#include <LiquidCrystal_I2C.h>

// set the LCD address to 0x27 for a 20 chars and 4 line display
LiquidCrystal_I2C lcd(0x27,20,4);
#define LCD_EMPTY_LINE "                    "
//pause char
//uint8_t pause_hex[8]  = {0x0,0x1b,0x1b,0x1b,0x1b,0x1b,0x1b,0x0};
uint8_t pause_hex[8]  = {B00000, B11011, B11011, B11011, B11011, B11011, B11011, B00000};
const int pause_char = 4;
//play char
uint8_t play_hex[8]  = {0x0,0x8,0xc,0xe,0xf,0xe,0xc,0x8};
const int play_char = 1;
//select char
//uint8_t select[8]  = {0x0,0x10,0x18,0xf,0xf,0x18,0x10,0x0};
uint8_t select_hex[8]  = {0x0,0x00,0x18,0x1e,0x1e,0x18,0x00,0x0};
const int select_char = 2;
//////////////////////////////:
byte radio_rec_hex[8] = {B00100, B01100, B11111, B01101, B00101, B00001, B00001, B11111};
const int radio_rec_char = 3;

//volt meter pwm output
#define volt_m_pin 6
//rotary encoder input
#define rotary_enc_A_pin 3
#define rotary_enc_B_pin 2
int A, B;

#define right_switch_pin 5
int right_switch;
#define left_switch_pin 7
int left_switch;
enum mode{
  RADIO_MODE,
  PODCAST_MODE,
  FILES_MODE,
  ALARM_MODE
};

#define yellow_button_pin 9
int yellow_button;
#define black_button_pin 8
int black_button;

unsigned int scroll_pos;
unsigned int scroll_max;
short int select_ind;
short int select_ind_last;
boolean browser_mode = false;
boolean podcast_mode = false;
short int path_mem[10];
unsigned char path_mem_ind = 0;

/** receive a message from server
@return the number of message processed */
int receive_messages(){  
  //receive msg from server
  String msg = Wifly::readline();
  int n = 0;
  while (msg.length() != 0){
    n ++;
    //process message
    int ind = msg.indexOf(":");
    String cmd = msg.substring(0, ind);
    String data = msg.substring(ind + 1);
    if (cmd.equals("r")){
      int l = data.length();
      l = (20 - l) / 2;
      //empty line
      lcd.setCursor(0, 0);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 1);
      lcd.print(LCD_EMPTY_LINE);
      //write radio name to screen
      lcd.setCursor(l, 1);
      lcd.print(data);
      //empty two last lines (if titles from previous station are displayed)
      lcd.setCursor(0, 2);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 3);
      lcd.print(LCD_EMPTY_LINE);
    }else if (cmd.equals("s")){
      int ind = data.indexOf("/");
      char buff[5];
      //position
      String s = data.substring(0, ind);
      s.toCharArray(buff, 5);
      scroll_pos = atoi(buff);
      //number of stations
      s = data.substring(ind + 1);
      s.toCharArray(buff, 5);
      scroll_max = atoi(buff);
      //set volt meter
      analogWrite(volt_m_pin, scroll_pos*255/(scroll_max));
    }else if (cmd.equals("rt")){
      //empty two last lines
      lcd.setCursor(0, 2);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 3);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 2);
      for (int i=0; i<data.length(); i++){
        if (i == 20){
          //go to next line
          lcd.setCursor(0, 3);
        }else if (i >= 40){
          //truncate the end if it is too long
          break;
        }
        lcd.write(data.charAt(i));
      }
    }else if (cmd.equals("channel_name")){
    //}else if (cmd.equals("channel_date")){
      lcd.setCursor(0, 0);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 1);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 2);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 0);
      int y = 0;
      for (int i=0; i<data.length(); i++){
        if (i == 20 || i == 40){
          //go to next line
           y++;
          lcd.setCursor(0, y);
        }else if (i >= 60){
          //truncate the end if it is too long
          break;
        }
        lcd.write(data.charAt(i));
      }
    }else if (cmd.equals("channel_date")){
      lcd.setCursor(0, 3);
      lcd.print("    ");
      lcd.print(data);
    }else if (cmd.equals("episode_name")){
      lcd.setCursor(0, 1);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 2);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 3);
      lcd.print(LCD_EMPTY_LINE);
      lcd.setCursor(0, 1);
      int y = 1;
      for (int i=0; i<data.length(); i++){
        if (i%20 == 0 && i!=0){
          //go to next line
          y++;
          lcd.setCursor(0, y);
        }else if (i >= 60){
          //truncate the end if it is too long
          break;
        }
        lcd.write(data.charAt(i));
      }
    }else if (cmd.equals("episode_date")){
      lcd.setCursor(0, 0);
      lcd.print(data);
      lcd.print("    ");
    }else if (cmd.equals("l")){
      ind = data.indexOf(":");
      char tmp[20];
      data.substring(0, ind).toCharArray(tmp, 19);
      int y = atoi(tmp);
      data = data.substring(ind + 1);
      lcd.setCursor(1, y);
      lcd.print(data);
      int cpt = data.length();
      while (cpt < 19){
        lcd.print(" ");
        cpt++;
      }
    }else if(cmd.equals("cursor")){
      if (data.equals("next")){
        select_ind ++;
      }else{
        select_ind --;
      }
    }
    msg = Wifly::readline();
  }
  return n;
}

/** Starts the radio */
void start_radio(){
  //start radio playback, process the 2 replies
  Wifly::write("radio\n");
  int c = receive_messages();
  while (c < 2){
     c += receive_messages();
  }
  lcd.setCursor(0, 0);
}

/** Starts the podcast */
void start_podcast(){
  //put loading msg
  lcd.setCursor(0, 0);
  lcd.print(LCD_EMPTY_LINE);
  lcd.setCursor(0, 1);
  lcd.print("      Podcast       ");
  lcd.setCursor(0, 2);
  lcd.print(LCD_EMPTY_LINE);
  lcd.setCursor(0, 3);
  lcd.print("          loading...");
  //stop the radio
  Wifly::write("podcast\n");
  //process reply (3)
  int c = receive_messages();
  while (c < 3){
     c += receive_messages();
  }
}

void start_browser(){
  //put loading msg
  lcd.setCursor(0, 0);
  lcd.print(LCD_EMPTY_LINE);
  lcd.setCursor(0, 1);
  lcd.print("      Browser       ");
  lcd.setCursor(0, 2);
  lcd.print(LCD_EMPTY_LINE);
  lcd.setCursor(0, 3);
  lcd.print("          loading...");
  Wifly::write("browser\n");
  //process reply (2)
  int c = receive_messages();
  while (c < 2){
     c += receive_messages();
  }
  select_ind = 3;
  select_ind_last = -1;
}

String tmp;
byte b;

void setup() {
  //LCD screen
  lcd.init();
  lcd.backlight();
  lcd.createChar(pause_char, pause_hex);
  lcd.createChar(play_char, play_hex);
  lcd.createChar(select_char, select_hex);
  lcd.createChar(radio_rec_char, radio_rec_hex);

  //Wifly
  Wifly::init();
  //Wifly auto connect to server
  //wait for TCP connection to be opened
  while (1){
    tmp = Wifly::readline();
    if (tmp.startsWith("Listen on ")){
      //wait for *OPEN* ack
      tmp = "";
      for (int i=0; i<6; i++){
        while(!WiflySerial::read(b)){
          delay(10);
        }
        tmp += b;
      }
      if (! tmp.equals("*OPEN*")){
        lcd.setCursor(0, 0);
        lcd.print("TCP Open Error !");
        //lcd.print(pause_char,BYTE);
        //lcd.print(play_char,BYTE);
        //block here
        while(1){
          delay(1000);
        }
      }
      break;
    }
  }

  ////Volt Meter  
  pinMode(volt_m_pin, OUTPUT);

  ////rotary encoder
  pinMode(rotary_enc_A_pin, INPUT);
  pinMode(rotary_enc_B_pin, INPUT);
  //set pull up resistor
  digitalWrite(rotary_enc_A_pin, HIGH);
  digitalWrite(rotary_enc_B_pin, HIGH);
  A = digitalRead(rotary_enc_A_pin);
  B = digitalRead(rotary_enc_B_pin);
  
  ////metal switch
  //left switch
  pinMode(left_switch_pin, INPUT);
  digitalWrite(left_switch_pin, HIGH);
  left_switch = digitalRead(left_switch_pin);
  //right switch
  pinMode(right_switch_pin, INPUT);
  digitalWrite(right_switch_pin, HIGH);
  right_switch = digitalRead(right_switch_pin);
  
  ////buttons
  //yellow
  pinMode(yellow_button_pin, INPUT);
  digitalWrite(yellow_button_pin, HIGH);
  yellow_button = digitalRead(yellow_button_pin);
  //black
  pinMode(black_button_pin, INPUT);
  digitalWrite(black_button_pin, HIGH);
  black_button = digitalRead(black_button_pin);
  
  process_switches(true);
}

void process_switches(bool is_init){
  int tmpL = digitalRead(left_switch_pin);
  int tmpR = digitalRead(right_switch_pin);
  if (tmpL != left_switch || tmpR != right_switch || is_init){
    //change occured
    left_switch = tmpL;
    right_switch = tmpR;
    if (left_switch == HIGH){
      if (right_switch == HIGH){
        start_radio();
        browser_mode = false;
        podcast_mode = false;
        Wifly::write("debug 0\n");
      }else{
        //do not relaod podcast if already in podcast mode
        if (!podcast_mode){
          start_podcast();
          browser_mode = false;
          podcast_mode = true;
          Wifly::write("debug 1\n");
        }
      }
    }else{
      if (right_switch == HIGH){
        //do not relaod browser mode is already in this mode
        if (!browser_mode){
          start_browser();
          podcast_mode = false;
          browser_mode = true;
          Wifly::write("debug 2\n");
        }
      }else{
        //browser_mode = false;
        Wifly::write("debug 3\n");
      }
    }
    //avoid some back and forth switching of mode due to transition
    delay(10);
  }
}

/** return true if rotary enc turned */
boolean process_rotary_enc(){
  boolean turned = false;
  int tmpA = digitalRead(rotary_enc_A_pin);
  int tmpB = digitalRead(rotary_enc_B_pin);
  if ((A==B && tmpB!=B) || (A!=B && tmpA!=A)){
    //turn left
    if (browser_mode){
      select_ind --;
      if (select_ind < 0){
        select_ind = 0;
        Wifly::write("p\n");
        turned = true;
      }
    }else{
      Wifly::write("p\n");
      turned = true;
    }
  }else if ((A==B && tmpA!=A) || (A!=B && tmpB!=B)){
    //turn right
    if (browser_mode){
      select_ind ++;
      if (select_ind > 3){
        select_ind = 3;
        Wifly::write("n\n");
        turned = true;
      }
    }else{
      Wifly::write("n\n");
      turned = true;
    }
  }
  B = tmpB;
  A = tmpA;
  return turned;
}

void update_select_cursor(){
  if ((select_ind != select_ind_last) && browser_mode){
    lcd.setCursor(0, select_ind_last);
    lcd.print(" ");
    select_ind_last = select_ind;
    lcd.setCursor(0, select_ind);
    lcd.print(select_char,BYTE);
  }
}

void process_buttons(){
  int tmp0, tmp1;
  tmp0 = digitalRead(yellow_button_pin);
  tmp1 = digitalRead(black_button_pin);
  boolean yellow_pressed = false, black_pressed = false;
  while (tmp0 == LOW || tmp1 == LOW){
    if (tmp0 == LOW){
      yellow_pressed = true;
    }
    if (tmp1 == LOW){
      black_pressed = true;
    }
    delay(10);
    tmp0 = digitalRead(yellow_button_pin);
    tmp1 = digitalRead(black_button_pin);
  }
  
  if (yellow_pressed && black_pressed){
    Wifly::write("both\n");
  }else if (yellow_pressed){
    if (browser_mode){
      Wifly::write("select:");
      Wifly::write(String(select_ind));
      Wifly::write("\n");
    }else{
      Wifly::write("select\n");
    }
  }else if (black_pressed){
    Wifly::write("back\n");
  }
  
  
  /*
  //read yellow button
  tmp_int = digitalRead(yellow_button_pin);
  boolean was_pressed = false;
  while (tmp_int == LOW){
     was_pressed = true;
    delay(10);
    tmp_int = digitalRead(yellow_button_pin);
  }
  if (was_pressed){
    if (browser_mode){
      Wifly::write("select:");
      Wifly::write(String(select_ind));
      Wifly::write("\n");
    }else{
      Wifly::write("select\n");
    }
  }
  //read black button
  tmp_int = digitalRead(black_button_pin);
  was_pressed = false;
  while (tmp_int == LOW){
    was_pressed = true;
    delay(10);
    tmp_int = digitalRead(black_button_pin);
  }
  if (was_pressed){
    Wifly::write("back\n");
  }*/
}

void loop() {
  //read and process messages received from server
  receive_messages();
  process_rotary_enc();
  /*while (process_rotary_enc()){
    delay(50);
  }*/
  process_switches(false);
  process_buttons();
  //update cursor
  update_select_cursor();
}


