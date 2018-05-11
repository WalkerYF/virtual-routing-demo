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
import pickle
from include.utilities import IP_Package
from include import shortestPath

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# using Interface = Host;
Interface = link.Host

link_layer = link.DataLinkLayer()

class Route():
    def __init__(self, config_file):
        config = json.load(config_file)
        self.name = config['name']
        self.interfaces = []
        for intf in config['interfaces']:
            self.interfaces.append(
                Interface(
                self.name,
                (intf['vip'], intf['netmask']),
                (intf['pip'], intf['port']),
                (intf['counter_vip'], intf['counter_netmask']),
                (intf['counter_pip'], intf['counter_port'])
                )
            )
        logger.debug(self.interfaces)
        self.index = config['index']
        self.route_table = {}
        link_layer.host_register(self.interfaces)

        f = open('matrix_topo.dump', 'rb')
        graph = pickle.load(f)
        f.close()

        logger.debug(graph)
        self.shortestPath, self.previous_node = shortestPath.SPFA(graph, self.index)
        logger.debug(self.shortestPath)
        logger.debug(self.previous_node)

        # TODO:读取配置文件，将接口状态写入
        # 此时应该建立连接，获取用于模拟物理连接的socket
        # self.interface
    def route_table_init(self):
        # TODO:使用接口，初始化路由表
        raise NotImplementedError()

    def test_send(self, s):
        pkg = IP_Package('8.8.1.2', '8.8.1.3', 24, s.encode('ascii'))
        link_layer.send(pkg.to_bytes())
    
if __name__ == "__main__":
    """ 这里是测试 """
    config_file = sys.argv[1]
    config_f =  open(config_file, 'r')
    route = Route(config_f)

    while True:
        s = input("Route {} >".format(route.name))
        route.test_send(s)