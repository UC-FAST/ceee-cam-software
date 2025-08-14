#!/usr/bin/env python3
import os
import time


import universalControl
from components import lcd20, configLoader
from controlledEnd import MenuControlledEnd, GalleryControlledEnd, CameraControlledEnd

tuning = './pisp/imx477.json'


config = configLoader.ConfigLoader('./config.json')
u = universalControl.UniversalControl(
    lcd20.Lcd(),
    [
        CameraControlledEnd(
            verbose_console=config['debug_level'],
            #tuningFilePath=tuning
        ),
        MenuControlledEnd(
            path='a.json',
            showPreview=True,
            rowCount=5,
            showIndex=True,
            fontHeight=14,
            padding=(5, 5, 5, 5)
        ),
        GalleryControlledEnd(pictPath=config['camera']['path'])
    ]
)

u.mainLoop()
