import pandas as pd
class RouteTable():
    def __init__(self, csv_file_name, local_link_list=''):
        """ pandas的Dataframe，会更加好用一些 :-) """
        self.route_table = pd.read_csv(csv_file_name, header=0)
        if local_link_list != '':
            self.init_local_link(local_link_list)
    
    def init_local_link(self,dest_net_mask_list):
        """ 传入（dest_net, net_mask)元组的列表  : [(str, int)] """
        for dest_net,net_mask in dest_net_mask_list:
            self.update_local_link(dest_net, net_mask)
    
    def __str__(self):
        return self.route_table.__str__()
    
    def __repr__(self):
        return self.__str__()

    def update_local_link(self, dest_net : str, net_mask: int):
        """ 在转发表中增加本地直连的子网列表 """
        # 对于直连的情况，写死为'on-link'
        self.update_item(dest_net, net_mask, 'on-link')

    def update_item(self, dest_net : str, net_mask : int, dest_ip :str):
        """ 如果子网在表中已存在，就替换之，否则添加表项 """
        index = self.get_index(dest_net, net_mask)
        self.route_table.loc[index] = [dest_net, net_mask, dest_ip]

    def get_dest_ip(self, dest_net :str, net_mask : int):
        """ 传入子网, 得到下一跳ip """
        # 如果传入了本地直连的子网，会返回'on-link'
        index = self.get_index(dest_net, net_mask)
        return self.route_table.loc[index, 'dest_ip']
    
    def delete_item(self, dest_net : str, net_mask : int):
        """ 删除一个表项 TODO:没有处理表格中不存在这一项的情况""" 
        index = self.get_index(dest_net, net_mask)
        self.route_table.drop(index, inplace=True)
    
    def is_local_link(self, dest_net : str, net_mask : int) -> bool:
        """ 检测这个是不是本地链路已连接的子网 """
        gateway = self.get_dest_ip(dest_net, net_mask)
        return gateway == 'on-link'
    
    def show_route_table(self):
        print(self)
    
    @staticmethod
    def get_index(dest_net : str, net_mask : int):
        """ 构造这个表格的index """
        return dest_net+'/'+str(net_mask)


if __name__ == '__main__':
    local_link_net = [
        ('8.8.8',24),
        ('8.8.1',24),
        ('8.8.2',24),
    ]
    t = RouteTable('../test/test_route_table.csv', local_link_net)

    t.show_route_table()

    t.update_item('8.8.1', 24, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1', 24, '8.8.2.5') \n")
    
    t.show_route_table()
    
    t.update_item('8.8.1', 25, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1', 25, '8.8.2.5') \n")
    
    t.show_route_table()
    
    t.delete_item('8.8.1', 25)

    print("\nafter :      t.delete_item('8.8.1', 25) \n")
    
    t.show_route_table()
    
    print("\nafter : t.get_dest_ip('8.8.1', 24)")

    print(t.get_dest_ip('8.8.1', 24))
    
    print("\nafter : t.get_dest_ip('8.8.8', 24)")

    print(t.get_dest_ip('8.8.8', 24))

    print("\nafter :(t.is_local_link('8.8.8', 24)")

    print(t.is_local_link('8.8.8', 24))

    print("\nafter :(t.is_local_link('8.8.1', 24)")

    print(t.is_local_link('8.8.1', 24))

    t.show_route_table()
    