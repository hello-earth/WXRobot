# -*- coding:utf-8 -*-

import os,re,httplib2,json,time
import FtpHelper


class requestHelper(object):

    def __init__(self):
        self.ROBOT_INFO_FILE = os.path.join(os.getcwd(), r'./config/robot.json')
        self.ROBOT_COOKIE_FILE = os.path.join(os.getcwd(), r'./config/cookie.txt')
        self.ROBOT_QRPIC_FILE = os.path.join(os.getcwd(), r'./config/qrcode.jpg')
        self.ROBOT_QRHTML_FILE = os.path.join(os.getcwd(), r'./config/wechat.html')
        self.ROBOT_QRHTML_BAK_FILE = os.path.join(os.getcwd(), r'./config/index.html.bak')
        self.TIMEOUT = 50

        self.FTP = FtpHelper.FTPHelper()

        self.GET_DEFAULT_HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'gzip, deflate, sdch, br',
            'Accept-Encoding': 'gzip',
            'Connection': 'keep-alive',
        }

        self.POST_DEFAULT_HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'ContentType': 'application/json; charset=UTF-8'
        }

    def update_cookie(self,response):
        if response.get('set-cookie'):
            cookie = re.sub(r'Domain.*?GMT,?', '', response['set-cookie'])
            self.GET_DEFAULT_HEADERS['Cookie'] = cookie
            self.POST_DEFAULT_HEADERS['Cookie'] = cookie
            with open(self.ROBOT_COOKIE_FILE, 'wb') as fp:
                fp.write(self.GET_DEFAULT_HEADERS['Cookie'])

    def update_html(self):
        now = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        content = ""
        with open(self.ROBOT_QRHTML_BAK_FILE, 'r') as fp:
            content = fp.read().decode('u8')
            fp.close()
        content = content.replace('<p>time</p>', u'<p class="sub_content">更新于: %s</p>' % now).replace(
            "./qrcode.jpg",
            "./qrcode.jpg?%s" % time.time())
        with open(self.ROBOT_QRHTML_FILE, 'wb') as fp:
            fp.write(content.encode("u8"))
            fp.close()
        self.FTP.upload_file(self.ROBOT_QRHTML_FILE, "/WEB/wxrobot/index.html")
        self.FTP.upload_file(self.ROBOT_QRPIC_FILE, "/WEB/wxrobot/qrcode.jpg")

    def http_post(self, url, params):
        conn = httplib2.Http(timeout=self.TIMEOUT)
        json_obj = json.dumps(params, ensure_ascii=False).encode('u8')
        response, content = conn.request(uri=url, method='POST', headers=self.POST_DEFAULT_HEADERS, body=json_obj)
        self.update_cookie(response)
        return content

    def http_get(self, url):
        conn = httplib2.Http(timeout=self.TIMEOUT)
        response, content = conn.request(uri=url, method='GET', body=None, headers=self.GET_DEFAULT_HEADERS)
        self.update_cookie(response)
        return content

    def __del__(self):
        print 'delete netUtil connect'
        if(self.FTP):
            del self.FTP

if __name__ == '__main__':
    net = requestHelper()
    print net.http_get("https://www.baidu.com")