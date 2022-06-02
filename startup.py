#!/usr/bin/env python3
import os
import time

import wiringpi

import universalControl
from components import screen, configLoader
from controlledEnd import MenuControlledEnd, GalleryControlledEnd, CameraControlledEnd

tuning = './tuning.json'
t = 0
config = configLoader.ConfigLoader('./config.json')
while wiringpi.digitalRead(config['pin']['square']) and t < 1:
    t += 0.01
    time.sleep(0.01)
if t >= 1:
    if os.path.exists('./tuning.json'):
        tuning = './tuning.json'

u = universalControl.UniversalControl(
    screen.Lcd(),
    [
        CameraControlledEnd(
            verbose_console=configLoader.ConfigLoader('./config.json')['debug_level'],
            tuningFilePath=tuning
        ),
        MenuControlledEnd(
            showPreview=True,
            rowCount=4,
            showIndex=True,
            fontHeight=10,
            padding=(5, 5, 5, 5)
        ),
        GalleryControlledEnd()
    ]
)

u.mainLoop()
