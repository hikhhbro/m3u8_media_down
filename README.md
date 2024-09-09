# 使用说明

1. 给定一个url,创建新的动漫或电视剧,同步从给定的url开始到更新的最有一集的资源链接

```shell
linux: python3 mv.py url
win: your_patch/python3.exe mv.py url
```

2. 下载指定动漫或者电源新更新的资源

```shell
//linux: 
python3mv.py sync move_name
//win: 
your_patch/python3.exe mv.py sync move_name
```

# 例子

1. 同步一世独尊第一集到最新一集的视频链接

```shell
python3 mv.py https://www.kanxiz.com/play/383019-2-1.html
```

2. 下载一世独尊第一集到最新一集的所有视频

```shell
python3 mv.py https://www.kanxiz.com/play/383019-2-1.html
```

# 所支持网站

看戏网:https://www.kanxiz.com/