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
# logger.setLevel(logging.DEBUG)
logger.setLevel(logging.INFO)

# using Interface = Host;
Interface = link.Host

link_layer = link.DataLinkLayer()
my_route_table = RouteTable()


class TransmitThread(threading.Thread):
    """
    一个监听转发线程，只做两件事，
    1. 根据路由表 转发接收到的包，
    2. 如果不转发的话，就将包往上送往网络层处理
    """
    def __init__(self):
        threading.Thread.__init__(self)
    def run(self):
        """ 监听线程，用于从链路层得到IP包，并确定是转发还是交由网络层进一步处理 """
        while True:
            recv_data = link_layer.receive()
            if recv_data == None:
                continue
            ip_package = IP_Package.bytes_package_to_objdect(recv_data)
            ret = self.ip_package_handler(ip_package)
            if ret == None:
                # 网络层要了IP包，并交给了更上层的协议
                continue
            else:
                # 网络层修改了ip包，要转发
                link_layer.send(ret)

    def ip_package_handler(self, ip_pkg : 'IP_Package'):
        """ 处理一个IP包，如果由网络层接受，则返回None，否则返回一个新的IP包(bytes)用于转发 """
        logger.info('receive!!')
        logger.info(ip_pkg)
        is_local = my_route_table.is_local_link(ip_pkg.final_ip)
        if is_local:
            logger.info('I receive a package which is sent to me!')
            logger.info(ip_pkg)
            return None
        else:
            # 修改IP包，进行转发
            dest_net = utilities.get_subnet(ip_pkg.final_ip, ip_pkg.net_mask)
            next_ip = my_route_table.get_dest_ip(dest_net, ip_pkg.net_mask)
            ip_pkg.dest_ip = next_ip
            logger.info('I should transmit this package')
            logger.info(ip_pkg)
            return ip_pkg.to_bytes()

my_transmit_thread = TransmitThread()

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
        local_link_list = []
        local_direct_link = []
        for intf in config['interfaces']:
            new_interface = Interface(
                self.name,
                (intf['vip'], intf['netmask']),
                (intf['pip'], intf['port']),
                (intf['counter_vip'], intf['counter_netmask']),
                (intf['counter_pip'], intf['counter_port'])
            )
            self.interfaces.append(new_interface)
            # 初始化本地链路
            local_link_list.append((intf['vip'], 32))
            local_direct_link.append((utilities.get_subnet(intf['vip'], intf['netmask']), intf['netmask'], intf['counter_vip']))
            # TODO:在配置文件里面找不到'counter_index'一项
            # self.index2ip[intf['counter_index']] = intf['counter_ip']
            # TODO:下面这一句我认为应该放在循环外，因为host_register接的是list
            # link_layer.host_register(new_interface) # host and interface are just two names for the same thing
        logger.debug(self.interfaces)
        
        # 初始化转发表，在转发表中写入本机ip以及本机相连子网
        my_route_table.init_local_link(local_link_list)
        my_route_table.init_item(local_direct_link)
        my_route_table.show()

        # 在注册后，每一个接口都保证有对应的socket
        # TODO:由于注册那一块尝试连接的过程开了新的线程，会出现，还没有全部注册完，就开始往下执行的情况
        # TODO:具体的修改方式是：HostManager的connent_all函数不应该在新的线程中运行，在主线程中运行即可，等到物理链路联通了在进行下面的工作
        link_layer.host_register(self.interfaces)

        # 开启监听线程，用于转发包
        my_transmit_thread.start()

        f = open('matrix_topo.dump', 'rb')
        graph = pickle.load(f)
        f.close()

        logger.debug(graph)
        self.shortestPath, self.previous_node = shortestPath.SPFA(graph, self.index)
        logger.debug(self.shortestPath)
        logger.debug(self.previous_node)
        logger.debug(self.index2ip)


            # #TODO: 判断是自己要了还是发给别人
            # #TODO: 
            # #FIXME: error
            # send_ip_package = IP_Package(
            #     src_ip,
            #     dst_ip,# TODO: dst ip here, start here
            #     final_dst_ip,
            #     netmask,
            #     body_data
            # )
            # link_layer.send(send_ip_package.to_bytes())



    def route_table_init(self):
        # TODO:使用接口，初始化路由表
        raise NotImplementedError()

    def test_send(self, s):
        pkg = IP_Package('8.8.1.2', '8.8.1.3', '8.8.4.2', 24, s.encode('ascii'))
        link_layer.send(pkg.to_bytes())



if __name__ == "__main__":
    """ 这里是测试 """
    config_file = sys.argv[1]
    config_f =  open(config_file, 'r')
    route = Route(config_f)

    while True:
        s = input("Route {} >".format(route.name))
        print(s)
        if s == 'show ipv4 interface':
            link_layer.show()
        elif s == 'show tcp':
            link_layer.show_tcp()
        else:
            route.test_send(s)