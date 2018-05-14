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
from prettytable import PrettyTable

logging.addLevelName( logging.WARNING, "\033[1;31m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
logging.addLevelName( logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))
logging.basicConfig(
    # filename='../../log/client.{}.log'.format(__name__),
    format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
    # datefmt='%M:%S',
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

DV_INF = int(1E9)

class RIP(threading.Thread):
    def __init__(self, route_name, interfaces):
        """
        从配置文件读取和直连的Interfaces间的距离
        """
        threading.Thread.__init__(self)
        self.route_name = route_name
        self.interfaces = interfaces
        self.tear_down = []
        self.dis_vec = {
            intf.counter_name :
                {
                "cost": intf.link_cost,
                "path": [intf.counter_name]
                }
            for intf in interfaces}
        #已知的网络拓扑
        self.topo = {route_name: [(inf.vip, inf.netmask) for inf in interfaces]}
        self.direct_routes = [intf.counter_name for intf in interfaces]
        self.next_hop = {intf.counter_name: intf.counter_vip for intf in interfaces}
        self.received_set = set()
        self.working_flag = True

    def run(self):
        logger.debug("rip protocol is working")
        while True:
            logger.debug("[RIP] Broadcasting RIP msg")
            self.broadcast(self.interfaces)
            time.sleep(2)

    def broadcast(self, interfaces):
        md5 = hashlib.md5()
        md5.update((self.route_name + str(time.time())).encode('utf-8'))
        rip_msg = {
            "from" : self.route_name,
            # "intfs": [(inf.vip, inf.netmask) for inf in interfaces],
            "topo": self.topo,
            "md5" : md5.hexdigest(),
            'tear_down': self.tear_down,
            "dv": self.dis_vec

        }
        s = utilities.objEncode(rip_msg)
        for inf in interfaces:
            pkg = route.IP_Package(inf.vip, inf.counter_vip, inf.counter_vip, 24, s)
            pkg.protocol = 120
            route.link_layer.send(pkg.to_bytes())

    def process(self, rip_msg : dict):
        medium = rip_msg['from']
        # 阻止含有之前已经处理过的离线的路由器的信息的rip报文
        if medium in self.tear_down:
            return
        
        for rname, detail in rip_msg['dv'].items():
            for drname in self.tear_down:
                if drname in detail['path']:
                    logger.debug("[RIP] [Dropped] DV of %s contain offline route %s", medium, drname)
                    return

        for rname in rip_msg['topo'].keys():
            if rname in self.tear_down:
                logger.debug("[RIP] [Dropped] TOPO of %s contain offline route %s", medium, drname)
                return

        logger.debug("[RIP] received rip package from %s", medium)
        new_tear_down = set(rip_msg['tear_down']) - set(self.tear_down)
        self.tear_down = list(set().union(self.tear_down, rip_msg['tear_down']))

        # 删除自身所有有关已经离线了的路由器的信息
        # 删除距离向量中的这一行
        if len(new_tear_down) != 0:
            to_del = []
            for drname in new_tear_down:
                if drname in self.dis_vec.keys():
                    to_del.append(drname)
            for drname in to_del:
                del self.dis_vec[drname]

            # 删除距离向量中所有途径offline路由器的
            to_del = []
            for drname in new_tear_down:
                for rname, detail in self.dis_vec.items():
                    if drname in detail['path']:
                        to_del.append(rname)
            for rname in to_del:
                del self.dis_vec[rname]


            for drname in new_tear_down:
                # 删除路由表中有关的
                for vip, nm in self.topo[drname]:
                    route.my_route_table.delete_item(vip, nm)
                    route.my_route_table.delete_item(utilities.get_subnet(vip, nm), nm)
                # 网络层端口中将其设为offline
                for intf in network_layer.interfaces:
                    if intf.counter_name == drname:
                        intf.status = "offline"
                # 删除关于它的拓扑记录
                del self.topo[drname]
                return

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
                    continue
                elif dest not in self.dis_vec.keys():
                    newpath = detail['path']
                    newpath.insert(0, medium)
                    self.dis_vec[dest] = \
                        {
                            "cost": newcost,
                            "path": newpath
                        }
                    logger.info("[RIP] New shortest path found\n{} -> {} cost {}, path: {}".format(
                        self.route_name, dest, self.dis_vec[dest]['cost'], self.dis_vec[dest]['path']))
                    for vip, netmask in self.topo[dest]:
                        logger.info("[RIP] Updating route table\n{} {} THROUTH {}".format(vip, netmask, self.next_hop[medium]))
                        route.my_route_table.update_item(vip, netmask, self.next_hop[medium])
                else:
                    # print(dest, newcost, self.dis_vec[dest]['cost'])
                    if newcost < self.dis_vec[dest]['cost']:
                        self.dis_vec[dest]['cost'] = newcost
                        newpath = detail['path']
                        # logger.warning('New Path is {}, now append {} to it'.format(newpath, medium))
                        newpath.insert(0, medium)
                        self.dis_vec[dest]['path'] = newpath
                        logger.info("[RIP] New shortest path found\n{} -> {} cost {}, path: {}".format(
                            self.route_name, dest, self.dis_vec[dest]['cost'], self.dis_vec[dest]['path']))
                        for vip, netmask in self.topo[dest]:
                            logger.info("[RIP] Updating route table\n{} {} THROUTH {}".format(vip, netmask, self.next_hop[medium]))
                            route.my_route_table.update_item(vip, netmask, self.next_hop[medium])
            if msg_used:
                self.received_set.add(rip_msg['md5'])

    def show_dv(self):
        x = PrettyTable(['Dest', 'Cost', 'Path'])
        x.padding_width = 1
        for rname, detail in self.dis_vec.items():
            x.add_row([rname, detail['cost'], detail['path']])
        print(x)

class NetworkLayerListener(threading.Thread):
    """
    非阻塞地询问网络层是否有数据到达。若有，则向终端输出数据
    """
    def __init__(self) -> None:
        threading.Thread.__init__(self)
    def run(self) -> None:
        logger.debug('network layer listener begin to work')
        while True:
            pkg = network_layer.recv_rip()
            if pkg is None:
                time.sleep(0.01)
                continue
            if(pkg.protocol == 120):
                rip_msg = utilities.objDecode(pkg.data)
                rip_worker.process(rip_msg)
            # else:
                # route.route_recv_package.put(pkg)

if __name__ == "__main__":

    config_name = sys.argv[1]
    with open(config_name, 'r') as config_f:
        config = json.load(config_f)
    # 初始化网络层
    network_layer = route.NetworkLayer(config)
    network_layer_listener = NetworkLayerListener()
    network_layer_listener.start()
    rip_worker = RIP(network_layer.name, network_layer.interfaces)
    # rip_worker.start()

    Completer = WordCompleter(['show help', 'show tcp', 'show interface', 'show route', 'show dv', 'add', 'send', 'recv'],
                              ignore_case=True)
    help_menu = [
        'show help\n\t: show the help message',
        'show tcp\n\t: show lower level tcp socket information',
        'show interface\n\t: show simulation interface status',
        'show route\n\t: show the route table',
        'send src_ip dest_ip data \n\t: send the data to a route\n\texample : send 8.8.1.1 8.8.4.2 teste!',
        'add dest_net net_mask next_ip \n\t: add an item in route table \n\texample : add 8.8.3.0 24 8.8.4.2 \n\tIt means that "to the net(8.8.3.0/24) via 8.8.4.2"',
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
            user_lines = user_input.split(';')
            for line in user_lines:
                # 拆分用户参数
                user_args = line.split()
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
                    elif user_args[1] == 'dv':
                        rip_worker.show_dv()
                elif main_action == 'start':
                    # 开启RIP协议
                    rip_worker.start()
                elif main_action == 'add':
                    # 往路由表中增加表项
                    route.my_route_table.update_item(user_args[1], int(user_args[2]), user_args[3])
                elif main_action == 'delete':
                    # 删除某一项
                    route.my_route_table.delete_item(user_args[1], int(user_args[2]))
                    for rname, lvip_mask in rip_worker.topo.items():
                        for lvip, lmask in lvip_mask:
                            if user_args[1] == lvip and int(user_args[2]) == lmask:
                                if rname in rip_worker.direct_routes:
                                    print("Cannot delete, {} is a directly connected route")
                                else:
                                    logger.info('[RIP] Reset cost %s to %s to INF', network_layer.name, rname)
                                    rip_worker.dis_vec[rname]['cost'] = DV_INF
                                    rip_worker.dis_vec[rname]['path'] = []

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
                elif user_args[1] == 'dv':
                    rip_worker.show_dv()
                elif user_args[1] == 'off':
                    print(rip_worker.tear_down)
            elif main_action == 'add':
                # 往路由表中增加表项
                route.my_route_table.update_item(user_args[1], int(user_args[2]), user_args[3])
            elif main_action == 'delete':
                # 删除某一项
                route.my_route_table.delete_item(user_args[1], int(user_args[2]))
                for rname, lvip_mask in rip_worker.topo.items():
                    for lvip, lmask in lvip_mask:
                        if user_args[1] == lvip and int(user_args[2]) == lmask:
                            if rname in rip_worker.direct_routes:
                                print("Cannot delete, {} is a directly connected route")
                            else:
                                logger.info('[RIP] Reset cost %s to %s to INF', network_layer.name, rname)
                                rip_worker.dis_vec[rname]['cost'] = DV_INF
                                rip_worker.dis_vec[rname]['path'] = []

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
            elif main_action == 'offline':
                rip_worker.working_flag = False
                for rname, detail in rip_worker.dis_vec.items():
                    detail['cost'] = DV_INF
                rip_worker.tear_down.append(rip_worker.route_name)
            elif main_action == 'debug':
                if user_args[1] == 'start':
                    logger.disabled = False
                if user_args[1] == 'stop':
                    logger.disabled = True
            elif main_action == 'sleep':
                time.sleep(int(user_args[1]))
            elif main_action == 'p':
                logger.setLevel(logging.INFO)
            elif main_action == 'o':
                logger.setLevel(logging.DEBUG)
            elif main_action == 'q':
                os._exit(0)
        except IndexError:
            print('invalid command!')
            continue
        except Exception as e:
            # 捕获所有异常，并且打印错误信息
            print(traceback.format_exc())
            continue

