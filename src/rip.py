import os
import traceback
import route
import threading
import logging
import json
import datetime
import time
import sys
import hashlib
import include.utilities as utilities
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter

logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DV_INF = -1

class RIP(threading.Thread):
    def __init__(self, route_name, interfaces):
        """
        从配置文件读取和直连的Interfaces间的距离
        """
        threading.Thread.__init__(self)
        self.route_name = route_name
        self.interfaces = interfaces
        self.dis_vec = {
            intf.counter_name :
                {
                "cost": intf.link_cost,
                "path": [route_name]
                }
            for intf in interfaces}
        #已知的网络拓扑
        self.topo = {route_name: [(inf.vip, inf.netmask) for inf in interfaces]}
        self.direct_routes = [intf.counter_name for intf in interfaces]
        self.next_hop = {intf.counter_name: intf.vip for intf in interfaces}
        self.received_set = set()

    def run(self):
        logger.debug("rip protocol is working")
        while True:
            logger.debug("[RIP] Broadcasting RIP msg")
            self.broadcast(self.interfaces)
            time.sleep(10)

    def broadcast(self, interfaces):
        md5 = hashlib.md5()
        md5.update((self.route_name + str(time.time())).encode('utf-8'))
        rip_msg = {
            "from" : self.route_name,
            # "intfs": [(inf.vip, inf.netmask) for inf in interfaces],
            "topo": self.topo,
            "md5" : md5.hexdigest(),
            "dv": self.dis_vec
        }
        s = utilities.objEncode(rip_msg)
        for inf in interfaces:
            pkg = route.IP_Package(inf.vip, inf.counter_vip, inf.counter_vip, 24, s)
            pkg.protocol = 120
            route.link_layer.send(pkg.to_bytes())

    def process(self, rip_msg : dict):
        medium = rip_msg['from']
        logger.debug("[RIP] received rip package from %s", medium)
        for dest, intfs in rip_msg['topo'].items():
            if dest not in self.topo:
                self.topo[dest] = intfs
                logger.info("[RIP] learned topo of {} : {}".format(dest, intfs))
                if dest in self.direct_routes:
                    for vip, netmask in intfs:
                        logger.info("[RIP] Updating route table\n{} {} THROUTH {}".format(vip, netmask, self.next_hop[dest]))
                        route.my_route_table.update_item(vip, netmask, self.next_hop[dest])
        # if medium not in self.topo.keys():
        #     self.topo[medium] = rip_msg['intfs']
        if rip_msg['md5'] in self.received_set:
            logger.info("[RIP] droped, already received")
            pass
        elif medium not in self.dis_vec.keys():
                logger.critical("Unexpected rip msg from %s", rip_msg['from'])
                self.received_set.add(rip_msg['md5'])
        else:
            msg_used = True
            for dest, detail in rip_msg['dv'].items():
                if not dest in self.topo.keys():
                    msg_used = False
                    continue
                cost = detail['cost']
                newcost = self.dis_vec[medium]['cost'] + cost
                if dest == self.route_name:
                    pass
                elif dest not in self.dis_vec:
                    self.dis_vec[dest] = \
                        {
                            "cost": newcost,
                            "path": [medium, dest]
                        }
                    logger.info("[RIP] New shortest path found\n{} -> {} cost {}, path: {}".format(
                        self.route_name, dest, self.dis_vec[dest]['cost'], self.dis_vec[dest]['path']))
                    for vip, netmask in self.topo[dest]:
                        logger.info("[RIP] Updating route table\n{} {} THROUTH {}".format(vip, netmask, self.next_hop[medium]))
                        route.my_route_table.update_item(vip, netmask, self.next_hop[medium])
                else:
                    if newcost < self.dis_vec[dest]['cost']:
                        self.dis_vec[dest]['cost'] = newcost
                        self.dis_vec[dest]['path'] = detail['path'].insert(0, medium)
                        logger.info("[RIP] New shortest path found\n{} -> {} cost {}, path: {}".format(
                            self.route_name, dest, self.dis_vec[dest]['cost'], self.dis_vec[dest]['path']))
                        for vip, netmask in self.topo[dest]:
                            logger.info("[RIP] Updating route table\n{} {} THROUTH {}".format(vip, netmask, self.next_hop[medium]))
                            route.my_route_table.update_item(vip, netmask, self.next_hop[medium])
            if msg_used:
                self.received_set.add(rip_msg['md5'])


class NetworkLayerListener(threading.Thread):
    """
    非阻塞地询问网络层是否有数据到达。若有，则向终端输出数据
    """
    def __init__(self) -> None:
        threading.Thread.__init__(self)
    def run(self) -> None:
        logger.debug('network layer listener begin to work')
        while True:
            pkg = network_layer.recv()
            if pkg is None:
                time.sleep(0.01)
                continue
            if(pkg.protocol == 120):
                rip_msg = utilities.objDecode(pkg.data)
                rip_worker.process(rip_msg)
            else:
                route.route_recv_package.put(pkg)

if __name__ == "__main__":

    config_name = sys.argv[1]
    with open(config_name, 'r') as config_f:
        config = json.load(config_f)
    # 初始化网络层
    network_layer = route.NetworkLayer(config)
    network_layer_listener = NetworkLayerListener()
    network_layer_listener.start()
    rip_worker = RIP(network_layer.name, network_layer.interfaces)
    rip_worker.start()

    Completer = WordCompleter(['show help', 'show tcp', 'show interface', 'show route', 'add', 'send', 'recv'],
                              ignore_case=True)
    help_menu = [
        'show help\n\t: show the help message',
        'show tcp\n\t: show lower level tcp socket information',
        'show interface\n\t: show simulation interface status',
        'show route\n\t: show the route table',
        'send src_ip dest_ip data \n\t: send the data to a route\n\texample : send 8.8.1.1 8.8.4.2 teste!',
        'add dest_net net_mask final_ip \n\t: add an item in route table \n\texample : add 8.8.3.0 24 8.8.1.3 \n\tIt means that "to the net(8.8.3.0/24) via 8.8.4.2"',
        'delete dest_net net_mask\n\t: delete an item in route table \n\texample : delete 8.8.3.0 24"',
        'recv\n\t: no arguments',
    ]
    while True:
        user_input = prompt('Route {}>'.format(network_layer.name),
                            history=FileHistory('history.txt'),
                            auto_suggest=AutoSuggestFromHistory(),
                            completer=Completer,
                            )
        try:
            if user_input == '':
                continue
            # 拆分用户参数
            user_args = user_input.split()
            main_action = user_args[0]

            # 解析参数
            if main_action == 'show':
                if user_args[1] == 'interface':
                    route.link_layer.show_interface()
                elif user_args[1] == 'tcp':
                    route.link_layer.show_tcp()
                elif user_args[1] == 'route':
                    route.my_route_table.show()
                elif user_args[1] == 'help':
                    print('This is help message!')
                    for help_msg in help_menu:
                        print('-'*40)
                        print(help_msg)
            elif main_action == 'add':
                # 往路由表中增加表项
                route.my_route_table.update_item(user_args[1], int(user_args[2]), user_args[3])
            elif main_action == 'delete':
                # 删除某一项
                route.my_route_table.delete_item(user_args[1], int(user_args[2]))
            elif main_action == 'send':
                # 发送信息
                network_layer.send(user_args[1], user_args[2], user_args[3].encode('ascii'))
            elif main_action == 'recv':
                # 非阻塞接受IP包
                ip_pkg = network_layer.recv()
                if ip_pkg == None:
                    print('no receive!')
                else:
                    print(ip_pkg)
            elif main_action == 'q':
                os._exit(0)
        except IndexError:
            print('invalid command!')
            continue
        except Exception as e:
            # 捕获所有异常，并且打印错误信息
            print(traceback.format_exc())
            continue

