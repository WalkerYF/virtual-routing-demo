import socket
import json
import config
import utilities

class DataLinkLayer():
    def __init__(self):
        self.num_interface = 3
        self.interfaces = [] # 用于存放多个端口对象
        # TODO:监听线程，用于检测是否有网线动态连接
        # self.monitor.start()
        self.interface_init()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         
    
    def run(self):
        # 监听线程，用于检测是否有网线连上
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((utilities.get_host_ip(), config.SERVER_PORT))
        self.server_socket.listen(MAX_TCP_LINK)
        while True:
            # 阻塞型接受新链接
            (new_socket, addr) = listen_socket.accept()
            logger.debug('get new socket from listener port, addr is {}'.format(addr))
            # 开启新线程建立链接
            peer_connection = PeerConnection(new_socket,queue_lock)
            peer_connection.start()


    def interface_init(self):

        # TODO: 初始化端口

class Interface():
    def __init__(self, src_ip, dest_ip, net_mask, link_simulation):
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.net_mask = net_mask
        self.link_simulation = socket

    def get_status(self):
        return self.status

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
        # TODO:将一个ip包扔到这个函数，然后就会根据最长匹配原则，shomo选择一个端口发送。
        raise NotImplementedError()
