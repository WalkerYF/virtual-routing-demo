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
        # TODO:这里传进来的是一个已打开的文件对象，并不好，我认为修改为一个json字符串更合适
        config = json.load(config_file)
        # 从配置文件中初始化各项数据
        self.name = config['name']
        self.index = config['index']
        # 用来存储该路由器上已连接网线的接口
        self.interfaces = []
        # 使用路由器的index，得到对应的ip
        self.index2ip = {}
        for intf in config['interfaces']:
            new_interface = Interface(
                self.name,
                (intf['vip'], intf['netmask']),
                (intf['pip'], intf['port']),
                (intf['counter_vip'], intf['counter_netmask']),
                (intf['counter_pip'], intf['counter_port'])
            )
            self.interfaces.append(new_interface)
            # TODO:下面这一句我认为应该放在循环外，因为host_register接的是list
            link_layer.host_register(new_interface) # host and interface are just two names for the same thing
            # TODO:在配置文件里面找不到'counter_index'一项
            self.index2ip[intf['counter_index']] = intf['counter_ip']
        logger.debug(self.interfaces)
        
        self.route_table = {}
        link_layer.host_register(self.interfaces)

        f = open('matrix_topo.dump', 'rb')
        graph = pickle.load(f)
        f.close()

        logger.debug(graph)
        self.shortestPath, self.previous_node = shortestPath.SPFA(graph, self.index)
        logger.debug(self.shortestPath)
        logger.debug(self.previous_node)
        logger.debug(self.index2ip)

        while True:
            recv_data = link_layer.receive()
            if recv_data == None:
                continue
            ip_package = IP_Package.bytes_package_to_objdect(recv_data)
            src_ip = ip_package.src_ip
            dst_ip = ip_package.dest_ip
            netmask = ip_package.net_mask
            final_dst_ip = ip_package.final_ip
            body_data = ip_package.data
            #TODO: 判断是自己要了还是发给别人
            #TODO: 
            #FIXME: error
            send_ip_package = IP_Package(
                src_ip,
                dst_ip,# TODO: dst ip here, start here
                final_dst_ip,
                netmask,
                body_data
            )
            link_layer.send(send_ip_package.to_bytes())



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