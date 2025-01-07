# 使用说明

1. 给定一个url,创建新的动漫或电视剧,同步从给定的url开始到更新的最有一集的资源链接

```shell
linux: python3 mv.py url
win: your_patch/python3.exe mv.py url
```

2. 如果想同时下载资源,则增加-d参数

```shell
//linux: 
linux: python3 mv.py url -d
win: your_patch/python3.exe mv.py url -d
```

3. 显示本地资源
   
   
```shell
//linux: 
linux: python3 mv.py show
win: your_patch/python3.exe mv.py show
```

# 例子

```shell
1.同步一世独尊第一集到最新一集的视频链接不下载
python3 mv.py https://www.ikanxi.com/play/383019-2-1.html

2. 同步一世独尊第一集到最新一集的视频链接 并下载到本地
python3 mv.py https://www.ikanxi.com/play/383019-2-1.html -d

3.同步本地所有电影到最新一集,不下载 加上-d则下载到最新一集
python3 mv.py sync

4. 同步本地指定电影到最新一集,给定参数类型为已保存的电影名字或者序号, 电影名字或者序号用show查看,可支持输入多个
python3 mv.py sync 1 
python3 mv.py sync 一世独尊

5. 显示本地所有电影资源
python3 mv.py show
```


# 所支持网站

看戏网:https://www.ikanxi.com/