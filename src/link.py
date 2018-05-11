import socket
import json
import config
import threading
import logging
from include import rdt_socket
from include.utilities import get_subnet
logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
class Host(threading.Thread):
    def __init__(self, name, vip_netmask, pip_port, counter_vip_netmask, counter_pip_port):
        threading.Thread.__init__(self)
        if not type(vip_netmask) is tuple or len(vip_netmask) != 2:
            raise ValueError('vip_netmask should be a tuple and length 2')
        if not type(pip_port) is tuple or len(pip_port) != 2:
            raise ValueError('pip_port should be a tuple and length 2')
        self.name = name
        self.vip, self.netmask = vip_netmask
        self.counter_vip, self.counter_netmask = counter_vip_netmask
        self.pip_port = pip_port
        self.counter_pip_port = counter_pip_port
        # server socket 是这个Interface 监听的socket
        self.server_socket = None
        # counter socket 是用来给网线那一头的Interface发送消息的socket
        self.counter_socket = None
        # 初始Interface的状态时down的
        self.status = "down"
    
    def run(self):
        """ 启动一个新的线程，监听一个端口 """
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(self.pip_port)
        self.server_socket.listen(config.MAX_TCP_LINK)
        # 等待网线那一头，直连的Interface与我建立连接
        (client_socket, address) = self.server_socket.accept()
        # 等待网线那一头的Interface给我发消息
        rdt_s = rdt_socket.rdt_socket(client_socket)
        while True:
            data = rdt_s.recvBytes()
            s = str(data)
            logger.debug("Route {} recv {}".format(self.vip, s))
            #TODO: not finished

    def getSubnetPrefix(self):
        return get_subnet(self.vip, self.netmask)
class Subnet():
    """ FIXME:子网内的主机列表，多台路由器之间内存级共享，需要改 """
    def __init__(self, prefix):
        self.prefix = prefix
        self.hosts = [] #子网由(2个)主机组成
        
class HostManager(threading.Thread):
    def __init__(self, hosts, subnets):
        threading.Thread.__init__(self)
        self.hosts = hosts
        self.subnets = subnets
        for host in self.hosts:
            subnet_prefix = Host.getSubnetPrefix(host)
            new_subnet = Subnet(subnet_prefix)
            # 新的子网中加入这台主机
            new_subnet.hosts.append(host)
            # 链路层子网列表中加入这个子网
            self.subnets.append(new_subnet)
            # 这台主机（该子网第一台主机）的监听线程开始工作
            host.start() 
            logger.debug("Interface %s listening", host.vip)
        self.connected_cnt = 0
    
    def run(self):
        logger.debug("Trying to connect all counterpart interface")
        self.connect_all()

    def connect_all(self):
        # TODO O(n^2)
        while len(self.hosts) != self.connected_cnt:
            for host in self.hosts:
                # is_connected = False
                # for subnet in self.subnets:
                #     if subnet.prefix == Host.getSubnetPrefix(host):
                #         is_connected = True
                #         break
                if host.status == "down":
                    ret = self.try_connect(host)
                    # logger.debug("Trying connect %s -> %s", host.vip, host.counter_vip)
                    if ret == 0: #TODO macro for SUCCESS ?
                        self.connected_cnt = self.connected_cnt + 1
                        logger.debug("Interface %s is on, connected to %s", host.vip, host.counter_vip)
                        host.status = "on"

    def try_connect(self, host):
        counter_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            counter_socket.connect(host.counter_pip_port)
            host.counter_socket = counter_socket
            return 0
        except Exception:
            return -1
        

class DataLinkLayer():
    """
    模拟链路层，两个Interface之间用网线/八爪线直连的场景
    """
    def __init__(self):
        self.num_interface = 0
        self.subnets = []  #存储所有子网

    def host_register(self, hosts):
        self.host_manager = HostManager(hosts, self.subnets)
        self.host_manager.start()


    # def host_register(self, host):
        # """ 被网络层调用"""
        # # 根据host的vip和netmask，能够确定它的子网编号
        # subnet_prefix = Host.getSubnetPrefix(host) #TODO: 根据vip和netmask判断子网编号
        # # 如果这个子网现在不存在, 说明这是该子网第一台主机，因此新建这个子网
        # print(self.subnets)
        # if not subnet_prefix in [i.prefix for i in self.subnets]: 
        #     new_subnet = Subnet(subnet_prefix)
        #     # 新的子网中加入这台主机
        #     new_subnet.hosts.append(host)
        #     # 链路层子网列表中加入这个子网
        #     self.subnets.append(new_subnet)
        #     # 这台主机（该子网第一台主机）的监听线程开始工作
        #     host.start()
        #     logger.debug("New subnet {} created, {} is in it".format(subnet_prefix, host.vip))
        # else: # 这台主机应该加入的子网已经存在
        #     # 遍历所有子网
        #     for subnet in self.subnets:
        #         # 找到它应该加入的子网
        #         if subnet.prefix == subnet_prefix:
        #             # 加入该子网
        #             subnet.hosts.append(host)
        #             # 主机的监听线程开始工作
        #             host.start()
        #             # 这时候这个子网应该有两台主机了，让它们各自获得一个向对方发送信息的socket
        #             logger.debug("{} joined subnet {}".format(host.vip, subnet_prefix))
        #             for idx, _host in enumerate(subnet.hosts):
        #                 _host.counter_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #                 # 注意：该语句依赖于一个子网里只有两台主机
        #                 _host.counter_socket.connect(subnet.hosts[1 - idx].pip_port)

    def send(self, src, dest, ip_pkg):
        """
        实现假设：
            1. src这一台host自带的socket能够直接发送到dest
            2. 两台host在同一个子网内
        作用：
            1. 将ip_pkg从src这个host发送到dest这个host
        注意：
            1. dest这个参数似乎没用上
        """
        ip1, nm1 = src
        _, nm2 = dest
        if nm1 != nm2:
            logger.error('{} and {} not in same subnet'.format(str(nm1), str(nm2)))
            raise Exception("{} and {} not in same subnet".format(nm1, nm2))
        subnet_prefix = get_subnet(ip1, nm1)
        for subnet in self.subnets:
            if subnet.prefix == subnet_prefix:
                for host in subnet.hosts:
                    if host.vip == src[0] and host.netmask == src[1]:
                        rsock = rdt_socket.rdt_socket(host.counter_socket)
                        rsock.sendBytes(ip_pkg)
                        

# using Interface = Host;
Interface = Host


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
    
if __name__ == "__main__":
    """ 这里是测试 """
    