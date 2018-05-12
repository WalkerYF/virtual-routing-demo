import pandas as pd
class RouteTable():
    """
    逻辑：使用索引，找到子网/掩码对应的项，直接返回
    不足：真正的转发表应该是寻找最长匹配，找到最适合这个子网的ip来返回
    并且表中还需要有这一项 ‘0.0.0.0,/0’这样无论是哪一个子网和掩码都会匹配到这一项
    从而避免转发表找不到的情况（相当于默认路由）
    """
    def __init__(self, csv_file_name='', local_link_list=''):
        """ pandas的Dataframe，会更加好用一些 :-) """
        if csv_file_name == '':
            self.route_table = pd.DataFrame(data=[], columns=['dest_net','net_mask','dest_ip'])
        else:
            self.route_table = pd.read_csv(csv_file_name, header=0, index_col=0)
        if local_link_list != '':
            self.init_local_link(local_link_list)
    
    def init_local_link(self,dest_net_mask_list):
        """ 传入（dest_net, net_mask)元组的列表  : [(str, int)] """
        for dest_net,net_mask in dest_net_mask_list:
            self.update_local_link(dest_net, net_mask)

    def init_item(self,dest_net_mask_dest_ip_list):
        """ 传入（dest_net, net_mask, dest_ip)元组的列表  : [(str, int, str)] """
        for dest_net,net_mask,dest_ip in dest_net_mask_dest_ip_list:
            self.update_item(dest_net, net_mask, dest_ip)
    
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
        """
        传入子网, 得到下一跳ip 
        如果表中没有这一项 ,处理KeyError异常，返回None
        """
        # 如果传入了本地直连的子网，会返回'on-link'
        
        index = self.get_index(dest_net, net_mask)
        try:
            return self.route_table.loc[index, 'dest_ip']
        except KeyError:
            return None
    
    def delete_item(self, dest_net : str, net_mask : int):
        """ 删除一个表项 TODO:没有处理表格中不存在这一项的情况""" 
        index = self.get_index(dest_net, net_mask)
        self.route_table.drop(index, inplace=True)
    
    def is_local_link(self, dest_net : str, net_mask : int=32) -> bool:
        """ 检测这个是不是本地链路的ip，应该直接拿完整的ip地址进行比较 """
        gateway = self.get_dest_ip(dest_net, net_mask)
        return gateway == 'on-link'

    def save_route_table(self, csv_file_name):
        self.route_table.to_csv(csv_file_name, index=True, sep=',')
    
    def show(self):
        print(self)
    
    @staticmethod
    def get_index(dest_net : str, net_mask : int):
        """ 构造这个表格的index """
        return dest_net+'/'+str(net_mask)


if __name__ == '__main__':
    local_link_net = [
        ('8.8.8.1',32),
        ('8.8.1.1',32),
        ('8.8.2.1',32),
    ]
    init_net = [
        ('8.8.8',24, '8.8.1.2'),
        ('8.8.1',24, '8.8.2.2'),
        ('8.8.2',24, '8.8.4.2'),
    ]

    init = RouteTable()
    init.init_item(init_net)
    init.show()

    t = RouteTable(local_link_list=local_link_net)
    t.init_item(init_net)

    t.show()

    t.update_item('8.8.1', 24, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1', 24, '8.8.2.5') \n")
    
    t.show()
    
    t.update_item('8.8.1', 25, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1', 25, '8.8.2.5') \n")
    
    t.show()
    
    t.delete_item('8.8.1', 25)

    print("\nafter :      t.delete_item('8.8.1', 25) \n")
    
    t.show()
    
    print("\nafter : t.get_dest_ip('8.8.1', 24)")

    print(t.get_dest_ip('8.8.1', 24))
    
    print("\nafter : t.get_dest_ip('8.8.8', 24)")

    print(t.get_dest_ip('8.8.8', 24))

    print("\nafter :(t.is_local_link('8.8.8.1')")

    print(t.is_local_link('8.8.8.1'))

    print("\nafter :(t.is_local_link('8.8.1', 24)")

    print(t.is_local_link('8.8.1', 24))

    t.show()
    
    t.save_route_table('../test/test_route_table.csv')