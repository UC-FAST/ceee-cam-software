# CEEE-树莓派相机 软件

# 运行环境

系统版本(已测试)：

2022-01-28-raspios-bullseye-armhf
2022-01-28-raspios-bullseye-arm64-lite

Python版本：3.9.2

# 准备工作：

```
sudo apt update
sudo apt install python3-libcamera python3-pyqt5 python3-kms++ libatlas-base-dev raspberrypi-ui-mods ffmpeg git python3-pip libcap-dev
```

在raspi-config的Interface Options选项中开启SPI和I2C，Legacy Camera选择'No'

```
cd ~
git clone https://github.com/UC-FAST/ceee-cam-software.git
cd ceee-cam-software/
pip3 install -r requirements-py39.txt
```

_____________
设置开机自启动

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

____________
可选的swap分区扩容

```
sudo dd if=/dev/zero of=/swap bs=1k count=2048000
sudo mkswap /swap
sudo swapon /swap
```

编辑/etc/fstab，加入一行：

```
/swap swap swap defaults 0 0
```

______
启动

```sudo systemctl start cam```

或

```python3 startup.py```

