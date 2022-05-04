import cv2
import logging
import os
import sys
import time
import threading as th  
from datetime import datetime

ROOT_PATH = '/records'
CAMERA_NAME = VIDEO_DIR = None

NEXT_VIDEO = False
VIDEO_MINUTES = 1

class RTSPVideoWriterObject(object):
	def __init__(self, src):
		self.src = src
		self.capture = cv2.VideoCapture(self.src)

		self.fps = int(self.capture.get(5))
		self.frame_width = int(self.capture.get(3))
		self.frame_height = int(self.capture.get(4))
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

	def update(self):
		global NEXT_VIDEO
		while True:
			if self.capture.isOpened():
				(self.status, self.frame) = self.capture.read()
				if self.status:
					self.output_video.write(self.frame)
					self.frame_count += 1
				else:
					self.reconnect()
			else:
				self.reconnect()

			if (NEXT_VIDEO and self.frame_count >= VIDEO_MINUTES * 60 * 25): #or \

				print(f'Frames saved: {self.frame_count}')
				self.frame_count = 0

				self.output_video.release()
				end_time = str(round(time.time() * 1000))
				saved_videoname = f'{self.current_videoname.replace("0_.ts", "") + end_time + "_.ts"}'
				os.system(f'mv "{self.current_videoname}" "{saved_videoname}"')

				self.current_videoname = f'{VIDEO_DIR}/{str(round(time.time() * 1000))}_0_.ts'
				logging.info(f'New video ({saved_videoname.split("/")[-1]}) saved for camera {CAMERA_NAME}')

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

	logging.basicConfig(level=logging.INFO, filename='/logs/cameras.log', 
							  format='[%(asctime)s] %(levelname)s: %(message)s',
							  datefmt='%d-%m-%y %H:%M:%S')
	logging.info(f'Start recorder for camera {CAMERA_NAME}')

	updateVideoDir()
	timerThread = th.Thread(target=timer)  
	timerThread.daemon = True
	timerThread.start()  
	video_stream_widget = RTSPVideoWriterObject(rtsp_stream_link)

	try:
		video_stream_widget.update()
	except IndexError:
		print("KeyboardInterrupt received.")
		sys.exit()