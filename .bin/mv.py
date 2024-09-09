import requests
from bs4 import BeautifulSoup
import json
import sys
import os
import re
import shutil


mv_data_json = {
    "activity": 0,
    "sync" : 0,
    "url_header":"https://www.kanxiz.com",
    "url":[]
}

class mv :
    def __init__(self,age) -> None:
        self.mv_list = []
        if os.path.exists("mv_list.json"):
            with open("mv_list.json", 'r', encoding='utf-8') as f:
                self.mv_list = json.load(f)
                
        self.mv_fun = {
            'download': self.download,
            'sync':self.sync
        }
        self.arg = self.age_parse(age)
        self.root_dir = os.getcwd()
        self.mv_dir  = os.path.dirname(self.root_dir) + '/'
        
    
    
    def mv_data_file(self,mv_name):
        return self.mv_dir+ mv_name +  "/.mv_data.json"
    
    def mv_data_dir(self,mv_name):
        return self.mv_dir + mv_name +  "/"
    
    def age_parse(self,arg):
        if len(arg) == 1 and isinstance(arg[0],str):
            if  'http' in arg[0]:
                return ('sync',arg[0])      
        elif len(arg) > 1:
            return ('download',arg[1]) 
        else:
            print("参数错误")
          
    
    def get_player_data(self,url,fisrt=False):
        response = requests.get(url)
        response.raise_for_status() #检查请求是否成功
        soup =  BeautifulSoup(response.text,'html.parser')
        script_tags = soup.find_all('script')

        for script in script_tags:
            if 'var player_data' in script.text:
                player_data = json.loads(script.text[len('var player_data='):])
                if not fisrt:
                    return [mv_data_json['url_header'] + player_data["link_next"],player_data["url_next"],False]
                else:
                    return player_data['vod_data']['vod_name'],[url,player_data["url"],False]
                    
                

    def get_nid(self,url):
        return "第" + url[url.rfind("-")+1:url.rfind(".")] + "集"
    
                    
    
    def sync(self,url):
        print("sync:",url)
        if  'http' in url:
            mv_name,next_url = self.get_player_data(url,fisrt=True)
            print(mv_name)
            print(self.get_nid(next_url[0]),next_url)
        else :
            mv_name = url

        
        if mv_name not in self.mv_list:
            self.mv_list.append(mv_name)
            with open("mv_list.json",'+a',encoding='utf-8') as f:
                json.dump(self.mv_list,f,ensure_ascii=False)
            os.mkdir(mv_name)
            mv_data = mv_data_json.copy()
            mv_data['url'].append(next_url)
        else :
            if os.path.exists(self.mv_data_file(mv_name)):
                with open(self.mv_data_file(mv_name), 'r', encoding='utf-8') as f:
                    mv_data = json.load(f)
                next_url = mv_data['url'][-1]
            else:
                mv_data = mv_data_json.copy()
                mv_data['url'].append(next_url)

        while True :
            next_url = self.get_player_data(next_url[0])
            if next_url[0] and next_url[1] :
                mv_data['url'].append(next_url)
                print(self.get_nid(next_url[0]),next_url)
            else:
                break
        
        # print(mv_data)
        with open(self.mv_data_file(mv_name),'w',encoding='utf-8') as f:
            json.dump(mv_data,f,indent=4, sort_keys=True,ensure_ascii=False)
        
        
        
        
            
        
        
    def download(self,mv_name):
        if os.path.exists(self.mv_data_file(mv_name)):
            with open(self.mv_data_file(mv_name), 'r', encoding='utf-8') as f:
                mv_data = json.load(f)
            start = mv_data["sync"]
            for i in range(start,len(mv_data['url'])):
                cmd = "N_m3u8DL-CLI_v3.0.2.exe \"%s\" --enableDelAfterDone  --workDir \"%s\"  --saveName \"%s\" " %(mv_data['url'][i][1],self.root_dir ,mv_name + self.get_nid(mv_data['url'][i][0]))
                
                print(cmd)
                
                if not os.system(cmd):
                    mv_data['url'][i][2] = True
                    mv_data['sync'] = i
                    shutil.move(mv_name + self.get_nid(mv_data['url'][i][0]) +'.mp4',self.mv_data_dir(mv_name))
                    
                    with open(self.mv_data_file(mv_name),'w',encoding='utf-8') as f:
                        json.dump(mv_data,f,indent=4, sort_keys=True,ensure_ascii=False)
                break
        
            
            
    def run(self):
        self.mv_fun[self.arg[0]](self.arg[1])
        


        
        
if __name__ == '__main__':
    
    if len(sys.argv) > 1:
        m = mv(sys.argv[1:])
        m.run()
    else:
        print("mv --help")
        print("linux:")
        print("python3 mv.py url,eg: python3 mv.py https://www.kanxiz.com/play/383019-2-1.html")
        print("python3 mv.py sync move_name, eg: sync 一世独尊")
        print("win:")
        print("your_path/python3.exe mv.py url,eg: python3 mv.py https://www.kanxiz.com/play/383019-2-1.html")
        print("your_path/python3.exe mv.py sync move_name, eg: sync 一世独尊")
        print("tip: 创建新的动漫或电视剧,先给第一集的链接,自动抓取所有资源的m3u8资源后,在用sync下载所有视频资源")
        print("目前只支持看戏网")
    
