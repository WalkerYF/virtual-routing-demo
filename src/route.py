import socket

class Interface():
    def __init__(self, ip, net_mask, next_hop):
        self.ip = ip
        self.net_mask = net_mask
        self.next_hop = next_hop


class Route():
    def __init__(self, config_file):
        self.name = 'test'
        # TODO:读取配置文件，将接口状态写入
        # self.interface