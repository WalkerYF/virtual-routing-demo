#!/bin/bash

# 在test2文件夹下运行下运行
ROOT=.
# 使用的源代码的文件名
FILE_NAME=$1
# 源代码路径
SRC_ROOT=$ROOT/../src
# 测试的配置文件路径
TEST_ROOT=$ROOT

# 下面放一个参数，这个参数代表的命令会让每一台路由器运行
COMMAND_FOR_ALL=$2

# 是否显示调试信息
# start or srtp
# 如果将下面这一行取消注释，在输入命令的时候使用:./text.sh rip.py stop，就会在每一个路由器上都运行：debug stop，就不会显示调试信息
# DEBUG_COMMAND="debug $2"

# 加上路径后的源代码文件
SRC_FILE=$SRC_ROOT/$FILE_NAME

# 配置文件列表
ROUTE_LIST=($TEST_ROOT/routeA.json $TEST_ROOT/routeB.json $TEST_ROOT/routeC.json $TEST_ROOT/routeD.json $TEST_ROOT/routeE.json $TEST_ROOT/routeF.json $TEST_ROOT/routeG.json)
# 也许有用？
ALL_ROUTE=all_route.json
# 所使用的python，有的电脑可能用的是python
PYTHON=python3


tmux new-session -s init -n service -d

# 左右分屏
tmux split-window -h -p 66 -t "init":0.0
# 左右分屏
tmux split-window -h -p 50 -t "init":0.1
# 上下分屏
tmux split-window -t "init":0.0
# 上下分屏
tmux split-window -t "init":0.1
# 上下分屏
tmux split-window -p 66 -t  "init":0.2
# 上下分屏
tmux split-window -p 50 -t "init":0.5

# 切换到指定目录并运行服务
tmux send -t "init":0.0 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[0]}" Enter
tmux send -t "init":0.1 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[1]}" Enter
tmux send -t "init":0.2 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[2]}" Enter
tmux send -t "init":0.3 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[3]}" Enter
tmux send -t "init":0.4 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[4]}" Enter
tmux send -t "init":0.5 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[5]}" Enter
tmux send -t "init":0.6 "sleep 0 ; $PYTHON $SRC_FILE ${ROUTE_LIST[6]}" Enter

# 给每一个路由器发送一个初始化运行脚本
# 注意如果脚本只有一条命令的话不要在后面加分号;不然会出问题
# 给路由器A发送初始化脚本
tmux send -t "init":0.0 "$COMMAND_FOR_ALL" Enter

# 给路由器B发送初始化脚本
tmux send -t "init":0.1 "$COMMAND_FOR_ALL" Enter

# 给路由器C发送初始化脚本
tmux send -t "init":0.2 "$COMMAND_FOR_ALL" Enter

# 给路由器D发送初始化脚本
tmux send -t "init":0.3 "$COMMAND_FOR_ALL" Enter

# 给路由器E发送初始化脚本
tmux send -t "init":0.4 "$COMMAND_FOR_ALL" Enter

# 给路由器F发送初始化脚本
tmux send -t "init":0.5 "$COMMAND_FOR_ALL" Enter

# 给路由器G发送初始化脚本
tmux send -t "init":0.6 "$COMMAND_FOR_ALL" Enter



tmux a -t init


tmux kill-session -t  init
