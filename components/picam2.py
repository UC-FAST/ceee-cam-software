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
from libcamera import controls

from . import configLoader


class Cam:
    def __init__(self, verbose_console=None, tuning=None):
        self.__cam = picamera2.Picamera2(verbose_console=verbose_console, tuning=tuning)
        #self.__cam = picamera2.Picamera2()
        self.__config = configLoader.ConfigLoader('./config.json')
        self.__pictConfig = self.__cam.create_preview_configuration(
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
        self.__brightness = 0
        self.__controls = dict()
        self.__metadata = None
        self.__frame = np.zeros((self.__height, self.__width, 3), np.uint8)
        self.__cam.start_preview()
        self.__cam.start()

        with self.__lock:
            self.__wOffset, self.__hOffset, self.__fWidth, self.__fHeight = self.__cam.capture_metadata()['ScalerCrop']

    def zoom(self, zoom):
        if zoom < 1:
            zoom = 1
        self.__digitalZoom = zoom
        self.__zoom(update=True)

    def __zoom(self, coordinate=None, update=False):
        if coordinate:
            wOffset, hOffset, fWidth, fHeight = tuple(coordinate)
        else:
            wOffset, hOffset, fWidth, fHeight = self.__wOffset, self.__hOffset, self.__fWidth, self.__fHeight
        pWidth, pHeight = fWidth // self.__digitalZoom, fHeight // self.__digitalZoom
        offset = [
            int((fWidth - pWidth) // 2 + wOffset),
            int((fHeight - pHeight) // 2 + hOffset)
        ]

        size = [int(pWidth), int(pHeight)]
        control = {"ScalerCrop": offset + size}
        self.__cam.set_controls(control)
        if update:
            self.__controls.update(control)

    @property
    def framePerSecond(self):
        return self.__framePerSecond

    def setAeExposureMode(self, code):
        print(dir(controls.AeMeteringModeEnum))
        control = {
            "AeEnable": True,
            "AeExposureMode": code
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)

    def setAwbMode(self, code):
        control = {
            "AwbEnable": True,
            "AwbMode": code
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)

    def brightness(self, brt):
        if brt <= -1:
            brt = -1
        if brt >= 1:
            brt = 1
        self.__brightness = brt
        control = {'Brightness': brt}
        self.__cam.set_controls(control)
        self.__controls.update(control)

    def setExposure(self, exposureTime, analogueGain):
        if exposureTime or analogueGain:
            control = {
                'AeEnable': False,
                "ExposureTime": exposureTime,
                'AnalogueGain': analogueGain,
            }
        else:
            control = {
                'AeEnable': True,
                "ExposureTime": exposureTime,
                'AnalogueGain': analogueGain,
            }
        self.__cam.set_controls(control)
        self.__controls.update(control)

    def setAeMeteringMode(self, code):
        """
        Spot:1
        
        """
        
        
        control = {
            'AeEnable': True,
            'AeMeteringMode': code
        }
        self.__cam.set_controls(control)
        self.__controls.update(control)

    def setColourGains(self, red, blue):
        return
        if red or blue:
            control = {
                "AwbEnable": False,
                "ColourGains": (red, blue)
            }

        else:
            control = {
                "AwbEnable": True,
            }
        self.__cam.set_controls(control)
        self.__controls.update(control)

    @property
    def frameQuality(self):
        if self.__metadata:
            try:
                return self.__metadata['FocusFoM']
            except KeyError:
                return 0
        return None

    @property
    def metadata(self):
        return self.__metadata

    def preview(self):
        present, t = 0, 0
        while True:
            with self.__lock:
                request = self.__cam.capture_request()
                buffer = request.make_buffer(name="lores")
                self.__metadata = request.get_metadata()
                request.release()
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
        if width == 0 or height == 0 or width > 1920 or height > 1920:
            width, height = 1920, 1080

        directoryPath = os.path.split(filePath)[0]
        if directoryPath:
            if not os.path.exists(directoryPath):
                os.makedirs(directoryPath)

        videoConfig = self.__cam.create_video_configuration(
            main={"size": (int(width), int(height))},
            lores={"size": (int(self.__config['screen']['width'] * 2), int(self.__config['screen']['height'] * 2))}
        )

        tempConfig = self.__cam.create_preview_configuration(
            main={"size": (int(width), int(height))},
            lores={"size": (int(self.__config['screen']['width'] * 2), int(self.__config['screen']['height'] * 2))}
        )

        with self.__lock:
            request = self.__cam.switch_mode_capture_request_and_stop(tempConfig)
            self.__wOffset, self.__hOffset, self.__fWidth, self.__fHeight = request.get_metadata()['ScalerCrop']
            self.__cam.configure(videoConfig)
            self.__cam.set_controls(self.__controls)
            self.__zoom()
            output = FfmpegOutput(filePath)
            self.__cam.start_recording(self.__encoder, output)

    def stopRecording(self):
        with self.__lock:
            self.__cam.stop_recording()
            self.__cam.configure(self.__pictConfig)
            self.__cam.start()
            self.__wOffset, self.__hOffset, self.__fWidth, self.__fHeight = self.__cam.capture_metadata()['ScalerCrop']
            self.__zoom()
            self.__cam.set_controls(self.__controls)

    def saveFrame(self, filePath: str, fmat, width, height, rotate=0, saveMetadata=False, saveRaw=False):
        path, filename = os.path.split(filePath)

        if not os.path.exists(path):
            os.makedirs(path)

        if width == 0 or height == 0:
            width, height = self.__cam.sensor_resolution
        if saveRaw:
            config = self.__cam.create_still_configuration(
                main={"size": (width, height)},
                raw={"size": self.__cam.sensor_resolution}
            )
        else:
            config = self.__cam.create_still_configuration(
                main={"size": (width, height)},
            )
        with self.__lock:
            self.__cam.switch_mode(config)
            coordinate = self.__cam.capture_metadata()['ScalerCrop']
            self.__cam.set_controls(self.__controls)
            self.__zoom(coordinate)
            time.sleep(1)
            request = self.__cam.capture_request()
            if fmat:
                frame = request.make_array("main")
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                if rotate:
                    frame = np.rot90(frame, -rotate // 90)
                cv2.imwrite("{}.{}".format(filePath, fmat['value']), frame)
            if saveMetadata:
                metadata = request.get_metadata()
                with open('{}.{}'.format(filePath, 'json'), 'w') as f:
                    json.dump(metadata, f, indent=4)
            if saveRaw:
                request.save_dng('{}.{}'.format(filePath, 'dng'))
            request.release()
            self.__cam.switch_mode(self.__pictConfig)
            self.__cam.set_controls(self.__controls)

    def exposureCapture(self, exposeTime, width, height):
        if width == 0 or height == 0 or width > 1920 or height > 1920:
            width, height = 1920, 1080
        config = self.__cam.still_configuration(
            main={"size": (width, height)},
        )
        with self.__lock:
            self.__cam.switch_mode(config)
            coordinate = self.__cam.capture_metadata()['ScalerCrop']
            self.__cam.set_controls(self.__controls)
            self.__zoom(coordinate)
            self.setExposure(exposeTime, 1)
            time.sleep(1)
            request = self.__cam.capture_request()
            frame = request.make_array("main")
            metadata = request.get_metadata()
            request.release()
            self.__cam.switch_mode(self.__pictConfig)
            self.__cam.set_controls(self.__controls)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return metadata['ExposureTime'], frame

    def stop(self):
        with self.__lock:
            self.__cam.stop()

    def start(self):
        with self.__lock:
            self.__cam.start()

    def release(self):
        self.__cam.close()
