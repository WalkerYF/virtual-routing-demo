'''controller
a subproblem of this project
how-to-run:
$ python3 controller.py ../test/routeA.json
'''
import sys
import json
import threading
import time

import route
import console
from include import utilities
from include import shortestPath
from include.logger import logger
# 运行目录
ROOT='.'

# 在src文件夹下运行
# CONFIG_ROOT=ROOT+'/../test_controller'

# 在test文件夹下运行
CONFIG_ROOT=ROOT
GLOBAL_ROUTE_INFORMATIOIN_FILE = CONFIG_ROOT+'/all_route.json'

CONFIG_NAME = sys.argv[1]
f = open(CONFIG_NAME, 'rt')
config_data = json.load(f)
f.close()
ROUTER_INDEX = config_data['index']

interface2index = {} # type: Dict[Tuple[str, str], int]
index2interface = {} # type: Dict[int, Tuple[str, str]]

is_controller = config_data['is_controller']

# config_file中的内容是，所有test/route*.json的文件的文件名
f = open(GLOBAL_ROUTE_INFORMATIOIN_FILE, 'rt')
json_files = json.load(f)
f.close()
logger.debug("[controller] read all files\n %s ", format(json_files))

V = len(json_files['filenames'])
# graph 是用于求最短路的邻接矩阵
graph = [[-1 for i in range(V)] for j in range(V)] # type: List[List[int]]
class NetworkLayerListener(threading.Thread):
    def __init__(self, network_layer) -> None:
        threading.Thread.__init__(self)
        self.network_layer = network_layer
    def run(self):
        logger.info('network layer listener begin to work...')
        while True:
            ospf_pkg = self.network_layer.recv_ospf()
            ordinary_pkg = self.network_layer.recv()
            if ospf_pkg is None and ordinary_pkg is None:
                time.sleep(0.01)
                continue
            if ospf_pkg:
                src_ip = ospf_pkg.dest_ip
                dest_ip = ospf_pkg.src_ip
                netmask = ospf_pkg.net_mask
                if ospf_pkg.protocol != 119:
                    logger.error('error! get ospf pkg, protocol is %d instead of 119', ospf_pkg.protocol)
                ospf_msg = utilities.objDecode(ospf_pkg.data)
                logger.info("get ospf msg\n%s", ospf_msg)

                if ospf_msg['code'] == 0:
                    if not is_controller:
                        logger.warn("IM NOT CONTROLLER. get request msg. ignore.")
                        continue
                    src_index = ospf_msg['src_index']
                    init_global_route_table(GLOBAL_ROUTE_INFORMATIOIN_FILE, src_index)
                    sp = calculate_shortest_path(src_index)
                    response_msg = {
                        "code": 1,
                        "msg": "here's your route table",
                        "route_table": sp
                    }
                    response_msg_bytes = utilities.objEncode(response_msg)
                    pkg = route.IP_Package(src_ip, dest_ip, dest_ip, netmask, response_msg_bytes)
                    pkg.protocol = 119
                    errno = route.link_layer.send(pkg.to_bytes())
                    if errno < 0:
                        logger.warning('fail to send to link layer. errno is %d\n', errno)
                elif ospf_msg['code'] == 1:
                    logger.info('get route table response msg\n%s', ospf_msg)
                    route_table = ospf_msg['route_table']
                    for dest_net, netmask, dest_ip in route_table:
                        route.my_route_table.update_item(dest_net, netmask, dest_ip)




            if ordinary_pkg:
                #TODO: refine here
                logger.info("get odinary msg\n%s", ordinary_pkg)


def calculate_shortest_path(src:int):
    ret = []

    dist, prev = shortestPath.SPFA(graph, src)
    logger.debug("[controller] finished run spfa\n dist %s \n prev %s\n", dist, prev)
    logger.debug("[controller, info] interface2index\n%s", interface2index)
    logger.debug("[controller, info] index2interface\n%s", index2interface)

    for ip, netmask in interface2index:
        # 自己的端口不需要作转发
        if interface2index[(ip, netmask)] == src:
            continue
        logger.debug('[controller] dealing with %s, %s', ip, netmask)
        subnet = utilities.get_subnet(ip, netmask)
        index = interface2index[(ip, netmask)]
        prev_index = prev[index]
        if prev_index == -1:
            continue
        if prev_index == src:
            target_index = interface2index[(ip, netmask)]
            (dst_ip, dst_nm) = index2interface[target_index]
            # route.my_route_table.update_item(ip, netmask, dst_ip)
            ret.append((ip, netmask, dst_ip))
            logger.info('[1]add item into response msg\n \
                %s, %s, %s', ip, netmask, dst_ip)
        else:
            try_get = index2interface.get(prev_index)
            while try_get is None:
                prev_index = prev[prev_index]
                try_get = index2interface.get(prev_index)
            prev_ip, prev_netmask = try_get
            # route.my_route_table.update_item(ip, netmask, prev_ip)
            ret.append((ip, netmask, prev_ip))
            logger.info('[2]add item into response msg\n \
                %s, %s, %s', ip, netmask, prev_ip)
    logger.debug("calculation return value\n%s", ret)
    return ret

def init_global_route_table(config_file: str, src : int) -> None:
    """
    用SPFA算法，读取配置文件，更新路由表中的最短路信息
    input:
        config_file: 储存有“所有route配置文件的文件名”文件名
    """
    logger.debug("[spfa] init graph\n %s", format(graph))
    for filename in json_files['filenames']:
        f = open(CONFIG_ROOT + '/' + filename) #TODO:(YB) refactor. let it be path.resolve
        json_data = json.load(f)
        f.close()

        node = json_data['index'] # 当前配置文件/test/route*.json的路由标号
        interfaces = json_data['interfaces']
        for interface in interfaces:
            cvip = interface['counter_vip']
            netmask = interface['netmask']

            # interface2index 记录了所有的interfaces.它是一个从interface到所属路由的映射。
            interface2index[(cvip, netmask)] = interface['counter_index']
            if interface['counter_index'] == src:
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
    
def ask_for_global_table():
    controller_index = config_data['controller_index']
    src_ip = ''
    dst_ip = ''
    netmask = ''
    for interface in config_data['interfaces']:
        if interface['counter_index'] != controller_index:
            continue
        # now counter_index is controller_index
        src_ip = interface['vip']
        dst_ip = interface['counter_vip']
        netmask = interface['netmask']
    logger.debug('going to send route table request msg\n, \
        src_ip %s, dst_ip %s, netmask %s', src_ip, dst_ip, netmask)
    request_msg = {
        "code": 0,
        "msg": "request for route table",
        "src_index": ROUTER_INDEX
    }
    msg_bytes = utilities.objEncode(request_msg)
    pkg = route.IP_Package(src_ip, dst_ip, dst_ip, netmask, msg_bytes)
    pkg.protocol = 119
    errno = route.link_layer.send(pkg.to_bytes())
    if errno < 0:
        logger.warning('fail to send to link layer, errno: %d', errno)
    
def main():
    '''main'''
    # open file

    network_layer = route.NetworkLayer(config_data)

    if is_controller:
        logger.debug("I am controller. not calculate until asked")
        #init_global_route_table(GLOBAL_ROUTE_INFORMATIOIN_FILE)
        
    network_layer_listener = NetworkLayerListener(network_layer)
    network_layer_listener.start()

    if not is_controller:
        logger.debug("begin to ask for global table")
        ask_for_global_table()
    consoler = console.Console(network_layer, route)
    consoler.task()
if __name__ == "__main__":
    main()