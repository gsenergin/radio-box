import threading, time, string
from Queue import Queue, Empty
from RadioBoxConstant import *
import os

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gobject
gobject.threads_init() 
import gst

class MediaPlayer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.worker = StreamWorker()
		self.last_addr = ""

	def run(self):
		self.shouldRun = True
		self.worker.start()
		time.sleep(0.1)
		while self.shouldRun:
			if not self.worker.isAlive() or (time.time() - self.worker.timestamp > PLAYER_INACTIVE_TIMEOUT):
				print "re-spawn player - dead or frozen"
				self.worker.stop()
				self.worker = StreamWorker()
				self.worker.start()
				time.sleep(0.1)
				self.updateAddr(self.last_addr)
			else:
				time.sleep(0.1)

	def updateAddr(self, newAddr, follow=[]):
		self.worker.addrQ.put_nowait(newAddr)
		self.worker.follow = follow
		print ">>>>>>>>>>>>>><", follow

	def terminate(self):
		self.shouldRun = False
		time.sleep(0.1)
		self.worker.shouldRun = False

	def pause(self):
		self.worker.cmdQ.put_nowait("PAUSE")

	def resume(self):
		self.worker.cmdQ.put_nowait("RESUME")

	def seek(self, diff):
		self.worker.cmdQ.put_nowait("SEEK:"+str(diff))

	def play_episode(self, e):
		self.worker.addrQ.put_nowait(e.path())
		if e.already_dl():
			pass
		else:
			e.download()
		
	
#TODO timestamp, to be checked to conclude if stream player is frozen
class StreamWorker(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.addrQ = Queue()
		self.cmdQ = Queue()
		self.follow = []

	def stop(self):
		self.shouldRun = False

	def run(self):
		self.shouldRun = True
		gst_player = gst.Pipeline("player")
		self.timestamp = time.time()
		start_track_timestamp = time.time()
		buff_l = []
		sink = None
		source = None
		while self.shouldRun:
			self.timestamp = time.time()
			'''t, s, r = gst_player.get_state()
			if s != gst.STATE_PLAYING and len(self.follow) > 0:
				#play next file
				#print s
				#if len(self.follow) > 0\ 
				if time.time() - start_track_timestamp > 10:
					e = self.follow.pop(0)
					print "play next ", e
					self.addrQ.put_nowait(e)'''
			if not self.addrQ.empty():
				#TODO only take last in list
				#set player
				url = self.addrQ.get_nowait()
				#if address is empty, no radio are played
				if not len(url) == 0:
					gst_player.set_state(gst.STATE_NULL)
					source_engine = ""
					if (string.split(url, "://")[0] == "mms"):
						source_engine = "mmssrc location=\"" + url + "\""
					else:
						#http, local file, etc...
						source_engine = "gnomevfssrc location=\"" + url + "\""
					gst_player = gst.parse_launch(source_engine+" ! decodebin2 ! audioresample ! pulsesink")
					self.timestamp = time.time()
					start_track_timestamp = time.time()
					print "start url player"

				else:
					gst_player.set_state(gst.STATE_NULL)
			elif not self.cmdQ.empty():
				cmd = self.cmdQ.get_nowait()
				a = cmd.split(":")
				cmd = a[0]
				if len(a) > 1:
					data = a[1]
				else:
					data = "prout"
				print "SH cmd ", cmd
				print data
				if cmd == "PAUSE":
					gst_player.set_state(gst.STATE_PAUSED)
					print "pause player"
				elif cmd == "RESUME":
					gst_player.set_state(gst.STATE_PLAYING)
					print "resume player"
				elif cmd == "SEEK":
					pos = gst_player.query_position(gst.FORMAT_TIME, None)[0]
					print "current ", pos
					duration = gst_player.query_duration(gst.FORMAT_TIME, None)[0]
					print "duration ", duration
					pos += int(data)*gst.SECOND
					if pos > duration:
						pos = duration
					if pos < 0:
						pos = 0
					gst_player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, pos)
					#avoids loosing playout
					time.sleep(0.1)
		gst_player.set_state(gst.STATE_NULL)

