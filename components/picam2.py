import json
import os
import threading
import time

import cv2
import numpy as np

import picamera2
from picamera2 import YUV420_to_RGB
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput
from . import configLoader


class Cam:
    def __init__(self, verbose_console=None, tuning=None):
        self.__cam = picamera2.Picamera2(verbose_console=verbose_console, tuning=tuning)
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__pictConfig = self.__cam.preview_configuration(
            main={"size": (self.__config['screen']['width'] * 2, self.__config['screen']['height'] * 2)},
            lores={"size": (self.__config['screen']['width'] * 2, self.__config['screen']['height'] * 2)},
        )

        self.__cam.configure(self.__pictConfig)
        self.__encoder = H264Encoder(self.__config['camera']['video_bitrate'])
        self.__lock = threading.Lock()
        self.__framePerSecond = 0
        self.__width = self.__config['screen']['width']
        self.__height = self.__config['screen']['height']
        self.__digitalZoom = 1
        self.__metadata = None
        self.__frame = np.zeros((self.__height, self.__width, 3), np.uint8)
        self.__cam.start_preview()
        self.__cam.start()

    def zoom(self, zoom):
        if zoom < 1:
            zoom = 1
        self.__digitalZoom = zoom
        self.__setZoom()

    def __setZoom(self):
        # [2, 0, 4052, 3040]
        # 4056,3040
        if self.__digitalZoom == 1:
            self.__cam.set_controls({"ScalerCrop": [2, 0, 4052, 3040]})
            return
        swidth, sheight = (4052 - 2, 3040 - 0)
        pwidth, pheight = swidth // self.__digitalZoom, sheight // self.__digitalZoom
        offset = [int((swidth - pwidth) // 2) + 2, int((sheight - pheight) // 2)]
        size = [int(pwidth), int(pheight)]
        self.__cam.set_controls({"ScalerCrop": offset + size})

    @property
    def framePerSecond(self):
        '''if self.__metadata is None:
            return 0
        return 1 / self.__metadata['FrameDuration'] * 10e5'''
        return self.__framePerSecond

    @property
    def exposureTime(self):
        try:
            return self.__metadata['ExposureTime']
        except TypeError:
            return None

    @exposureTime.setter
    def exposureTime(self, value):
        self.__lock.acquire()
        if value != 0:
            self.__cam.set_controls({
                "ExposureTime": int(value),
                'AnalogueGain': 1
            })
        else:
            self.__cam.set_controls({
                "ExposureTime": 0,
                'AnalogueGain': 0,
            })
        self.__lock.release()

    @property
    def frameQuality(self):
        if self.__metadata:
            return self.__metadata['FocusFoM']
        return None

    @property
    def metadata(self):
        return self.__metadata

    def preview(self):
        '''
        ['__class__', '__delattr__', '__dict__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__',
         '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__',
         '__subclasshook__', '__weakref__', 'acquire', 'configure_count', 'get_metadata', 'lock', 'make_array', 'make_buffer', 'make_image', 'picam2', 'ref_count', 'release', 'request', 'save', 'save_dng', 'stop_count']
        '''

        present, t = 0, 0
        while True:
            self.__lock.acquire()
            request = self.__cam.capture_request()
            buffer = request.make_buffer(name="lores")
            self.__metadata = request.get_metadata()
            request.release()
            self.__lock.release()
            self.__frame = YUV420_to_RGB(
                buffer,
                (
                    self.__config['screen']['width'] * 2,
                    self.__config['screen']['height'] * 2
                )
            )
            yield self.__frame
            present = time.time()
            self.__framePerSecond = 1 / (present - t)
            t = present

    def startRecording(self, width, height, filePath):
        if width == 0 or height == 0:
            width, height = self.__cam.sensor_resolution

        directoryPath = os.path.split(filePath)[0]
        if directoryPath:
            if not os.path.exists(directoryPath):
                os.makedirs(directoryPath)

        self.__lock.acquire()
        self.__cam.stop()

        videoConfig = self.__cam.video_configuration(
            main={"size": (int(width), int(height))},
            lores={"size": (int(self.__config['screen']['width'] * 2), int(self.__config['screen']['height'] * 2))}
        )
        self.__cam.configure(videoConfig)
        output = FfmpegOutput(filePath)
        self.__cam.start_recording(self.__encoder, output)
        self.__lock.release()

    def stopRecording(self):
        self.__lock.acquire()
        self.__cam.stop_recording()
        self.__cam.start()
        self.__lock.release()

    def saveFrame(self, filePath, width, height, rotate=0, saveMetadata=False, saveRaw=False):
        directoryPath = os.path.split(filePath)[0]
        if directoryPath:
            if not os.path.exists(directoryPath):
                os.makedirs(directoryPath)

        if width == 0 or height == 0:
            width, height = self.__cam.sensor_resolution
        if saveRaw:
            config = self.__cam.still_configuration(
                main={"size": (width, height)},
                raw={"size": self.__cam.sensor_resolution}
            )
        else:
            config = self.__cam.still_configuration(
                main={"size": (width, height)},
            )
        self.__lock.acquire()
        self.__cam.switch_mode(config)
        self.__setZoom()
        request = self.__cam.capture_request()
        frame = request.make_array("main")
        if rotate:
            frame = np.rot90(frame, -rotate // 90)
        if saveMetadata:
            metadata = request.get_metadata()
            with open('{}.{}'.format(os.path.splitext(filePath)[0], 'json'), 'w') as f:
                json.dump(metadata, f, indent=4)
        if saveRaw:
            request.save_dng('{}.{}'.format(os.path.splitext(filePath)[0], 'dng'))
        request.release()
        self.__cam.switch_mode(self.__pictConfig)
        self.__setZoom()
        self.__lock.release()
        frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        threading.Thread(target=cv2.imwrite, args=(filePath, frame)).start()

    def exposureCapture(self, exposeTime, width, height):
        if width == 0 or height == 0:
            width, height = 3000, 2000
        config = self.__cam.still_configuration(
            main={"size": (width, height)},
            lores={"size": (self.__config['screen']['width'] * 2, self.__config['screen']['height'] * 2)}
        )
        self.__lock.acquire()
        self.__cam.switch_mode(config)
        self.__lock.release()
        self.exposureTime = exposeTime
        self.__lock.acquire()
        frame = self.__cam.capture_array()
        self.__cam.switch_mode(self.__pictConfig)
        self.__lock.release()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.exposureTime = 0
        return frame

    def stop(self):
        self.__lock.acquire()
        self.__cam.stop()
        self.__lock.release()

    def release(self):
        self.__cam.close()
