import route
import json
import sys
from include.utilities import IP_Package

config_name = sys.argv[1]
with open(config_name, 'r') as config_f:
    config = json.load(config_f)

# 初始化网络层
network_layer = route.NetworkLayer(config)

# 添加路由表项
# route.my_route_table.update_item('8.8.4.0', 24, '8.8.1.3')

while True:
    s = input()
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
        route.my_route_table.update_item(dest_net, net_mask, next_ip)
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

# while True:
#     network_layer.recv()

# if __name__ == '__main__':
