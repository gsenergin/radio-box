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

	def play_episode(self, e):
		self.player.addrQ.put_nowait(e.path())
		if e.already_dl():
			pass
		else:
			e.download()
		
	
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
		gst_player = gst.Pipeline("player")
		gst_src = gst.Pipeline("source")
		self.timestamp = time.time()
		start_track_timestamp = time.time()
		buff_l = []
		sink = None
		source = None
		while self.shouldRun:
			'''t, s, r = gst_player.get_state()
			if s != gst.STATE_PLAYING:
				#play next file
				#print s
				if len(self.follow) > 0\
				and time.time() - start_track_timestamp > PLAYER_INACTIVE_TIMEOUT*2:
					e = self.follow.pop(0)
					print "play next ", e
					self.addrQ.put_nowait(e)'''
			if not self.addrQ.empty():
				#TODO only take last in list
				#set player
				url = self.addrQ.get_nowait()
				#if address is empty, no radio are played
				if not len(url) == 0:
					source_engine = ""
					if (string.split(url, "://")[0] == "mms"):
						source_engine = "mmssrc location=\"" + url + "\""
					elif (string.split(url, "://")[0] == "http"):
						#http (do ssh ? ftp ?)
						source_engine = "gnomevfssrc location=\"" + url + "\""
					else:
						time.sleep(2.0)
						#fd = open(url, 'r')
						fd = os.open(url, os.O_RDONLY)
						source_engine = "fdsrc fd=\""+str(fd)+"\""
						#source_engine = "filesrc use-mmap=\"TRUE\" touch=\"FALSE\""
					gst_src = gst.parse_launch(source_engine+" name=\"src\" ! appsink name=\"sink\"")
					gst_player = gst.parse_launch("appsrc name=\"source\" ! decodebin ! volume name=\"volume\" ! alsasink")
					#print source_engine+" location=\"" + url + "\" name=\"src\" ! decodebin ! volume name=\"volume\" ! alsasink"

					#test appsink appsrc
					sink = gst_src.get_by_name('sink') 
					source = gst_player.get_by_name("source")
					'''buf = sink.emit('pull-buffer') 
					buff_l.append(buf)
					while buff_l:
						source.emit('push-buffer', buff_l.pop(0))'''

					#mute and wait 0.5 sec to avoid a loud "crack" sound when starting streaming
					gst_player.get_by_name("volume").set_property('mute', True)
					gst_player.set_state(gst.STATE_PLAYING)
					gst_src.set_state(gst.STATE_PLAYING)
					time.sleep(0.5)
					gst_player.get_by_name("volume").set_property("mute", False)
					self.timestamp = time.time()
					start_track_timestamp = time.time()
					print "start url player"
					#debug
					'''time.sleep(2.5)
					pos_int = gst_player.query_position(gst.FORMAT_TIME, None)[0]
					print pos_int
					seek_ns = pos_int + (50 * 1000000000)
					print seek_ns, " set to "
					#gst_player.set_state(gst.STATE_PAUSED)
					gst_player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, seek_ns)
					#gst_player.set_state(gst.STATE_PLAYING)
					#gst_player.get_by_name("src").seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, 5000000000)
					#gst_player.set_state(gst.STATE_PLAYING)'''
				else:
					gst_player.set_state(gst.STATE_NULL)
					gst_src.set_state(gst.STATE_NULL)
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
					#gst_player.set_state(gst.STATE_PAUSED)
					gst_src.set_state(gst.STATE_NULL)
					print "pause player"
				elif cmd == "RESUME":
					#gst_player.set_state(gst.STATE_PLAYING)
					gst_src.set_state(gst.STATE_NULL)
					print "resume player"
				elif cmd == "SEEK":
					pos = gst_src.query_position(gst.FORMAT_TIME, None)[0]
					print "current ", pos
					duration = gst_src.query_duration(gst.FORMAT_TIME, None)[0]
					print "duration ", duration
					pos += int(data)*gst.SECOND
					if pos > duration:
						pos = duration
					if pos < 0:
						pos = 0
					gst_src.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_FLUSH, pos)
					#avoids loosing playout
					time.sleep(0.1)
			else:
				self.timestamp = time.time()
				if source != None and sink != None:
					buff = sink.emit('pull-buffer') 
					#buff_l.append(buff)
					if buff:
						source.emit('push-buffer', buff)
						#buf = sink.emit('pull-buffer') 
				time.sleep(0.001)
		gst_player.set_state(gst.STATE_NULL)



	def run222(self):
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
				self.timestamp = time.time()
				time.sleep(0.1)
		self.gstream_player.set_state(gst.STATE_NULL)

