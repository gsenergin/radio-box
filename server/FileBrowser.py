#!/usr/bin/python
# -*- coding: utf-8 -*-

import os, time
from RadioBoxConstant import *

class FileBrowser:
	def __init__(self):
		self.current_dir = BROWSER_HOME_DIR
		self.l = self.ls()
		self.ind = 0;
		self.ind_stack = []

	def cd(self, path):
		tmp = []
		try:
			tmp = self.ls(path)
			self.l = tmp
			self.current_dir = path + "/"
			self.ind_stack.append(self.ind)
			self.ind = 0;
			return True
		except:
			print "not such F or D  : " + path + "/"
			return False

	def up(self):
		#print "before up : ", self.current_dir
		if self.current_dir != BROWSER_HOME_DIR:
			l = self.current_dir.split("/")
			#last element l[-1] == ""
			l.pop(-2)
			self.current_dir = "/".join(l)
			self.l = self.ls()
			self.ind = self.ind_stack.pop()

	def ls(self, path=""):
		if path == "":
			path = self.current_dir
		l = os.listdir(path)
		files = []
		directories = []
		for e in l:
			if not e.startswith("."):
				if os.path.isfile(path + "/" + e):
					if e.split(".")[-1] in ALLOWED_FILE_EXT:
						files.append(e)
				else:
					directories.append(e)
		files = sorted(files, key=lambda s: s.lower())
		directories = sorted(directories, key=lambda s: s.lower())
		l = directories
		l.extend(files)
		return l

	def getListWindow(self, l=None, index=None):
		ret = []
		if index == None:
			index = self.ind
		if l == None:
			l = self.l
		print "window", index, "/", len(l)
		for i in range(index, index + 4):
			if i >= len(l):
				#add an empty line
				ret.append("l:"+str(i-index)+":                   \n")
			else:
				ret.append("l:"+str(i-index)+":")
				tmp = l[i]
				i += 1
				if len(tmp) > 19:
					ret.append(tmp[:19])
				else:
					ret.append(tmp)
				ret.append("\n")
			
		return "".join(ret)

	def getPos(self):
		return self.ind

	def getTotal(self):
		return len(self.l)

	def __str__(self):
		l = ["List of : "+self.current_dir+"\n"]
		l.append(str(self.l))
		return "".join(l)

	def next(self):
		self.ind += 4
		if self.ind >= len(self.l):
			self.ind = 0

	def prev(self):
		self.ind -= 4
		if self.ind < 0:
			#self.ind = (len(self.l) + self.ind) + (len(self.l) + self.ind)%4
			self.ind = (len(self.l) - 1)/4*4

	def get_item_path_at(self, index):
		return self.current_dir + self.l[self.ind + int(index)]

	def get_following_item_paths_of(self, index):
		l = []
		for i in range(self.ind + int(index) + 1, len(self.l)):
			l.append(self.current_dir + self.l[i])
		return l

if __name__=="__main__":
	f = FileBrowser()
	print f
	print "____________________________________________"
	print f.getListWindow()
	print f.getPos(), "/", f.getTotal()
	print "____________________________________________"
	f.next()
	print f.getListWindow()
	print f.getPos(), "/", f.getTotal()
	print "____________________________________________"
	f.cd(f.l[5])
	print f
	print "____________________________________________"
	print f.getListWindow()
	f.up()
	print f.getListWindow()
	f.up()
	print f.getListWindow()
	i = f.getPos()
	while True:
		print f.getListWindow()
		f.next()
		time.sleep(1.0)
