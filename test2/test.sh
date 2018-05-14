#!/bin/bash

# 在test2文件夹下运行下运行
ROOT=.
# 使用的源代码的文件名
FILE_NAME=$1
# 源代码路劲
SRC_ROOT=$ROOT/../src
# 测试的配置文件路径
TEST_ROOT=$ROOT

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
tmux send -t "init":0.1 "sleep 0.2 ; $PYTHON $SRC_FILE ${ROUTE_LIST[1]}" Enter
tmux send -t "init":0.2 "sleep 0.4 ; $PYTHON $SRC_FILE ${ROUTE_LIST[2]}" Enter
tmux send -t "init":0.3 "sleep 0.6 ; $PYTHON $SRC_FILE ${ROUTE_LIST[3]}" Enter
tmux send -t "init":0.4 "sleep 0.8 ; $PYTHON $SRC_FILE ${ROUTE_LIST[4]}" Enter
tmux send -t "init":0.5 "sleep 1 ; $PYTHON $SRC_FILE ${ROUTE_LIST[5]}" Enter
tmux send -t "init":0.6 "sleep 1.2 ; $PYTHON $SRC_FILE ${ROUTE_LIST[6]}" Enter

# 给每一个路由器发送一个初始化运行脚本

# # 给路由器A发送初始化脚本
# tmux send -t "init":0.0 "show interface;sleep 3;show interface;send 7.7.2.1 7.7.7.1 test-A-to-D;add 7.7.7.0 24 7.7.2.2;send 7.7.2.1 7.7.7.1 test-A-to-D" Enter

# # 给路由器B发送初始化脚本
# tmux send -t "init":0.1 "" Enter

# # 给路由器C发送初始化脚本
# tmux send -t "init":0.2 "" Enter

# # 给路由器D发送初始化脚本
# tmux send -t "init":0.3 "sleep 5;recv" Enter

# # 给路由器E发送初始化脚本
# tmux send -t "init":0.4 "sleep 4;recv" Enter

# # 给路由器F发送初始化脚本
# tmux send -t "init":0.5 "" Enter

# # 给路由器G发送初始化脚本
# tmux send -t "init":0.6 "" Enter



tmux a -t init


tmux kill-session -t  init