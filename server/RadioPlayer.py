#!/usr/bin/python
# -*- coding: utf-8 -*-

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
		self.last_need_data_failed = False

	def stop(self):
		self.shouldRun = False

	def feed_appsrc(self, a, b):
		print "feed_appsrc"
		if self.cursor != None and  self.cursor.next != None:
			print "feeding"
			self.outPipeSrc.emit('push-buffer', self.cursor.buff)
			self.cursor = self.cursor.next
		else:
			self.last_need_data_failed = True

	def fetch_appsink(self, a):
		print a
		t = time.time()
		buff = self.inPipeSink.emit('pull-buffer')
		print "pull-buffer : ", time.time() - t
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
			if self.inPipe != None:
				#print "loop"
				#t = time.time()
				#buff = self.inPipeSink.emit('pull-buffer')
				buff = None
				#print "pull-buffer : ", time.time() - t
				if buff:
					#this is needed to workaround assertion which does not allow stream to start at offset 0
					#print "got buff, recording"
					buff.offset = 0
					e = self.H
					self.H = StreamElement(buff, e)
					if e == None:
						#it is the 1st buff
						self.T = self.H
						self.cursor = self.H
					'''while StreamElement.count > (REC_MAX_SIZE/BLOCK_SIZE):
							e = self.T
							self.T = self.T.next
							self.T.prev = None
							e.delete()'''
					#time.sleep(0.001)
					#print "rec buffer #", StreamElement.count
				else:
					pass
					#print "buff is None"
					#time.sleep(2.01)
			else:
				print "no inPipe"
				time.sleep(2.01)
			#process commands
			if not self.cmdQ.empty():
				cmd = self.cmdQ.get_nowait()
				print cmd
				try:
					i = cmd.index(":")
					data = cmd[i+1:]
					cmd = cmd[:i]
				except:
					pass
				if cmd == "PLAY":
					if self.inPipe != None:
						self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! pulsesink")
						self.outPipeSrc = self.outPipe.get_by_name('appsrc')
						self.outPipeSrc.connect('need-data', self.feed_appsrc)
						self.outPipe.set_state(gst.STATE_PLAYING)
				elif cmd == "PAUSE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
				elif cmd == "LIVE":
					if self.outPipe != None:
						self.outPipe.set_state(gst.STATE_NULL)
					if self.inPipe != None:
						#wait for a minimum number of streamElement
						if streamElement.count < 40:
							continue
						#set cursor to Head - margin
						self.cursor = self.H
						time.sleep(1.5)
						#for j in range(40):
						#	self.cursor = self.cursor.prev
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
					print "URL update finish"
		#stop
		if self.inPipe != None:
			self.inPipe.set_state(gst.STATE_NULL)
		#stop
		print "--------run end loop"
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
	#gobject.MainLoop().run()
	print time.time()
	r = RadioPlayer()
	r.start()
	#r.goLive()
	print time.time()
	r.tuneToAddr("http://stream.sing-sing.org:8000/singsing128")
	time.sleep(10.0)
	r.play()
	'''print time.time()
	time.sleep(2000.0)
	print time.time()
	r.pause()
	print time.time()
	print "pause..."
	print "after pause", time.time()
	time.sleep(10.0)
	print time.time()
	r.play()
	print time.time()
	print "play"'''
	time.sleep(100.0)
	#gobject.MainLoop().run()
	#r.stop()



