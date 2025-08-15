import json
import math
import queue
import time
import typing

import cv2
import numpy as np


from components import configLoader
from frameDecorator.colors import Colors
from .controlledEnd import ControlledEnd


class MenuControlledEnd(ControlledEnd):
    """
    MenuControlledEnd is a menu controller class for a graphical user interface, inheriting from ControlledEnd.
    It manages a menu system with multiple options, supporting navigation, selection, and configuration of menu items.
    The class is designed for use with OpenCV for rendering and supports various input actions (button presses, rotary encoder, etc.).
    Attributes:
        __options (list): List of current menu options.
        __optionList (dict): Dictionary of all menu options loaded from a JSON file.
        __path (str): Path to the menu configuration JSON file.
        __width (int): Width of the menu display.
        __height (int): Height of the menu display.
        __rowCount (int): Number of rows (menu items) per page.
        __fontHeight (int): Height of the font used for menu text.
        __fontScale (float): Font scale for normal text.
        __highLightFontScale (float): Font scale for highlighted text.
        __padding (tuple): Padding for the menu display (left, top, right, bottom).
        __showIndex (bool): Whether to show index numbers for menu items.
        __showPreview (bool): Whether to show a preview of the selected item.
        __thickness (int): Thickness of the text.
        __spaceHeight (int): Vertical space between menu items.
        __currentOptions (list): List of currently visible menu options.
        __pageCount (int): Total number of pages in the menu.
        __currentPage (int): Index of the current page.
        __currentIndex (int): Index of the currently selected item on the current page.
        __currentMenuID (str): ID of the current menu.
        __selectIndex (int): Index of the currently selected option for editing.
        __title (str): Title of the current menu.
        __from (str): Sender ID for message passing.
        __valueTemp: Temporary value for editing options.
        __routeList (list): Stack for tracking menu navigation history.
        __theme (dict): Color theme for the menu display.
        __frameList (queue): Queue for storing rendered frames.
        __direction (int): Display rotation direction.
        __config (ConfigLoader): Configuration loader instance.
    Methods:
        __init__(...): Initialize the menu controller with display and menu parameters.
        __pageCountCalc(): Calculate the number of pages based on enabled options.
        options: Property to get the current option list.
        setOption(key): Set the current menu options by key.
        dumpConfig(): Save the current menu configuration to file.
        __spaceCalc(): Calculate vertical spacing for menu items.
        __drawSlideBar(frame): Draw the slide bar for page navigation.
        __genItemStartCoordinate(...): Generate coordinates for menu item rendering.
        __jumpToPrevious(): Navigate to the previous menu in the route stack.
        __setEnableState(option): Enable or disable options based on dependencies.
        select(): Handle selection of the current menu item.
        unselect(): Finalize editing of an option and send updates.
        upAction(), upOneStep(), __pageUp(): Navigate up in the menu.
        downAction(), downOneStep(), __pageDown(): Navigate down in the menu.
        __jumpByIndex(index), __jumpByID(target, record): Jump to a submenu by index or ID.
        __drawContent(frame): Draw menu item text.
        __drawUnderLinePreview(frame): Draw preview of the selected item.
        __drawData(frame): Draw data values for menu items.
        __drawCursor(frame): Draw the selection cursor.
        __drawTitle(background): Draw the menu title.
        __numericalSlideBar(frame): Draw a slider for numerical options.
        __optionMenu(frame): Draw the option selection menu.
        decorate(): Render the current menu state to a frame.
        __nextStep(), __previousStep(): Change the step size for numerical options.
        __valuePlus(), __valueMinus(): Increment or decrement a numerical value.
        __optionUp(), __optionDown(): Navigate through option values.
        centerPressAction(), upPressAction(), downPressAction(), leftPressAction(), rightPressAction(): Handle button press actions.
        circlePressAction(), crossPressAction(), crossLongPressAction(): Handle special button actions.
        rotaryEncoderCounterClockwise(), rotaryEncoderClockwise(), rotaryEncoderSelect(): Handle rotary encoder actions.
        shutterPressAction(), squarePressAction(): Placeholder for additional actions.
        msgReceiver(sender, msg): Receive and process external messages.
        onEnter(lastID): Initialize the menu when entering.
        onExit(): Clean up when exiting the menu.
        mainLoop(): Generator yielding rendered frames for display.
        """

    def __init__(
            self,
            _id='MenuControlledEnd',
            path=None,
            width: int = 320,
            height: int = 240,
            padding: tuple = (10, 10, 10, 10),
            rowCount: int = 4,
            showIndex: bool = False,
            showPreview: bool = True,
            fontHeight: int = 24,
            thickness: int = 1
    ):
        """
            Initializes a MenuControlledEnd instance with customizable menu display options.
            Parameters:
                _id (str): Identifier for the menu instance. Defaults to 'MenuControlledEnd'.
                path (str, optional): Path to a JSON file containing menu options. If provided, menu options are loaded from this file.
                width (int): Width of the menu display in pixels. Defaults to 320.
                height (int): Height of the menu display in pixels. Defaults to 240.
                padding (tuple): Padding around the menu content, specified as (left, top, right, bottom). Defaults to (10, 10, 10, 10).
                rowCount (int): Number of rows to display in the menu. Defaults to 4.
                showIndex (bool): Whether to display the index of each menu option. Defaults to False.
                showPreview (bool): Whether to show a preview for menu options. Defaults to True.
                fontHeight (int): Height of the font used for menu text. Defaults to 24.
                thickness (int): Thickness of the font and menu borders. Defaults to 1.
            Attributes initialized:
                - Loads menu options from file if path is provided.
                - Sets up font scaling for normal and highlighted text.
                - Initializes menu state variables (current options, page, index, etc.).
                - Sets up color themes for menu display.
                - Loads configuration from './config.json'.
            """

        ControlledEnd.__init__(self, _id)
        self.__options = None
        self.__optionList = None
        self.__path, self.__width, self.__height, self.__rowCount = path, width, height, rowCount
        if self.__path:
            with open(self.__path) as f:
                self.__menuOptions = json.load(f)

        self.__fontHeight = fontHeight
        self.__fontScale = cv2.getFontScaleFromHeight(
            cv2.FONT_ITALIC, self.__fontHeight)
        self.__highLightFontScale = cv2.getFontScaleFromHeight(
            cv2.FONT_ITALIC, int(self.__fontHeight * 1.5))
        self.__padding = padding
        self.__showIndex, self.__showPreview, self.__thickness = showIndex, showPreview, thickness
        self.__spaceHeight = 0
        self.__currentOptions: typing.List[dict] = list()
        self.__pageCount = 0
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentMenuID = None
        self.__selectIndex = None  # Index selected
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
        {
            'background': Colors.industrialBlue.value,
            'cursor': Colors.industrialGreen.value,
            'text': Colors.white.value,
            'boolTrue': Colors.industrialYellow.value,
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
        """
        Calculates the total number of pages required to display enabled options.
        Iterates through the list of options, counting only those that are enabled.
        Determines the highest index of enabled options and calculates the number of pages
        needed based on the row count per page. Ensures that there is at least one page.
        Updates:
            self.__pageCount (int): The calculated number of pages.
        """

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
        """
        Returns the list of available options.
        Returns:
            list: The list of options stored in the __optionList attribute.
        """

        return self.__optionList

    def setOption(self, key):
        """
        Sets the current menu option based on the provided key.
        This method updates the internal state of the menu, including the list of options,
        current menu ID, navigation route, title, available options, and pagination details.
        It resets the selection index, current page, and current option index, and prepares
        the options to be displayed on the first page.
        Args:
            key (str): The key identifying the menu options to display.
        Side Effects:
            Updates several internal attributes related to menu state and navigation.
        """


        self.__optionList = self.__menuOptions[key]
        self.__currentMenuID = "0"
        self.__routeList = list()
        self.__title = self.__title = self.__optionList[self.__currentMenuID].get(
            'title', None)
        self.__options = self.__optionList[self.__currentMenuID]['options']
        self.__pageCountCalc()
        self.__spaceCalc()
        self.__selectIndex = None
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentOptions = self.__options[0:self.__rowCount]

    def dumpConfig(self):
        """
        Saves the current menu options to a JSON file.
        Writes the contents of self.__menuOptions to the file specified by self.__path
        in JSON format with indentation for readability.
        Raises:
            IOError: If the file cannot be opened or written to.
            TypeError: If self.__menuOptions contains non-serializable objects.
        """

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
        """
        Draws a vertical slide bar (pagination indicator) on the given frame.

        The slide bar visually represents the current page among multiple pages, with up and down arrows indicating navigation availability. The bar and arrows are styled according to the current theme and padding settings.

        Args:
            frame (numpy.ndarray): The image/frame on which to draw the slide bar.

        Side Effects:
            Modifies the input frame in place by drawing the slide bar, navigation arrows, and the current page indicator.

        Visual Elements:
            - Background rectangle for the slide bar.
            - Top and bottom navigation arrows (solid or outlined depending on page position).
            - Highlighted rectangle indicating the current page.

        Depends on:
            - self.__width (int): Width of the frame.
            - self.__height (int): Height of the frame.
            - self.__padding (tuple): Padding values for the frame (left, top, right, bottom).
            - self.__currentPage (int): Index of the current page.
            - self.__pageCount (int): Total number of pages.
            - self.__theme (dict): Color theme for drawing.
        """
        refLength = min(self.__width, self.__height)

        topSolid, bottomSolid = True, True
        if self.__currentPage == self.__pageCount - 1:
            bottomSolid = False
        if self.__currentPage == 0:
            topSolid = False

        backgroundCoordinate = (
            (self.__width - self.__padding[2] -
             refLength // 21, self.__padding[1]),
            (self.__width, self.__height - self.__padding[3])
        )
        cv2.rectangle(
            frame, backgroundCoordinate[0], backgroundCoordinate[1], self.__theme['background'], -1)
        topCoordinate = (
            (self.__width - self.__padding[2],
             self.__padding[1] + refLength // 21),
            (self.__width - self.__padding[2] - refLength //
             21, self.__padding[1] + refLength // 21),
            (self.__width - self.__padding[2] -
             refLength // 42, self.__padding[1]),
            (self.__width - self.__padding[2],
             self.__padding[1] + refLength // 21),
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
            (self.__width - self.__padding[2], self.__height -
             self.__padding[1] - refLength // 21),
            (self.__width - self.__padding[2] - refLength // 21,
             self.__height - self.__padding[3] - refLength // 21),
            (self.__width - self.__padding[2] - refLength //
             42, self.__height - self.__padding[3]),
            (self.__width - self.__padding[2], self.__height -
             self.__padding[1] - refLength // 21),
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

        cv2.rectangle(frame, beginCoordinate, endCoordinate,
                      self.__theme['cursor'], -1)

    def __genItemStartCoordinate(self, itemCount=None, ignoreTitle=False):
        """
        Generates the starting (x, y) coordinates for menu items, accounting for padding, spacing, font height, and optional title.

        Args:
            itemCount (int, optional): The number of items to generate coordinates for. If None, uses self.__rowCount.
            ignoreTitle (bool, optional): If True, ignores the title when calculating the starting coordinate. Defaults to False.

        Yields:
            list: The [x, y] coordinate for each menu item.
        """
        if not itemCount:
            itemCount = self.__rowCount
        if self.__title is not None and not ignoreTitle:
            firstStartCoordinate = (
                self.__padding[0],
                self.__padding[1] +
                int(self.__spaceHeight * 1.5) + self.__fontHeight,
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
        """
        Updates the 'enable' state of options based on the provided configuration.

        Args:
            option (dict): A dictionary containing the following optional keys:
                - 'setDisable' (list): List of option IDs to be disabled or enabled based on 'value'.
                - 'setEnable' (list): List of option IDs to be enabled or disabled based on 'value'.
                - 'enableWith' (list): List of option IDs to be enabled or disabled together with the current option.
                - 'value' (bool): Determines whether to enable or disable options in 'setDisable' and 'setEnable'.
                - 'enable' (bool, optional): If True (default), enables options in 'enableWith'; if False, disables them.

        Side Effects:
            Modifies the 'enable' state of options in self.__options in place.
        """
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
            receiver = self.__currentOptions[self.__currentIndex].get(
                'receiver', None)
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
        elif t == 'option' or t == 'numeral':
            self.__valueTemp = self.__currentOptions[self.__currentIndex]['value']
            self.__selectIndex = self.__currentIndex
        else:
            raise RuntimeError()

    def unselect(self):
        """
        Handles the unselection of the current menu option.

        This method performs the following actions:
        - Updates the current option's value with the temporary value.
        - Resets the temporary value.
        - Sends a message with the current menu state to the originating sender.
        - If the current option has a receiver and a value, sends the updated option to the receiver.
        - Resets the selection index.
        - Dumps (saves) the current configuration.
        """
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
        # If have reveiver in option, send value to it
        receiver = self.__currentOptions[self.__selectIndex].get(
            'receiver', None)
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
            self.__routeList.append(
                (self.__currentMenuID, self.__currentIndex))
        self.__currentMenuID = target
        self.__title = self.__optionList[self.__currentMenuID].get(
            'title', None)
        self.__options = self.__optionList[self.__currentMenuID]['options']

        self.__pageCountCalc()
        self.__spaceCalc()
        self.__selectIndex = None
        self.__currentPage = 0
        self.__currentIndex = 0
        self.__currentOptions = self.__options[0:self.__rowCount]

    def __drawContent(self, frame):
        """
        Draws the menu options onto the provided frame.
        This method iterates through the current menu options and renders each option's text and a background rectangle
        on the given frame using OpenCV. The text color depends on whether the option is enabled or disabled. If
        `self.__showIndex` is True, the index of each option is displayed before its content.
        Args:
            frame (numpy.ndarray): The image/frame on which the menu content will be drawn.
        Returns:
            None
        """
        
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
                    "{} {}".format(
                        index + 1, self.__currentOptions[index]['content']),
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
                    self.__width -
                    self.__padding[2] - self.__width // 21 -
                    self.__width // 21,
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
            value = self.__currentOptions[self.__currentIndex]['value']['content']
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
                line * (self.__fontHeight + self.__spaceHeight) +
                self.__spaceHeight + self.__padding[1]
            ),
            (
                self.__width - self.__padding[2] -
                self.__width // 21 - self.__width // 21,
                (line + 1) * (self.__fontHeight +
                              self.__spaceHeight) + self.__padding[1]
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
            (self.__width - self.__padding[2] -
             self.__width // 21, coordinate[1][1]),
            self.__theme['background'],
            -1
        )

    def __drawData(self, frame):
        """
        Draws the data options onto the provided frame if preview is enabled.

        This method iterates through the current menu options and renders their visual representation
        on the given frame using OpenCV drawing functions. It highlights the currently selected option,
        displays option values with appropriate background colors based on their type, and handles
        different option types such as boolean, message, menu, IRQ, option, and numeral.

        Args:
            frame: The image/frame (as a NumPy array) on which the menu options will be drawn.

        Raises:
            TypeError: If an unknown option type is encountered in the current options.
        """
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
                        self.__width -
                        self.__padding[2] -
                        self.__width // 21 - self.__width // 21,
                        i[1] - self.__spaceHeight
                    ),
                    (
                        self.__width -
                        self.__padding[2] - self.__width // 42 - 1,
                        i[1] + self.__fontHeight + self.__spaceHeight
                    ),
                    self.__theme['background'],
                    - 1
                )
                self.__drawUnderLinePreview(frame)
                # continue
            fontColor = self.__theme['text']
            t = self.__currentOptions[index]['type'].lower()
            # Show little hint value
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
                # When option have extra value, show it's name
                value = self.__currentOptions[index]['value']['content']
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
                    self.__width -
                    self.__padding[2] - 3 *
                    (self.__width // 42) - 8 * self.__fontHeight,
                    i[1] - self.__spaceHeight // 3
                ),
                (
                    self.__width -
                    self.__padding[2] - self.__width // 21 -
                    self.__width // 21,
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
                        2] - self.__width // 42 - self.__width // 21 - 8 * self.__fontHeight,
                    i[1] + self.__fontHeight
                ),
                cv2.FONT_ITALIC,
                self.__fontScale,
                fontColor
            )
            cv2.rectangle(
                frame,
                (
                    self.__width -
                    self.__padding[2] - self.__width // 21 -
                    self.__width // 21,
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
                        self.__width -
                        self.__padding[2] -
                        self.__width // 21 - self.__width // 21,
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
                self.__width -
                self.__padding[2] - self.__width // 21 -
                self.__width // 21 + 1,
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
        """
        Draws a numerical slide bar UI component on the given frame.

        This method visualizes a slider for adjusting a numerical value within a specified range.
        It displays the minimum and maximum labels, arrow indicators for increment/decrement,
        the current value, the range, and the step size. The slider bar is filled according to
        the current value, and the UI is rendered using OpenCV drawing functions.

        Args:
            frame (numpy.ndarray): The image/frame on which the slider UI will be drawn.

        Visual Elements:
            - "min" and "max" labels at the ends of the slider.
            - Left and right arrow indicators, filled or outlined depending on value limits.
            - A filled rectangle representing the current value's position on the slider.
            - The current value, centered below the slider.
            - The range (min <--> max) and step size displayed below the slider.

        Uses:
            - self.__currentOptions: List of option dictionaries containing 'min', 'max', 'value', and 'step'.
            - self.__currentIndex: Index of the currently selected option.
            - self.__valueTemp: Temporary value for the slider, if set.
            - self.__theme: Dictionary containing color settings for text and cursor.
            - self.__fontHeight, self.__fontScale: Font size settings.
            - self.__width, self.__padding: UI layout settings.
            - self.__genItemStartCoordinate: Helper method to generate coordinates for UI elements.
        """
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
                    (int(
                        self.__width - self.__padding[2] - self.__fontHeight * 3), i[1] + self.__fontHeight),
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

                if value <= mi:# No fill
                    last = rightCoordinate[0]
                    for _ in rightCoordinate[1:]:
                        cv2.line(frame, last, _, self.__theme['cursor'])
                        last = _
                else:
                    polygon = np.array(rightCoordinate)
                    cv2.fillConvexPoly(frame, polygon, self.__theme['cursor'])

                leftCoordinate = (
                    (self.__width -
                     self.__padding[2] - self.__fontHeight, i[1]),
                    (self.__width -
                     self.__padding[2] - self.__fontHeight, i[1] + self.__fontHeight),
                    (self.__width - self.__padding[2],
                     i[1] + self.__fontHeight // 2),
                    (self.__width -
                     self.__padding[2] - self.__fontHeight, i[1]),
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
                slideBarWidth = int(slideBarTotalWidth * (value-1) / (ma - mi))
                slideBarCoordinate = (
                    (i[0] + self.__fontHeight + self.__width // 42, i[1]),
                    (i[0] + self.__fontHeight + self.__width //
                     42 + slideBarWidth, i[1] + self.__fontHeight),
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
                    (int((self.__width - self.__fontHeight *
                     len(str(value))) // 2), i[1] + self.__fontHeight),
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
                    "Step {}".format(
                        self.__currentOptions[self.__currentIndex]['step']),
                    (i[0], i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text'],
                )
                return

    def __optionMenu(self, frame):
        # Gt Current Value
        value = self.__valueTemp if self.__valueTemp is not None else self.__currentOptions[
            self.__currentIndex]['value']
        # Get Current Options
        options: list = self.__currentOptions[self.__currentIndex]['options']
        # Get Current Index of Selected Option
        selectIndex = options.index(value)
        value = value['content']
        for _, (index, i) in zip(
                range(
                    len(self.__currentOptions[self.__currentIndex]['options']) + 1),
                enumerate(self.__genItemStartCoordinate(
                    itemCount=self.__rowCount + 1, ignoreTitle=True))
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
                    (i[0] + self.__fontHeight + self.__width //
                     42, i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text']
                )
            else:  # Render the rest of the options
                try:
                    option = options[(selectIndex + index - 2) % len(options)]
                    text = option['content']
                except IndexError:
                    break
                cv2.putText(
                    frame,
                    text,
                    (i[0] + self.__fontHeight + self.__width //
                     42, i[1] + self.__fontHeight),
                    cv2.FONT_ITALIC,
                    self.__fontScale,
                    self.__theme['text']
                )

    def decorate(self):
        sketch = np.full((self.__height, self.__width, 3),
                         self.__theme['background'], np.uint8)
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

    def crossPressAction(self):
        if self.__selectIndex is not None:
            self.__selectIndex = None
            self.decorate()
        else:
            try:
                self.__jumpToPrevious()
                self.decorate()
            except IndexError:
                self._irq(self.__from)

    def crossLongPressAction(self):
        self._irq(self.__from)

    def rotaryEncoderCounterClockwise(self):
        if self.__selectIndex is None:
            self.downAction()
            self.decorate()
            time.sleep(0.05)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__valuePlus()
                self.decorate()
                time.sleep(0.1)
            else:
                self.__optionDown()
                self.decorate()
                time.sleep(0.2)

    def rotaryEncoderClockwise(self):
        if self.__selectIndex is None:
            self.upAction()
            self.decorate()
            time.sleep(0.05)
        else:
            if self.__currentOptions[self.__selectIndex]['type'] == 'numeral':
                self.__valueMinus()
                self.decorate()
                time.sleep(0.1)
            else:
                self.__optionUp()
                self.decorate()
                time.sleep(0.2)

    def rotaryEncoderSelect(self):
        if self.__selectIndex is not None:
            self.unselect()
        else:
            self.select()
        self.decorate()

    def shutterPressAction(self):
        pass

    def squarePressAction(self):
        pass

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
            np.full((self.__height, self.__width, 3),
                    self.__theme['background'], np.uint8),
            block=True
        )

    def mainLoop(self):
        while True:
            yield self.__frameList.get(True)
