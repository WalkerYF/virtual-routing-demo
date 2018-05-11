'''
utilities functions here
'''
import json
import socket
import struct
from bitarray import bitarray

def objEncode(obj):
    """ obj，返回binary对象 """
    return json.dumps(obj,indent=4, sort_keys=True,separators=(',',':')).encode('utf-8')

def objDecode(binary):
    """ binary 返回dict对象 """
    return json.loads(binary.decode('utf-8'))

def binary_to_beautiful_json(binary):
    """ binary数据转成漂亮的json格式化字符串,便于输出查看调试 """
    obj = objDecode(binary)
    return json.dumps(obj,indent=4, sort_keys=True)

def obj_to_beautiful_json(obj):
    """ obj数据转成漂亮的json格式化字符串，便于输出调试 """
    return json.dumps(obj,indent=4, sort_keys=True)

def get_host_ip():
    """得到本机IP"""
    try:
       s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
       s.connect(('8.8.8.8', 80))
       ip = s.getsockname()[0]
    finally:
       s.close()
    return ip
    
def get_subnet(ip:str, netmask:int):
    n1, n2, n3, n4 = ip.split('.')
    MASK = (2**netmask)-1
    if netmask <= 8:
        n1 = str(int(n1) & MASK)
        return '.'.join([str(n1), '0', '0', '0'])
    elif netmask <= 16:
        n2 = str(int(n2) & MASK)
        return '.'.join([n1, str(n2), '0', '0'])
    elif netmask <= 24:
        n3 = str(int(n3) & MASK)
        return '.'.join([n1, n2, n3, '0'])
    else:
        return '.'.join([n1, n2, n3, str(int(n4) & MASK)])


class IP_Package():
    """ 
    提供对IP package相关的工具函数
    方便的让IP package从字符串和二进制之间互转
    """
    def __init__(self, src_ip : str, dest_ip : str, final_ip : str, net_mask : int,  data : bytes):
        self.src_ip = src_ip
        self.dest_ip = dest_ip
        self.final_ip = final_ip
        self.net_mask = net_mask
        self.data = data
        self.data_bytes_length = len(self.data)

    def to_bytes(self) -> bytes:
        """ 将自己转成比特形式返回 """
        binary_ip_pkg = struct.pack(
            '!HHIHH',
            0,self.data_bytes_length,
            0,
            0,self.net_mask
        )
        # print(binary_ip_pkg)
        binary_ip_pkg += str_ip_to_bytes(self.src_ip)
        binary_ip_pkg += str_ip_to_bytes(self.final_ip)
        binary_ip_pkg += str_ip_to_bytes(self.dest_ip)
        binary_ip_pkg += self.data
        return binary_ip_pkg

    def __str__(self):
        """ 给print函数调用 """
        display_str = ''
        display_str = 'net_mask : {}\n'.format(self.net_mask)
        display_str += 'src_ip : {}\n'.format(self.src_ip)
        display_str += 'final_ip : {}\n'.format(self.final_ip)
        display_str += 'dest_ip : {}\n'.format(self.dest_ip)
        display_str += 'data : {}\n'.format(str(self.data))
        return display_str
    
    def __repr__(self):
        return self.__str__()
        
    # TODO: objdect 打错了，应为object
    @staticmethod
    def bytes_package_to_objdect(ip_pkg : bytes) -> 'IP_Package':
        """ 将一个bytes格式的IP包转成易操作的对象 """
        net_mask = struct.unpack_from('!H', ip_pkg, 10)[0]
        src_ip = bytes_ip_to_str(ip_pkg[12:16])
        final_ip = bytes_ip_to_str(ip_pkg[16:20])
        dest_ip = bytes_ip_to_str(ip_pkg[20:24])
        data = ip_pkg[24:]
        return IP_Package(src_ip, dest_ip, final_ip, net_mask, data)


def str_ip_to_bytes(ip : str) -> bytes:
    """ 将ip转成32比特的二进制对象 """
    # 将数字从字符形式的ip地址中抽出来
    num_list =[int(i) for i in ip.split('.')]
    # 将数字转成二进制样子的字符串
    binary_list = [format(i, '08b') for i in num_list]
    # 连接字符串
    binary_str_ip = ''.join(binary_list)
    # 转成二进制
    return bitarray(binary_str_ip).tobytes()


def bytes_ip_to_str(bytes_ip : bytes) -> str:
    """ 将比特形式的ip转成字符串形式，形如 '192.168.3.5' """
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
        

if __name__ == '__main__':
    test_ip1 = '192.168.2.4'
    test_ip2 = '192.168.2.6'
    test_ip3 = '192.168.2.56'
    print(str_ip_to_bytes(test_ip1))
    test_bytes1_ip = str_ip_to_bytes(test_ip1)
    print(bytes_ip_to_str(test_bytes1_ip))
    test_ip_pkg = IP_Package(test_ip1, test_ip2, test_ip3, 24, b'safasdasfd')
    print(test_ip_pkg)


    test_binary_ip_pkg = test_ip_pkg.to_bytes()
    print(test_binary_ip_pkg)

    test_after_ip_pkg = IP_Package.bytes_package_to_objdect(test_binary_ip_pkg)
    print(test_after_ip_pkg)

