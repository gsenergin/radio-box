import threading, time, string
from Queue import Queue, Empty
from RadioBoxConstant import *

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
import gobject
gobject.threads_init() 
import gst

class StreamHandler(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.player = StreamPlayer()
		self.last_addr = ""

	def run(self):
		self.shouldRun = True
		self.player.start()
		time.sleep(0.1)
		while self.shouldRun:
			if not self.player.isAlive():
				print "re-spawn player - dead"
				self.player.stop()
				self.player = StreamPlayer()
				self.player.start()
				time.sleep(0.1)
				self.updateAddr(self.last_addr)
			elif time.time() - self.player.timestamp > PLAYER_INACTIVE_TIMEOUT:
				print "re-spawn player - frozen"
				self.player.stop()
				self.player = StreamPlayer()
				self.player.start()
				time.sleep(0.1)
				self.updateAddr(self.last_addr)
			else:
				#debug
				#clk = self.player.gstream_player.get_clock()
				#print clk.get_time()
				time.sleep(0.1)

	def updateAddr(self, newAddr, follow=[]):
		self.player.addrQ.put_nowait(newAddr)
		self.player.follow = follow
		print ">>>>>>>>>>>>>><", follow

	def terminate(self):
		self.shouldRun = False
		time.sleep(0.1)
		self.player.shouldRun = False

	def pause(self):
		self.player.cmdQ.put_nowait("PAUSE")

	def resume(self):
		self.player.cmdQ.put_nowait("RESUME")

	def seek(self, diff):
		self.player.cmdQ.put_nowait("SEEK:"+str(diff))
		
	
#TODO timestamp, to be checked to conclude if stream player is frozen
class StreamPlayer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.addrQ = Queue()
		self.cmdQ = Queue()
		self.follow = []

	def stop(self):
		self.shouldRun = False

	def run(self):
		self.shouldRun = True
		self.gstream_player = gst.Pipeline("player")
		self.gstream_player.set_state(gst.STATE_NULL)
		self.timestamp = time.time()
		start_track_timestamp = time.time()
		while self.shouldRun:
			t, s, r = self.gstream_player.get_state()
			if s != gst.STATE_PLAYING:
				#play next file
				#print s
				if len(self.follow) > 0\
				and time.time() - start_track_timestamp > PLAYER_INACTIVE_TIMEOUT*2:
					e = self.follow.pop(0)
					print "play next ", e
					self.addrQ.put_nowait(e)
			if not self.addrQ.empty():
				#TODO only take last in list
				#set player
				url = self.addrQ.get_nowait()
				#if address is empty, no radio are played
				if not len(url) == 0:
					source_engine = ""
					if (string.split(url, "://")[0] == "mms"):
						source_engine = "mmssrc"
					elif (string.split(url, "://")[0] == "http"):
						#http (do ssh ? ftp ?)
						source_engine = "gnomevfssrc"
					else:
						source_engine = "gnomevfssrc"
						#source_engine = "filesrc use-mmap=\"TRUE\" touch=\"FALSE\""
					self.gstream_player = gst.parse_launch(source_engine+" location=\"" + url + "\" name=\"src\" ! decodebin ! volume name=\"volume\" ! alsasink")
					print source_engine+" location=\"" + url + "\" name=\"src\" ! decodebin ! volume name=\"volume\" ! alsasink"
					#mute and wait 0.5 sec to avoid a loud "crack" sound when starting streaming
					self.gstream_player.get_by_name("volume").set_property('mute', True)
					self.gstream_player.set_state(gst.STATE_PLAYING)
					time.sleep(0.5)
					self.gstream_player.get_by_name("volume").set_property("mute", False)
					self.timestamp = time.time()
					start_track_timestamp = time.time()
					print "start url player"
					#debug
					'''time.sleep(2.5)
					pos_int = self.gstream_player.query_position(gst.FORMAT_TIME, None)[0]
					print pos_int
					seek_ns = pos_int + (50 * 1000000000)
					print seek_ns, " set to "
					#self.gstream_player.set_state(gst.STATE_PAUSED)
					self.gstream_player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns)
					#self.gstream_player.set_state(gst.STATE_PLAYING)
					#self.gstream_player.get_by_name("src").seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, 5000000000)
					#self.gstream_player.set_state(gst.STATE_PLAYING)'''
				else:
					self.gstream_player.set_state(gst.STATE_NULL)
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
					self.gstream_player.set_state(gst.STATE_PAUSED)
					print "pause player"
				elif cmd == "RESUME":
					self.gstream_player.set_state(gst.STATE_PLAYING)
					print "resume player"
				elif cmd == "SEEK":
					pos = self.gstream_player.query_position(gst.FORMAT_TIME, None)[0]
					print "current ", pos
					duration = self.gstream_player.query_duration(gst.FORMAT_TIME, None)[0]
					print "duration ", duration
					pos += int(data)*gst.SECOND
					if pos > duration:
						pos = duration
					if pos < 0:
						pos = 0
					self.gstream_player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, pos)
					#avoids loosing playout
					time.sleep(0.1)
			else:
				#debug
				'''clk = self.gstream_player.get_clock()
				print clk.get_time()'''
				#time.sleep(3.1)
				#print "alive !!"
				self.timestamp = time.time()
				time.sleep(0.1)
		self.gstream_player.set_state(gst.STATE_NULL)

