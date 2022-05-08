import cv2
import logging
import logging.handlers as handlers
import os
import time
import threading as th  
from datetime import datetime


ROOT_PATH = '/records'
LOG_PATH = '/logs'
CAMERA_NAME = VIDEO_DIR = None
LOGGER = None

NEXT_VIDEO = False
VIDEO_MINUTES = 3


def initLogger():
	global LOGGER
	logging.basicConfig(level=logging.INFO,
						format='[%(asctime)s] %(levelname)s: %(message)s',
						datefmt='%d-%m-%y %H:%M:%S')
	LOGGER = logging.getLogger('recorder')
	logHandler = handlers.TimedRotatingFileHandler(f'/{LOG_PATH}/cameras.log', when='H', interval=1)
	formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s')
	logHandler.setFormatter(formatter)
	logHandler.setLevel(logging.INFO)
	logHandler.suffix = '%d-%m-%y_%H-%M'
	LOGGER.addHandler(logHandler)


class RTSPVideoWriterObject(object):
	def __init__(self, src):
		self.src = src
		self.capture = cv2.VideoCapture(self.src)

		self.fps = int(self.capture.get(5))
		self.frame_width = 800
		self.frame_height = 450
		self.codec = cv2.VideoWriter_fourcc(*'h264')

		self.frame_count = 1
		self.current_videoname = f'{VIDEO_DIR}/{str(round(time.time() * 1000))}_0_.ts'
		self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (self.frame_width, self.frame_height))


	def reconnect(self):
		logging.warning(f'Connection lost for camera {CAMERA_NAME} - sleeping for 5 second and reconnecting...')
		print('Connection lost, sleep 5 second and reconnecting...')
		time.sleep(5)
		self.capture = cv2.VideoCapture(self.src)
		if self.capture.isOpened():
			logging.info(f'Reconnect for camera {CAMERA_NAME} - SUCCESS')

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
				LOGGER.info(f'New video ({saved_videoname.split("/")[-1]}) saved for camera {CAMERA_NAME}')

				self.output_video = cv2.VideoWriter(self.current_videoname, self.codec, self.fps, (self.frame_width, self.frame_height))
				NEXT_VIDEO = False


def updateVideoDir():
	global VIDEO_DIR
	year, month, day, hour = datetime.now().strftime("%Y %m %d %H").split(' ')
	VIDEO_DIR = f'{ROOT_PATH}/{CAMERA_NAME}/vid/{year}/{month}/{day}/{hour}'
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

	initLogger()
	LOGGER.info(f'Start recorder for camera {CAMERA_NAME}')

	updateVideoDir()
	timerThread = th.Thread(target=timer)  
	timerThread.daemon = True
	timerThread.start()  
	video_stream_widget = RTSPVideoWriterObject(rtsp_stream_link)

	while True:
		try:
			video_stream_widget.startRecorder()
		except Exception as e:
			print("KeyboardInterrupt received.")
			LOGGER.error(e)