#!/usr/bin/env python3
import os
import sys

sys.path.append('.')    
sys.path.append('./components/')
sys.path.append('./utils/')     


from utils import ConfigLoader
ConfigLoader(os.path.abspath('./config.json'))


import universalControl
from components import lcd20
from controlledEnd import MenuControlledEnd, GalleryControlledEnd, CameraControlledEnd, SystemMonitor
from utils.exceptionRecorder import exceptionRecorder


tuning = './pisp/imx477.json'


config = ConfigLoader('./config.json')
u = universalControl.UniversalControl(
    lcd20.Lcd(),
    [
        CameraControlledEnd(
            verbose_console=config['debug_level'],
            #tuningFilePath=tuning
        ),
        SystemMonitor(),
        
        MenuControlledEnd(
            path='a.json',
            showPreview=True,
            rowCount=5,
            showIndex=True,
            fontHeight=14,
            padding=(5, 5, 5, 5)
        ),
        GalleryControlledEnd(pictPath=config['camera']['path']),
        
    ]
)


u.mainLoop()


