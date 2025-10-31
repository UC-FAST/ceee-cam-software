import inspect
import json
import logging
import os
import threading
import time
import typing

import cv2
import numpy as np
import picamera2
from picamera2 import YUV420_to_RGB
from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

from utils import ConfigLoader,Logger,LogMsg


class Cam:
    def __init__(self, verbose_console:int=logging.INFO, tuning=None):
        self.__cam = picamera2.Picamera2(tuning=tuning)
        self.__cam.set_logging(verbose_console)
        self.__config = ConfigLoader('./config.json')
        self.__pict_config = self.__cam.create_preview_configuration(
            main={"size": (
                self.__config['screen']['width'] * 2, self.__config['screen']['height'] * 2)},
            lores={"size": (
                self.__config['screen']['width'] * 2, self.__config['screen']['height'] * 2)},
        )
        self.__cam.configure(self.__pict_config)
        self.__encoder = H264Encoder(self.__config['camera']['video_bitrate'])

        self.__lock = threading.Lock()
        self.__frame_per_second = 0
        self.__width = self.__config['screen']['width']
        self.__height = self.__config['screen']['height']
        self.__digital_zoom = 1
        self.__brightness = 0
        self.__controls = dict()
        self.__metadata:None|typing.Dict = None
        self.__frame = np.zeros((self.__height, self.__width, 3), np.uint8)
        self.__cam.start_preview(picamera2.Preview.NULL)
        self.__cam.start()

        self.__logger=Logger()
        self.__logger.info(LogMsg(
                content=f'Cam module init finished tuning={tuning}',
                module=self.__module__,
                filename=os.path.basename(os.path.abspath(__file__)),
                currentframe=inspect.currentframe()
            ))

        with self.__lock:
            self.__w_offset, self.__h_offset, self.__f_width, self.__f_height = self.__cam.capture_metadata()[
                'ScalerCrop']

    def zoom(self, zoom):
        if zoom < 1:
            zoom = 1
        self.__digital_zoom = zoom
        self.__zoom(update=True)

    def __zoom(self, coordinate=None, update=False):
        if coordinate:
            w_offset, h_offset, f_width, f_height = tuple(coordinate)
        else:
            w_offset, h_offset, f_width, f_height = self.__w_offset, self.__h_offset, self.__f_width, self.__f_height
        p_width, p_height = f_width // self.__digital_zoom, f_height // self.__digital_zoom
        offset = [
            int((f_width - p_width) // 2 + w_offset),
            int((f_height - p_height) // 2 + h_offset)
        ]

        size = [int(p_width), int(p_height)]
        control = {"ScalerCrop": offset + size}
        self.__cam.set_controls(control)
        if update:
            self.__controls.update(control)

    @property
    def frame_per_second(self):
        return self.__frame_per_second



    def brightness(self, brt):
        if brt <= -1:
            brt = -1
        if brt >= 1:
            brt = 1
        self.__brightness = brt
        control = {'Brightness': brt}
        self.__cam.set_controls(control)
        self.__controls.update(control)

    

    def set_AE_enable(self, enable:bool):
        control = {
            "AeEnable": enable
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)
        self.__logger.info(LogMsg(
            content=f'Set AE {"enable" if enable else "disable"}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AE_exposureMode(self, code):
        control = {
            #"AeEnable": True,
            "AeExposureMode": code
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)
        self.__logger.info(LogMsg(
            content=f'Set AE exposure mode={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AE_constraint_mode(self, code):
        control = {
            #'AeEnable': True,
            'AeConstraintMode': code
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)
        self.__logger.info(LogMsg(
            content=f'Set AE constraint mode={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AE_metering_mode(self, code):
        control = {
            #'AeEnable': True,
            'AeMeteringMode': code
        }
        self.__cam.set_controls(control)
        self.__controls.update(control)
        self.__logger.info(LogMsg(
            content=f'Set AE metering mode={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AE_flicker_mode(self, code):
        control = {
            #'AeEnable': True,
            'AeFlickerMode': code
        }
        self.__cam.set_controls(control)
        self.__controls.update(control)
        self.__logger.info(LogMsg(
            content=f'Set AE flicker mode={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))
        

    def set_AE_flicker_period(self, code):
        control = {
            'AeFlickerPeriod': code
        }
        self.__cam.set_controls(control)
        self.__controls.update(control)

        self.__logger.info(LogMsg(
            content=f'Set AE flicker period={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))


    def set_manual_exposure(self, exposure_time, analogue_gain):
        if exposure_time or analogue_gain:
            control = {
                'AeEnable': False,
                "ExposureTime": exposure_time,
                'AnalogueGain': analogue_gain,
            }
        else:
            control = {
                'AeEnable': True,
                "ExposureTime": exposure_time,
                'AnalogueGain': analogue_gain,
            }
        self.__cam.set_controls(control)
        self.__controls.update(control)

        self.__logger.info(LogMsg(
            content=f'Manual Exposure set exposure time={exposure_time} analogue gain={analogue_gain}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AWB_enable(self, enable:bool):
        control = {
            "AwbEnable": enable
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)

        self.__logger.info(LogMsg(
            content=f'Set AWB {"enable" if enable else "disable"}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_AWB_mode(self, code):
        control = {
            "AwbMode": code
        }
        self.__controls.update(control)
        self.__cam.set_controls(control)

        self.__logger.info(LogMsg(
            content=f'Set AWB mode={code}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    def set_colour_gains(self, red_gain, blue_gain):
        control = {
            "AwbEnable": False,
            "ColourGains": (red_gain, blue_gain)
        }
        self.__cam.set_controls(control)
        self.__controls.update(control)

        self.__logger.info(LogMsg(
            content=f'Set color gain red={red_gain} blue={blue_gain}',
            module=self.__module__,
            filename=os.path.basename(os.path.abspath(__file__)),
            currentframe=inspect.currentframe()
        ))

    @property
    def frame_quality(self):
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
            self.__frame_per_second = 1 / (present - t)
            t = present

    def start_recording(self, width, height, filePath):
        if width == 0 or height == 0 or width > 1920 or height > 1920:
            width, height = 1920, 1080

        directory_path = os.path.split(filePath)[0]
        if directory_path:
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)

        video_config = self.__cam.create_video_configuration(
            main={"size": (int(width), int(height))},
            lores={"size": (int(
                self.__config['screen']['width'] * 2), int(self.__config['screen']['height'] * 2))}
        )

        temp_config = self.__cam.create_preview_configuration(
            main={"size": (int(width), int(height))},
            lores={"size": (int(
                self.__config['screen']['width'] * 2), int(self.__config['screen']['height'] * 2))}
        )

        with self.__lock:
            request = self.__cam.switch_mode_capture_request_and_stop(
                temp_config)
            self.__w_offset, self.__h_offset, self.__f_width, self.__f_height = request.get_metadata()[
                'ScalerCrop']
            self.__cam.configure(video_config)
            self.__cam.set_controls(self.__controls)
            self.__zoom()
            output = FfmpegOutput(filePath)
            self.__cam.start_recording(self.__encoder, output)

    def stop_recording(self):
        with self.__lock:
            self.__cam.stop_recording()
            self.__cam.configure(self.__pict_config)
            self.__cam.start()
            self.__w_offset, self.__h_offset, self.__f_width, self.__f_height = self.__cam.capture_metadata()[
                'ScalerCrop']
            self.__zoom()
            self.__cam.set_controls(self.__controls)

    def save_frame(self, filePath: str, fmat, width, height, rotate=0, saveMetadata=False, saveRaw=False):
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
            self.__cam.switch_mode(self.__pict_config)
            self.__cam.set_controls(self.__controls)

    def exposure_capture(self, exposeTime, width, height):
        if width == 0 or height == 0 or width > 1920 or height > 1920:
            width, height = 1920, 1080
        config = self.__cam.create_still_configuration(
            main={"size": (width, height)},
        )
        
        with self.__lock:
            self.__cam.switch_mode(config)
            coordinate = self.__cam.capture_metadata()['ScalerCrop']
            self.__cam.set_controls(self.__controls)
            self.__zoom(coordinate)
            self.set_manual_exposure(exposeTime, 1)
            time.sleep(1)
            request = self.__cam.capture_request()
            frame = request.make_array("main")
            metadata = request.get_metadata()
            request.release()
            self.__cam.switch_mode(self.__pict_config)
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
