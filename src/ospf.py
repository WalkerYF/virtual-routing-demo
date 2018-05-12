import route
import json
import sys
from include.utilities import IP_Package
import threading
import logging
import time

config_name = sys.argv[1]
with open(config_name, 'r') as config_f:
    config = json.load(config_f)

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 初始化网络层
network_layer = route.NetworkLayer(config)

# 添加路由表项
# route.my_route_table.update_item('8.8.4.0', 24, '8.8.1.3')
class NetworkLayerListener(threading.Thread):
    """
    非阻塞地询问网络层是否有数据到达。若有，则向终端输出数据
    """
    def __init__(self) -> None:
        threading.Thread.__init__(self)
    def run(self) -> None:
        logger.debug('network layer listerner begin to work')
        while True:
            recv = network_layer.recv()
            logger.info('network layer pkg received\n{}'.format(recv))
            time.sleep(0.1)
while True:
    time.sleep(0.1)
    network_layer_listener = NetworkLayerListener()
    network_layer_listener.start()
    s = input('Route {} > '.format(network_layer.name))
    print(s)
    if s == 'show interface':
        route.link_layer.show_interface()
    elif s == 'show tcp':
        route.link_layer.show_tcp()
    elif s == 'show route table':
        route.my_route_table.show()
    elif s == 'add':
        dest_net = input('dest_net : ')
        net_mask = input('net_mask : ')
        next_ip = input('next_ip : ')
        route.my_route_table.update_item(dest_net, int(net_mask), next_ip)
    elif s == 'send':
        src_ip = input('src_ip : ')
        final_ip = input('final_ip :')
        data = input('data : ')
        network_layer.send(src_ip,final_ip,data.encode('ascii'))
    elif s == 'test add':
        route.my_route_table.update_item('8.8.4.0',24,'8.8.1.3')
    elif s == 'test send':
        network_layer.send('8.8.1.2', '8.8.4.2', b'testtest!!!!')
    else:
        continue        
