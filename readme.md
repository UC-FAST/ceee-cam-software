# 树莓派HQ相机——CEEE
# 硬件
## 我需要准备什么
* 学硬件是要烧钱的，为了完成这个项目，1000元是可能需要花费的。
* 需要购买的成品组件：
    - 树莓派HQ摄像头模组
    - 一个C或者CS接口的镜头，1/23"以上面积
    - 树莓派Zero 2w
* 必须的工具：电烙铁、热风枪、焊锡、锡浆、镊子等
* 额外的工具：游标卡尺，可以帮助你更加精确地测算机械尺寸
* 基本的电路板绘制技能
* 一些其他零件：在文件BOM.xlsx内
* 若干电阻以及电容等，参照原理图
_____
## 需要自制的电路板组件
本项目内含四块需要自制的电路板，分别为：
* Z01-2：电源板，负责整个系统的充放电，附带电量指示功能，并提供基本的输入按钮
![电源板](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Z01.png "Z01")
* Z02：摄像头转接板及支架，这一部分是作为结构板、不含电路的
![转接板](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Z02-1.png "摄像头转接板")
![支架](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Z02-2.png "摄像头支架")
* Z03：Lcd显示屏板，附带一个5D开关
![Lcd显示屏板](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Z03.png "Lcd显示屏板")

为了区分相对于树莓派正反的安装方向，电路板在阻焊层颜色上做了区分。安装于于树莓派正面的电路板为绿色，反面为紫色。

____

## 组装
需要用到若干5mm尼龙柱、10mm尼龙柱、12mm尼龙柱、15mm尼龙柱、M2.5尼龙螺丝以及M2.5尼龙螺母。本项目中所有安装孔都是2.5mm的直径。

### 组装顺序：
|层数|名称|高度（尼龙柱长度，单位mm）|
|-|-|-|
|1|树莓派HQ摄像头模组|
||尼龙柱|5|
|2|摄像头转接板 Z02||
||尼龙柱|5|
|3|摄像头支架 Z02|
||尼龙柱|10|
|4|树莓派Zero 2w，焊接17mm双排针|
||尼龙柱|12或15|
|5|电源板 Z01-2|
||尼龙柱|12|
|6|Lcd显示屏板|

* **组装前最好先做些测量工作，步步为营，不要急于求成**


_____
# 软件

## 运行环境

系统版本：2022-01-28-raspios-bullseye-armhf

Python版本：3.9.2

## 准备工作：
```
sudo apt update
sudo apt install python3-libcamera python3-kms++ libatlas-base-dev raspberrypi-ui-mods ffmpeg
```
```
pip3 install -r requirements.txt
```
```
cd ~
git clone https://github.com/raspberrypi/picamera2.git
export PYTHONPATH=/home/pi/picamera2
```

## universalControl.UniversalControl
类universalControl.UniversalControl起到控制与协调本项目运行的作用，是程序主循环的入口

```
universalControl.UniversalControl(
self, lcd: screen.Lcd, controlledEndList: List[controlledEnd.ControlledEnd]):
```

## 摄像头类 picam2.cam


类cam.camera用于创建摄像头句柄并录制图像，是cv2.VideoCapture的封装
```
camera(self, camid=0, width=128, height=128)
```
类的初始化函数

参数：
camid：摄像头的ID，默认为0

width：期望输出的图像宽度

height：期望输出的图像高度

```
camera.preview(self)
```
图像采集生成器函数，返回摄像头采集到的画面

```
camera.saveFrame(self, filePath):
```
保存当前的下一帧到磁盘，成功返回1，不成功返回0

参数：

filePath：保存文件路径

```
camera.rotate(self,angle)
```
旋转图像

参数：

angle：旋转角度

```
camera.zoom(self,zoom)
```
放大图像

参数：

zoom：放大系数，当系数输入小于1时不产生变化
```
camera.release(self)
```
释放摄像头资源

```
camera.revive(self)
```
重新获取摄像头资源

```
camera.frameQuality
```

图像清晰度评价结果，使用拉普拉斯算子。当拍其他条件不变时，画面越清晰，数值越大 只读

```
camera.framePerSecond
```
摄像机帧率 只读

```
camera.frameWidth
```
图像宽度

```
camera.frameHeight
```
图像高度



----
## 帧渲染模块 frameDecorator:
frameDecorator用于将文字和菜单等添加至OpenCV传入的帧中。

### 简单文本类 frameDecorator.SimpleText
frameDecorator.SimpleText是一个可以自动根据显示区域大小排版的用于显示单列文字的类，是cv2.putText的封装。

![SimpleText](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/SimpleText.png "SimpleText")

```
frameDecorator.SimpleText(
    self,
    func: list,
    height: int,
    padding: tuple = (0, 0, 0, 0),
    fontHeight: int = 12,
    color: tuple = (255, 255, 255),
    thickness: float = 1
)
```
类的初始化函数

参数：

func：一个元素为函数列表，列表中的函数因返回字典类型，字典的key为字符串，字典的value为字符串格式化参数。同一函数的返回值会在同一页面上显示。

height：显示窗口的高度

padding：显示区域的内边距，(左边距,上边距,右边距,下边距)。由于当前版本显示的字符串没有换行功能，右边距是一个没有用的参数

fontHeight：字体高度，单位像素

color：字体颜色，BGR格式。该参数将被直接赋值给cv2.putText的color参数，建议选择(255,255,255)纯白色，这样当屏幕背景色为白色时可手动遮住摄像头使背景色变暗，方便读取。

thickness: 字体粗细。该参数将被直接赋值给cv2.putText的thickness参数


```
SimpleText.nextPage(self)
```
用于选取函数列表中的下一个函数。当执行函数前已经是最后一个函数时，执行此方法可跳回第一个函数

```
SimpleText.setPage(self, page: int):
```
选取指定位置的函数

参数：

page：函数在函数列表中的位置，当page超出函数列表的范围时产生IndexError

```
SimpleText.decorate(self, frame)
```
渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

----

### 菜单类 frameDecorator.DialogBox
类frameDecorator.DialogBox是一个可以自动根据显示区域大小排版的用于显示菜单的类，是cv2.putText和cv2.rectangle的封装。

![DialogBox](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/DialogBox.png "DialogBox")

```
frameDecorator.DialogBox(
            width: int,
            height: int,
            options: list = None,
            title: str = None,
            padding: tuple = (0, 0, 0, 0),
            columnCount: int = 1,
            showIndex: bool = False,
            fontHeight: int = 12,
            color: tuple = (255, 255, 255),
            thickness: int = 1
                 
)
```
类的初始化函数

参数：


width：显示窗口的宽度

height：显示窗口的高度

options：一个保存菜单选项的列表

title：菜单标题

padding：显示区域的内边距，(左边距,上边距,右边距,下边距)

columnCount：菜单列数

showIndex：设置是否显示选项序号

fontHeight：字体高度，单位像素

color：字体颜色，BGR格式。该参数将被直接赋值给cv2.putText的color参数，建议选择(255,255,255)纯白色，这样当屏幕背景色为白色时可手动遮住摄像头使背景色变暗，方便读取

thickness: 字体粗细。该参数将被直接赋值给cv2.putText的thickness参数

```
DialogBox.setIndex(self, index:int):
```
选取指定选项的函数

参数：

index：选项在选项列表中的位置，当当options为None时或index超出选项列表的范围时产生IndexError

```
DialogBox.getCurrentIndex(self)
```
返回当前光标指向的选项在选项列表中的位置，从0开始。当options为None时产生IndexError


```
DialogBox.optionUp(self)
DialogBox.optionDown(self)
DialogBox.optionRight(self)
DialogBox.optionLeft(self)
```
用于控制光标的运动方向，在光标超出边界时不产生任何效果

```
DialogBox.decorate(self, frame)
```
渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

```
DialogBox.options
```

一个保存菜单选项的列表

```
DialogBox.title
```

菜单标题

---

### 柱状图类 frameDecorator.BarChart
类frameDecorator.BarChart是一个可以叠加在现有图像上的滚动柱状图显示类，是cv2.rectangle的封装。其内部维护了一个队列用于保存数据。

![BarChart](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/BarChart.png "BarChart")

```
frameDecorator.BarChart(
    self, 
    width=128, 
    height=128,
    maxSize=128, 
    scale=0, 
    color=(0, 0, 255), 
    thickness=1, 
    fill=False,
    alpha: float = 1
)
```
类的初始化函数

参数：

width：显示区域宽度

height：显示区域高度

maxSize：队列最大长度

scale：Y轴缩放系数，为0时自动调整

color：显示颜色，BGR格式。该参数将被直接赋值给cv2.rectangle的color参数

thickness：垂直高度，单位像素，仅在参数fill为False时有效

fill：为True时填充到图像底部，为False时仅显示顶部线条

alpha：柱状图透明度，范围0~1，为1时不透明

```
BarChart.addData(self, data):

```
向队列中添加数据
参数：

data：添加的数据

```
BarChart.decorate(self, frame):
```
渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

```
BarChart.dataList
```
数据列表，可将其他列表直接赋值。列表长度大于maxSize时会进行抽样。


### 帧直方图类 frameDecorator.Hist
类frameDecorator.Hist是一个可以叠加在现有图像上的图像色彩直方图显示类，是cv2.rectangle的封装。渲染速度较慢，不建议用于……场合中

![Hist](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Hist.png "Hist")

```
frameDecorator.Hist(
    self,
    width=128, 
    height=128, 
    padding=(0, 0, 0, 0),
    thickness=1, 
    fill=False, 
    alpha: float = 1
):
```
类的初始化函数

参数：

width：显示区域宽度

height：显示区域高度

padding：显示区域的内边距，(左边距,上边距,右边距,下边距)

thickness：垂直高度，单位像素，仅在参数fill为False时有效

fill：为True时填充到图像底部，为False时仅显示顶部线条

alpha：柱状图透明度，范围0~1，为1时不透明

```
BarChart.decorate(self, frame):
```
渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

-----
### Busy frameDecorator.Busy
类frameDecorator.Busy用于在图像的右上角绘制一个小方块表示程序正忙，是cv2.rectangle的封装。
![Busy](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/Busy.png "Busy")
```
frameDecorator.Busy(
    self, 
    width=128, 
    height=128, 
    color=(0, 0, 255)
    ):
```
类的初始化函数

参数：

width：显示区域宽度

height：显示区域高度

color：显示颜色，BGR格式。该参数将被直接赋值给cv2.rectangle的color参数

```
Busy.decorate(self,frame)
```

渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

---

### 注入灵魂 frameDecorator.WaterMark
加水印！

![WaterMark](https://github.com/UC-FAST/CEEE-HQ-CAMERA/blob/main/pict/WaterMark.png "WaterMark")
```
frameDecorator.WaterMark(
    self, 
    width=128, 
    height=128, 
    fontHeight=0
    )
```
类的初始化函数

参数

width：显示区域宽度

height：显示区域高度

fontHeight：字体高度，单位像素，为0时自动调整

```
WaterMark.decorate(self, frame):
```
渲染一帧OpenCV的图像

参数：

frame：OpenCV的图像数组

----


##  Lcd类 screen.Lcd:
类Lcd用于初始化屏幕并显示固定图像，在spi通信频率为17500000Hz、传入的图像为opencv生成时至少可达到30fps的显示帧率。（好用到哭）

```
screen.Lcd(self, width=128, height=128, ScanDir=ScanDir.R2L_D2U):
```
类的初始化函数

参数：

width：屏幕宽度

height：屏幕高度

ScanDir：刷新方向，见[screen.ScanDir](#ScanDir)

```
Lcd.backlight(self, state: bool)
```
背光开关

参数：

state：背光控制
```
Lcd.reset(self)
```
屏幕重置

```
Lcd.init(self)
```
屏幕初始化

```
Lcd.clear(self)
```
清屏

```
showImage(self, image)
```
显示一张图像

参数：

image：图像数组，可以由PIL（有性能问题）或者opencv生成

------

## 屏幕刷新方向<span id="ScanDir">screen.ScanDir</span>
设置屏幕的刷新方向

```ScanDir.L2R_U2D```

从左到右，从上到下

```ScanDir.L2R_D2U```

从左到右，从下到上

```ScanDir.R2L_U2D```

从右到左，从上到下

```ScanDir.R2L_D2U```

从右到左，从下到上

```ScanDir.U2D_L2R```

从上到下，从左到右

```ScanDir.U2D_R2L```

从上到下，从右到左

```ScanDir.D2U_L2R```

从下到上，从左到右

```ScanDir.D2U_R2L```

从下到上，从右到左


# 设置开机自启动
* 按需修改cam.service
* 执行
```
sudo cp cam.service /etc/systemd/system/
sudo systemctl daemon-reload
```
* 检查是否能正常执行
```
sudo systemctl start cam
```
若无报错，进入下一步

```
sudo systemctl enable cam.service
```
