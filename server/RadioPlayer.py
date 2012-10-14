#!/usr/bin/python
# -*- coding: utf-8 -*-

BLOCK_SIZE = 4096
#50 MB - around 1h for sing sing radio
REC_MAX_ELEMENT = 50000000/BLOCK_SIZE
REC_HEAD_MARGIN = 10
REC_MIN_TAIL_DISTANCE = 100
#buff to rewind before resuming to avoid lossing sound (pre-roll, start mute)
RESUME_REWIND = 5

PLAYER_INACTIVE_TIMEOUT = 20.0

'''Some Notes, to organize later
_ GstBuffer.offset should be set to 0 to work-around some stupid assertion
_ inPipeSink.emit('pull-buffer') is blocking. 
	For non blocking behaviour, enable emit-signals, then connect to a handler'''
import threading, time, string
from Queue import Queue, Empty

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
#without GstPipe gives : segmentation fault
import gobject
gobject.threads_init()
import gst

'''Base element for an audio stream buffer list
Radio buffer are stored in a double linked list made of this element class'''
class StreamElement():
	count = 0

	'''prev is the current Head
	this new element is set as head'''
	def __init__(self, buff, prev=None):
		#self.ts = time.time()
		self.buff = buff
		self.prev = prev
		if prev != None:
			prev.next = self
			self.index = self.prev.index + 1
		else:
			self.index = 0
		StreamElement.count += 1
		self.next = None

	def delete(self):
		StreamElement.count -= 1
		self.buff = None
		if self.prev != None:
			self.prev.next = None
		if self.next != None:
			self.next.prev = None
		#print "delete element #", self.index

class RadioPlayer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.inPipe = gst.Pipeline()
		self.inPipeSink = None
		self.outPipe = gst.Pipeline()
		self.outPipeSrc = None
		#Head of double linked list of buff
		self.H = None
		#Tail of double linked list of buff
		self.T = None
		#current position in the double linked list of buff
		self.cursor = None
		self.seekLock = threading.Lock()
		self.cmdQ = Queue()
		self.input_addr = None

	def stop(self):
		self.shouldRun = False

	'''called by outPipe appsrc when it needs data'''
	def feed_appsrc(self, a, b):
		self.seekLock.acquire()
		if self.cursor != None and  self.cursor.next != None:
			self.outPipeSrc.emit('push-buffer', self.cursor.buff)
			self.cursor = self.cursor.next
		self.seekLock.release()

	'''called by inPipe appsink when a buff is ready'''
	def fetch_appsink(self, sink):
		t = time.time()
		buff = self.inPipeSink.emit('pull-buffer')
		#this is needed to workaround assertion which does not allow stream to start at offset 0
		buff.offset = 0
		e = self.H
		self.H = StreamElement(buff, e)
		if e == None:
			#1st buff
			self.T = self.H
			self.cursor = self.H

	def run(self):
		self.shouldRun = True
		self.worker = Worker(self)
		self.worker.start()
		time.sleep(0.1)
		while self.shouldRun:
			if not self.worker.isAlive() or \
			time.time() - self.worker.timestamp > PLAYER_INACTIVE_TIMEOUT:
				print "re-spawn worker - frozen or dead"
				self.inPipe.set_state(gst.STATE_NULL)
				self.outPipe.set_state(gst.STATE_NULL)
				self.worker.stop()
				self.worker = Worker(self)
				self.worker.start()
			time.sleep(0.1)
		print "END RadioPlayer"
		self.worker.stop()
		self.inPipe.set_state(gst.STATE_NULL)
		self.outPipe.set_state(gst.STATE_NULL)

	def goLive(self, addr=""):
		self.cmdQ.put_nowait("LIVE:" + addr)

	def pause(self):
		self.cmdQ.put_nowait("PAUSE")

	def resume(self):
		self.cmdQ.put_nowait("RESUME")

	def seek(self, diff):
		self.cmdQ.put_nowait("SEEK:"+str(diff))

	'''stop recording, ready to play/goLive'''
	def standBy(self):
		self.input_addr = None
		self.cmdQ.put_nowait("LIVE:")

	def startSoundPlayout(self):
		#wait that enough data has been buffered
		while self.cursor == None or self.H == None or self.cursor.index + REC_HEAD_MARGIN > self.H.index:
			time.sleep(0.1)
			print "8=>"
		self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! volume name=\"volume\" ! pulsesink")
		self.outPipeSrc = self.outPipe.get_by_name('appsrc')
		self.outPipeSrc.connect('need-data', self.feed_appsrc)
		mute_delay = self.cursor.index + 4
		#mute for 4 buffs to avoid a loud "crack" sound when starting streaming on some stations
		self.outPipe.get_by_name("volume").set_property('mute', True)
		self.outPipe.set_state(gst.STATE_PLAYING)
		while self.cursor.index < mute_delay:
			time.sleep(0.1)
		self.outPipe.get_by_name("volume").set_property("mute", False)
		print "@@@@@@@@@@@@@@@@@@@@@@@@@@"

'''This class is for gst related call
Indeed such call can lead to crash or freeze
So this thread does such call, and when frozen/dead, it is restarted by the RadioPlayer thread'''
class Worker(threading.Thread):
	def __init__(self, rp):
		threading.Thread.__init__(self)
		self.radioPlayer = rp
		self.timestamp = time.time()

	def stop(self):
		self.shouldRun = False

	def run(self):
		self.shouldRun = True
		print "worker start"
		#main loop : process commands, delete old buff
		while self.shouldRun:
			self.timestamp = time.time()
			#print "Ha Ha !!!"
			#time.sleep(3)

			#debug
			'''a, state, c = self.radioPlayer.inPipe.get_state()
			if state != gst.STATE_PLAYING:
				print "Not Rec !!"
				time.sleep(1)
			a, state, c = self.radioPlayer.outPipe.get_state()
			if state != gst.STATE_PLAYING:
				print "Not Playing !!"
				time.sleep(1)'''

			if StreamElement.count > REC_MAX_ELEMENT:
				if self.radioPlayer.cursor.index - self.radioPlayer.T.index < REC_MIN_TAIL_DISTANCE:
					#stop recording stream, tail reached cursor
						self.radioPlayer.inPipe.set_state(gst.STATE_NULL)
						#print "stop REC T:", self.radioPlayer.T.index, "  cursor:", self.radioPlayer.cursor.index
				else:
					#delete old buffer
					e = self.radioPlayer.T
					self.radioPlayer.T = self.radioPlayer.T.next
					e.delete()
			#process commands
			if not self.radioPlayer.cmdQ.empty():
				#only consider last command, more responsive human interface
				while not self.radioPlayer.cmdQ.empty():
					cmd = self.radioPlayer.cmdQ.get_nowait()
					print cmd
				#extract cmd and optional data values
				try:
					i = cmd.index(":")
					data = cmd[i+1:]
					cmd = cmd[:i]
				except:
					pass
				if cmd == "LIVE":
					self.radioPlayer.outPipe.set_state(gst.STATE_NULL)
					self.radioPlayer.inPipe.set_state(gst.STATE_NULL)
					#set cursor to Head
					self.radioPlayer.cursor = self.radioPlayer.H
					#a, state, c = self.radioPlayer.inPipe.get_state()
					#inPipe_active = state == gst.STATE_PLAYING
					if len(data) > 0:
						self.radioPlayer.input_addr= data
					if self.radioPlayer.input_addr != None:# and not inPipe_active:
						source_engine = ""
						if (string.split(self.radioPlayer.input_addr, "://")[0] == "mms"):
							source_engine = "mmssrc"
						elif (string.split(self.radioPlayer.input_addr, "://")[0] == "http"):
							source_engine = "gnomevfssrc"
						self.radioPlayer.inPipe = gst.parse_launch(source_engine + " location=\"" + self.radioPlayer.input_addr + "\" ! appsink name=\"sink\" blocksize=\""+str(BLOCK_SIZE)+"\" emit-signals=\"true\"")
						self.radioPlayer.inPipeSink = self.radioPlayer.inPipe.get_by_name('sink') 
						self.radioPlayer.inPipeSink.connect('new-buffer', self.radioPlayer.fetch_appsink)
						self.radioPlayer.inPipe.set_state(gst.STATE_PLAYING)
						#start sound playout
						self.radioPlayer.startSoundPlayout()
				elif cmd == "RESUME":
					#self.radioPlayer.outPipe.set_state(gst.STATE_NULL)
					#rewind a little
					ind = self.radioPlayer.cursor.index - RESUME_REWIND
					if ind < self.radioPlayer.T.index:
						ind = self.radioPlayer.T.index
					while self.radioPlayer.cursor.index > ind:
						self.radioPlayer.cursor = self.radioPlayer.cursor.prev
					#start sound playout
					self.radioPlayer.startSoundPlayout()
				elif cmd == "PAUSE":
					self.radioPlayer.outPipe.set_state(gst.STATE_NULL)
				elif cmd == "SEEK":
					self.radioPlayer.outPipe.set_state(gst.STATE_NULL)
					try:
						diff = int(data)
					except:
						continue
					self.radioPlayer.seekLock.acquire()
					if diff >= 0:
						for i in range(diff):
							if self.radioPlayer.cursor.index + REC_HEAD_MARGIN > self.radioPlayer.H.index:
								break
							self.radioPlayer.cursor = self.radioPlayer.cursor.next
					else:
						for i in range(abs(diff)):
							if self.radioPlayer.cursor == self.radioPlayer.T:
								break
							self.radioPlayer.cursor = self.radioPlayer.cursor.prev
					self.radioPlayer.seekLock.release()
			else:
				time.sleep(0.1)
		print "END worker Thread"


if __name__=="__main__":
	r = RadioPlayer()
	r.start()
	r.tuneToAddr("http://stream.sing-sing.org:8000/singsing128")
	r.play()
	print "Playing Sing-Sing Radio"
	while True:
		print "1. play"
		print "2. pause"
		print "3. +50"
		print "4. -50"
		print "5. live"
		print "0. exit"
		print "total num of rec buff", StreamElement.count
		c = -1
		try:
			c = input()
		except:
			print "??"
		if c == 0:
			break
		elif c == 1:
			r.play()
		elif c == 2:
			r.pause()
		elif c == 3:
			r.seek(50)
		elif c == 4:
			r.seek(-50)
		elif c == 5:
			r.goLive()
		elif c == 6:
			r.tuneToAddr("http://mp3.live.tv-radio.com/franceinfo/all/franceinfo.mp3")

	r.stop()



