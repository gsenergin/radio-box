#!/usr/bin/python
# -*- coding: utf-8 -*-

#TODO pause/play no work with mms://. When resume, one buff is taken, then nothing...

'''
## Radio Box Simple Control protocol v0.1 ##
each command is sent in the format : "cmd[;data]\n"
number are transmited in little endian

from box to server
+ radio : turns on the radio, the server should return the name and position of the station played
+ podcast : turns on podcast, return first podcast channel in list
          default is the first radio in the list, else it resumes last station played
+ browser : starts browser
+ n : next element, rotary encoder turned 1 pos to the right
+ p : previous element, rotary encoder turned 1 pos to the left
+ select : yellow button pressed
+ back : black button pressed

from server to box
- r:<name> : name of the station played
- rt:<title> : titles of current program (for example Artist/Title, or show name, etc)
- s:i/n : i position of the active element (radio station, podcast, episode, folder, etc)
- podcast_channel:<name> : name of a podcast channel
- podcast_position:i/n : i position of the channel displayed, n number of channels
- podcast_episode:<name> : name of an episode to display


threads list :
 * main : control other threads, accept conn, end other threads (use time stamp to see if threads are active)
 * active conn : manages the active conn with radioBox
 * radio player (2 threads + gstPipe processes)
 * watch dog
 * title updater

'''
from TitleMonitor import *
from FrontEndWatchdog import *
from MediaPlayer import *
from PodcastManager import *
from FileBrowser import *
from RadioPlayer import *

import time, socket
import fileinput, string, os

#log
import sys
#sys.stdout = open(LOG_PATH, 'a', 0)


from RadioBoxConstant import *

'''
## Radio Box Server ##
Provides simple network base interface to command selection and playout of internet radio
Radio box is meant to run on a computer with audio output attached to amplifier, Hifi or loudspeakers
It :
	_ Listen for incoming connection (TCP/IP)
	_ wait for commands. see Radio Box Simple Control protocol for more details
	_ control radio sation selection, play/pause
	_ provides feedback to the client : station name, position
'''
class RadioBoxServer:
	def __init__(self):
		#load radio list from RADIO_STATION_LIST file
		self.current_station = 0;
		self.radio_list = []
		for line in fileinput.input(RADIO_STATION_LIST):
			if line[0] == '#' or len(line) == 0:
				#ignore this line
				continue
			#add (tag, url) tuple to list (without trailing \n)
			self.radio_list.append(tuple(string.split(line[:-1], " :: ", 1)))
		fileinput.close()
		#last played radio for resume feature
		self.resume_radio_tag = ""
		self.current_channel = 0;
		self.current_episode = 0;
		self.mode = ""
		self.prev_next_ts = time.time()
		#playing now
		self.playing_now_list = []
		self.playing_now_ind = 0
		self.playing_now_ind_stack = []
		self.playing_now_folder = ""
		self.playing_now = False


	''' Play the selected radio station
	play live (last available data'''
	def play_radio(self):
		#pause any playing media
		self.mediaPlayer.updateAddr("")
		#TitleMonitor fetch title of current program
		#update current radio station
		self.title_monitor.update_name(self.radio_list[self.current_station][0])
		#print "TM update_name : " + self.radio_list[self.current_station][0]
		self.radioPlayer.goLive(self.radio_list[self.current_station][1])
		#print "Radio update : " + self.radio_list[self.current_station][1]

	'''pause the playout, radio is buffered'''
	def pause_radio(self):
		self.radioPlayer.pause()

	'''resume where the radio was previously paused'''
	def resume_radio(self):
		if self.mode != "radio.resume" or self.mode != "radio":
			self.radioPlayer.resume()

	'''stop the radio playout, stop buffering'''
	def stop_radio(self):
		self.title_monitor.update_name("")
		self.radioPlayer.standBy()

	def scroll_position_to_cmd(self, i, n):
		#i/n
		r = ["s:"]
		r.append(str(i))
		r.append("/")
		r.append(str(n-1))
		r.append('\n')
		return r

	'''Execute a command received from the client
	@param cmd the command to execute
	@param conn the active connection
	@return 1 if success, 0 else'''
	def execute_command(self, cmd, conn):
		print "execute : ", cmd
		l = string.split(cmd, ":", 1)
		reply = []
		if l[0] == "radio" :
			self.mode = "radio"
			#play the radio stream
			self.play_radio()
			#send current radio station name and position
			reply.append("r:")
			reply.append(self.radio_list[self.current_station][0])
			reply.append('\n')
			reply.extend(self.scroll_position_to_cmd(self.current_station, len(self.radio_list)))
		elif l[0] == "n":
			#next
			if self.mode == "radio":
				self.current_station = (self.current_station + 1) % len(self.radio_list)
				#send current radio station name and position
				reply.append("r:")
				reply.append(self.radio_list[self.current_station][0])
				reply.append('\n')
				reply.extend(self.scroll_position_to_cmd(self.current_station, len(self.radio_list)))
				#play the next radio
				self.play_radio()
			elif self.mode == "podcast":
				self.current_episode = 0
				self.current_channel = (self.current_channel + 1) % len(self.podcast_manager.channels)
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "podcast.episode" or self.mode == "podcast.episode.paused":
				self.mode = "podcast.episode"
				self.current_episode = (self.current_episode + 1) % len(self.podcast_manager.channels[self.current_channel].episodes)
				reply.extend(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_episode, len(self.podcast_manager.channels[self.current_channel].episodes)))
			elif self.mode == "podcast.episode.playing":
				#seek forward
				#self.mediaPlayer.seek(10)
				pass
			elif self.mode == "browser" or self.mode == "browser.play":
				self.file_browser.next()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
				self.playing_now = False
			elif self.mode == "radio.pause" or self.mode == "radio.resume":
				reply.extend("l:0:                  \x04\n")
				self.radioPlayer.seek(50)
				self.mode = "radio.pause"
		elif l[0] == "p":
			#previous
			if self.mode == "radio":
				self.current_station = self.current_station - 1
				if (self.current_station < 0):
					self.current_station += len(self.radio_list)
				#send current radio station name and position
				reply.append("r:")
				reply.append(self.radio_list[self.current_station][0])
				reply.append('\n')
				reply.extend(self.scroll_position_to_cmd(self.current_station, len(self.radio_list)))
				#play the previous radio
				self.play_radio()
			elif self.mode == "podcast":
				self.current_episode = 0
				self.current_channel = self.current_channel - 1
				if (self.current_channel < 0):
					self.current_channel += len(self.podcast_manager.channels)
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "podcast.episode" or self.mode == "podcast.episode.paused":
				self.mode = "podcast.episode"
				self.current_episode -= 1;
				if self.current_episode < 0:
					self.current_episode += len(self.podcast_manager.channels[self.current_channel].episodes)
				reply.extend(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_episode, len(self.podcast_manager.channels[self.current_channel].episodes)))
			elif self.mode == "podcast.episode.playing":
				#seek backward
				#self.mediaPlayer.seek(-10)
				pass
			elif self.mode == "browser" or self.mode == "browser.play":
				self.file_browser.prev()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
				self.playing_now = False
			elif self.mode == "radio.pause" or self.mode == "radio.resume":
				reply.extend("l:0:                  \x04\n")
				self.radioPlayer.seek(-50)
				self.mode = "radio.pause"
		elif l[0] == "podcast":
			#self.mediaPlayer.updateAddr("")
			self.mode = "podcast"
			self.current_episode = 0
			self.stop_radio()
			self.podcast_manager.update(wait=True)
			#send first channel name and position
			reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
			reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
		elif l[0] == "select":
			if self.mode == "podcast":
				self.mode = "podcast.episode"
				reply.extend(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_episode, len(self.podcast_manager.channels[self.current_channel].episodes)))
			elif self.mode == "podcast.episode":
				#self.mediaPlayer.play_episode(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode])
				self.mediaPlayer.updateAddr(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode].url)
				self.mode = "podcast.episode.playing"
			elif self.mode == "podcast.episode.playing":
				self.mediaPlayer.pause()
				self.mode = "podcast.episode.paused"
			elif self.mode == "podcast.episode.paused":
				self.mediaPlayer.resume()
				self.mode = "podcast.episode.playing"
			elif self.mode == "browser" or self.mode == "browser.play":
				try:
					p = self.file_browser.get_item_path_at(l[1])
				except:
					return 0
				print p
				if os.path.isfile(p):
					follow = self.file_browser.get_following_item_paths_of(l[1])
					self.mediaPlayer.updateAddr(p, follow)
					self.mode = "browser.play"
					#update play now
					self.playing_now_list = self.file_browser.ls()
					self.playing_now_ind = int(l[1]) + self.file_browser.getPos()
					self.playing_now_ind_stack = list(self.file_browser.ind_stack)
					self.playing_now_folder = self.file_browser.current_dir
					print self.playing_now_folder
					self.playing_now = True
				else:
					self.file_browser.cd(p)
					reply.extend(self.file_browser.getListWindow())
					reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
					self.playing_now = False
			elif self.mode == "radio" or self.mode == "radio.resume":
				self.pause_radio()
				reply.extend("l:0:                  \x04\n")
				self.mode = "radio.pause"
			elif self.mode == "radio.pause":
				self.resume_radio()
				reply.extend("l:0:                  \x01\n")
				self.mode = "radio.resume"
		elif l[0] == "back":
			if self.mode == "podcast.episode":
				self.mode = "podcast"
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "podcast.episode.playing"\
			or self.mode == "podcast.episode.paused":
				self.mediaPlayer.updateAddr("")
				self.mode = "podcast"
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "browser" or self.mode == "browser.play":
				self.file_browser.up()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
				self.playing_now = False
			elif self.mode == "radio.pause" or self.mode == "radio.resume":
				self.mode = "radio"
				self.play_radio()
				reply.extend("l:0:                   \n")
		elif l[0] == "browser":
			self.mode = "browser"
			self.stop_radio()
			reply.extend(self.file_browser.getListWindow())
			reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
			self.playing_now = False
		elif l[0] == "both":
			if self.mode == "browser.play":
				self.mode = "browser"
				self.mediaPlayer.pause()
			elif self.mode == "browser":
				self.mode = "browser.play"
				self.mediaPlayer.resume()
			if self.mode == "podcast.episode.playing":
				self.mode = "podcast.episode.paused"
				self.mediaPlayer.pause()
			elif self.mode == "podcast.episode.paused":
				self.mode = "podcast.episode.playing"
				self.mediaPlayer.resume()
		elif l[0] == "select_long":
			if self.playing_now_folder != "":
				self.playing_now = True
				print "!!!!!!!!!!!!!!!!!"
				print self.playing_now_list
				print self.playing_now_ind
				self.file_browser.l = self.playing_now_list
				div = int(self.playing_now_ind)/4*4
				rest = int(self.playing_now_ind) % 4
				self.file_browser.ind_stack = list(self.playing_now_ind_stack)
				self.file_browser.ind = self.playing_now_ind - (self.playing_now_ind % 4)
				self.file_browser.current_dir = self.playing_now_folder
				print self.file_browser.current_dir
				reply.extend(self.file_browser.getListWindow(l=self.playing_now_list, index=div))
				reply.extend(self.scroll_position_to_cmd(self.playing_now_ind, len(self.playing_now_list)))
				msg = []
				msg.append("cursor:")
				msg.append(str(rest))
				msg.append('\n')
				reply.extend(msg)
			else:
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))

		### send reply
		if len(reply) != 0:
			#remove french char
			reply = replace_non_ascii("".join(reply))
			print reply
			try:
				conn.send(reply)
			except:
				return 0
		return 1

	def send_title_update(self, title, conn):
		if self.mode == "radio" :
			msg = []
			msg.append("rt:")
			msg.append(title)
			msg.append('\n')
			#print msg
			try:
				conn.send("".join(msg))
			except:
				return 0

	def update_box_cursor_pos(self, cmd, conn):
		#only relevant in browser mode
		if self.playing_now:
			msg = []
			msg.append("cursor:")
			msg.append(cmd)
			msg.append('\n')
			#only next is possible
			self.playing_now_ind += 1
			#print msg
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
		#file browser
		self.file_browser = FileBrowser()
		#used to update box on currently played track
		self.playerFeedbackQ = Queue()
		while True:
			try :
				#wait for incoming connection
				print "- waiting for incoming connection at ", (HOST, PORT)
				conn, addr = s.accept()
				conn.settimeout(TIMEOUT)
			except:
				break
			#listen for incoming commands
			#watchdog monitor client with ping
			dog = Watchdog()
			dog.start()
			data = []
			#Title Monitor
			self.title_monitor = TitleMonitor(self.titleQ)
			self.title_monitor.start()
			#RadioPlayer
			self.radioPlayer = RadioPlayer()
			self.radioPlayer.start()
			#podcast manager
			self.podcast_manager = PodcastManager()
			self.podcast_manager.start()
			#mediaPlayer
			self.mediaPlayer = MediaPlayer(self.playerFeedbackQ)
			self.mediaPlayer.start()
			#while client is connected, this loop is main
			while dog.shouldRun:
				#update title of currentely running program
				if not self.titleQ.empty():
					self.send_title_update(self.titleQ.get_nowait(), conn)
				#update file browser cursor position
				if not self.playerFeedbackQ.empty():
					self.update_box_cursor_pos(self.playerFeedbackQ.get_nowait(), conn)
				#process data received from client (non blocking)
				try:
					data.append(conn.recv(BUFFER_SIZE))
				except socket.timeout:
					time.sleep(0.1)
					continue
				except:
					#it looks like gst makes exceptions occurs on first connection from client
					#... plus this is not needed to detect enf of connection, coz watchdog
					time.sleep(0.1)
					continue
				if data[-1].find("\n") != -1:
					#a new line has been received
					tmp = "".join(data).split("\n")
					#execute received command(s)
					#last element is either empty or uncomplete command
					for i in range(len(tmp) - 1):
						self.execute_command(tmp[i], conn)
					#keep any trailing data, to complete it with next recv
					data = [tmp[-1]]
			dog.stop()
			conn.close()
			self.title_monitor.stop()
			self.radioPlayer.stop()
			self.podcast_manager.stop()
			self.mediaPlayer.terminate()
		s.close()


if __name__=="__main__":
	radio_box = RadioBoxServer()
	radio_box.run()
