import json
import math
import queue
import time
import typing

import cv2
import numpy as np
import wiringpi

from components import configLoader
from frameDecorator.colors import Colors
from .controlledEnd import ControlledEnd


class MenuControlledEnd(ControlledEnd):
    def __init__(
            self,
            _id='MenuControlledEnd',
            path='./menu.json',
            width: int = 128,
            height: int = 128,
            padding: tuple = (10, 10, 10, 10),
            rowCount: int = 4,
            showIndex: bool = False,
            showPreview: bool = True,
            fontHeight: int = 12,
            thickness: int = 1
    ):
        ControlledEnd.__init__(self, _id)
        self.__options = None
        self.__optionList = None
        self.__path, self.__width, self.__height, self.__rowCount = path, width, height, rowCount
        with open(self.__path) as f:
            self.__menuOptions = json.load(f)

        self.__fontHeight = fontHeight
        self.__fontScale = cv2.getFontScaleFromHeight(cv2.FONT_ITALIC, self.__fontHeight)
        self.__highLightFontScale = cv2.getFontScaleFromHeight(cv2.FONT_ITALIC, int(self.__fontHeight * 1.5))
        self.__padding = padding
        self.__showIndex, self.__showPreview, self.__thickness = showIndex, showPreview, thickness
        self.__spaceHeight = 0
        self.__currentOptions: typing.List[dict] = list()
        self.__pageCount = 0
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentMenuID = None
        self.__selectIndex = None
        self.__title = None
        self.__from = None
        self.__valueTemp = None
        self.__routeList: typing.List[tuple] = list()
        self.__theme = {
            'background': Colors.black.value,
            'cursor': Colors.steelblue.value,
            'text': Colors.white.value,
            'boolTrue': Colors.darkolivegreen.value,
            'boolFalse': Colors.darkred.value,
            'numeral': Colors.darkgoldenrod.value,
            'msg': Colors.gray.value,
            'option': Colors.palevioletred.value,
            'irq': Colors.darkorchid.value,
            'cursorDisable': Colors.darkgray.value,
            'textDisable': Colors.gray.value
        }

        self.__frameList = None
        self.__direction = 0
        self.__config = configLoader.ConfigLoader('./config.json')

    def __pageCountCalc(self):
        enableOptionRange = 0
        for index, option in enumerate(self.__options, start=1):
            enable = option.get('enable', True)
            if enable:
                enableOptionRange = index
        self.__pageCount = math.ceil(enableOptionRange / self.__rowCount)
        if self.__pageCount == 0:
            self.__pageCount = 1

    @property
    def options(self):
        return self.__optionList

    def setOption(self, key):
        self.__optionList = self.__menuOptions[key]
        self.__currentMenuID = "0"
        self.__routeList = list()
        self.__title = self.__title = self.__optionList[self.__currentMenuID].get('title', None)
        self.__options = self.__optionList[self.__currentMenuID]['options']
        self.__pageCountCalc()
        self.__spaceCalc()
        self.__selectIndex = None
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentOptions = self.__options[0:self.__rowCount]

    def dumpConfig(self):
        with open(self.__path, 'w') as f:
            json.dump(self.__menuOptions, f, indent=4)

    def __spaceCalc(self):
        lineCount = self.__rowCount
        if self.__showPreview:
            lineCount += 1
        if self.__title is not None:
            lineCount += 1
        totalHeight = self.__height - self.__padding[1] - self.__padding[3]
        totalSpace = totalHeight - lineCount * self.__fontHeight
        spaceCount = lineCount
        self.__spaceHeight = totalSpace // spaceCount

    def __drawSlideBar(self, frame):
        refLength = min(self.__width, self.__height)

        topSolid, bottomSolid = True, True
        if self.__currentPage == self.__pageCount - 1:
            bottomSolid = False
        if self.__currentPage == 0:
            topSolid = False

        backgroundCoordinate = (
            (self.__width - self.__padding[2] - refLength // 21, self.__padding[1]),
            (self.__width, self.__height - self.__padding[3])
        )
        cv2.rectangle(frame, backgroundCoordinate[0], backgroundCoordinate[1], self.__theme['background'], -1)
        topCoordinate = (
            (self.__width - self.__padding[2], self.__padding[1] + refLength // 21),
            (self.__width - self.__padding[2] - refLength // 21, self.__padding[1] + refLength // 21),
            (self.__width - self.__padding[2] - refLength // 42, self.__padding[1]),
            (self.__width - self.__padding[2], self.__padding[1] + refLength // 21),
        )

        if topSolid:
            polygon = np.array(topCoordinate)
            cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])
        else:
            last = topCoordinate[0]
            for i in topCoordinate[1:]:
                cv2.line(frame, last, i, self.__theme['cursor'])
                last = i

        bottomCoordinate = (
            (self.__width - self.__padding[2], self.__height - self.__padding[1] - refLength // 21),
            (self.__width - self.__padding[2] - refLength // 21, self.__height - self.__padding[3] - refLength // 21),
            (self.__width - self.__padding[2] - refLength // 42, self.__height - self.__padding[3]),
            (self.__width - self.__padding[2], self.__height - self.__padding[1] - refLength // 21),
        )

        if bottomSolid:
            polygon = np.array(bottomCoordinate)
            cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])
        else:
            last = bottomCoordinate[0]
            for i in bottomCoordinate[1:]:
                cv2.line(frame, last, i, self.__theme['cursor'])
                last = i

        slideBarHeightTotal = self.__height - self.__padding[1] - self.__padding[
            3] - refLength // 21 * 2 - refLength // 42 * 2
        slideBarHeight = slideBarHeightTotal // self.__pageCount
        slideBarWidth = refLength // 21
        slideBarOffset = (
            self.__width - self.__padding[2] - slideBarWidth,
            self.__padding[1] + refLength // 21 + refLength // 42
        )

        beginCoordinate = (
            slideBarOffset[0],
            self.__currentPage * slideBarHeight + slideBarOffset[1]
        )

        endCoordinate = (
            slideBarOffset[0] + slideBarWidth,
            (self.__currentPage + 1) * slideBarHeight + slideBarOffset[1]
        )

        cv2.rectangle(frame, beginCoordinate, endCoordinate, self.__theme['cursor'], -1)

    def __genItemStartCoordinate(self, itemCount=None, ignoreTitle=False):
        if not itemCount:
            itemCount = self.__rowCount
        if self.__title is not None and not ignoreTitle:
            firstStartCoordinate = (
                self.__padding[0],
                self.__padding[1] + self.__spaceHeight * 2 + self.__fontHeight,
            )
        else:
            firstStartCoordinate = (
                self.__padding[0],
                self.__padding[1] + self.__spaceHeight
            )

        temp = list(firstStartCoordinate)

        for _ in range(itemCount):
            yield temp
            temp[1] += self.__fontHeight + self.__spaceHeight

    def __jumpToPrevious(self):
        last = self.__routeList.pop()
        self.__jumpByID(last[0], record=False)
        self.__currentIndex = last[1]

    def __setEnableState(self, option):
        setDisable: list = option.get('setDisable', [])
        setEnable: list = option.get('setEnable', [])
        enableWith: list = option.get('enableWith', [])
        if not setDisable and not setEnable and not enableWith:
            return
        readyToEnable, readyToDisable = [], []

        for i in self.__options:
            if i['id'] in setDisable:
                if option['value']:
                    readyToDisable.append(i)
                else:
                    readyToEnable.append(i)
            if i['id'] in setEnable:
                if option['value']:
                    readyToEnable.append(i)
                else:
                    readyToDisable.append(i)

        if option.get('enable', True):
            for i in self.__options:
                if i['id'] in enableWith:
                    if i in readyToDisable:
                        continue
                    readyToEnable.append(i)
        else:
            for i in self.__options:
                if i['id'] in enableWith:
                    if i in readyToEnable:
                        readyToEnable.remove(i)
                    readyToDisable.append(i)

        for i in readyToEnable:
            i['enable'] = True
        for j in readyToDisable:
            j['enable'] = False

    def select(self):
        t = self.__currentOptions[self.__currentIndex]['type'].lower()
        if t == 'bool':
            self.__currentOptions[self.__currentIndex]['value'] = not self.__currentOptions[self.__currentIndex][
                'value']
            self.__setEnableState(self.__currentOptions[self.__currentIndex])
            self._msgSender(
                self._id,
                self.__from,
                (
                    self.__currentMenuID,
                    self.__menuOptions[self.__from]
                )
            )
            self.__pageCountCalc()
            receiver = self.__currentOptions[self.__currentIndex].get('receiver', None)
            if receiver:
                self._msgSender(
                    receiver,
                    receiver,
                    self.__currentOptions[self.__currentIndex]['value']
                )
            self.dumpConfig()
        elif t == 'menu':
            self.__jumpByIndex(self.__currentIndex)
            self.decorate()
            return
        elif t == 'irq':
            self._irq(self.__currentOptions[self.__currentIndex]['value'])
            return
        elif t == 'msg':
            self._msgSender(
                self._id,
                self.__currentOptions[self.__currentIndex]['receiver'],
                (
                    self.__currentOptions[self.__currentIndex]['value'],
                    self.__menuOptions[self.__from]
                )
            )
            self._irq(self.__from)
        else:
            self.__valueTemp = self.__currentOptions[self.__currentIndex]['value']
            self.__selectIndex = self.__currentIndex

    def unselect(self):
        self.__currentOptions[self.__selectIndex]['value'] = self.__valueTemp
        self.__valueTemp = None
        self._msgSender(
            self._id,
            self.__from,
            (
                self.__currentMenuID,
                self.__menuOptions[self.__from]
            )
        )
        receiver = self.__currentOptions[self.__selectIndex].get('receiver', None)
        if receiver and 'value' in self.__currentOptions[self.__selectIndex].keys():
            self._msgSender(
                None,
                receiver,
                self.__currentOptions[self.__selectIndex]
            )
        self.__selectIndex = None
        self.dumpConfig()

    def upAction(self):
        times = 1
        for i in self.__options[self.__currentPage * self.__rowCount + self.__currentIndex - 1::-1]:
            enable = i.get('enable', True)
            if not enable:
                times += 1
            else:
                break
        else:
            times = 0

        for i in range(times):
            self.upOneStep()

    def upOneStep(self):
        if self.__currentPage == 0 and self.__currentIndex == 0:
            return
        elif self.__currentPage != 0 and self.__currentIndex == 0:
            self.__pageUp()
            return
        self.__currentIndex -= 1

    def __pageUp(self):
        if self.__currentPage == 0:
            return
        self.__currentPage -= 1
        self.__currentIndex = self.__rowCount - 1
        self.__currentOptions = self.__options[
                                self.__currentPage * self.__rowCount:(self.__currentPage + 1) * self.__rowCount
                                ]

    def downAction(self):
        times = 1
        for i in self.__options[self.__currentPage * self.__rowCount + self.__currentIndex + 1:]:
            enable = i.get('enable', True)
            if not enable:
                times += 1
            else:
                break
        else:
            times = 0

        for i in range(times):
            self.downOneStep()

    def downOneStep(self):
        if self.__currentPage * self.__rowCount + self.__currentIndex + 1 == len(self.__options):
            return
        elif self.__currentIndex == self.__rowCount - 1:
            self.__pageDown()
            return
        self.__currentIndex += 1

    def __pageDown(self):
        if self.__currentPage == self.__pageCount:
            return
        self.__currentPage += 1
        self.__currentIndex = 0
        self.__currentOptions = self.__options[
                                self.__currentPage * self.__rowCount:(self.__currentPage + 1) * self.__rowCount
                                ]

    def __jumpByIndex(self, index):
        self.__jumpByID(self.__currentOptions[index]['value'])

    def __jumpByID(self, target, record=True):
        if record:
            self.__routeList.append((self.__currentMenuID, self.__currentIndex))
        self.__currentMenuID = target
        self.__title = self.__optionList[self.__currentMenuID].get('title', None)
        self.__options = self.__optionList[self.__currentMenuID]['options']

        self.__pageCountCalc()
        self.__spaceCalc()
        self.__selectIndex = None
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentOptions = self.__options[0:self.__rowCount]

    def __drawContent(self, frame):
        if not self.__showIndex:
            return
        for index, i in zip(
                range(len(self.__currentOptions)),
                self.__genItemStartCoordinate()
        ):
            enable = self.__currentOptions[index].get('enable', True)
            color = self.__theme['text'] if enable else self.__theme['textDisable']

            if self.__showIndex:
                cv2.putText(
                    frame,
                    "{} {}".format(index + 1, self.__currentOptions[index]['content']),
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    color
                )
            else:
                cv2.putText(
                    frame,
                    "{}".format(self.__currentOptions[index]['content']),
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    color
                )
            cv2.rectangle(
                frame,
                (
                    self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                    i[1] - self.__spaceHeight,
                ),
                (
                    self.__width - self.__padding[2] - self.__width // 21,
                    i[1] + self.__spaceHeight + self.__fontHeight,
                ),
                self.__theme['background'],
                -1
            )

    def __drawUnderLinePreview(self, frame):
        if not self.__showPreview:
            return
        line = self.__rowCount
        if self.__title is not None:
            line += 1

        t = self.__currentOptions[self.__currentIndex]['type'].lower()

        if t == 'bool':
            if self.__currentOptions[self.__currentIndex]['value']:
                backgroundColor = self.__theme['boolTrue']
                text = 'Y'
            else:
                backgroundColor = self.__theme['boolFalse']
                text = 'N'
        elif t == 'irq':
            backgroundColor = self.__theme[t]
            text = str(self.__currentOptions[self.__currentIndex]['value'])
        elif t == 'option':
            backgroundColor = self.__theme[t]
            value = self.__currentOptions[self.__currentIndex]['value']
            if isinstance(value, list):
                text = str(value[0])
            else:
                text = str(value)
        elif t == 'numeral':
            value = self.__currentOptions[self.__currentIndex]['value']
            if isinstance(value, float):
                value = round(value, 2)
            text = str(value)
            backgroundColor = self.__theme[t]
        elif t == 'msg':
            backgroundColor = self.__theme[t]
            text = str(self.__currentOptions[self.__currentIndex]['receiver'])
        elif t == 'menu':
            return
        else:
            raise TypeError(t)

        coordinate = (
            (
                self.__padding[0],
                line * (self.__fontHeight + self.__spaceHeight) + self.__spaceHeight + self.__padding[1]
            ),
            (
                self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                (line + 1) * (self.__fontHeight + self.__spaceHeight) + self.__padding[1]
            )
        )

        cv2.rectangle(frame, coordinate[0], coordinate[1], backgroundColor, -1)

        cv2.putText(
            frame,
            str(text),
            (
                coordinate[0][0], coordinate[1][1]
            ),
            cv2.FONT_ITALIC,
            self.__fontScale,
            self.__theme['text'],
        )

        cv2.rectangle(
            frame,
            (coordinate[1][0], coordinate[0][1]),
            (self.__width - self.__padding[2] - self.__width // 21, coordinate[1][1]),
            self.__theme['background'],
            -1
        )

    def __drawData(self, frame):
        if not self.__showPreview:
            return
        for index, i in zip(
                range(len(self.__currentOptions)),
                self.__genItemStartCoordinate()
        ):
            if not self.__currentOptions[index].get('enable', True):
                continue
            if self.__currentIndex == index:
                cv2.rectangle(
                    frame,
                    (
                        self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                        i[1] - self.__spaceHeight
                    ),
                    (
                        self.__width - self.__padding[2] - self.__width // 42 - 1,
                        i[1] + self.__fontHeight + self.__spaceHeight
                    ),
                    self.__theme['background'],
                    - 1
                )
                self.__drawUnderLinePreview(frame)
                continue
            fontColor = self.__theme['text']
            t = self.__currentOptions[index]['type'].lower()
            if t == 'bool':
                if self.__currentOptions[index]['value']:
                    value = 'Y'
                    backgroundColor = self.__theme['boolTrue']
                else:
                    value = 'N'
                    backgroundColor = self.__theme['boolFalse']
            elif t == 'msg':
                value = self.__currentOptions[index]['receiver']
                backgroundColor = self.__theme[t]
            elif t == 'menu':
                continue
            elif t == 'irq':
                value = self.__currentOptions[index]['value']
                backgroundColor = self.__theme[t]

            elif t == 'option':
                value = self.__currentOptions[index]['value']
                if isinstance(value, list):
                    value = value[0]
                backgroundColor = self.__theme[t]
            elif t == 'numeral':
                value = self.__currentOptions[index]['value']
                if isinstance(value, float):
                    value = round(value, 2)
                backgroundColor = self.__theme[t]
            else:
                raise TypeError(t)

            cv2.rectangle(
                frame,
                (
                    self.__width - self.__padding[2] - 3 * (self.__width // 42) - 3 * self.__fontHeight,
                    i[1] - self.__spaceHeight // 3
                ),
                (
                    self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                    i[1] + self.__fontHeight + self.__spaceHeight // 3
                ),
                backgroundColor,
                -1
            )
            cv2.putText(
                frame,
                "{}".format(value),
                (
                    self.__width - self.__padding[
                        2] - self.__width // 42 - self.__width // 21 - 3 * self.__fontHeight,
                    i[1] + self.__fontHeight
                ),
                cv2.FONT_ITALIC,
                self.__fontScale / 1.2,
                fontColor
            )
            cv2.rectangle(
                frame,
                (
                    self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                    i[1] - self.__spaceHeight
                ),
                (
                    self.__width - self.__padding[2] - self.__width // 42 - 1,
                    i[1] + self.__fontHeight + self.__spaceHeight
                ),
                self.__theme['background'],
                -1
            )

    def __drawCursor(self, frame):
        for index, i in enumerate(self.__genItemStartCoordinate()):
            if self.__currentIndex == index:
                enable = self.__currentOptions[index].get('enable', True)
                color = self.__theme['cursor'] if enable else self.__theme['cursorDisable']
                cv2.rectangle(
                    frame,
                    (
                        i[0],
                        i[1] - self.__spaceHeight // 3
                    ),
                    (
                        self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21,
                        i[1] + self.__fontHeight + self.__spaceHeight // 3
                    ),
                    color,
                    -1
                )
                break

    def __drawTitle(self, background):
        if not self.__title:
            return
        coordinate = (
            self.__padding[0],
            self.__padding[1] + self.__fontHeight
        )

        cv2.putText(
            background,
            self.__title,
            coordinate,
            cv2.FONT_ITALIC,
            self.__fontScale,
            self.__theme['text'],
            self.__thickness
        )
        cv2.rectangle(
            background,
            (
                self.__width - self.__padding[2] - self.__width // 21 - self.__width // 21 + 1,
                self.__padding[1] - self.__spaceHeight
            ),
            (
                self.__width - self.__padding[2] - self.__width // 21 - 1,
                self.__padding[1] + self.__fontHeight + self.__spaceHeight
            ),
            self.__theme['background'],
            -1
        )

    def __numericalSlideBar(self, frame):
        value = self.__valueTemp if self.__valueTemp is not None else self.__currentOptions[self.__currentIndex][
            'value']
        mi = self.__currentOptions[self.__currentIndex]['min']
        ma = self.__currentOptions[self.__currentIndex]['max']
        for index, i in enumerate(self.__genItemStartCoordinate(itemCount=5, ignoreTitle=True)):
            if index == 0:
                cv2.putText(
                    frame,
                    "min",
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )
                cv2.putText(
                    frame,
                    "max",
                    (int(self.__width - self.__padding[2] - self.__fontHeight * 3), i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )

            elif index == 1:
                rightCoordinate = (
                    (i[0] + self.__fontHeight, i[1]),
                    (i[0] + self.__fontHeight, i[1] + self.__fontHeight),
                    (i[0], i[1] + self.__fontHeight // 2),
                    (i[0] + self.__fontHeight, i[1]),
                )

                if value <= mi:
                    last = rightCoordinate[0]
                    for _ in rightCoordinate[1:]:
                        cv2.line(frame, last, _, self.__theme['cursor'])
                        last = _
                else:
                    polygon = np.array(rightCoordinate)
                    cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])

                leftCoordinate = (
                    (self.__width - self.__padding[2] - self.__fontHeight, i[1]),
                    (self.__width - self.__padding[2] - self.__fontHeight, i[1] + self.__fontHeight),
                    (self.__width - self.__padding[2], i[1] + self.__fontHeight // 2),
                    (self.__width - self.__padding[2] - self.__fontHeight, i[1]),
                )

                if value >= ma:
                    last = leftCoordinate[0]
                    for _ in leftCoordinate[1:]:
                        cv2.line(frame, last, _, self.__theme['cursor'])
                        last = _
                else:
                    polygon = np.array(leftCoordinate)
                    cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])

                slideBarTotalWidth = self.__width - self.__padding[0] - self.__padding[2] - (
                        self.__fontHeight + self.__width // 42) * 2
                slideBarWidth = int(slideBarTotalWidth * value / (ma - mi))
                slideBarCoordinate = (
                    (i[0] + self.__fontHeight + self.__width // 42, i[1]),
                    (i[0] + self.__fontHeight + self.__width // 42 + slideBarWidth, i[1] + self.__fontHeight),
                )
                cv2.rectangle(
                    frame,
                    slideBarCoordinate[0],
                    slideBarCoordinate[1],
                    self.__theme['cursor'],
                    -1
                )

            elif index == 2:
                if isinstance(value, float):
                    value = round(value, 2)
                cv2.putText(
                    frame,
                    str(value),
                    (int((self.__width - self.__fontHeight * len(str(value))) // 2), i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )

            elif index == 3:
                cv2.putText(
                    frame,
                    "{} <--> {}".format(mi, ma),
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )
            elif index == 4:
                cv2.putText(
                    frame,
                    "Step {}".format(self.__currentOptions[self.__currentIndex]['step']),
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )
                return

    def __optionMenu(self, frame):
        value = self.__valueTemp if self.__valueTemp is not None else self.__currentOptions[self.__currentIndex][
            'value']
        options: list = self.__currentOptions[self.__currentIndex]['options']
        selectIndex = options.index(value)
        if isinstance(value, list):
            value = value[0]
        for _, (index, i) in zip(
                range(len(self.__currentOptions[self.__currentIndex]['options']) + 1),
                enumerate(self.__genItemStartCoordinate(itemCount=self.__rowCount + 1, ignoreTitle=True))
        ):
            if index == 0:
                cv2.putText(
                    frame,
                    self.__currentOptions[self.__currentIndex]['content'],
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text']
                )

            elif index == 2:
                rightCoordinate = (
                    (i[0], i[1]),
                    (i[0] + self.__fontHeight, i[1] + self.__fontHeight // 2),
                    (i[0], i[1] + self.__fontHeight),
                    (i[0], i[1]),
                )
                polygon = np.array(rightCoordinate)
                cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])
                cv2.putText(
                    frame,
                    str(value),
                    (i[0] + self.__fontHeight + self.__width // 42, i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text']
                )
            else:
                try:
                    option = options[(selectIndex + index - 2) % len(options)]
                    if isinstance(option, list):
                        text = str(option[0])
                    else:
                        text = str(option)
                except IndexError:
                    break
                cv2.putText(
                    frame,
                    text,
                    (i[0] + self.__fontHeight + self.__width // 42, i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text']
                )

    def decorate(self):
        sketch = np.full((self.__height, self.__width, 3), self.__theme['background'], np.uint8)
        if self.__selectIndex is None:
            if self.__title is not None:
                self.__drawTitle(sketch)
            self.__drawCursor(sketch)
            self.__drawContent(sketch)
            self.__drawData(sketch)
            self.__drawSlideBar(sketch)
        else:
            t = self.__currentOptions[self.__currentIndex]['type'].lower()
            if t == 'numeral':
                self.__numericalSlideBar(sketch)
            elif t == 'option':
                self.__optionMenu(sketch)

        if self.__direction:
            sketch = np.rot90(sketch, -self.__direction // 90)
        self.__frameList.put(sketch)

    def direction(self, direction):
        self.__direction = direction
        if self.__frameList is not None:
            self.decorate()

    def __nextStep(self):
        item: dict = self.__currentOptions[self.__currentIndex]
        if 'stepOptions' not in item.keys():
            return
        currentStepIndex = item['stepOptions'].index(item['step'])
        if currentStepIndex == len(item['stepOptions']) - 1:
            item['step'] = item['stepOptions'][0]
        else:
            item['step'] = item['stepOptions'][currentStepIndex + 1]

    def __previousStep(self):
        item: dict = self.__currentOptions[self.__currentIndex]
        if 'stepOptions' not in item.keys():
            return
        currentStepIndex = item['stepOptions'].index(item['step'])
        if currentStepIndex == 0:
            item['step'] = item['stepOptions'][-1]
        else:
            item['step'] = item['stepOptions'][currentStepIndex - 1]

    def __valuePlus(self):
        item = self.__currentOptions[self.__selectIndex]
        if item['type'] != 'numeral':
            return
        value, step, ma = self.__valueTemp, item['step'], item['max']
        value += step
        if value >= ma:
            value = ma
        self.__valueTemp = value

    def __valueMinus(self):
        item = self.__currentOptions[self.__selectIndex]
        if item['type'] != 'numeral':
            return
        value, step, mi = self.__valueTemp, item['step'], item['min']
        value -= step
        if value <= mi:
            value = mi
        self.__valueTemp = value

    def __optionUp(self):
        item = self.__currentOptions[self.__selectIndex]
        if item['type'] != 'option':
            return
        value, optionList = self.__valueTemp, item['options']
        optionIndex = optionList.index(value)
        self.__valueTemp = optionList[optionIndex - 1]

    def __optionDown(self):
        item = self.__currentOptions[self.__selectIndex]
        if item['type'] != 'option':
            return
        value, optionList = self.__valueTemp, item['options']
        optionIndex = optionList.index(value)
        try:
            self.__valueTemp = optionList[optionIndex + 1]
        except IndexError:
            self.__valueTemp = optionList[0]

    def centerPressAction(self):
        '''t = 0
        while wiringpi.digitalRead(self.__config['pin']['center']) and t < 1:
            t += 0.01
            time.sleep(0.01)
        if t < 0.09:
            return'''
        if self.__selectIndex is not None:
            self.unselect()
        else:
            self.select()
        self.decorate()

    def upPressAction(self):
        if self.__selectIndex is None:
            self.upAction()
            self.decorate()
            time.sleep(0.2)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__previousStep()
                self.decorate()
                time.sleep(0.2)
            else:
                self.__optionUp()
                self.decorate()
                time.sleep(0.2)

    def downPressAction(self):
        if self.__selectIndex is None:
            self.downAction()
            self.decorate()
            time.sleep(0.2)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__nextStep()
                self.decorate()
                time.sleep(0.2)
            else:
                self.__optionDown()
                self.decorate()
                time.sleep(0.2)

    def leftPressAction(self):
        if self.__selectIndex is None:
            self.upAction()
            self.decorate()
            time.sleep(0.2)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__valueMinus()
                self.decorate()
                time.sleep(0.1)
            else:
                self.__optionUp()
                self.decorate()
                time.sleep(0.2)

    def rightPressAction(self):
        if self.__selectIndex is None:
            self.downAction()
            self.decorate()
            time.sleep(0.2)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__valuePlus()
                self.decorate()
                time.sleep(0.1)
            else:
                self.__optionDown()
                self.decorate()
                time.sleep(0.2)

    def circlePressAction(self):
        if self.__selectIndex is not None:
            self.unselect()
        else:
            self.select()
        self.decorate()

    def trianglePressAction(self):
        if self.__selectIndex is not None:
            self.__selectIndex = None
            self.decorate()
        else:
            try:
                self.__jumpToPrevious()
                self.decorate()
            except IndexError:
                self._irq(self.__from)

    def triangleLongPressAction(self):
        self._irq(self.__from)

    def msgReceiver(self, sender, msg):
        self.setOption(msg)
        self.__from = sender
        self._msgSender(
            self._id,
            self.__from,
            (
                self.__currentMenuID,
                self.__menuOptions[self.__from]
            )
        )

    def onEnter(self, lastID):
        self.__frameList = queue.SimpleQueue()
        self.decorate()

    def onExit(self):
        self.__frameList.put(
            np.full((self.__height, self.__width, 3), self.__theme['background'], np.uint8),
            block=True
        )

    def mainLoop(self):
        while True:
            yield self.__frameList.get(True)
