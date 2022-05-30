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
    fontHeight=10
)

debugLevel = configLoader.ConfigLoader('./config.json')['debug_level']

u = universalControl.UniversalControl(
    l,
    [
        CameraControlledEnd(verbose_console=debugLevel),
        m,
        GalleryControlledEnd()
    ]
)

u.mainLoop()
