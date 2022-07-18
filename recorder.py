import cv2
import os
import time
import threading as th  
from datetime import datetime, timedelta


ROOT_PATH = '/records'
LOG_PATH = '/logs'
LOG_FILE = ''
CAMERA_NAME = VIDEO_DIR = None

NEXT_VIDEO = False
VIDEO_MINUTES = 3


def videoLimitExceeded(dirpath):
	if not os.path.exists(dirpath):
		return False
	return len([
			s for s in os.listdir(dirpath)
			if os.path.isfile(os.path.join(dirpath, s)) 
			and os.path.splitext(s)[1] == '.ts'
		]) >= 20


def logMessage(type, message):
	tries = 0
	while tries <= 5:
		try:
			with open(f'{LOG_PATH}/{LOG_FILE}', 'a') as logFile:
				timestamp = datetime.now().strftime('%d-%m-%y %H:%M:%S')
				logFile.write(f'[{timestamp}] {type}: {message}\n')
			break
		except Exception:
			tries += 1
			time.sleep(0.01)
			pass


class RTSPVideoWriterObject(object):
	def __init__(self, src):
		self.src = src
		self.capture = cv2.VideoCapture(self.src)
		self.frame_width = 800
		self.frame_height = 450

		self.reconnect_time = 1

		self.fps = int(self.capture.get(cv2.CAP_PROP_FPS))
		self.codec = cv2.VideoWriter_fourcc(*'h264')

		self.frame_count = 1
		self.current_videoname = f'{VIDEO_DIR}/{str(round(time.time() * 1000))}_0_.ts'
		self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (self.frame_width, self.frame_height))


	def reconnect(self):
		if self.reconnect_time == 1:
			logMessage('WARNING', f'Connection lost for camera {CAMERA_NAME} - sleep for a {self.reconnect_time} seconds and reconnecting...')
		else:
			logMessage('WARNING', f'Connection failed for camera {CAMERA_NAME} - sleep for a {self.reconnect_time} seconds and reconnecting...')
		time.sleep(self.reconnect_time)
		self.capture = cv2.VideoCapture(self.src)
		if self.capture.isOpened():
			logMessage('INFO', f'Reconnect for camera {CAMERA_NAME} - SUCCESS')
			self.reconnect_time = 1
		else:
			self.reconnect_time *= 2
			if self.reconnect_time > 300:
				self.reconnect_time = 300


	def startRecorder(self):
		global NEXT_VIDEO
		while True:
			if self.capture.isOpened():
				(self.status, self.frame) = self.capture.read()
				if self.status:
					self.frame = cv2.resize(self.frame, (self.frame_width, self.frame_height)) 
					self.output_video.write(self.frame)
					self.frame_count += 1
				else:
					self.reconnect()
			else:
				self.reconnect()

			if (NEXT_VIDEO and self.frame_count >= VIDEO_MINUTES * 60 * 25):
				print(f'Frames saved: {self.frame_count}')
				self.frame_count = 0

				self.output_video.release()
				end_time = str(round(time.time() * 1000))
				saved_videoname = f'{self.current_videoname.replace("0_.ts", "") + end_time + "_.ts"}'
				os.system(f'mv "{self.current_videoname}" "{saved_videoname}"')

				self.current_videoname = f'{VIDEO_DIR}/{str(round(time.time() * 1000))}_0_.ts'
				logMessage('INFO', f'New video ({saved_videoname.split("/")[-1]}) saved for camera {CAMERA_NAME}')

				self.output_video.release()
				self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (self.frame_width, self.frame_height))
				NEXT_VIDEO = False


def updateVideoDir():
	global VIDEO_DIR
	global LOG_FILE
	year, month, day, hour = datetime.now().strftime("%Y %m %d %H").split(' ')
	VIDEO_DIR = f'{ROOT_PATH}/{CAMERA_NAME}/vid/{year}/{month}/{day}/{hour}'
	if videoLimitExceeded(VIDEO_DIR):
		year, month, day, hour = (datetime.now() + timedelta(hours=1)).strftime("%Y %m %d %H").split(' ')
		VIDEO_DIR = f'{ROOT_PATH}/{CAMERA_NAME}/vid/{year}/{month}/{day}/{hour}'
	
	LOG_FILE = f'log_{year}_{month}_{day}_{hour}.log'
	os.makedirs(VIDEO_DIR, exist_ok=True)


def timer():  
	global NEXT_VIDEO
	while True:
		time.sleep(60 * VIDEO_MINUTES - 1)
		updateVideoDir()
		NEXT_VIDEO = True


if __name__ == '__main__':
	CAMERA_NAME = os.environ['CAMERA_NAME']
	rtsp_stream_link = os.environ['STREAM_LINK']

	try:
		os.makedirs(LOG_PATH, exist_ok=True)
	except Exception:
		pass
	
	updateVideoDir()
	logMessage('INFO', f'Start recorder for camera {CAMERA_NAME}')

	timerThread = th.Thread(target=timer)  
	timerThread.daemon = True
	timerThread.start()  
	video_stream_widget = RTSPVideoWriterObject(rtsp_stream_link)

	while True:
		try:
			video_stream_widget.startRecorder()
		except Exception as e:
			logMessage('ERROR', e)