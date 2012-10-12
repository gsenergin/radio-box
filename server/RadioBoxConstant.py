# -*- coding: utf-8 -*-

BLOCK_SIZE = 4096
REC_MAX_ELEMENT = 409600*6/BLOCK_SIZE#100000/BLOCK_SIZE
REC_HEAD_MARGIN = 20

HOST = '192.168.1.51'
PORT = 50456
BUFFER_SIZE = 4096
TIMEOUT = 0.01

HOME_DIR = "/home/bastien/Documents/radio-box/server"
RADIO_STATION_LIST = HOME_DIR + "/live_radio.list"
#PARSE_RSS_CMD = "xsltproc parse_title.xsl "
XSLT_PARSE = HOME_DIR + "/parse_title.xsl"
EPISODE_CACHE_FILE_NAME = "episode.list"
MAX_EPISODE_PER_CHANNEL = 50
LOG_PATH = HOME_DIR + "/log.txt"
BROWSER_HOME_DIR = "/home/bastien/Music/"

PLAYER_INACTIVE_TIMEOUT = 20.0

ALLOWED_FILE_EXT = ["mp3", "ogg", "wav", "flac", "wma"]

from HTMLParser import HTMLParser

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

def replace_non_ascii(s):
	return s.replace("é","e").replace("ê","e").replace("è","e").replace("ë","e").replace("à","a").replace("ù","u").replace("ô","o").replace("ç","c").replace("\xe2\x80\x99", "'")
