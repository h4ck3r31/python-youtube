import requests
import json
import os
from functools import cmp_to_key
from threading import Thread

PART_SIZE = 1048576 # In bytes per part
MAX_THREADS = 10 # Max threads in parallel

class YoutubeDownload(Thread):
	def __init__(self, url, path, partNumber = None, byteFrom=0, byteTo=None):
		self.url = url
		self.byteFrom = byteFrom
		self.byteTo = byteTo
		self.partNumber = partNumber
		self.path = path
		Thread.__init__(self)

	def getPath(self):
		return self.path

	def run(self):
		if self.byteTo is None:
			self.byteTo = ""
		headers = {
			"Range" : "bytes=" + str(self.byteFrom) + "-" + str(self.byteTo)
		}
		try:
			r = requests.get(self.url, headers=headers)
			open(self.path, 'wb').write(r.content)
		except:
			raise Exception("Unable to download part " + str(self.partNumber))

	@staticmethod
	def createDirectories(path):
		os.makedirs(path, exist_ok=True)

	@staticmethod
	def startDownload(fullpath, filename, path, url, tmpdir=True):
		try:
			r = requests.head(url)
		except:
			raise Exception("Unable to get headers of the url")
		if 'Content-Length' not in r.headers:
			raise Exception("Unable to get Length of audio/video")

		contentLength = int(r.headers['Content-Length'])
		byteFrom = 0
		byteTo = byteFrom + PART_SIZE
		threads = []
		partNumber = 0
		paralellThreads = 0
		tmpPath = path
		tmpPath += "tmp/" if tmpdir else ""
		YoutubeDownload.createDirectories(tmpPath)
		while byteFrom < contentLength:
			partPath = tmpPath + filename + "." + str(partNumber)
			th = YoutubeDownload(url, partPath,
								 partNumber=partNumber, byteFrom=byteFrom,
								 byteTo=byteTo if byteTo < contentLength else None)
			th.start()
			threads.append(th)
			byteFrom = byteTo + 1
			byteTo += PART_SIZE + 1
			partNumber += 1
			paralellThreads += 1
			if paralellThreads >= MAX_THREADS:
				for th in threads:
					th.join()
				paralellThreads = 0

		for th in threads:
			th.join()

		finalFile = open(fullpath, 'wb')
		for th in threads:
			file = open(th.getPath(), 'rb').read()
			finalFile.write(file)
			os.remove(th.path)


class YoutubeMusic:
	def __init__(self, youtubeItem, bitrate, size, rate, duration, mime, url):
		self.youtubeItem = youtubeItem
		self.bitrate = bitrate
		self.size = size
		self.rate = rate
		self.duration = duration
		self.url = url
		self.mime = mime

	def download(self, fullpath=None, filename=None, path=None, tmpdir=True):
		ext = self.mime.split("/")[1]
		if path is None and fullpath is None:
			path = "./"
		elif path is None:
			path = os.path.dirname(fullpath)
		if filename is None:
			filename = self.youtubeItem.getTitle() + "." + ext
		if fullpath is None:
			fullpath = path + filename
		try:
			YoutubeDownload.startDownload(fullpath, filename, path, self.url, tmpdir)
		except Exception as e:
			raise e

	def __str__(self):
		return self.mime + " " + str(int(self.bitrate / 1000)) + "kbps"


class YoutubeVideo:
	def __init__(self, youtubeItem, bitrate, size, duration, mime, width, height, quality, fps, url):
		self.youtubeItem = youtubeItem
		self.bitrate = bitrate
		self.size = size
		self.duration = duration
		self.url = url
		self.mime = mime
		self.width = width
		self.height = height
		self.quality = quality
		self.fps = fps

	def download(self, fullpath=None, filename=None, path=None, tmpdir=True):
		ext = self.mime.split("/")[1]
		if path is None and fullpath is None:
			path = "./"
		elif path is None:
			path = os.path.dirname(fullpath)
		if filename is None:
			filename = self.youtubeItem.getTitle() + "." + ext
		if fullpath is None:
			fullpath = path + filename
		try:
			YoutubeDownload.startDownload(fullpath, filename, path, self.url, tmpdir)
		except Exception as e:
			raise e

	def __str__(self):
		return self.mime + " " + self.quality


class YoutubeItem:
	def __init__(self, url, audioformat=None, videoformat=None):
		self.url = url
		self.mainData = None
		self.audioFormat = audioformat
		self.videoFormat = videoformat
		self.title = None
		self.videos = []
		self.audios = []
		self.getSourceCode()

	def getSourceCode(self):
		try:
			cs = requests.get(self.url).content.decode("utf-8")
		except:
			raise Exception("Impossible d'effectuer la requête")

		parse = cs.split("ytplayer.config = ")
		if len(parse) > 1:
			parse = parse[1].split(";ytplayer.load")
			if len(parse) > 1:
				jsonStr = parse[0]
				jsonData = json.loads(jsonStr)
				self.mainData = jsonData
				self.getYoutubeData()
				return
		raise Exception("Impossible de parser le code source")

	def getYoutubeData(self):
		self.title = self.mainData["args"]["title"]
		videoData = self.mainData["args"]["player_response"]
		videoData = json.loads(videoData)

		multimediaObjects = videoData["streamingData"]["adaptiveFormats"]
		for obj in multimediaObjects:
			mime = obj['mimeType'].split(";")[0]
			if 'audio' in mime and (self.audioFormat is None or self.audioFormat in mime):
				audioItem = YoutubeMusic(self, bitrate=obj['bitrate'],
										 size=obj['contentLength'], rate=obj['audioSampleRate'],
										 duration=obj['approxDurationMs'], mime=mime,
										 url=obj['url'])
				self.audios.append(audioItem)
			elif 'video' in mime and (self.videoFormat is None or self.videoFormat in mime):
				videoItem = YoutubeVideo(self, bitrate=obj['bitrate'],
										 size=obj['contentLength'], duration=obj['approxDurationMs'],
										 mime=mime, width=obj["width"],
										 height=obj['height'], quality=obj['qualityLabel'],
										 fps=obj['fps'], url=obj['url'])
				self.videos.append(videoItem)
		self.sortAudio()
		self.sortVideo()

	def getTitle(self):
		return self.title

	def sortAudio(self):
		self.audios.sort(key=cmp_to_key(YoutubeItem.bitrateSort), reverse=True)

	def sortVideo(self):
		self.videos.sort(key=cmp_to_key(YoutubeItem.videoFormatSort), reverse=True)

	def getAudioList(self):
		return self.audios

	def getVideoList(self):
		return self.videos

	@staticmethod
	def bitrateSort(item1, item2):
		return (int(item1.bitrate) - int(item2.bitrate))

	@staticmethod
	def videoFormatSort(item1, item2):
		return (int(item1.height) - int(item2.height))

	def __str__(self):
		return self.title