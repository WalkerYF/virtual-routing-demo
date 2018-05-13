import os
import json
import sys
import threading
import logging
import traceback
import time

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.contrib.completers import WordCompleter

import route
from include.utilities import IP_Package
# logging.basicConfig(
#     # filename='../../log/client.{}.log'.format(__name__),
#     format='[%(asctime)s - %(name)s - %(levelname)s] : \n%(message)s\n',
#     # datefmt='%M:%S',
# )
# logger = logging.getLogger(__name__)
# logger.setLevel(logging.DEBUG)

# 初始化网络层(内部还会初始化链路层)
config_name = sys.argv[1]
with open(config_name, 'r') as config_f:
    config = json.load(config_f)
network_layer = route.NetworkLayer(config)



# NOTICE:如果需要使用终端，将以下代码复制到对应脚本的if __name__ == '__main__':下，并且import上面的库
# NOTICE:我是默认你们用终端之前已经import route并且初始化了网络层的，所以下面的代码直接使用网络层的接口
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


