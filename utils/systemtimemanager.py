import socket
import struct
from datetime import datetime
import subprocess

from . import network
from components import BQ32002
from utils import configLoader, logger


class SystemTimeManager():
    def __init__(self) -> None:
        self.__config=configLoader.ConfigLoader('./config.json')
        self.__logger=logger()#initialize_logger(console_level=self.__config['debug_level'])

    def get_time(self):
        if network.network().refresh_internet_connection_state()[0]:
            timestamp = self.get_time_from_ntp()
            BQ32002.BQ32002().write_time(timestamp)
        else:
            timestamp = BQ32002.BQ32002().read_time()

        self.set_system_time_with_timestamp(timestamp)

    def set_system_time_with_timestamp(self, timestamp):
        try:
            # 格式化时间字符串
            dt = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

            # 设置系统时间
            cmd = f"date -s '{dt}'"
            result = subprocess.run(
                cmd, shell=True, check=True, capture_output=True, text=True)

            self.__logger.info(f"System time has been setted to : {dt}")
            return True

        except subprocess.CalledProcessError as e:
            self.__logger.error(f"An failure occurred while setting time: {e}")
            return False
        except Exception as e:
            self.__logger.error(f"An unexpected error occurred while setting time: {e}")
            return False

    def get_time_from_ntp(
            self,
            ntp_server: str = 'ntp1.aliyun.com',
            timeout: int = 5
    ):
        """
        使用 NTP 协议从 NTP 服务器获取时间

        Args:
            ntp_server: NTP 服务器地址
            timeout: 超时时间（秒）

        Returns:
            Unix timestamp
        """
        try:
            # NTP 协议格式
            ntp_packet = bytearray(48)
            ntp_packet[0] = 0x1B  # LI, Version, Mode

            # 创建 UDP socket
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)

                # 发送 NTP 请求
                sock.sendto(ntp_packet, (ntp_server, 123))

                # 接收响应
                data, _ = sock.recvfrom(1024)

                if len(data) >= 48:
                    # 解析 NTP 时间戳（从第40字节开始）
                    ntp_timestamp = struct.unpack('!12I', data)[10]

                    # NTP 时间戳是从 1900年1月1日开始的秒数
                    # 转换为 Unix 时间戳（从 1970年1月1日开始的秒数）
                    ntp_epoch = 2208988800  # 1900到1970的秒数差
                    unix_timestamp = ntp_timestamp - ntp_epoch

                    return unix_timestamp

        except Exception as e:
            print(f"NTP 请求失败: {e}")
            return None


# 使用示例
if __name__ == "__main__":
    '''ntp_time = get_ntp_time('ntp1.aliyun.com')
    if ntp_time:
        print(f"Aliyun NTP 时间: {ntp_time}")
        print(f"本地时间: {datetime.now(timezone.utc)}")
        print(
            f"时间差: {(datetime.now(timezone.utc) - ntp_time).total_seconds():.3f} 秒")'''

 