#!/usr/bin/env python3
import universalControl
from components import screen, configLoader
from controlledEnd import MenuControlledEnd, GalleryControlledEnd, CameraControlledEnd

u = universalControl.UniversalControl(
    screen.Lcd(),
    [
        CameraControlledEnd(
            verbose_console=configLoader.ConfigLoader('./config.json')['debug_level'],
            tuningFilePath='./tuning/imx477.json'
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
