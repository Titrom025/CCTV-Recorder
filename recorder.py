import cv2
import os
import time
import threading as th  
from datetime import datetime, timedelta


ROOT_PATH = '/records'
LOG_PATH = '/logs'
LOG_FILE = ''

RECONNECTION_TIME_LIMIT = 60
CAMERA_NAME = VIDEO_DIR = None

NEXT_VIDEO = False
VIDEO_LENGTH = 1

VIDEO_WIDTH = 800
VIDEO_HEIGHT = 450

CAPTURE_PARAMETERS = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 2000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 2000]

def videoLimitExceeded(dirpath):
	if not os.path.exists(dirpath):
		return False
	return len([
			s for s in os.listdir(dirpath)
			if os.path.isfile(os.path.join(dirpath, s)) 
			and os.path.splitext(s)[1] == '.ts'
		]) >= (60 / VIDEO_LENGTH)


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
	def __init__(self, src, image_x=None, image_y=None, image_width=None, image_height=None):
		self.src = src
		self.capture = cv2.VideoCapture(self.src, 0, CAPTURE_PARAMETERS)

		if image_x is not None and image_y is not None \
				and image_width is not None and image_height is not None:
			self.image_x = image_x
			self.image_y = image_y
			self.image_width = image_width
			self.image_height = image_height
		else:
			self.image_x = 0
			self.image_y = 0
			self.image_width = self.fps = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
			self.image_height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))

		self.reconnect_time = 0.1

		self.fps = int(self.capture.get(cv2.CAP_PROP_FPS))
		self.codec = cv2.VideoWriter_fourcc(*'h264')

		self.frame_count = 1
		self.current_videoname = f'{VIDEO_DIR}/{datetime.now().strftime("%Y-%m-%d_%H-%M")}_0_.ts'
		self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (VIDEO_WIDTH, VIDEO_HEIGHT))


	def reconnect(self):
		if self.reconnect_time == 0.1:
			logMessage('WARNING', f'Connection lost for camera {CAMERA_NAME} - sleep for a {self.reconnect_time} seconds and reconnecting...')
		else:
			logMessage('WARNING', f'Connection failed for camera {CAMERA_NAME} - sleep for a {self.reconnect_time} seconds and reconnecting...')
		time.sleep(self.reconnect_time)
		self.capture.open(self.src, 0, CAPTURE_PARAMETERS)
		if self.capture.isOpened():
			logMessage('INFO', f'Reconnect for camera {CAMERA_NAME} - SUCCESS')
			self.reconnect_time = 0.1
		else:
			self.reconnect_time *= 5
			if self.reconnect_time > RECONNECTION_TIME_LIMIT:
				self.reconnect_time = RECONNECTION_TIME_LIMIT


	def startRecorder(self):
		global NEXT_VIDEO
		while True:
			if self.capture.isOpened():
				(self.status, self.frame) = self.capture.read()
				if self.status:
					try:
						self.frame = self.frame[self.image_y:self.image_y + self.image_height, self.image_x:self.image_x + self.image_width]
						self.frame = cv2.resize(self.frame, (VIDEO_WIDTH, VIDEO_HEIGHT)) 
						self.output_video.write(self.frame)
						self.frame_count += 1
					except Exception:
						pass
				else:
					self.reconnect()
			else:
				self.reconnect()

			if NEXT_VIDEO and self.frame_count >= VIDEO_LENGTH * 60 * 25:
				self.frame_count = 0

				self.output_video.release()
				end_time = datetime.now().strftime("%Y-%m-%d_%H-%M")
				saved_videoname = f'{self.current_videoname.replace("_0_.ts", "___") + end_time + "_.ts"}'
				os.system(f'mv "{self.current_videoname}" "{saved_videoname}"')

				self.current_videoname = f'{VIDEO_DIR}/{datetime.now().strftime("%Y-%m-%d_%H-%M")}_0_.ts'
				logMessage('INFO', f'New video ({saved_videoname.split("/")[-1]}) saved for camera {CAMERA_NAME}')

				self.output_video.release()
				self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (VIDEO_WIDTH, VIDEO_HEIGHT))
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
		time.sleep(60 * VIDEO_LENGTH - 0.1)
		updateVideoDir()
		NEXT_VIDEO = True


def calibrateTime():
	dt = datetime.now()
	while dt.second != 0:
		dt = datetime.now()
		time.sleep(0.5)


if __name__ == '__main__':
	VIDEO_LENGTH = int(os.environ['VIDEO_LENGTH'])
	CAMERA_NAME = os.environ['CAMERA_NAME'] 
	rtsp_stream_link = os.environ['STREAM_LINK'] + '?tcp'

	image_x = image_y = image_width = image_height = None
	if 'IMAGE_X' in os.environ and 'IMAGE_Y' in os.environ \
			and 'IMAGE_WIDTH' in os.environ and 'IMAGE_HEIGHT' in os.environ:
		image_x = int(os.environ['IMAGE_X'])
		image_y = int(os.environ['IMAGE_Y'])
		image_width = int(os.environ['IMAGE_WIDTH'])
		image_height = int(os.environ['IMAGE_HEIGHT'])

	try:
		os.makedirs(LOG_PATH, exist_ok=True)
	except Exception:
		pass

	updateVideoDir()
	logMessage('INFO', f'Time calibration for camera {CAMERA_NAME}')
	calibrateTime()
	logMessage('INFO', f'Start recorder for camera {CAMERA_NAME}')

	timerThread = th.Thread(target=timer)  
	timerThread.daemon = True
	timerThread.start()  
	video_stream_widget = RTSPVideoWriterObject(rtsp_stream_link, image_x, image_y, image_width, image_height)

	while True:
		try:
			video_stream_widget.startRecorder()
		except Exception as e:
			logMessage('ERROR', e)
