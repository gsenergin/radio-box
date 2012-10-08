#!/usr/bin/python
# -*- coding: utf-8 -*-

import threading, time, string
from Queue import Queue, Empty
from RadioBoxConstant import *
import os

#import pygtk, gtk, gobject
import pygst
pygst.require("0.10")
#import gobject
#gobject.threads_init() 
import gst

class MusicBuff():
	count = 0

	def __init__(self, buff, prev=None):
		self.timestamp = time.time()
		self.buff = buff
		self.prev = prev
		if prev != None:
			prev.next = self
		MusicBuff.count += 1
		self.next = None

	'''def delete(self):
		MusicBuff.count -= 1
		self.buff = None
		self.prev = None'''

class RadioBuff(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.inPipe = None
		self.inPipeSink = None
		#self.inPipeSink = self.inPipeSink.get_by_name('appsink')
		self.inPipeLock = threading.Lock()
		#create out pipe
		#self.outPipe = gst.parse_launch("appsrc name=\"appsrc\" blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin2 ! alsasink")
		self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! pulsesink")
		#self.outPipe = gst.parse_launch("appsrc name=\"appsrc\" ! oggdemux ! vorbisdec ! pulsesink")
		self.outPipeSrc = self.outPipe.get_by_name('appsrc')
		#self.outPipeSrc.connect("need-data"
		self.outPipeLock = threading.Lock()
		#Live, Pause, Play
		self.state = "Live"
		#self.recQ = Queue()
		self.buff_H = None
		self.buff_T = None
		self.buff_current = None
		self.lock = threading.Lock()


	def stop(self):
		self.shouldRun = False

	def run(self):
		self.shouldRun = True
		streamRecThread = threading.Thread(None, self.StreamRecThreadHandler)
		streamRecThread.start()
		while self.shouldRun:
			self.lock.acquire()
			if self.state == "Play":
				if self.buff_current.next != None:
					b = self.buff_current.buff
					self.buff_current = self.buff_current.next
					self.lock.release()
					self.outPipeLock.acquire()
					self.outPipeSrc.emit('push-buffer', b)
					self.outPipeLock.release()
					#time.sleep(0.01)
				else:
					self.lock.release()
					time.sleep(0.01)
			else:
				self.lock.release()
				time.sleep(0.01)
		#stop
		print "--------run end loop"
		self.outPipe.set_state(gst.STATE_NULL)


	def goLive(self):
		self.outPipeLock.acquire()
		self.outPipe.set_state(gst.STATE_PLAYING)
		self.outPipeLock.release()

	def pause(self):
		print "pause : ", time.time()
		self.lock.acquire()
		if self.state == "Live":
			self.buff_current = self.buff_T
			'''for i in range(20):
				if self.buff_current.prev == None:
					break
				else:
					self.buff_current = self.buff_current.prev'''
				
		self.state = "Pause"
		print "pause 1: ", time.time()
		self.lock.release()
		self.outPipeLock.acquire()
		print "pause 2: ", time.time()
		self.outPipe.set_state(gst.STATE_NULL)
		self.outPipeLock.release()
		print "pause 3: ", time.time()

	def play(self):
		self.lock.acquire()
		self.state = "Play"
		self.buff_current.buff.offset = 0
		self.lock.release()
		#time.sleep(2.0)
		self.outPipeLock.acquire()
		self.outPipe = gst.parse_launch("appsrc name=\"appsrc\"  blocksize=\""+str(BLOCK_SIZE)+"\" ! decodebin ! pulsesink")
		self.outPipeSrc = self.outPipe.get_by_name('appsrc')
		self.outPipe.set_state(gst.STATE_PLAYING)
		self.outPipeLock.release()

	def seek(self, n):
		pass

	def setInput(self, uri):
		self.inPipeLock.acquire()
		if len(uri) != 0:
			source_engine = ""
			if (string.split(uri, "://")[0] == "mms"):
				source_engine = "mmssrc location=\"" + uri + "\""
			elif (string.split(uri, "://")[0] == "http"):
				source_engine = "gnomevfssrc location=\"" + uri + "\""
			#self.inPipe = gst.parse_launch(source_engine+" ! decodebin2 ! volume name=\"volume\" ! audioconvert ! vorbisenc ! oggmux ! appsink name=\"sink\"")
			#self.inPipe = gst.parse_launch(source_engine+" ! decodebin2 ! volume name=\"volume\" ! audioconvert ! vorbisenc ! oggmux ! appsink name=\"sink\"")
			self.inPipe = gst.parse_launch(source_engine+" ! appsink name=\"sink\"")
			#self.inPipe = gst.parse_launch(source_engine+" ! decodebin2 ! audioconvert ! vorbisenc ! oggmux ! appsink name=\"sink\" blocksize=\""+str(BLOCK_SIZE)+"\"")
			#test appsink appsrc
			self.inPipeSink = self.inPipe.get_by_name('sink') 
			self.inPipe.set_state(gst.STATE_PLAYING)
		self.inPipeLock.release()

	def StreamRecThreadHandler(self):
		self.shouldRun = True
		while self.shouldRun:
			self.inPipeLock.acquire()
			if self.inPipe != None:
				#if self.state == "Live":
				buff = self.inPipeSink.emit('pull-buffer')
				self.inPipeLock.release()
				if buff:
					#debug
					buff.offset = 0
					'''print "DEBUG -------------------"
					print buff.flag_is_set(gst.BUFFER_OFFSET_NONE)
					print buff.__class__.__name__
					print "pts : ", gst.GST_BUFFER_PTS(buff), "\nduration : ", gst.GST_BUFFER_DURATION(buff), "offsert : ", gst.GST_BUFFER_OFFSET(buf)'''
					#rec radio
					self.lock.acquire()
					e = self.buff_H
					self.buff_H = MusicBuff(buff, e)
					if e == None:
						#it is the 1st buff
						self.buff_T = self.buff_H
					s = self.state
					self.lock.release()
					if s == "Live":
						self.outPipeLock.acquire()
						#self.outPipeSrc.emit('push-buffer', buff)
						self.outPipeSrc.emit('push-buffer', self.buff_H.buff)
						self.outPipeLock.release()
						'''while MusicBuff.count > (REC_MAX_SIZE/BLOCK_SIZE):
							self.lock.acquire()
							e = self.buff_T
							self.buff_t = self.buff_t.next
							self.buff_t.prev = None
							e.delete()
							self.lock.release()'''
					time.sleep(0.01)
				else:
					time.sleep(0.01)
			else:
				self.inPipeLock.release()
				time.sleep(0.1)
		#stop
		if self.inPipe != None:
			self.inPipe.set_state(gst.STATE_NULL)

if __name__=="__main__":
	print time.time()
	r = RadioBuff()
	r.start()
	r.goLive()
	print time.time()
	r.setInput("http://stream.sing-sing.org:8000/singsing128")
	print time.time()
	time.sleep(10.0)
	print time.time()
	r.pause()
	print time.time()
	print "pause..."
	print "after pause", time.time()
	time.sleep(10.0)
	print time.time()
	r.play()
	print time.time()
	print "play"
	time.sleep(30.0)
	r.stop()



