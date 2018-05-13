import route
import json
import sys
from include.utilities import IP_Package
from include import utilities
import threading
import logging
import time
from include import shortestPath
from typing import Dict, List, Tuple
import console
GLOBAL_ROUTE_INFORMATION_FILE = '../test/all_route.json'
config_name = sys.argv[1]
with open(config_name, 'r') as config_f:
    config = json.load(config_f)

ROUTER_INDEX = config['index']
logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

interface2index = {} # type: Dict[Tuple[str, str], int]
index2interface = {} # type: Dict[int, Tuple[str, str]]
# 初始化网络层

# 添加路由表项
# route.my_route_table.update_item('8.8.4.0', 24, '8.8.1.3')
class NetworkLayerListener(threading.Thread):
    """
    非阻塞地询问网络层是否有数据到达。若有，则向终端输出数据
    """
    def __init__(self, network_layer) -> None:
        threading.Thread.__init__(self)
        self.network_layer = network_layer
    def run(self) -> None:
        logger.debug('network layer listerner begin to work')
        while True:
            recv = self.network_layer.recv()
            if recv:
                logger.info('network layer pkg received\n{}'.format(recv))
            time.sleep(0.1)

def init_global_route_table(network_layer, config_file: str) -> None:
    """
    用SPFA算法，读取配置文件，更新路由表中的最短路信息
    input:
        network_layer: unused. why???
        config_file: 储存有“所有route配置文件的文件名”文件名
    """
    # config_file中的内容是，所有test/route*.json的文件的文件名
    f = open(config_file, 'rt')
    json_files = json.load(f)
    f.close()
    logger.debug("[spfa] read all files\n %s ", format(json_files))

    V = len(json_files['filenames'])
    # graph 是用于求最短路的邻接矩阵
    graph = [[-1 for i in range(V)] for j in range(V)] # type: List[List[int]]
    logger.debug("[spfa] init graph\n %s", format(graph))
    for filename in json_files['filenames']:
        f = open('../test/' + filename) #TODO:(YB) refactor. let it be path.resolve
        json_data = json.load(f)
        f.close()

        node = json_data['index'] # 当前配置文件/test/route*.json的路由标号
        interfaces = json_data['interfaces']
        for interface in interfaces:
            cvip = interface['counter_vip']
            netmask = interface['netmask']

            # interface2index 记录了所有的interfaces.它是一个从interface到所属路由的映射。
            interface2index[(cvip, netmask)] = interface['counter_index']
            if interface['counter_index'] == ROUTER_INDEX:
                # index2interface， 
                # idx -> intf
                # 记录了，站在本路由的角度，到达idx这个路由，需要通过的intf是什么
                index2interface[node] = (interface['vip'], interface['netmask'])

            inf_node = interface['counter_index']
            weight = 1
            try:
                weight = interface['weight']
            except KeyError:
                logger.warning('no weight info in %s, %s defaut to 1', filename, interface)
            graph[node][inf_node] = weight
    logger.debug("[spfa] finished loading neighbour info into graph\n %s", format(graph))
    dist, prev = shortestPath.SPFA(graph, ROUTER_INDEX)
    logger.debug("[spfa] finished run spfa\n dist %s \n prev %s\n", dist, prev)
    logger.debug("[spfa, info] interface2index\n%s", interface2index)
    logger.debug("[spfa, info] index2interface\n%s", index2interface)

    for ip, netmask in interface2index:
        # 自己的端口不需要作转发
        if interface2index[(ip, netmask)] == ROUTER_INDEX:
            continue
        logger.debug('[spfa] dealing with %s, %s', ip, netmask)
        subnet = utilities.get_subnet(ip, netmask)
        index = interface2index[(ip, netmask)]
        prev_index = prev[index]
        if prev_index == -1:
            continue
        if prev_index == ROUTER_INDEX:
            target_index = interface2index[(ip, netmask)]
            (dst_ip, dst_nm) = index2interface[target_index]
            route.my_route_table.update_item(ip, netmask, dst_ip)
            logger.info('[1]add item into route table\n \
                %s, %s, %s', ip, netmask, dst_ip)
        else:
            prev_ip, prev_netmask = index2interface[prev_index]
            route.my_route_table.update_item(ip, netmask, prev_ip)
            logger.info('[2]add item into route table\n \
                %s, %s, %s', ip, netmask, prev_ip)




if __name__ == "__main__":
    network_layer = route.NetworkLayer(config)
    network_layer_listener = NetworkLayerListener(network_layer)
    network_layer_listener.start()
    init_global_route_table(network_layer, GLOBAL_ROUTE_INFORMATION_FILE)

    console = console.Console(network_layer, route)
    console.task()
