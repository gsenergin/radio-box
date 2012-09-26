#!/usr/bin/python
# -*- coding: utf-8 -*-


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

+ podcast : turns on podcast, return first podcast channel in list
- podcast_channel:<name> : name of a podcast channel
- podcast_position:i/n : i position of the channel displayed, n number of channels
+ podcast_next : display next podcast channel
+ podcast_prev : display previous podcast channel
+ podcast_select : open the current channel
- podcast_episode:<name> : name of an episode to display
- podcast_position:i/n : i position of the episode displayed, n number of episodes
+ episode_next : display next episode in channel
+ episode_prev : display previous episode in channel
+ episode_play : play the current episode
+ episode_pause : pause the current episode

TODO
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
from TitleMonitor import *
from FrontEndWatchdog import *
from StreamHandler import *
from PodcastManager import *
from FileBrowser import *

import time, socket
import fileinput, string, os

#log
import sys
#sys.stdout = open(LOG_PATH, 'a', 0)

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gobject
gobject.threads_init() 
import gst

from RadioBoxConstant import *

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
		#load radio list from RADIO_STATION_LIST file
		self.current_station = 0;
		self.radio_list = []
		for line in fileinput.input(RADIO_STATION_LIST):
			#add (tag, url) tuple to list (without trailing \n)
			self.radio_list.append(tuple(string.split(line[:-1], " :: ", 1)))
		fileinput.close()
		#last played radio for resume feature
		self.resume_radio_tag = ""
		self.current_channel = 0;
		self.current_episode = 0;
		self.mode = ""


	''' Play the selected radio station '''
	def play_radio(self):
		#TitleMonitor fetch title of current program
		#update current radio station
		self.title_monitor.update_name(self.radio_list[self.current_station][0])
		print "TM update_name : " + self.radio_list[self.current_station][0]
		self.streamHandler.updateAddr(self.radio_list[self.current_station][1])
		print "SH update : " + self.radio_list[self.current_station][1]

	def pause_radio(self):
		self.title_monitor.update_name("")
		self.streamHandler.updateAddr("")

	def play_episode(self, episode):
		'''self.podcast_manager.download(episode)
		time.sleep(2.0);
		self.streamHandler.updateAddr(episode.path())'''
		self.streamHandler.updateAddr(episode.url)

	def scroll_position_to_cmd(self, i, n):
		#i/n
		r = ["scroll_position:"]
		r.append(str(i))
		r.append("/")
		r.append(str(n))
		r.append('\n')
		return r

	'''
	Execute a command received from the client
	@param cmd the command to execute
	@param conn the active connection
	@return 1 if success, 0 else
	'''
	def execute_command(self, cmd, conn):
		print "execute : ", cmd
		l = string.split(cmd, ":", 1)
		reply = []
		if l[0] == "radio" :
			self.mode = "radio"
			#play the radio stream
			self.play_radio()
			#send current radio station name and position
			reply.append("radio_name:")
			reply.append(self.radio_list[self.current_station][0])
			reply.append('\n')
			reply.extend(self.scroll_position_to_cmd(self.current_station, len(self.radio_list)))
			#print "play station : ", self.radio_list[self.current_station]

		elif l[0] == "next":
			if self.mode == "radio":
				self.current_station = (self.current_station + 1) % len(self.radio_list)
				#send current radio station name and position
				reply.append("radio_name:")
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
				self.streamHandler.seek(10)
			elif self.mode == "browser"\
			or self.mode == "browser.play":
				self.file_browser.next()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
		elif l[0] == "prev":
			if self.mode == "radio":
				self.current_station = self.current_station - 1
				if (self.current_station < 0):
					self.current_station += len(self.radio_list)
				#send current radio station name and position
				reply.append("radio_name:")
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
				self.streamHandler.seek(-10)
			elif self.mode == "browser"\
			or self.mode == "browser.play":
				self.file_browser.prev()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
		elif l[0] == "podcast":
			self.mode = "podcast"
			self.current_episode = 0
			self.pause_radio()
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
				self.play_episode(self.podcast_manager.channels[self.current_channel].episodes[self.current_episode])
				self.mode = "podcast.episode.playing"
			elif self.mode == "podcast.episode.playing":
				self.streamHandler.pause()
				self.mode = "podcast.episode.paused"
			elif self.mode == "podcast.episode.paused":
				self.streamHandler.resume()
				self.mode = "podcast.episode.playing"
			elif self.mode == "browser":
				try:
					p = self.file_browser.get_item_path_at(l[1])
				except:
					return 0
				print p
				if os.path.isfile(p):
					follow = self.file_browser.get_following_item_paths_of(l[1])
					self.streamHandler.updateAddr(p, follow)
					self.mode = "browser.play"
				else:
					self.file_browser.cd(p)
					reply.extend(self.file_browser.getListWindow())
					reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
			elif self.mode == "browser.pause":
				self.streamHandler.resume()
		elif l[0] == "back":
			if self.mode == "podcast.episode":
				self.mode = "podcast"
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "podcast.episode.playing"\
			or self.mode == "podcast.episode.paused":
				self.streamHandler.updateAddr("")
				self.mode = "podcast"
				reply.extend(self.podcast_manager.channels[self.current_channel].to_cmd())
				reply.extend(self.scroll_position_to_cmd(self.current_channel, len(self.podcast_manager.channels)))
			elif self.mode == "browser"\
			or self.mode == "browser.pause":
				self.mode = "browser"
				self.file_browser.up()
				reply.extend(self.file_browser.getListWindow())
				reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
			elif self.mode == "browser.play":
				self.mode = "browser.pause"
				self.streamHandler.pause()
		elif l[0] == "browser":
			self.mode = "browser"
			self.pause_radio()
			reply.extend(self.file_browser.getListWindow())
			reply.extend(self.scroll_position_to_cmd(self.file_browser.getPos(), self.file_browser.getTotal()))
			

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
			#StreamHandler
			self.streamHandler = StreamHandler()
			self.streamHandler.start()
			#podcast manager
			self.podcast_manager = PodcastManager()
			self.podcast_manager.start()
			#file browser
			self.file_browser = FileBrowser()
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
					#it looks like gst makes exceptions occurs on first connection from client
					#... plus this is not needed to detect enf of connection, coz watchdog
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
			self.streamHandler.terminate()
			self.podcast_manager.stop()
		s.close()


if __name__=="__main__":
	radio_box = RadioBoxServer()
	radio_box.run()
