测试说明

安装tmux

然后运行一下脚本

```sh
./test.sh console.py
# or
./test.sh ospf.py
# or
./test.sh rip.py
```


用完之后，如果想要完全删除退出这个会话，可在退出tmux后输入一下命令

```sh
tmux kill-session -t  init
```