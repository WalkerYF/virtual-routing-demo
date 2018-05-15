'''controller
a subproblem of this project
how-to-run:
$ python3 controller.py ../test/routeA.json
'''
import sys
import json
import threading
import logging
import time

import route
import console
from include import utilities
from include import shortestPath
# 运行目录
ROOT='.'

# 在src文件夹下运行
# CONFIG_ROOT=ROOT+'/../test_controller'

# 在test文件夹下运行
CONFIG_ROOT=ROOT
GLOBAL_ROUTE_INFORMATIOIN_FILE = CONFIG_ROOT+'/all_route.json'
logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

CONFIG_NAME = sys.argv[1]
f = open(CONFIG_NAME, 'rt')
config_data = json.load(f)
f.close()
ROUTER_INDEX = config_data['index']

interface2index = {} # type: Dict[Tuple[str, str], int]
index2interface = {} # type: Dict[int, Tuple[str, str]]

# config_file中的内容是，所有test/route*.json的文件的文件名
f = open(GLOBAL_ROUTE_INFORMATIOIN_FILE, 'rt')
json_files = json.load(f)
f.close()
logger.debug("[controller] read all files\n %s ", format(json_files))

V = len(json_files['filenames'])
# graph 是用于求最短路的邻接矩阵
graph = [[-1 for i in range(V)] for j in range(V)] # type: List[List[int]]

class TrackingNeighbourAlive(threading.Thread):
    def __init__(self, network_layer, interfaces) -> None:
        threading.Thread.__init__(self)
        self.network_layer = network_layer
        self.interfaces = []
        for interface in interfaces:
            self.interfaces.append((interface.vip, interface.counter_vip))
        self.dead_interfaces = []
        self.track = {}
        for interface in self.interfaces:
            self.track[interface] = 0

        self.tracking_direct_router_neighbour = TrackingDirectRouterNeighbour(self.network_layer)
    def wakeup(self, sip, dip):
        # logger.info('wake up sip %s, dip %s', sip, dip)
        self.track[(sip, dip)] = 1
        try:
            self.dead_interfaces.remove((sip,dip))
        except Exception:
            pass
    def run(self):
        while True:
            time.sleep(10)
            self.tracking_direct_router_neighbour.run_ping()
            time.sleep(5)
            #logger.debug('-----------------tracking is alive running-----------------')
            for interface in self.track:
                #logger.debug('--------------interface----------\n%s', interface)
                if self.track[interface] == 0:
                    cvip = interface[1]
                    logger.info('######## ip %s logout! #########', cvip)
                    if interface not in self.dead_interfaces:
                        self.dead_interfaces.append(interface)
                    # self.track.remove(interface)
                else:
                    self.track[interface] = 0
            for interface in self.dead_interfaces:
                ip = interface[1]
                logger.info('[logout] logout ip is %s', ip)

        
class TrackingDirectRouterNeighbour():
    def __init__(self, network_layer) -> None:
        self.network_layer = network_layer
    def run_ping(self):
        logger.info("tracking direct router neighbor threading run...")
        for interface in self.network_layer.interfaces:
            src_ip = interface.vip 
            dst_ip = interface.counter_vip
            netmask = interface.netmask
            msg = {
                'code': 0,
                'msg': "are you still here?"
            }
            self.network_layer.send(src_ip, dst_ip, utilities.objEncode(msg), 100)
            logger.debug('send ping from %s to %s', src_ip, dst_ip)


class NetworkLayerListener(threading.Thread):
    def __init__(self, network_layer) -> None:
        threading.Thread.__init__(self)
        self.network_layer = network_layer
        self.tracking_neighbour_alive = TrackingNeighbourAlive(network_layer, network_layer.interfaces)
        self.tracking_neighbour_alive.start()
    def run(self):
        logger.info('network layer listener begin to work...')
        while True:
            self.task()
    def task(self):
        time.sleep(0.1)
        msg_queue = []
        msg_queue.append(self.network_layer.recv_ospf())
        msg_queue.append(self.network_layer.recv())
        msg_queue.append(self.network_layer.recv_ping())

        available_msg = [msg for msg in msg_queue if not msg is None]
        for msg in available_msg:
            if msg.protocol == 100:
                data = utilities.objDecode(msg.data)
                sip = msg.src_ip
                dip = msg.dest_ip
                netmask = msg.net_mask
                if data['code'] == 0:
                    # get ping request from other
                    logger.info('get ping from %s\n', sip)
                    msg = {
                        'code': 1,
                        'msg': 'I am here.'
                    }
                    self.network_layer.send(dip, sip, utilities.objEncode(msg), 100)
                if data['code'] == 1:
                    # get ping response from it
                    logger.info('ping response. I know %s reachable', sip)
                    self.tracking_neighbour_alive.wakeup(dip, sip)
            else:
                logger.debug('recv msg!!\n%s', msg)
                    
                




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

def init_shortest_path_prerequisite(src : int) -> None:
    """
    用SPFA算法，读取配置文件，更新路由表中的最短路信息
    input:
    """
    logger.debug("[ospf.spfa] init graph\n %s", format(graph))
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
    
def init_route_table():
    init_shortest_path_prerequisite(ROUTER_INDEX)
    ret = calculate_shortest_path(ROUTER_INDEX)
    for dest_net, netmask, dest_ip in ret:
        route.my_route_table.update_item(dest_net, netmask, dest_ip)
    logger.debug("finish init route table.")
def main():
    '''main'''
    network_layer = route.NetworkLayer(config_data)

    network_layer_listener = NetworkLayerListener(network_layer)
    network_layer_listener.start()

    init_route_table()

    consoler = console.Console(network_layer, route)
    consoler.task()
if __name__ == "__main__":
    main()