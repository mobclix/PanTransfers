import re
import json
import threading
import time
import random
import requests
import requests.cookies
import webbrowser
from tkinter import *
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from retrying import retry

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

S_WIDTH = 600
S_HEIGHT = 500

HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,'
              'application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Connection': 'keep-alive',
    'Host': 'pan.baidu.com',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="98", "Google Chrome";v="98"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'Referer': 'https://pan.baidu.com'
}

BDSTOKEN_URL = 'https://pan.baidu.com/api/loginStatus?clienttype=0&web=1'
VERIFY_URL = 'https://pan.baidu.com/share/verify'
TRANSFER_URL = 'https://pan.baidu.com/share/transfer'
TRANSFER_REPID_URL = 'https://pan.baidu.com/api/rapidupload'
TRANSFER_RENAME_URL = 'https://pan.baidu.com/api/filemanager?async=2&onnest=fail&clienttype=0&opera=rename&app_id=250528&web=1'
GET_DIR_LIST_URL = 'https://pan.baidu.com/api/list?order=time&desc=1&showempty=0&web=1&page=1&num=1000'
CREATE_DIR_URL = 'https://pan.baidu.com/api/create?a=commit'


class Thread:
    def __init__(self, func, *args):
        self.func = func
        self.args = args

    def thread_start(self):
        t = threading.Thread(target=self.func, args=self.args)
        t.setDaemon(True)
        t.start()


class GUI:
    def __init__(self, init_window_name):
        self.init_window_name = init_window_name

    def set_init_window(self):
        self.init_window_name.title("百度云批量转存工具_v1.0 / by mobclix")
        self.init_window_name.geometry(str(S_WIDTH) + 'x' + str(S_HEIGHT) + '+'
                                       + str((self.init_window_name.winfo_screenwidth() - S_WIDTH) // 2) + '+'
                                       + str((self.init_window_name.winfo_screenheight() - S_HEIGHT) // 2 - 18))
        self.init_window_name.attributes("-alpha", 0.9)

        self.cookie_data_label = Label(self.init_window_name, anchor='w', text="cookie：")
        self.cookie_data_label.place(relx=0.025, rely=0.01, relheight=0.04, relwidth=0.32)

        self.dirname_data_label = Label(self.init_window_name, anchor='w', text="保存路径：")
        self.dirname_data_label.place(relx=0.025, rely=0.12, relheight=0.04, relwidth=0.32)

        self.link_data_label = Label(self.init_window_name, anchor='w', text="链接：")
        self.link_data_label.place(relx=0.025, rely=0.21, relheight=0.04, relwidth=0.32)

        self.cookie_data_Text = Text(self.init_window_name)
        self.cookie_data_Text.place(relx=0.025, rely=0.05, relheight=0.06, relwidth=0.42)

        self.dirname_data_Text = Text(self.init_window_name)
        self.dirname_data_Text.place(relx=0.025, rely=0.16, relheight=0.04, relwidth=0.42)

        self.scrollbar_link = Scrollbar(self.init_window_name)
        self.scrollbar_link.place(relx=0.445, rely=0.25, relheight=0.65, width=18)
        self.link_data_Text = Text(self.init_window_name, yscrollcommand=self.scrollbar_link.set)
        self.link_data_Text.place(relx=0.025, rely=0.25, relheight=0.65, relwidth=0.42)
        self.scrollbar_link.configure(command=self.link_data_Text.yview)

        self.scrollbar_log = Scrollbar(self.init_window_name)
        self.scrollbar_log.place(relx=0.95, rely=0.05, relheight=0.85, width=18)
        self.log_data_Text = Text(self.init_window_name, yscrollcommand=self.scrollbar_log.set)
        self.log_data_Text.place(relx=0.5, rely=0.05, relheight=0.85, relwidth=0.45)
        self.scrollbar_log.configure(command=self.log_data_Text.yview)

        self.start_button = Button(self.init_window_name, text="开始", bg="#fff", width=10,
                                   command=lambda: Thread(main, self).thread_start())
        self.start_button.place(relx=0.025, rely=0.92, relheight=0.06, relwidth=0.1)

        self.label_update = Label(self.init_window_name, text='查看教程', font=('Arial', 9, 'underline'),
                                  foreground="#0000ff", cursor='mouse')
        self.label_update.place(relx=0.70, rely=0.92, relheight=0.06, relwidth=0.1)
        self.label_update.bind("<Button-1>",
                               lambda e: webbrowser.open("https://blog.csdn.net/mobclix/article/details/123068801", new=0))

        self.label_example = Label(self.init_window_name, text='检查新版', font=('Arial', 9, 'underline'),
                                   foreground="#0000ff", cursor='mouse')
        self.label_example.place(relx=0.82, rely=0.92, relheight=0.06, relwidth=0.1)
        self.label_example.bind("<Button-1>",
                                lambda e: webbrowser.open("https://www.bing.com", new=0))


def random_sleep(start=1, end=3):
    sleep_time = random.randint(start, end)
    time.sleep(sleep_time)


def check_link_type(link):
    if link.find('https://pan.baidu.com/s/') != -1:
        link_type = 'common'
    elif link.count('#') > 2:
        link_type = 'rapid'
    else:
        link_type = 'unknown'
    return link_type


def link_format(links):
    link_list = [link for link in links if link]
    link_list = [link + ' ' for link in link_list]
    return link_list


def parse_url_and_code(url):
    url = url.lstrip('链接:').strip()
    res = re.sub(r'提取码*[：:](.*)', r'\1', url).split(' ', maxsplit=2)
    link_url = res[0]
    pass_code = res[1]
    unzip_code = None
    if len(res) == 3:
        unzip_code = res[2]
    link_url = re.sub(r'\?pwd=(.*)', '', link_url)
    return link_url, pass_code, unzip_code


class PanTransfer:
    def __init__(self, cookie, user_agent, dir_name, gui):
        self.headers = dict(HEADERS)
        self.headers['Cookie'] = cookie
        self.dir_name = dir_name
        self.user_agent = user_agent
        self.gui = gui
        self.bdstoken = None
        self.timeout = 10
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update(self.headers)
        self.get_bdstoken()
        self.create_dir()

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def post(self, url, post_data):
        return self.session.post(url=url, data=post_data, timeout=self.timeout, allow_redirects=False, verify=False)

    @retry(stop_max_attempt_number=5, wait_fixed=1000)
    def get(self, url):
        return self.session.get(url=url, timeout=self.timeout, allow_redirects=True)

    def get_bdstoken(self):
        response = self.get(BDSTOKEN_URL)
        bdstoken_list = re.findall('"bdstoken":"(.*?)"', response.text)
        if bdstoken_list:
            self.bdstoken = bdstoken_list[0]
        else:
            raise ValueError('获取bdstoken失败！')

    def transfer_files_repid(self, rapid_data, dir_name):
        url = TRANSFER_REPID_URL + f'?bdstoken={self.bdstoken}'
        post_data = {'path': dir_name + '/' + rapid_data[3], 'content-md5': rapid_data[0],
                     'slice-md5': rapid_data[1], 'content-length': rapid_data[2]}
        response = self.post(url, post_data)
        if response.json()['errno'] == 404:
            post_data = {'path': dir_name + '/' + rapid_data[3], 'content-md5': rapid_data[0].lower(),
                         'slice-md5': rapid_data[1].lower(), 'content-length': rapid_data[2]}
            response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            self.logs(END, '转存成功！保存位置:' + data['info']['path'] + '\n\n')
        else:
            raise ValueError('转存失败！errno:' + str(data['errno']))

    def transfer_files(self, shareid, user_id, fs_id_list, dir_name, unzip_code):
        url = TRANSFER_URL + f'?shareid={shareid}&from={user_id}&bdstoken={self.bdstoken}'
        if not dir_name.strip().startswith('/'):
            dir_name = '/' + dir_name.strip()
        fsidlist = f"[{','.join(i for i in fs_id_list)}]"
        post_data = {'fsidlist': fsidlist, 'path': dir_name}
        response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            for each in data['extra']['list']:
                self.logs(END, '转存成功！保存位置:' + each['to'] + '\n')
                if unzip_code is not None:
                    self.transfer_files_rename(each['to_fs_id'], each['to'], each['from'].replace('/', ''), unzip_code)
                self.logs(END, '\n')
        else:
            raise ValueError('转存失败！errno:' + str(data['errno']))

    def get_dir_list(self, dir_name):
        url = GET_DIR_LIST_URL + f'&dir={dir_name}&bdstoken={self.bdstoken}'
        response = self.get(url)
        data = response.json()
        if data['errno'] == 0:
            dir_list_json = data['list']
            if type(dir_list_json) != list:
                raise ValueError('没获取到网盘目录列表,请检查cookie和网络后重试!\n\n')
            else:
                return dir_list_json
        else:
            ValueError('获取网盘目录列表失败! errno:' + data['errno'] + '\n\n')

    def create_dir(self):
        if self.dir_name != '/' and self.dir_name != '':
            # dir_list_json = self.get_dir_list()
            # dir_list = [dir_json['server_filename'] for dir_json in dir_list_json]
            dir_name_list = self.dir_name.split('/')
            dir_name = dir_name_list[len(dir_name_list) - 1]
            dir_name_list.pop()
            path = '/'.join(dir_name_list) + '/'
            dir_list_json = self.get_dir_list(path)
            dir_list = [dir_json['server_filename'] for dir_json in dir_list_json]
            if dir_name and dir_name not in dir_list:
                url = CREATE_DIR_URL + f'&bdstoken={self.bdstoken}'
                post_data = {'path': self.dir_name, 'isdir': '1', 'block_list': '[]', }
                response = self.post(url, post_data)
                data = response.json()
                if data['errno'] == 0:
                    self.logs(END, '创建目录成功！\n\n')
                else:
                    self.logs(END, '创建目录失败！路径中不能包含以下任何字符: \\:*?"<>|\n\n')

    def transfer_files_rename(self, fs_id, path, name, unzip_code):
        try:
            url = TRANSFER_RENAME_URL + f'&bdstoken={self.bdstoken}'
            newname = name + ' ' + unzip_code
            post_data = {'filelist': f'[{{"id": {fs_id}, "path": "{path}", "newname": "{newname}"}}]'}
            response = self.post(url, post_data)
            data = response.json()
            if data['errno'] == 0:
                self.logs(END, '重命名成功！:' + newname + '\n')
            else:
                self.logs(END, '重命名失败！errno:' + str(data['errno']) + '\n')
        except Exception as e:
            self.logs(END, '重命名失败！err:' + str(e) + '\n')

    def verify_link(self, link_url, pass_code):
        url = VERIFY_URL + f'?surl={link_url[25:48]}'
        post_data = {'pwd': pass_code, 'vcode': '', 'vcode_str': '', }
        response = self.post(url, post_data)
        data = response.json()
        if data['errno'] == 0:
            bdclnd = data['randsk']
            cookie = self.session.headers['Cookie']
            if 'BDCLND=' in cookie:
                cookie = re.sub(r'BDCLND=(\S+?);', f'BDCLND={bdclnd};', cookie)
            else:
                cookie += f';BDCLND={bdclnd};'
            self.session.headers['Cookie'] = cookie
            return data
        elif data['errno'] == -9:
            raise ValueError('提取码错误！')
        elif data['errno'] == -62 or data['errno'] == -19 or data['errno'] == -63:
            raise ValueError('错误尝试次数过多，请稍后再试！')
        else:
            raise ValueError('验证链接失败！errno:' + str(data['errno']))

    def get_share_link_info(self, link_url, pass_code):
        self.verify_link(link_url, pass_code)
        random_sleep(start=1, end=3)
        response = self.get(link_url)
        info = re.findall(r'locals\.mset\((.*)\);', response.text)
        if len(info) == 0:
            raise ValueError("获取分享信息失败！")
        else:
            link_info = json.loads(info[0])
        return link_info

    def get_link_data(self, link_url, pass_code):
        link_info = self.get_share_link_info(link_url, pass_code)
        shareid = link_info['shareid']
        user_id = link_info['share_uk']
        file_list = [{'fs_id': i['fs_id'], 'filename': i['server_filename'], 'isdir': i['isdir']} for i in
                     link_info['file_list']]
        if len(file_list) == 0:
            raise ValueError('文件列表为空！')
        return {'shareid': shareid, 'user_id': user_id, 'file_list': file_list}

    def transfer_common(self, link):
        link_url, pass_code, unzip_code = parse_url_and_code(link)
        link_data = self.get_link_data(link_url, pass_code)
        shareid, user_id = link_data['shareid'], link_data['user_id']
        fs_id_list = [str(data['fs_id']) for data in link_data['file_list']]
        self.transfer_files(shareid, user_id, fs_id_list, self.dir_name, unzip_code)

    def transfer_repid(self, link):
        rapid_data = link.split('#', maxsplit=3)
        self.transfer_files_repid(rapid_data, self.dir_name)

    def transfer(self, link_list):
        link_list = link_format(link_list)
        for link in link_list:
            try:
                self.logs(END, '正在转存:' + link + '\n')
                link_type = check_link_type(link)
                if link_type == 'common':
                    self.transfer_common(link)
                elif link_type == 'rapid':
                    self.transfer_repid(link)
                else:
                    raise ValueError('未知链接类型')
            except Exception as e:
                self.logs(END, 'Transfer Error --- ' + str(e) + '\n\n')
        self.logs(END, '转存完成！' + '\n')

    def logs(self, index, text):
        self.gui.log_data_Text.insert(index, text)


def main(gui):
    try:
        gui.log_data_Text.delete(1.0, END)
        if gui.link_data_Text.get(1.0, END) == '\n' or gui.cookie_data_Text.get(1.0, END) == '\n':
            gui.log_data_Text.insert(END, 'cookie或链接不能为空！ ' + '\n\n')
            return
        dir_name = "".join(gui.dirname_data_Text.get(1.0, END).split())
        cookie = "".join(gui.cookie_data_Text.get(1.0, END).split())
        user_agent = ''
        link_list = gui.link_data_Text.get(1.0, END).split('\n')

        pan_transfer = PanTransfer(cookie, user_agent, dir_name, gui)
        pan_transfer.transfer(link_list)
    except Exception as e:
        gui.log_data_Text.insert(END, 'Error --- ' + str(e) + '\n\n')


def gui_start():
    init_window = Tk()
    gui = GUI(init_window)
    gui.set_init_window()
    init_window.mainloop()


gui_start()
