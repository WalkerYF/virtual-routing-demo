import pandas as pd
from typing import Tuple
from bitarray import bitarray
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
    
    def init_local_link(self, local_ip_list):
        """ 传入[local_ip ]的列表  : [str] """
        for local_ip in local_ip_list:
            self.update_local_link(local_ip)

    def init_item(self,dest_net_mask_dest_ip_list : Tuple[str, int, str]):
        """ 传入（dest_net, net_mask, dest_ip)元组的列表  : [(str, int, str)] """
        for dest_net,net_mask,dest_ip in dest_net_mask_dest_ip_list:
            self.update_item(dest_net, net_mask, dest_ip)
    
    def __str__(self):
        return self.route_table.__str__()
    
    def __repr__(self):
        return self.__str__()

    def update_local_link(self, dest_net : str, net_mask: int=32):
        """ 在转发表中增加本地直连的子网列表 """
        # 对于直连的情况，写死为'on-link'
        self.update_item(dest_net, net_mask, 'on-link')

    def update_item(self, dest_net : str, net_mask : int, dest_ip :str):
        """ 如果子网在表中已存在，就替换之，否则添加表项 """
        index = self.get_index(dest_net, net_mask)
        self.route_table.loc[index] = [dest_net, net_mask, dest_ip]

    def get_dest_ip(self, final_ip :str):
        """
        传入最终目的IP, 得到下一跳ip
        如果传入了本地直连的子网，会返回'on-link'\n
        通过**最长匹配方法**得到下一跳路由
        1. 取子网掩码与子网相与 与目的子网相等的
        2. 取子网掩码最大的
        返回目的ip，及目的子网掩码
        """
        dest_index = None
        max_net_mask = 0
        for index, row in self.route_table.iterrows():
            # 表中迭代每一行进行判断
            # 目的IP与子网相于   与对应的子网掩码相等，说明该ip在该子网内
            # 这里受限于子网的格式必须是X.X.X.X
            dest_net_bits = str_ip_to_bits(row.dest_net)
            final_ip_bits = str_ip_to_bits(final_ip)
            net_mask_bits = net_mask_to_bits(row.net_mask)

            if net_mask_bits & final_ip_bits == dest_net_bits:
                if max_net_mask < row.net_mask:
                    dest_index = index
                    max_net_mask = row.net_mask

        if dest_index == None:
            # 说明转发表内没有该ip对应的子网的项
            # TODO:并没有做相应的处理，以后可能要做？
            return None
        else:
            return self.route_table.loc[dest_index, 'dest_ip'],self.route_table.loc[dest_index,'net_mask']
    
    def delete_item(self, dest_net : str, net_mask : int):
        """ 删除一个表项 TODO:没有处理表格中不存在这一项的情况""" 
        index = self.get_index(dest_net, net_mask)
        self.route_table.drop(index, inplace=True)
    
    def is_local_link(self, dest_net : str, net_mask : int=32) -> bool:
        """ 检测这个是不是本地链路的ip，应该直接拿完整的ip地址进行比较 """
        gateway = self.get_dest_ip(dest_net)
        return gateway[0] == 'on-link'

    def save_route_table(self, csv_file_name):
        self.route_table.to_csv(csv_file_name, index=True, sep=',')
    
    def show(self):
        print(self)
    
    @staticmethod
    def get_index(dest_net : str, net_mask : int):
        """ 构造这个表格的index """
        return dest_net+'/'+str(net_mask)

def str_ip_to_bits(ip : str) -> bitarray:
    """ 将ip转成32比特的二进制对象 """
    # 将数字从字符形式的ip地址中抽出来
    num_list =[int(i) for i in ip.split('.')]
    # 将数字转成二进制样子的字符串
    binary_list = [format(i, '08b') for i in num_list]
    # 连接字符串
    binary_str_ip = ''.join(binary_list)
    # 转成二进制
    return bitarray(binary_str_ip)


def bits_ip_to_str(bit_ip : bitarray) -> str:
    """ 将比特形式的ip转成字符串形式，形如 '192.168.3.5' """
    bytes_ip = bit_ip.tobytes()
    ip_num_list = struct.unpack('!BBBB', bytes_ip)
    str_ip = ''
    # 首次循环标志，如果不是首次循环的话就加一个'.'
    first_flag = 1
    for i in range(0,4):
        if(1-first_flag):
            str_ip += '.'
        str_ip += str(ip_num_list[i])
        first_flag = 0
    return str_ip

def net_mask_to_bits(net_mask : int) -> bitarray:
    """ 将数字类型的子网掩码变为比特型的，方便之后比较 """
    # TODO:常量：ip长32比特
    net_mask = int(net_mask)
    bit_list = '1' * net_mask + '0' * (32-net_mask)
    return bitarray(bit_list)

def count_one_until_zero(bits : bitarray) -> int:
    """ 从左往右数一个比特串中1的数量，数到第一个不为0的数时停止计数 """
    bits_list = bits.tolist()
    one_count = 0
    while (one_count < 32 and bits_list[one_count] == 1):
        one_count += 1
    return one_count

if __name__ == '__main__':
    a = net_mask_to_bits(24)
    print (a)
    print(count_one_until_zero(a))


    local_link_net = [
        ('8.8.8.1',32),
        ('8.8.1.1',32),
        ('8.8.2.1',32),
    ]
    init_net = [
        ('8.8.8.0',24, '8.8.1.2'),
        ('8.8.1.0',24, '8.8.2.2'),
        ('8.8.2.0',24, '8.8.4.2'),
    ]
    

    # init = RouteTable()
    # init.init_item(init_net)
    # init.show()

    t = RouteTable(local_link_list=local_link_net)
    t.init_item(init_net)

    t.show()

    print(t.get_dest_ip('8.8.8.1'))
    print(t.get_dest_ip('8.8.1.5'))
    print(t.get_dest_ip('8.8.2.222'))

    t.update_item('8.8.1.0', 24, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1.0', 24, '8.8.2.5') \n")
    
    t.show()
    
    t.update_item('8.8.1.0', 25, '8.8.2.5')

    print("\nafter :  t.update_item('8.8.1.0', 25, '8.8.2.5') \n")
    
    t.show()
    
    t.delete_item('8.8.1.0', 25)

    print("\nafter :      t.delete_item('8.8.1.0', 25) \n")
    
    t.show()
    
    print("\nafter : t.get_dest_ip('8.8.1.0')")

    print(t.get_dest_ip('8.8.1.0'))
    
    print("\nafter : t.get_dest_ip('8.8.8.0')")

    print(t.get_dest_ip('8.8.8.0'))

    print("\nafter :(t.is_local_link('8.8.8.1')")

    print(t.is_local_link('8.8.8.1'))

    print("\nafter :(t.is_local_link('8.8.1.0', 24)")

    print(t.is_local_link('8.8.1.0', 24))

    t.show()
    
    t.save_route_table('../test/test_route_table.csv')