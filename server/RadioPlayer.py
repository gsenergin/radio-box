#!/usr/bin/python
# -*- coding: utf-8 -*-

BLOCK_SIZE = 4096
#50 MB - around 1h for sing sing
REC_MAX_ELEMENT = 50000000/BLOCK_SIZE
REC_HEAD_MARGIN = 10
REC_MIN_TAIL_DISTANCE = 70

'''
Some Notes, to organize later
_ GstBuffer.offset should be set to 0 to work-around some stupid assertion
_ inPipeSink.emit('pull-buffer') is blocking. For non blocking behaviour, enable emit-signals, then connect to a handler
'''
import threading, time, string
from Queue import Queue, Empty
#from RadioBoxConstant import *
#import os

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
#without GstPipe gives : segmentation fault
import gobject
gobject.threads_init()
import gst

'''
Base element for an audio stream buffer list
Radio buffer are stored in a double linked list made of this element class
'''
class StreamElement():
	count = 0

	'''
	prev is the current Head
	this new element is set as head'''
	def __init__(self, buff, prev=None):
		self.ts = time.time()
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
		self.inPipe = None
		self.inPipeSink = None
		self.outPipe = None
		self.outPipeSrc = None
		#Head of double linked list of buff
		self.H = None
		#Tail of double linked list of buff
		self.T = None
		#current position in the double linked list of buff
		self.cursor = None
		self.cmdQ = Queue()
		self.cursorLock = threading.Lock()
		self.current_src_addr = None

	def terminate(self):
		self.shouldRun = False

	def stop(self):
		self.shouldRun = False

	def feed_appsrc(self, a, b):
		self.cursorLock.acquire()
		if self.cursor != None and  self.cursor.next != None:
			self.outPipeSrc.emit('push-buffer', self.cursor.buff)
			self.cursor = self.cursor.next
		self.cursorLock.release()

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
		while self.shouldRun:
			#delete too old buff
			if StreamElement.count > REC_MAX_ELEMENT:
				if self.cursor.index - self.T.index < REC_MIN_TAIL_DISTANCE:
					#stop recording stream, tail reached cursor
					if self.inPipe != None:
						self.inPipe.set_state(gst.STATE_NULL)
						self.inPipe = None
						#print "stop REC T:", self.T.index, "  cursor:", self.cursor.index
				else:
					#delete old buffer
					e = self.T
					self.T = self.T.next
					e.delete()
			#process commands
			if not self.cmdQ.empty():
				cmd = self.cmdQ.get_nowait()
				#print cmd
				try:
					i = cmd.index(":")
					data = cmd[i+1:]
					cmd = cmd[:i]
				except:
					pass
				if cmd == "PLAY":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
					#start sound playout
					self.startOutPipe()
				elif cmd == "PAUSE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
				elif cmd == "LIVE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
					#set cursor to Head
					self.cursor = self.H

					if self.inPipe != None:
						a, b, c = self.inPipe.get_state()
						inPipe_already_rec = b == gst.STATE_PLAYING
					else:
						inPipe_already_rec = False
					if self.current_src_addr != None and not inPipe_already_rec:
						source_engine = ""
						if (string.split(self.current_src_addr, "://")[0] == "mms"):
							source_engine = "mmssrc location=\""
						elif (string.split(self.current_src_addr, "://")[0] == "http"):
							source_engine = "gnomevfssrc location=\""
						self.inPipe = gst.parse_launch(source_engine + self.current_src_addr + "\" ! appsink name=\"sink\" blocksize=\""+str(BLOCK_SIZE)+"\" emit-signals=\"true\"")
						self.inPipeSink = self.inPipe.get_by_name('sink') 
						self.inPipeSink.connect('new-buffer', self.fetch_appsink)
						self.inPipe.set_state(gst.STATE_PLAYING)
					#start sound playout
					self.startOutPipe()
				elif cmd == "SEEK":
					try:
						diff = int(data)
					except:
						continue
					self.cursorLock.acquire()
					if diff >= 0:
						for i in range(diff):
							if self.cursor.index + REC_HEAD_MARGIN > self.H.index:
								break
							self.cursor = self.cursor.next
					else:
						for i in range(abs(diff)):
							if self.cursor == self.T:
								break
							self.cursor = self.cursor.prev
					self.cursorLock.release()
				elif cmd == "URL":
					if len(data) != 0:
						if self.current_src_addr == data:
							#same address already set
							continue
						source_engine = ""
						if (string.split(data, "://")[0] == "mms"):
							source_engine = "mmssrc location=\""
						elif (string.split(data, "://")[0] == "http"):
							source_engine = "gnomevfssrc location=\""
						self.current_src_addr = data
						self.inPipe = gst.parse_launch(source_engine + data + "\" ! appsink name=\"sink\" blocksize=\""+str(BLOCK_SIZE)+"\" emit-signals=\"true\"")
						self.inPipeSink = self.inPipe.get_by_name('sink') 
						self.inPipeSink.connect('new-buffer', self.fetch_appsink)
						self.inPipe.set_state(gst.STATE_PLAYING)
					else:
						self.inPipe.set_state(gst.STATE_NULL)
						self.inPipe = None
			else:
				time.sleep(0.1)
		#stop
		if self.inPipe != None:
			self.inPipe.set_state(gst.STATE_NULL)
		if self.outPipe != None:
			self.outPipe.set_state(gst.STATE_NULL)

	def tuneToAddr(self, newAddr):
		self.cmdQ.put_nowait("URL:"+newAddr)

	def pause(self):
		self.cmdQ.put_nowait("PAUSE")

	def play(self):
		self.cmdQ.put_nowait("PLAY")

	def seek(self, diff):
		self.cmdQ.put_nowait("SEEK:"+str(diff))

	def goLive(self):
		self.cmdQ.put_nowait("LIVE")

	def startOutPipe(self):
		#wait that enough data has been buffered
		while self.cursor == None or self.H == None or self.cursor.index + REC_HEAD_MARGIN > self.H.index:
			time.sleep(0.1)
		self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! volume name=\"volume\" ! pulsesink")
		self.outPipeSrc = self.outPipe.get_by_name('appsrc')
		self.outPipeSrc.connect('need-data', self.feed_appsrc)
		mute_delay = self.cursor.index + 1
		#mute and wait 0.5 sec to avoid a loud "crack" sound when starting streaming
		self.outPipe.get_by_name("volume").set_property('mute', True)
		self.outPipe.set_state(gst.STATE_PLAYING)
		while self.cursor.index < mute_delay:
			time.sleep(0.1)
		self.outPipe.get_by_name("volume").set_property("mute", False)

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
	r.stop()



