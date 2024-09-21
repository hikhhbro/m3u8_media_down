import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import shutil
from tabulate import tabulate
import time
from collections import OrderedDict
from inputimeout import inputimeout, TimeoutOccurred
import concurrent.futures

mv_web = [
    {
        "name": "看戏网",
        "base_url": "https://www.kanxiz.com",
        "search": "https://www.kanxiz.com/search/-------------.html?wd=%s&submit=",
    }
]

mv_data_json = {
    "activity": 0,  # 观看记录
    "sync": 0,  # 下载集数
    "url_header": "https://www.kanxiz.com",  # 来源网站
    "period": [],  # 更新时间,[1,5]表示每周一和周五跟新
    "end": 0,  # 完结集数
    "url": [],  # 视频资源链接
}

bin_dir = os.path.dirname(os.path.abspath(__file__))
mv_dir = os.path.dirname(bin_dir) + "/"
executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)

class detail:
    fail_retries = 10

    def __init__(self, mv_name):
        self.name, self.last_links = self.set_name_and_lasturl(mv_name)

        self.dir = mv_dir + self.name + "/"
        if not os.path.exists(self.dir):
            os.mkdir(self.dir)

        self.deficiencies = []
        self.data_file = self.dir + ".mv_data.json"
        self.data = self.data_form_json()
        if self.data["url"][-1]:
            self.last_links = self.data["url"][-1]

        # self.data['end'] = 0
        # self.data_in_json()
        
        self.lock_path = self.dir + '/' + '.lock'
        
    def lock(self,lock_text):
        if not os.path.exists(self.lock_path):    
            with open(self.lock_path, "w", encoding="utf-8") as f:
                json.dump(lock_text, f, indent=4, sort_keys=True, ensure_ascii=False)
            return True
        else:
            return False
            
    def unlock(self):
        os.remove(self.lock_path)
    
    def get_lock(self):
        if os.path.exists(self.lock_path):
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            return None

    def data_form_json(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.set_activity(data)
        else:
            data = mv_data_json.copy()
            data["url"].append(self.last_links)
        return data

    def data_in_json(self):
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, sort_keys=True, ensure_ascii=False)

    def set_activity(self, data):
        local = []
        for root, dirs, names in os.walk(self.dir):
            for name in names:
                name_spl = os.path.splitext(name)
                if name_spl[1] == ".mp4":
                    local.append(int(name_spl[0][name_spl[0].rfind("第") + 1 : -1]))

        if not local:
            data["activity"] = data["sync"]
            return

        local.sort()
        full_seq = list(range(1, data["sync"] + 1, 1))
        dif = list(set(full_seq).difference(set(local)))
        if dif and dif[-1] + 1 != local[0]:
            self.deficiencies = dif[local[0] - 1 :]
        data["activity"] = local[0] - 1

    def soup_from_web(self, url):
        retry = self.fail_retries
        while retry:
            try:
                response = requests.get(url, timeout=5)
                response.raise_for_status()  # 检查请求是否成功
                retry = self.fail_retries
                break
            except:
                retry = retry - 1
                print("\033[91m失败重试: %s/%s\033[0m" % (10 - retry,self.fail_retries))

        return BeautifulSoup(response.text, "html.parser")

    def get_1080p(self, url_json):
        # {
        #     "神印王座2022":(url,count)
        # }
        ret_1080p = OrderedDict()
        print("搜索相关结果:")
        print("序号".ljust(3, "　") + "名称".ljust(15, "　") + "更新".rjust(4, "　"))
        i = 0
        for key, value in url_json.items():
            count = 0
            for url in value:
                h4s = self.soup_from_web(url).find_all("h4")
                for h4 in h4s:
                    if "红牛云" in h4.text:
                        li = (
                            h4.find_parent("div")
                            .find("ul", class_="stui-content__playlist clearfix")
                            .find_all("a")
                        )
                        if len(li) > count:
                            count = len(li)
                            ret_1080p[key] = (
                                mv_web[0]["base_url"] + li[0].get("href"),
                                count,
                            )

            if key in ret_1080p.keys():
                print(
                    str(i).ljust(3, "　")
                    + key.ljust(15, "　")
                    + str(ret_1080p[key][1]).rjust(4, "　")
                )
                i = i + 1
        return ret_1080p

    def search_from_web(self, name):
        mv_name = None
        last_links = None
        ret_url = {}
        url = mv_web[0]["search"] % name

        soup = self.soup_from_web(url)
        ul = soup.find("ul", class_="stui-vodlist clearfix")
        li = ul.find_all("a", class_="stui-vodlist__thumb lazyload")
        for mv in li:
            title = mv.get("title")
            link = mv_web[0]["base_url"] + mv.get("href")
            if title not in ret_url.keys():
                ret_url[title] = []

            ret_url[title].append(link)
        ret_url = self.get_1080p(ret_url)
        select_key = next(iter(ret_url))
        try:
            c = inputimeout(
                prompt="可输入序号或者名字,30s超时或回车默认第一个:", timeout=30
            )
            if c.isdigit():
                select_key, value = list(ret_url.items())[int(c)]
            elif c != "":
                select_key = c

        except TimeoutOccurred:
            # print("超时选择默认")
            pass
        self.name = select_key
        return self.get_player_data(ret_url[select_key][0], fisrt=True)

    # 1. arg 给定参数,可能是链接和电源名字
    def set_name_and_lasturl(self, mv_name):
        last_links = None
        if "http" in mv_name:
            mv_name, last_links = self.get_player_data(mv_name, fisrt=True)

        elif not os.path.exists(mv_dir + mv_name + "/"):
            mv_name, last_links = self.search_from_web(mv_name)

        if not mv_name:
            print("请输入正确的电源名字或链接")
            exit(1)

        return mv_name, last_links

    def get_player_data(self, url, fisrt=False):

        soup = self.soup_from_web(url)
        script_tags = soup.find_all("script")

        for script in script_tags:
            if "var player_data" in script.text:
                player_data = json.loads(script.text[len("var player_data=") :])
                if not fisrt:
                    return [
                        mv_data_json["url_header"] + player_data["link_next"],
                        player_data["url_next"],
                        None,
                        player_data["nid"] + 1,
                    ]
                else:
                    if "vod_data" in player_data.keys():
                        name = player_data["vod_data"]["vod_name"]
                    else:
                        name = self.name
                    return name , [
                        url,
                        player_data["url"],
                        None,
                        player_data["nid"],
                    ]

    def get_nid(self, url):
        return "第" + str(url[3]) + "集"

    def sync_from_web(self, count=sys.maxsize):
        i = 1
        while i < count:
            self.last_links = self.get_player_data(self.last_links[0])
            if self.last_links[0] and self.last_links[1]:
                self.data["url"].append(self.last_links)
                print(self.get_nid(self.last_links), self.last_links)
                i = i + 1
            else:
                break
        self.data_in_json()

    def add_download_list(self, url):


        cmd = (
            '%s/N_m3u8DL-CLI_v3.0.2.exe  --maxThreads 128 --minThreads 64 "%s" --enableDelAfterDone  --workDir "%s"  --saveName "%s" '
            % (
                bin_dir,
                url[1],
                bin_dir,
                self.name + self.get_nid(url),
            )
        )

        print(cmd)
        os.system(cmd)
        ds = shutil.move(
            bin_dir + "/" + self.name + self.get_nid(url) + ".mp4",
            self.dir,
        )
        url[2] = True
        self.data["sync"] = url[3]
        self.data_in_json()
        return ds

    def download(self):
        for url in self.data["url"]:
            if not url[2]:
                executor.submit(self.add_download_list,url)
            elif url[3] in self.deficiencies[:]:
                if self.add_download_list(url):
                    self.deficiencies.remove(url[3])
            else:
                # print(self.get_nid(url), "已经下载,跳过")
                pass


class mv:
    def __init__(self):

        self.mv_fun = {
            "show": self.show,
            "sync": self.sync,
            "--help": self.help,
            "rm": self.rm,
            "set": self.set,
        }
        local_mv = [
            d
            for d in os.listdir(mv_dir)
            if os.path.isdir(os.path.join(mv_dir, d)) and d[0] != "."
        ]
        self.mv_json_path = bin_dir + "/" + ".mv.json"
        mv_json = []
        if os.path.exists(self.mv_json_path):
            with open(self.mv_json_path, "r", encoding="utf-8") as f:
                mv_json = json.load(f)
        self.hot_mv = [item for item in mv_json if item in local_mv]
        mv_json = self.hot_mv.copy()
        if self.hot_mv != mv_json:
            with open(self.mv_json_path, "w", encoding="utf-8") as f:
                json.dump(self.hot_mv, f, indent=4, sort_keys=True, ensure_ascii=False)

        mv_json.extend(local_mv)

        self.mv_list = list(OrderedDict.fromkeys(mv_json))

        self.end_dir = bin_dir + "/end"
        if not os.path.exists(self.end_dir):
            os.mkdir(self.end_dir)

    def arg_parse(self, arg):
        short_opt = None
        if len(arg) > 0:
            if "-d" in arg[:]:
                short_opt = "-d"
                arg.remove("-d")
            if "-v" in arg:
                short_opt = "-v"
                arg.remove("-v")

            if "-s" in arg:
                short_opt = "-s"
                arg.remove("-s")

            if "-t" in arg:
                short_opt = "-s"
                arg.remove("-s")
            
            if "-c" in arg:
                short_opt = arg[-1]
                arg.remove("-c")
                del arg[-1] 
            

        if not arg:
            arg = self.mv_list
        return short_opt, arg

    def name_from_arg(self, arg):
        if arg.isdigit():
            mv_name = self.mv_list[int(arg)]
        else:
            mv_name = arg
        return mv_name

    # 1. arg 给定参数,可能是链接和电源名字,或者通过show显示的序号
    # 2. 获取电影名字和链接, 先从本地获取, 没有则从网页获取
    # 3. 循环获取资源到最新状态
    def sync(self, arg):
        mv_name = None

        # arg 剔除短选项后为空, 默认选择所有,则返回所有本地电影目录
        short_opt, arg_list = self.arg_parse(arg)
        if short_opt and short_opt.isdigit():
            count = int(short_opt)
            short_opt = '-d'
        else:
            count=sys.maxsize
        for arg_ in arg_list:
            mv_name = self.name_from_arg(arg_)

            mv_datail = detail(mv_name)
            print("%s更新:" % (mv_datail.name))
            mv_datail.sync_from_web(count)
            if short_opt == "-d":
                print("%s下载:" % (mv_datail.name))
                mv_datail.download()
            print("-------------------")
        executor.shutdown(wait=True)

    def show(self, arg):
        data = []
        short_opt, arg_list = self.arg_parse(arg)
        show_de = False
        for arg_ in arg_list:
            mv_name = self.name_from_arg(arg_)
            mv_detail = detail(mv_name)

            if short_opt == "-s":
                mv_detail.data_in_json()

            sync_rec = (
                str(mv_detail.data["activity"])
                + "/"
                + str(mv_detail.data["sync"])
                + "/"
                + str(mv_detail.data["url"][-1][3])
                + "/"
                + str(mv_detail.data["end"])
            )

            if mv_detail.data["sync"] < mv_detail.data["url"][-1][3]:
                sync_rec = "\033[34m" + sync_rec + "\033[0m"
            if mv_detail.name in self.hot_mv:
                name_ = "\033[91m" + mv_detail.name + "\033[0m"
            else:
                name_ = mv_detail.name
            
            action = mv_detail.get_lock()
            if action :
                seq_str = "* " + str(self.mv_list.index(mv_name))
            else:
                seq_str = str(self.mv_list.index(mv_name))
            
            l = [seq_str, name_, sync_rec]
            if mv_detail.deficiencies:
                show_de = True

            if short_opt == "-v":
                l.append(",".join(mv_detail.data["period"]))
                l.append(mv_detail.data_file)

            l.append(",".join([f"{i}" for i in mv_detail.deficiencies]))
            data.append(l)

        h = ["序号", "名字", "观看记录/已下载/更新/全集"]

        if short_opt == "-v":
            h.append("更新时间/周")
            h.append("配置文件")

        if show_de:
            h.append("缺少")
        else:
            for row in data:
                row.pop()

        print(
            tabulate(
                data,
                headers=h,
                tablefmt="grid",
            )
        )

    def set(self, arg):
        print(arg[0])
        if arg[0] in self.mv_list and arg[0] not in self.hot_mv:
            self.hot_mv.append(arg[0])
            with open(self.mv_json_path, "w", encoding="utf-8") as f:
                json.dump(self.hot_mv, f, indent=4, sort_keys=True, ensure_ascii=False)

    def help(self, arg):
        print("mv --help")
        print("linux:")
        print(
            "python3 mv.py url,eg: python3 mv.py https://www.kanxiz.com/play/383019-2-1.html"
        )
        print("python3 mv.py sync movie_name, eg: sync 一世独尊")
        print("win:")
        print(
            "your_path/python3.exe mv.py url,eg: python3 mv.py https://www.kanxiz.com/play/383019-2-1.html"
        )
        print("your_path/python3.exe mv.py sync movie_name, eg: sync 一世独尊")
        print(
            "tip: 创建新的动漫或电视剧,先给第一集的链接,自动抓取所有资源的m3u8资源后,在用sync下载所有视频资源"
        )
        print("目前只支持看戏网")

    def rm(self, arg):
        if arg[0] in self.mv_list:
            shutil.move(mv_dir + "/" + arg[0], self.end_dir + "/" + arg[0])

    # 1. 输入参数: 电源名称或者电源链接, 爬取电影视频的m3u8链接, 带上-d,爬取完之后同时下载
    def run(self, arg):
        opt = "--help"
        sub_arg = None

        if sys.argv[0] == arg[0]:
            sub_arg = arg[1:]
        else:
            sub_arg = arg

        if len(sub_arg) > 0:
            if sub_arg[0] not in self.mv_fun.keys():
                opt = "sync"
            else:
                opt = sub_arg[0]
                del sub_arg[0]

        self.mv_fun[opt](sub_arg)


if __name__ == "__main__":

    mv().run(sys.argv)
