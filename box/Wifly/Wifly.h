
#ifndef _WIFLY_H_
#define _WIFLY_H_

#include <WProgram.h>

/** Wifly Library
 * Connect to TCP server
 * initiate the TCP socket
 * send/receive data to/from TCP socket

Consider the following commands to configure the wifi :

set ssid
set wpa2
set phrase (password)
set channel to 0 (maybe not needed)
set wlan join 0 (auto join the network with the ssid name set)
set uart flow 1 (HW control enabled for UART)
set ip protocol 6 (enable tcp & udp)
set uart mode 0x1 (disable echo in cmd mode)
set time address 0.pool.ntp.org (NTP server)
set time zone 0 (time zone)
set time enable 1 (0 no sync to ntp, 1 on startup, n is very n minutes)
set opt deviceid "RadioBox"
set comm remote 0 (remove the default message when TCP connection opened)

open <addr> <port> 
ping <g | h | i | addr> <num> 

set ip address <addr> (local ip)
set ip localport <num>

set comm time <num> (set timeout after which data in socket buffer is sent)
set ip host
set ip remote <value> 
set sys autoconn 0 (1 : connect to host:port immediately after power up)


save
*/
class Wifly{
public:
	/** init the WiflySerial */
	static int init();

	static void reboot();

	/** connect to tcp server "address port"
	@return 1 success, 0 failure */
	static int tcp_connect(String host);

	/** read a line. If not data are available, return ""
	if at least 1 byte is available, blocks until it finds '\n'
	@return the line read */
	static String readline();

	/** writes a buff
	@param buff the buffer to write
	@return 1 success, 0 error*/
	static int write(String buff);
};

#endif
