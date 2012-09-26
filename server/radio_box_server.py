#!/usr/bin/python


'''
## Radio Box Simple Control protocol v0.1 ##
each command is sent in the format : "cmd[;data]\n"
number are transmited in little endian

Command List (+ receive, - send) :
+ radio : turns on the radio, the server should return the name and position of the station played
          default is the first radio in the list, else it resumes last station played
- radio_name:<name> : name of the station played
- radio_position:i/n : i position of the station played, n number of stations
- radio_title:<title> : titles of current program (for example Artist/Title, or show name, etc)
+ radio_next : set the active station to be the next in the list
+ radio_prev : set the active station to be the previous in the list

+ radio_rec : start record the active station, stop the playout (backup only last rec ? append to last rec ? max 200 MB ? then have to set position ?)
+ radio_rec_play : start play the record
+ radio_rec_pause : pause the record

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
TODO : re-orgnaize thread better coz of main thread fails (some error reading radio which isn't on-line, then other thread hangs for ever
threads list = 
 * main : monitor other threads, accept conn, end other threads (use time stamp to see if threads are active)
 * active conn : manages the active conn with radioBox
 * plays music (this also avoid to get lagging when stream takes time to come)
 * watch dog
 * title updater

'''
import time, socket
import fileinput, string, os

#debug
import sys
#sys.stdout = open('radio_stdout', 'w', 0)

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gobject
gobject.threads_init() 
import gst

RADIO_STATION_LIST = "live_radio.list"
REC_FILE_NAME = "radio_record.ogg"
REC_FILE_RATE = 128000
VOLUME = 80

#HOST = '127.0.0.1'
HOST = '192.168.1.107'
PORT = 50456
BUFFER_SIZE = 4096
TIMEOUT = 0.01


'''
## Radio Box Server ##
Provides simple network base interface to command selection and playout of internet radio
Radio box is meant to run on a computer with audio output attached to amplifier, Hifi or loudspeakers
It :
	_ Listen for incoming connection (TCP/IP)
	_ wait for commands. see Radio Box Simple Control protocol for more details
	_ control radio sation selection, play/pause
	_ provides data to the client : station name, position
'''
class RadioBoxServer:
	def __init__(self):
		self.streamHandler = StreamHandler()
		#self.gstream_rec = gst.Pipeline("recorder")
		#self.rec_appsink = gst.element_factory_make('appsink', 'rec_appsink')
		#self.rec_appsink.set_property('emit-signals', True)
		#self.rec_appsink.connect('new-buffer', self.write_rec_buffer)

		#rec file
		#self.rec_file = open(REC_FILE_NAME, 'r+')
		#test_pipeline = gst.parse_launch("gnomevfssrc location=\"http://mp3.live.tv-radio.com/franceinter/all/franceinterhautdebit.mp3\" ! decodebin ! alsasink")
		#test_pipeline.set_state(gst.STATE_PLAYING)

		#list of radio loaded from RADIO_STATION_LIST file
		self.current_station = 0;
		self.radio_list = []
		for line in fileinput.input(RADIO_STATION_LIST):
			#add (tag, url) tuple to list (without trailing \n)
			self.radio_list.append(tuple(string.split(line[:-1], " :: ", 1)))
		fileinput.close()

		#save last played radio to resume it
		self.resume_radio_tag = ""

	def write_rec_buffer(self, appsink):
		buff = appsink.emit('pull-buffer')
		self.rec_file.write(buff)
		#self.rec_file.flush()

	'''
	Play the selected radio station

	TODO make it in a sub-process, then it doesn't hang if a radio is off line (like sin-sing did
	'''
	def play_radio(self):
		url = self.radio_list[self.current_station][1]

		#TitleMonitor fetch title of current program
		#update current radio station
		self.title_monitor.update_name(self.radio_list[self.current_station][0])
		print "TM update_name : " + self.radio_list[self.current_station][0]

		#set player
		source_engine = ""
		if (string.split(url, "://")[0] == "mms"):
			source_engine = "mmssrc"
		else :
			#http, ssh, ftp, etc...
			source_engine = "gnomevfssrc"
		self.gstream_player.set_state(gst.STATE_NULL)
		##self.gstream_rec.set_state(gst.STATE_NULL)
		self.gstream_player = gst.parse_launch(source_engine+" location=\"" + url + "\" ! decodebin ! volume name=\"volume\" ! alsasink")
		#self.gstream_rec = gst.parse_launch(source_engine+" location=\"" + url + "\" ! mad ! volume name=\"volume\" ! audioconvert ! vorbisenc ! oggmux ! filesink location=radio_record.ogg")
		#self.gstream_rec = gst.parse_launch(source_engine+" location=\"" + url + "\" ! decodebin ! volume name=\"volume\" ! audioconvert ! vorbisenc name=vorbisenc ! oggmux name=oggmux ! filesink location=radio_record.ogg")

		##self.gstream_rec = gst.parse_launch(source_engine+" location=\"" + url + "\" ! decodebin ! volume name=\"volume\" ! audioconvert ! vorbisenc name=vorbisenc ! oggmux name=oggmux")
			
		##self.gstream_rec.add(self.rec_appsink)
		##gst.element_link_many(self.gstream_rec.get_by_name("oggmux"), self.rec_appsink)
		##print self.gstream_rec.get_by_name("oggmux")
		##print self.rec_appsink

		##self.gstream_rec.get_by_name("vorbisenc").set_property('bitrate', REC_FILE_RATE)
		#mute and wait 0.5 sec to avoid a loud "crack" sound when starting streaming
		self.gstream_player.get_by_name("volume").set_property('mute', True)
		##self.gstream_rec.get_by_name("volume").set_property('mute', True)
		#pos_int = self.gstream_player.query_position(gst.FORMAT_TIME, None)[0]
		#seek_ns = (2 * 1000000000)
		#self.gstream_player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns)

		self.gstream_player.set_state(gst.STATE_PLAYING)
		##self.gstream_rec.set_state(gst.STATE_PLAYING)

		time.sleep(0.5)
		self.gstream_player.get_by_name("volume").set_property("mute", False)
		##self.gstream_rec.get_by_name("volume").set_property("mute", False)


	'''
	Execute a command received from the client
	@param cmd the command to execute
	@param conn the active connection
	@return 1 if success, 0 else
	'''
	def execute_command(self, cmd, conn):
		print "execute : ", cmd
		l = string.split(cmd, ";", 1)
		reply = []
		if l[0] == "radio" :
			#print "resume was : ", self.resume_radio_tag
			#send current radio station name and position
			reply.append("radio_name:")
			reply.append(self.radio_list[self.current_station][0])
			reply.append('\n')

			reply.append("radio_position:")
			reply.append(str(self.current_station))
			reply.append("/")
			reply.append(str(len(self.radio_list)))
			reply.append('\n')
			#print "reply : ", reply

			#play the radio
			self.play_radio()
			#print "play station : ", self.radio_list[self.current_station]

		elif l[0] == "radio_next":
			self.current_station = (self.current_station + 1) % len(self.radio_list)
			#send current radio station name and position
			reply.append("radio_name:")
			reply.append(self.radio_list[self.current_station][0])
			reply.append('\n')

			reply.append("radio_position:")
			reply.append(str(self.current_station))
			reply.append("/")
			reply.append(str(len(self.radio_list)))
			reply.append('\n')
			#print "reply : ", reply

			#play the next radio
			self.play_radio()
			#print "play station : ", self.radio_list[self.current_station]

		elif l[0] == "radio_prev":
			self.current_station = (self.current_station - 1)
			if (self.current_station < 0):
				self.current_station += len(self.radio_list)
			#send current radio station name and position
			reply.append("radio_name:")
			reply.append(self.radio_list[self.current_station][0])
			reply.append('\n')

			reply.append("radio_position:")
			reply.append(str(self.current_station))
			reply.append("/")
			reply.append(str(len(self.radio_list)))
			reply.append('\n')
			#print "reply : ", reply

			#play the previous radio
			self.play_radio()
			#print "play station : ", self.radio_list[self.current_station]


		if len(reply) != 0:
			try:
				conn.send("".join(reply))
			except:
				return 0
		return 1

	def send_title_update(self, title, conn):
		msg = []
		msg.append("radio_title:")
		msg.append(title)
		msg.append('\n')
		print msg
		try:
			conn.send("".join(msg))
		except:
			return 0

	def run(self):
		#open socket, listen to port
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		s.bind((HOST, PORT))
		s.listen(1)
		self.titleQ = Queue()
		while True:
			try :
				#wait for incoming connection
				print "- waiting for incoming connection at ", (HOST, PORT)
				conn, addr = s.accept()
				conn.settimeout(TIMEOUT)
			except:
				break
			#listen for incoming commands
			print "-- waiting for command..."
			#watchdog monitor client with ping
			dog = Watchdog()
			dog.start()
			data = []
			#Title Monitor
			self.title_monitor = TitleMonitor(self.titleQ)
			self.title_monitor.start()
			#while client is connected, this loop is main
			while dog.shouldRun:
				#update title of currentely running program
				if not self.titleQ.empty():
					self.send_title_update(self.titleQ.get_nowait(), conn)
				#process data received from client (non blocking)
				try:
					data.append(conn.recv(BUFFER_SIZE))
				except socket.timeout:
					continue
				except:
					data = 0
				if not data:
					print "disconnected from client..."
					print "Unexpected error:", sys.exc_info()[0]
					break
				if data[-1].find("\n") != -1:
					#a new line has been received
					tmp = "".join(data).split("\n")
					#execute received command(s)
					#last element is either empty or uncomplete command
					#print "tmp : " + str(tmp)
					#print range(len(tmp) - 1)
					for i in range(len(tmp) - 1):
						self.execute_command(tmp[i], conn)
					#self.execute_command(tmp[0], conn)
					data = [tmp[-1]]
					#keep any trailing data, to complete it with next recv
					#data = tmp[-1]
			self.gstream_player.set_state(gst.STATE_NULL)
			#self.gstream_rec.set_state(gst.STATE_NULL)
			dog.stop()
			conn.close()
			self.title_monitor.stop()
		s.close()
		##self.rec_file.close()

import threading, time, subprocess
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty

#ping echo timeout in sec
ECHO_TIMEOUT = 0.5

class Watchdog(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		#self.conn = conn
		self.shouldRun = True;

	''' To be run in separate thread
	read data from pipe and write it to queue
	this allows to read pipe data through queue without blocking
	'''
	def read_pipe(self, q, p):
		while self.shouldRun:
			q.put(p.stdout.readline())

	def run(self):
		echo_timestamp = time.time()
		p = Popen(["ping", "-A", "192.168.1.69"], stdout=PIPE)
		#p = Popen(["ping", "192.168.1.69"], stdout=PIPE)
		q = Queue()
		worker = Thread(target=Watchdog.read_pipe, args=(self, q, p))
		worker.start()
		while self.shouldRun:
			if time.time() - echo_timestamp > ECHO_TIMEOUT:
				#no echo for too long, close the connection
				self.shouldRun = False
				break;
			try:
				line = q.get_nowait()
			except:
				time.sleep(0.01)
				continue
			if line.find("Unreachable") == -1 :
				echo_timestamp = time.time()

	def stop(self):
		self.shouldRun = False


class StreamHandler(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		#self.conn = conn
		self.shouldRun = True
		self.current_addr = ""
		self.gstream_player = gst.Pipeline("player")

	''' To be run in separate thread
	read data from pipe and write it to queue
	this allows to read pipe data through queue without blocking
	'''
	def read_pipe(self, q, p):
		while self.shouldRun:
			q.put(p.stdout.readline())

	def run(self):
		q = Queue()
		while self.shouldRun:
			if time.time() - echo_timestamp > ECHO_TIMEOUT:
				#no echo for too long, close the connection
				self.shouldRun = False
				break;
			try:
				line = q.get_nowait()
			except:
				time.sleep(0.01)
				continue
			if line.find("Unreachable") == -1 :
				echo_timestamp = time.time()

	def stop(self):
		self.shouldRun = False


import urllib2
#number of second between each relaod of title
RELOAD_TIMEOUT = 20.0
class TitleMonitor(threading.Thread):
	def __init__(self, q):
		threading.Thread.__init__(self)
		self.shouldRun = True;
		self.q = q
		self.radio_name = ""
		self.nameQ = Queue()
		self.url = ""

	def run(self):
		print "start TM : " + self.radio_name
		u = None
		last_title = ""
		reload_timestamp = time.time()
		while self.shouldRun:
			if not self.nameQ.empty():
				#get last item
				while not self.nameQ.empty():
					self.radio_name = self.nameQ.get_nowait()
				#update url address
				if u != None:
					u.close()
				print "title url changed"
				if self.radio_name == "Sing Sing":
					self.url = 'http://www.sing-sing.org/programmation/'
					#this will trigger relaod
					reload_timestamp = 0
				elif self.radio_name == "France Inter":
					self.url = 'http://www.franceinter.fr'
					reload_timestamp = 0
				else:
					self.url = ""
					u = None
					last_title = ""
					self.q.put_nowait("")
					continue
			#print "self.url " + self.url
			#print "(time.time() - reload_timestamp) " + str((time.time() - reload_timestamp))
			#time.sleep(10.0)
			if self.url != "" and (time.time() - reload_timestamp) > RELOAD_TIMEOUT:
				print "TM do reload " + self.radio_name
				reload_timestamp = time.time()
				#fetch url target
				if u != None:
					u.close()
				u = urllib2.urlopen(self.url)
				data = u.read()
				#parse url and enqueue status if it has changed
				if self.radio_name == "Sing Sing":
					#find the first line (from the table title)
					ind = data.find("Artiste", 261)
					#artist
					ind = data.find("<font color=\"black\">", ind)
					ind = data.find("<font color=\"black\">", ind+1)
					title = data[ind + 20 : data.find("</font>", ind)]
					title += "/"
					# title
					ind = data.find("<font color=\"black\">", ind+1)
					title += data[ind + 20 : data.find("</font>", ind)]
					if title != last_title:
						try:
							#print "send "+title
							self.q.put_nowait(title)
							#print "sent"
							last_title = title
						except:
							pass
				elif self.radio_name == "France Inter":
					ind = data.find("<a href=\"/player\" class=\"rf-player-open title\" title=\"Ecouter France Inter en direct\">")
					title = data[ind + 87 : data.find("</a>", ind) - 1]
					title = title.decode('utf8').encode('ascii', 'ignore')
					#print title
					print "bite cul last_title " + last_title
					print "--------------title " + title
					if title != last_title:
						try:
							#print "send "+title
							self.q.put_nowait(title)
							#print "sent"
							last_title = title
						except:
							pass
			else:
				#no url set
				time.sleep(0.01)
		if u != None:
			u.close()
		print "end TM"

	def update_name(self, name):
		self.nameQ.put_nowait(name)

	def stop(self):
		self.shouldRun = False


if __name__=="__main__":
	radio_box = RadioBoxServer()
	radio_box.run()



