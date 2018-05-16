# 虚拟路由协议实现
## 项目介绍
本次项目，我们实现了以下工作：
1. 实现了自组织虚拟路由程序。每个运行的虚拟路由程序充当router和client的角色，能够向虚拟网络中其他路由器发送消息，并路由转发其他路由器的消息。
1. 实现基于不同算法（LS和DV）的路由协议（OSPF和RIP），能够自动构建和维护各虚拟路由程序中的路由表。尝试了不同的网络拓扑验证了协议的正确性。
1. 实现了处理网络中其他路由节点下线或链路费用变化的情况。
1. 实现了中心化虚拟路由程序。
1. 仿照锐捷路由器，实现了友好的命令行用户界面。借助Tmux编写了一键测试脚本。

## 项目设计
我们使用python3.5 ，在TCP socket的基础上，模拟了链路层和网络层的工作，并在自己实现的虚拟网络层的接口之上增加了不同的路由选择协议用作路由表的自动配置与动态更新，用于完成路由转发的工作。
### 总体架构
因此本次项目我们采用了分层设计的基本方法。
我们将程序分三层：
1. 虚拟链路层：管理邻居路由器直连端口（Interface）之间的子网。之所以称之“虚拟”链路层，是因为它通过TCP socket实际执行了直连Interface之间的数据通信。
向网络层提供了`DataLinkLayer.send`和`DataLinkLayer.receive`两个接口。
2. 网络层：读取到IP数据报后，根据目的IP确定是否转发。保存了路由表，根据路由表修改要转发的IP报的下一跳地址。同时，还对从虚拟链路层收到的IP报进行多路分解，让运行在网络层上的多个进程只接收到自己需要处理的数据报。
网络层中不涉及任何具体的数据发送工作，只是调用虚拟链路层的接口。因此在真实的路由设备上，适配“真实”链路层接口后，我们网络层及以上的代码应当是可以工作的。
3. 路由协议：从网络层接收路由协议报文，根据其中反映的当前网络信息，对路由表进行构建和维护。

整体而言，我们实现了链路层，网络层，并在网络层提供的接口上实现了路由选择协议。
![](figure/replacement.png)

### 虚拟链路层的设计
我们设计的虚拟链路层模块为网络层提供了直接相邻的Interface之间的数据传输的接口。从接口和功能上看，它与实际的链路层是相同的。

然而其实现上则有别与真实的链路层，因此冠名“虚拟链路层“：
该模块实际上一并完成了链路层和物理层的功能。
该模块使用的是TCP socket完成数据发送接收。

本实验中，我们将网络拓扑中每一条连接两个路由器的线段看做一个子网，该子网由分属两个路由器的直连Interface组成。
在配置文件中，我们为每一个Interface分配了一对虚拟的IP地址和虚拟子网掩码以及一对用于建立socket连接的物理机IP和端口号。

举下图例子：路由器A和路由器B是邻居路由，两者的Interface1相连，A的Interface 1的虚拟IP为8.8.1.2，B的为8.8.1.3，虚拟子网掩码均为24，组成8.8.1.0/24子网。物理机IP均为127.0.0.1，端口分别为6012和6013，链路层初始化时路由器A/B会分别启动一个监听线程，监听自身的(物理IP, 端口号)，并向对方的(物理IP,端口号)发起TCP socket连接。
![](https://images-cdn.shimo.im/p5hoVdUwC0Q4A63j/image.png!thumbnail)
我们将TCP socket提供的可靠字节流抽象成物理链路的连接。并在实现链路层的过程中，将该从TCP socket获得的长连接封装到链路层中，从而对外体现为：将IP包交给链路层，链路层就能够通过该IP包中含有的信息，得知通过哪一条链路发送。

**注意**：在我们的虚拟链路层设计中，我们抛弃了MAC地址，没有采取在IP包上新加一层以太网帧首部，而是将下一跳IP直接写在IP包中，直接根据下一跳IP确定链路层转发目的地。
#### 虚拟链路层的实现
虚拟链路层的实现在`src/link.py`中，该文件中有4个类
``` python
class Host():
    ...
class Subnet():
    ...
class HostManager():
    ...
class DataLinkLayer():
    ...
```
Host类表示子网内的一台主机。在本实验中，所有Host均为路由器的Interface。
其属性包括
``` python
name                         #该Interface所属路由器
counter_name                 #直连Interface所属路由器
link_cost                    #链路代价
vip                          #虚拟IP
netmask                      #虚拟子网掩码
counter_vip                  #直连Interface的虚拟IP
counter_netmask              #直连Interface的虚拟IP子网掩码
pip_port                     #物理IP和端口号
counter_pip_port             #直连Interface的物理IP和端口号
server_socket                #该Interface监听的socket
counter_socket               #向直连Interface发送消息的socket
status = "down"              #状态<down, on, offline>
```
Subnet类储存了一个Host列表和子网前缀
HostManager的构造函数要求传入路由器所有Interface的列表。构造函数开启会每个Interface的监听线程，然后初始化链路层子网列表。然后开启一个后台线程，调用self.connect_all函数，该函数，采用轮询的方法尝试和所有直连Interface建立TCP连接，直到和所有直连Interface均连接成功。成功连接得到的socket将储存在对应Interface中。

DataLinkLayer类提供两个接口
``` python
def send(self, ip_pkg:bytes) -> int
def receive(self) -> Optional[bytes]
```
send函数读取ip_pkg中的dest_ip和netmask。dest_ip在网络层表示下一跳IP，但也允许是出接口IP。根据dest_ip和netmask，send遍历找到对应的Interface。使用socket进行发送。

recieve函数从socket中读取ip_pkg放入link_buf队列中。
我们这里复用了上次CS通信实验中实现的rdt_socket类，使用定长头部的方法解决TCP粘包/分包问题。

### 网络层的设计
以下简单地描述网络层的设计。
#### 网络层提供接口
在链路层提供的接口基础上，网络层需要完成以下工作：
从IP包中获得最终目的IP，并通过查询转发表得到下一跳IP，将该下一跳IP写入IP包中，并将该IP包放入链路层发送。
从链路层获得接收到的IP包，并根据IP包中包含的协议信息，进行多路分解，交给对应的进程处理。
据此，网络层提供了以下接口
``` python
发送数据包
network_layer.send(源ip，最终目的ip，所需发送数据)
非阻塞地接受普通包
network_layer.recv()
非阻塞地接受RIP协议包
network_layer.recv_rip()
非阻塞地接受COST协议包
network_layer.recv_cost()
非阻塞地接受OSPF协议包
network_layer.recv_ospf()
非阻塞地接收ping协议包（本协议是网络层协议，功能与应用层的icmp协议类似）
network_layer.recv_ping()
```
#### IP包格式
IP包的格式我们在原有IPV4协议包的基础上，做了一些改动。下图展现了我们所实现的IP包的格式。
![](https://images-cdn.shimo.im/NhdVcq2r9rA4HJWQ/image.png!thumbnail)
其中比较重要的字段我们做以下进一步说明
src_ip:发送源IP，在创建IP包的时候就需要写好该项的值
final_ip:发送目的IP，在创建IP包的时候就需要写好该项的值
dest_ip: 下一跳IP ,该项由网络层在转发表中查询后填入

上层协议类型
119：OSPF协议
120：RIP协议
#### 转发表格式
转发表的格式如下，这个可以在路由器控制台中通过show route命令来查看。
其中本地端口IP和本地连接的子网在路由器开机初始化的时候设置好，其他的表项可以手动添加，也可以通过路由选择协议自动填入。
![](https://images-cdn.shimo.im/usuBz06XY1sF55Fm/1526367717255.png!thumbnail)
#### 网络层转发逻辑
当网络层需要发送一个数据包，根据包中附带的最终目的IP，从转发表里根据最长匹配原则找到下一跳IP，如果从转发表中找到了对应的下一跳IP，则将该下一跳ip写入IP包的dest_ip项中。

其中最长匹配原则，使用了以下的逻辑来实现
判断转发表项是否可用：将目的IP与该转发表项子网掩码相与，并且将可达子网IP与对应子网掩码相与，若两者相等，则该子网可达目的IP，该表项可用。
计算匹配位数，取最长：目的子网与最终ip进行同或，计算前导1的个数，取个数最多的可用表项。

由此，实现了路由转发表中的最长匹配。
### OSPF协议的实现
在OSPF协议中，每个路由在上电（程序启动）后，即具有整个网络的所有信息。每个路由独自地执行最短路算法，求出到每个结点的最短路径。根据算法的结果在路由表中增添需要的表项。
#### 最短路的实现
在OSPF算法中，实现了两个接口
第一个接口的作用是初始化全局的拓扑信息（用邻接矩阵的形式储存）
``` python
def init_shortest_path_prerequisite(src : int) -> None:
```
第二个接口的作用是根据全局拓扑图计算出最短路
``` python
def calculate_shortest_path(src:int):
```
在路由器运行时，有可能部分路由会离线。在离线后只需要相应地修改全局拓扑信息，并使用第二个接口计算出最短路，即可重置路由表，让剩余的路由器正常工作。

#### 信息的监听和发送
本协议中将使用下述线程完成特定的任务。
``` python
class TrackingNeighbourAlive(threading.Thread):
```
该类在运行时将产生一个独立的线程，反复确认路由的邻居是否在线。这是通过反复向相邻的路由发送协议号为119的请求IP包实现的。IP包的有效载荷是一个`dict`, 其code字段为0.当其他路由收到该IP包时，会返回一个code字段为1的响应包。这样路由就可以知道其邻居的存在。

更详细的技术细节是，每次收到邻居的响应包，就将邻居的`alive`置位。每隔一定时间检查`alive`是否被置位，若是则说明邻居存在：将`alive`复位成0,等待下一次检测。若`alive`未被置位，则说明邻居长时间未回应包，此时可以认为邻居已断开链接。

每个路由结点仅维护和相邻结点的连接信息。路由检测到某个邻居断开连接后，需要将邻居的下线信息广播到整个局域网。

下列多线程类负责监听网络层的数据包。
``` python
class NetworkLayerListener(threading.Thread):
```
其会非阻塞地反复监听网络层送上来的数据。按照协议类型，接受ospf型数据包、ping型数据包和其他（无协议）数据包。用户可以通过调用不同的接口指明获取一种数据包。

ospf协议（协议号119）数据包负责广播某个结点的下线信息。
``` python
msg = {
    "type": "logout", # 代表下线
    "index": index, # 代表下线的路由器编号
    "id": msgID # 消息id。用于防止无限洪泛的发生
}
```
ping数据包（协议号100）负责侦查结点的邻居是否仍在线。
ping协议 请求格式
``` python
msg = {
  'code': 0,
  'msg': "are you still here?"
}
```
ping协议 响应格式
```python
 msg = {
    'code': 1,
    'msg': 'I am here.'
}
```
其他类型数据包（协议号0）负责在路由间交换信息（和用户在路由器终端测试路由时向其他路由发消息）
```python
msg = {
    anything
}
```
#### 广播
广播采用洪泛的方式实现。每条广播信息有一个唯一个的id。每个路由器缓存收到过的id。若路由器再次收到该id的信息，则直接丢弃该信息。

每个路由器有自己的消息id「定义域」。路由器从自己的消息定义域中选取id号，如此即可保证各个id之间互不相同。

当一个路由器收到广播信号，得知网络拓扑改变时，它会更新自己缓存的网络拓扑，重新执行一次最短路算法，并重置路由表。这个实现虽然效率不高，但能确保绝对正确。


### RIP协议的实现:
RIP协议是以DV算法为核心的分布式路由协议。本实验中主要在RIP类中实现。

下面我将从四个方面讲解RIP协议：

1. RIP协议维护的数据结构
2. RIP协议初始化过程
3. RIP报文的结构
4. 收到报文后的处理流程

RIP类中需要维护以下数据结构：

``` python
route_name: string            		 	#本路由器名
interfaces: list<Host>         			#本路由器的interfaces
tear_down:  list<string>       			#整个网络中处于离线状态的路由器列表
dis_vec:   dict<route_name: (cost, path)>#自身的距离向量(distance vector)
dis_mat:   dict<route_name: dis_vec>    #距离表(distance matrix)
topo:      dict<route_name: Subnet>     #已知的网络拓扑
```
RIP协议在网络层初始化完毕后启动。RIP协议启动时（即RIP类构造时），只需要知道本地链路的信息，并用本地链路信息初始化以上条目。各条目的意义和初始情况为：

- route_name和interfaces由网路层传入，RIP类把它保存下来方便之后的引用。
- dis_vec是字典类型，其中每一字典项不仅存储了到某个路由器的路径费用，还存储了路由路径，用于实现毒性逆转。初始化时在dis_vec中添加与直连路由器直接的字典项。
- dis_mat在初始化时为空，之后它将储存邻居的RIP报文中的dis_vec，但不会包含自身的dis_vec。
- 由于路由表是以目的子网为表项的，因此RIP协议中，在找到与某个路由器的最短路径时，只有当知道这个路由器的Interfaces连接着哪些子网，才能更新路由表。这中信息储存在topo变量中。

RIP协议通过发送RIP报文更新路由表。因此接下来将开启后台广播线程，隔指定时间通过所有本地Interface，向所有邻居路由器发送RIP报文。

RIP协议报文包含的内容为：
``` python
rip_msg = {
    "from" : self.route_name,    
    "topo": self.topo,           
    'tear_down': self.tear_down, 
    "dis_vec": self.dis_vec           
}
```
网络层的NetworkLayerListener类会监听网络层收到的IP数据报并判断数据报协议类型。如果发现收到的是RIP协议报文，将会调用RIP.process函数处理该报文。

RIP.process函数是RIP协议的重点，在收到RIP报文（rip_msg）后它的处理过程共分五步：

1. 检查RIP报文的所有项，如果该项和已知的离线状态的路由器有关，则抛弃该报文。
2. 检查rip_msg中邻居的tear_down列表，确认是否又有其他路由器离线了，如果有，则删除自身维护的数据结构中与该离线路由器相关的项。
3. 检查rip_msg中邻居的距离向量，如果有其中某些键（route_name）不在自身的距离向量的键中，则说明发现了新的与自身不直接相连的路由器，更新自己的距离向量和拓扑图。
4. 用rip_msg中新的邻居距离向量更新自身在距离表中储存的旧值。
5. 根据更新过的距离向量和距离表，计算新的到所有已知路由器的最短路径并更新路由表。

第1、2步确保了一个路由器offline的消息会自该offline路由器向外扩散。
第3步使得一个路由器获得邻居路由器之外的路由器的信息，逐步学习到整个网络的拓扑。
第5步执行了dv算法，该算法基于以下公式，其中$D_x(y)$指从路由器x到路由器y的最短路径。
集合v是x的邻居路由器集，c(x,v)是x到v的费用。$D_v(y)$是从v到y的费用。
在算法的实现过程中，若不存在从v到y的路径，则将$D_v(y)$看做无穷大。
$$D_x(y) = \min_y\{c(x,y)+D_v(y)\}\ \ \ for\ each\ y\in N$$

同时，由于我从一开始就储存了路径信息，因此我实现了毒性逆转，若v到y的路径中包含x，则也将$D_v(y)$看做无穷大。

### 中心化路由选择协议的实现

项中心化路由选择协议的实现比较简单。中心路由器（controller）获取全局路由器的信息，并计算出多源最短路。其他路由器向controller发送路由转发表请求，controller为各个路由器返回对应的路由转发表。路由器根据controller提供的信息配置自己的转发信息。

请求报文
``` python
msg = {
    "code": 0,
}
# 0表示请求报文    "msg": "request for route table",
# 面向用户的提示信息    "src_index": ROUTER_INDEX
# 本路由在局域网中的编号 
```
在controller接收到请求报文后，其计算出最短路，返回下列响应报文。# 响应报文
``` python
msg = {
    "code": 1, # 1代表响应报文
    "msg": "here's your route table", # 面向用户的提示信息
    "route_table": [
      # 由下一跳ip，目的ip和掩码构成的三元组（的列表）
      (dst_ip, final_ip, netmask) 
    ]
}
```
## 安装及部署
### 运行方式
可从github上获取源代码，该源代码库与我们的提交文件中的source文件夹一致。
以下为命令行操作，也可在source文件夹下运行
获取源代码
``` shell
$ git clone https://github.com/WalkerYF/virtual-routing-demo
$ cd virtual-routing-demo/
```
运行测试样例
``` shell
cd test/ # 也可以cd test2/ 使用另一个测试样例
./test_rip.sh # 或者 ./test_odpf.sh 使用另一种路由选择协议 
```
### 依赖
我们的测试与源代码依赖着一些第三方的软件与库，因此初次运行也许不能成功。
测试脚本的正常运行，依赖于终端管理程序tmux，在ubuntu下可以按以下指令安装
``` shell
sudo apt-get install tmux
```
python程序的正常运行，依赖着一些第三方库，可在命令行下如此安装
注意安装在python3环境下。如果pip对应python2的环境，请使用pip3
``` shell
pip install bitarray
pip install prompt_toolkit
pip install pandas
```
### 配置文件说明
每一个路由器的配置文件都放在了测试文件夹下（形如routeA.json，这些配置文件说明了每一台路由器的直连端口及该端口连接的其他路由器的ip，因此，这些配置文件与测试文件夹中的拓扑图配套使用。当然，如果需要对拓扑进行修改，也可以通过修改配置文件来实现。
## 项目结果
### 测试方法
在我们的测试过程中，主要使用了两种测试拓扑。对每一种拓扑，我们均使用了多种路由选择协议进行了测试，验证了我们实现的协议的正确性。同时，我们对每一个测试，均有相关的测试脚本以及测试视频，帮助其他想要测试本项目的人来复现。

在`test/test2/test*`文件夹下，运行以下的脚本（依赖tmux）即可进行测试。
``` shell
./test_rip.sh # 可用于测试rip协议
./test_ospf.sh # 可用于测试ospf协议
./test_controller.sh # 可用于测试中心化路由，
中心化路由对网络拓扑结构有要求，因此必须在test_controller文件夹下测试
```
### test文件夹
![](../test/2018-05-11-17-03-55.png)
#### test2文件夹
![](../test2/figure/2018-05-15-19-34-35.png)
### test_controller文件夹
![](../test_controller/figure/2018-05-15-19-32-39.png)

### 测试项目一：虚拟路由器的静态路由配置
在实现路由选择协议前，我们实现了虚拟的链路层及网络层，在这些层提供的接口之上，我们实现了一个能够对路由器各项属性进行查看及配置的控制台，以下视频是我们的测试结果。

**测试视频见**
`/ppt+demo_video/console_路由器控制台测试.mp4`

在我们的路由器控制台中，提供了以下命令，在视频中我们逐个进行了测试，并且还对转发表进行了设置以达到路由器间能够转发消息的结果。

``` shell
show route # 查看路由表
show interface # 查看接口情况
show tcp # 查看底层TCP socket的情况
show dv # 在RIP协议中可用，用于查看距离向量表
add (dest_net) (net_mask) (next_ip) # 用于在路由表中新增一项 
delete (dest_net) (net_mask) # 用于在路由表中删除一项
send (src_ip) (final_ip) (data) # 用于发送消息到指定路由器(功能与ping类似)
recv # 从本地队列中取得一个IP包并显示
```
### 测试项目二：RIP协议
RIP协议是一个使用距离向量算法进行路由表自适应配置的协议。我们主要测试了该协议在以下三个场景处所起的作用。

场景1：【路由器刚开机】每一个路由器都只有本地链路的信息。此时开启RIP协议后，每一个路由器应该要不断地广播距离向量直至收敛，同时转发表也能够设置好。
**见视频：**
`/ppt+demo_video/rip_路由器自动配置转发表.mp4`

场景2：【网络拓扑结构改变】此时路由器应该发现结构的改变并修改距离向量表，转发表，同时广播改变。
**见视频：**
`/ppt+demo_video/rip_路由表自适应更新网络拓扑.mp4`
场景3：【链路费用改变】此时路由器可能会发现一条更优的路径，修改距离向量和转发表，并广播此改变信息。
**见视频**
`/ppt+demo_video/rip_链路费用改变.mp4`
### 测试项目三：OSPF协议
OSPF是一个使用SPFA算法，通过全局拓扑信息计算得到最优的路的协议。对该协议的测试我们分为以下三个场景：
场景1：【路由器刚开机】每一个路由器都只有本地链路的信息。此时开启OSPF协议后，每一个路由器应该能够得到全局的拓扑信息，并且设置好本地的转发表。

场景2：【网络拓扑结构改变】此时路由器应该发现拓扑结构的改变并修改本地存储拓扑结构的数据库，转发表，同时广播此改变信息。
**以上两个场景的视频见**
`/ppt+demo_video/ospf_路由表自动配置及动态更新.mp4`
### 测试项目四：中心化路由
中心化路由让每一台路由器不再需要计算转发表，相反，每一台路由器只需要定时向中心路由请求自己的路由表即可。对该实现，主要测试了以下这一个场景。
【路由器刚开机】每一个路由器从中心化路由器得到转发表，从而实现路由器间的连同。
## 项目管理记录
TODO:git commit 表格？？
