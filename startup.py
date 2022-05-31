#!/usr/bin/env python3


import universalControl
from components import screen, configLoader
from controlledEnd import MenuControlledEnd, GalleryControlledEnd, CameraControlledEnd

l = screen.Lcd()
# c = picam2.cam(tuning="tuning.json")
m = MenuControlledEnd(
    showPreview=True,
    rowCount=4,
    showIndex=True,
    fontHeight=10,
    padding=(5, 5, 5, 5)
)

debugLevel = configLoader.ConfigLoader('./config.json')['debug_level']
u = universalControl.UniversalControl(
    l,
    [
        CameraControlledEnd(verbose_console=debugLevel, tuningFilePath='./tuning/imx477.json'),
        m,
        GalleryControlledEnd()
    ]
)

u.mainLoop()
