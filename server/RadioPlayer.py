#!/usr/bin/python
# -*- coding: utf-8 -*-

'''
Some Notes, to organize later
_ GstBuffer.offset should be set to 0 to work-around some stupid assertion
_ inPipeSink.emit('pull-buffer') is blocking. For non blocking behaviour, enable emit-signals, then connect to a handler
'''
import threading, time, string
from Queue import Queue, Empty
from RadioBoxConstant import *
import os

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
#without GstPipe gives : segmentation fault
import gobject
gobject.threads_init()

import gst

class StreamElement():
	count = 0

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
		print "delete element #", self.index

class RadioPlayer(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.inPipe = None
		self.inPipeSink = None
		self.outPipe = None
		self.outPipeSrc = None
		self.H = None
		self.T = None
		self.cursor = None
		self.cmdQ = Queue()

	def stop(self):
		self.shouldRun = False

	def feed_appsrc(self, a, b):
		if self.cursor != None and  self.cursor.next != None:
			#print "feeding"
			self.outPipeSrc.emit('push-buffer', self.cursor.buff)
			#print self.cursor.index
			self.cursor = self.cursor.next
		else:
			pass
			#self.last_need_data_failed = True

	def fetch_appsink(self, sink):
		t = time.time()
		buff = self.inPipeSink.emit('pull-buffer')
		#this is needed to workaround assertion which does not allow stream to start at offset 0
		buff.offset = 0
		e = self.H
		self.H = StreamElement(buff, e)
		if e == None:
			#it is the 1st buff
			self.T = self.H
			self.cursor = self.H

	def run(self):
		self.shouldRun = True
		while self.shouldRun:
			#delete too old buff
			if StreamElement.count > REC_MAX_ELEMENT:
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
					if self.inPipe != None:
						if self.outPipe != None:
							self.outPipe.set_state(gst.STATE_NULL)
						self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! pulsesink")
						self.outPipeSrc = self.outPipe.get_by_name('appsrc')
						self.outPipeSrc.connect('need-data', self.feed_appsrc)
						#wait that enough data has been buffered
						while self.cursor == None or self.H == None or self.cursor.index + REC_HEAD_MARGIN > self.H.index:
							time.sleep(0.1)
						self.outPipe.set_state(gst.STATE_PLAYING)
				elif cmd == "PAUSE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
				elif cmd == "LIVE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
					if self.inPipe != None:
						#set cursor to Head
						self.cursor = self.H
						#wait that enough data has been buffered
						while self.cursor == None or self.H == None or self.cursor.index + REC_HEAD_MARGIN > self.H.index:
							time.sleep(0.1)
						self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! pulsesink")
						self.outPipeSrc = self.outPipe.get_by_name('appsrc')
						self.outPipeSrc.connect('need-data', self.feed_appsrc)
						self.outPipe.set_state(gst.STATE_PLAYING)
				elif cmd == "SEEK":
					pass
				elif cmd == "URL":
					if len(data) != 0:
						source_engine = ""
						if (string.split(data, "://")[0] == "mms"):
							source_engine = "mmssrc location=\""
						elif (string.split(data, "://")[0] == "http"):
							source_engine = "gnomevfssrc location=\""
						self.inPipe = gst.parse_launch(source_engine + data + "\" ! appsink name=\"sink\" blocksize=\""+str(BLOCK_SIZE)+"\" emit-signals=\"true\"")
						self.inPipeSink = self.inPipe.get_by_name('sink') 
						self.inPipeSink.connect('new-buffer', self.fetch_appsink)
						self.inPipe.set_state(gst.STATE_PLAYING)
					#print "URL update finish"
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

if __name__=="__main__":
	r = RadioPlayer()
	r.start()
	r.tuneToAddr("http://stream.sing-sing.org:8000/singsing128")
	r.play()
	print "Playing Sing-Sing Radio"
	while True:
		print "1. play"
		print "2. pause"
		print "0. exit"
		print StreamElement.count
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
	r.stop()



