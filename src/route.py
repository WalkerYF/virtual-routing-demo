import socket
import json
import config
from include import utilities
import threading
from include import rdt_socket
import link
import sys
import logging
import unittest
import pdb
import queue
import pickle
import threading
from route_table import RouteTable
from include.utilities import IP_Package
from include import shortestPath

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logger.setLevel(logging.INFO)

# using Interface = Host;
Interface = link.Host

link_layer = link.DataLinkLayer()
my_route_table = RouteTable()

# 注意! 下面的两个队列存放对象，而不是二进制数据
# 用来存储网络层需要向上传递的ip包
route_recv_package = queue.Queue(0)
# 用来存储网络层需要发送的ip包
route_send_package = queue.Queue(0)


class TransmitThread(threading.Thread):
    """
    一个转发线程，只做一件事，
    根据路由表，修改需要发送的包中dest_ip中的值，并将包交给链路层
    """
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        """ 从队列中拿到一个包，做适当转换后，交给链路层 """
        while True:
            # 如果队列为空，那就等直到队列中有包
            while route_send_package.qsize() == 0:
                continue
            # 从队列中获得一个包
            #send_package = route_send_package.get()
            #ip_package = IP_Package.bytes_package_to_object(send_package)
            ip_package = route_send_package.get()

            # DEBUG信息
            logger.debug(' this package will be modiflied according to route table !')
            logger.debug(ip_package)

            # 使用成员函数处理IP包，修改其中的dest_ip字段，获得新的IP包
            ret_ip_package = self.ip_package_handler(ip_package)
            if ret_ip_package == None:
                logger.debug('{} is unreachable. \nShow your route table by "show route table"'.format(ip_package.final_ip))
                continue
            # DEBUG信息
            logger.debug(' had modifly !')
            logger.debug(ret_ip_package)

            # 发送IP包
            link_layer.send(ret_ip_package.to_bytes())

    def ip_package_handler(self, ip_pkg : 'IP_Package'):
        """ 
        使用转发表对IP包进行处理
        1. 使用目的ip获得其下一跳ip:dest_ip
        2. 使用其目的ip，获取目的子网掩码
        如果路由表找不到，返回None
        """
        final_ip = ip_pkg.final_ip
        # 从转发表中获得去往该子网需要的下一跳路由和路由所在子网
        dest_ip_net_mask = my_route_table.get_dest_ip(final_ip)
        if dest_ip_net_mask == None:
            return None
        # 修改ip包的下一跳路由
        ip_pkg.dest_ip = dest_ip_net_mask[0]
        ip_pkg.net_mask = dest_ip_net_mask[1]
        return ip_pkg

class MonitorLinkLayer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        """ 监听线程，用于从链路层得到IP包，并确定是转发还是交由网络层上层协议进一步处理 """
        while True:
            recv_data = link_layer.receive()
            if recv_data == None:
                continue
            # 查看该包是否是发给本机的
            ip_package = IP_Package.bytes_package_to_object(recv_data)
            is_local = my_route_table.is_local_link(ip_package.final_ip)
            if is_local:
                # 网络层要了IP包，并交给了更上层的协议
                route_recv_package.put(ip_package)
            else:
                # 网络层修改ip包，要转发
                route_send_package.put(ip_package)

my_transmit_thread = TransmitThread()
my_monitor_link_layer = MonitorLinkLayer()

class NetworkLayer():
    def __init__(self, config):
        # TODO:这里有两种方案，一种是传json字符串，另一种是传文件名，然后就可以在路由器内部进行读取配置文件初始化
        # 从配置文件中初始化各项数据
        self.name = config['name']
        self.index = config['index']

        # 开启转发线程
        my_transmit_thread.start()
        # 开启链路层监听线程，用于从链路层得到包
        my_monitor_link_layer.start()
        # 初始化转发表
        self.init_route_table(config)
        # 初始化网线接口
        self.init_interfaces(config)

        # f = open('matrix_topo.dump', 'rb')
        # graph = pickle.load(f)
        # f.close()

        # logger.debug(graph)
        # self.shortestPath, self.previous_node = shortestPath.SPFA(graph, self.index)
        # logger.debug(self.shortestPath)
        # logger.debug(self.previous_node)
        # logger.debug(self.index2ip)

    def init_route_table(self, config):
        """ 初始化路由表，写入本地链路地址以及直连子网地址 """
        local_link_list = []
        local_direct_link = []
        for intf in config['interfaces']:
            # 得到本地端口地址
            local_link_list.append(intf['vip'])
            # 得到本地连接子网
            local_direct_link.append((utilities.get_subnet(intf['vip'], intf['netmask']), intf['netmask'], intf['counter_vip']))
        # 初始化转发表，在转发表中写入本机ip以及本机相连子网
        my_route_table.init_local_link(local_link_list)
        my_route_table.init_item(local_direct_link)
        my_route_table.show()
    
    def init_interfaces(self, config):
        """ 初始化接口，并启动每一个接口 """
        interfaces = []
        for intf in config['interfaces']:
            new_interface = Interface(
                self.name,
                (intf['vip'], intf['netmask']),
                (intf['pip'], intf['port']),
                (intf['counter_vip'], intf['counter_netmask']),
                (intf['counter_pip'], intf['counter_port'])
            )
            interfaces.append(new_interface)
        link_layer.host_register(interfaces)

    def send(self, src_ip : str,  final_ip : str, ip_package_data : bytes):
        """ 只需要将这个包放到队列中即可，另一个线程负责队列中的包处理并发送出去 """
        # TODO:疑问：网络层的接口，是否需要提供源ip？
        # 我应该到了链路层才知道使用哪一个接口发送呀，才知道接口对应的IP呀！
        # 应用层应该只需要知道目的IP就好了，然后源ip在网络层中获取，子网掩码和目的ip由转发表设置
        # 这里ip包的子网掩码是目的网络的子网掩码，应用层是不知道的
        ip_pkg = IP_Package(src_ip, final_ip, final_ip, 0, ip_package_data)
        route_send_package.put(ip_pkg)

    def recv(self) -> bytes :
        """ 阻塞式接受IP包，该IP包一定是发给自己，需要处理的 """
        while route_recv_package.qsize == 0:
            continue
        return route_recv_package.get()

    def update_route_table(self):
        pass

    def test_send(self, s):
        pkg = IP_Package('8.8.1.2', '8.8.1.3', '8.8.4.2', 24, s.encode('ascii'))
        link_layer.send(pkg.to_bytes())



if __name__ == "__main__":
    """ 这里是测试 """
    config_file = sys.argv[1]
    config = ''
    with open(config_file, 'r') as config_f:
        config = json.load(config_f)
    route = NetworkLayer(config)

    while True:
        s = input("Route {} >".format(route.name))
        print(s)
        if s == 'show ipv4 interface':
            link_layer.show_interface()
        elif s == 'show tcp':
            link_layer.show_tcp()
        else:
            route.test_send(s)