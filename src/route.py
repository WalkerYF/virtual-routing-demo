import socket
import json
import config
import utilities
import threading
from include import rdt_socket
import link
import sys
import logging
import unittest
import pdb

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
        self.interfaces = config['interfaces']
        self.route_table = {}
        for interface in self.interfaces:
            link_layer.host_register(link.Host(
                (interface['vip'], interface['netmask']),
                (interface['pip'],interface['port'])
            ))

        # TODO:读取配置文件，将接口状态写入
        # 此时应该建立连接，获取用于模拟物理连接的socket
        # self.interface
    def route_table_init(self):
        # TODO:使用接口，初始化路由表
        raise NotImplementedError()

    def test_send(self, s):
        logger.info("int test_send")
        link_layer.send(("8.8.1.2", 24), ("8.8.1.3", 24), s.encode('ascii'))
    
if __name__ == "__main__":
    """ 这里是测试 """
    # config_file = sys.argv[1]
    config_f =  open("../test/routeA.json", 'r')
    routeA = Route(config_f)
    config_f =  open("../test/routeE.json", 'r')
    routeE = Route(config_f)

    while True:
        s = input("Route {} >".format(routeA.name))
        routeA.test_send(s)