import socket
import json



class Interface():
    def __init__(self, src_ip, dest_ip, net_mask, link_simulation):
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.net_mask = net_mask
        self.link_simulation = socket


class Route():
    def __init__(self, config_file):
        self.name = 'test'
        self.route_table = {}
        # TODO:读取配置文件，将接口状态写入
        # 此时应该建立连接，获取用于模拟物理连接的socket
        # self.interface
    def route_table_init(self):
        # TODO:使用接口，初始化路由表
        raise NotImplementedError()
    
    def data_link_layer(self, ip_package, next_hop_ip):
        # TODO:将一个ip包扔到这个函数，然后就会根据最长匹配原则，选择一个端口发送。
        raise NotImplementedError()