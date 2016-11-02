# -*- coding:utf-8 -*-
"""
python wx_robot.py
注意事项：
1.机器人运行期间不能该账号不能在手机退出，这样机器人会被强制下线
2.机器人运行期间不能再登录桌面微信或者web网页微信，这样机器人也会被强制下线
3.以上操作都会导致本地的cookie和其他信息失效，如果是实验阶段可以清除cookie.txt内容，删除robot.json文件，然后启动
"""
import copy
import re
import json
import os
import sys
import time
import random
import urllib
import xml.dom.minidom
import httplib2
from PIL import Image

ROBOT_INFO_FILE = os.path.join(os.getcwd(), 'robot.json')
ROBOT_COOKIE_FILE = os.path.join(os.getcwd(), 'cookie.txt')

TIMEOUT = 30
WX_URLS = {
    'jslogin': 'https://login.weixin.qq.com/jslogin?%s',
    'qrcode': 'https://login.weixin.qq.com/qrcode/%s',
    'login': 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s',
}
DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:18.0) Gecko/20100101 Firefox/18.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-us,en;q=0.5',
    'Accept-Encoding': 'gzip',
    'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
    'Keep-Alive': '115',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0'
}


def update_cookie(response):
    global DEFAULT_HEADERS
    if response.get('set-cookie'):
        cookie = re.sub(r'Domain.*?GMT,?', '', response['set-cookie'])
        DEFAULT_HEADERS['Cookie'] = cookie
        with open(ROBOT_COOKIE_FILE, 'wb') as fp:
            fp.write(DEFAULT_HEADERS['Cookie'])


def http_post(url, params):
    global DEFAULT_HEADERS
    headers = copy.deepcopy(DEFAULT_HEADERS)
    headers['ContentType'] = 'application/json; charset=UTF-8'
    conn = httplib2.Http(timeout=TIMEOUT)
    response, content = conn.request(uri=url, method='POST', headers=headers, body=json.dumps(params))
    update_cookie(response)
    return content


def http_get(url):
    conn = httplib2.Http(timeout=TIMEOUT)
    response, content = conn.request(uri=url, method='GET', body=None, headers=DEFAULT_HEADERS)
    update_cookie(response)
    return content


def get_icon(self, user_id):
    url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgeticon?username=%s' % user_id
    content = http_get(url)
    tmp_fn = 'img_%s.jpg' % user_id
    with open(tmp_fn, 'wb') as fp:
        fp.write(content)
    return tmp_fn


class WeiXinRobot(object):
    def __init__(self):
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.uuid = ''
        self.redirect_uri = ''
        self.base_uri = ''

        self.skey = ''
        self.sid = ''
        self.uin = ''
        self.pass_ticket = ''
        self.BaseRequest = {}

        self.User = {}
        self.SyncKey = []
        self.sync_key = ''
        self.sync_host = ''

        self.group_list = []
        self.group_member_dict = {}

    def __json__(self):
        json_data = {}
        for k, v in self.__dict__.items():
            if isinstance(v, (int, bool, str, unicode, list, dict)):
                json_data[k] = v
        return json_data

    def _echo(self, message, ends=''):
        sys.stdout.write(message + ends)
        sys.stdout.flush()

    def _run(self, msg, func, *args):
        self._echo(msg)
        if func(*args):
            self._echo(u'成功', '\n')
        else:
            self._echo(u'失败\n[*] 退出程序')
            exit()

    def get_uuid(self):
        params = {
            'appid': 'wx782c26e4c19acffb',
            'fun': 'new',
            'lang': 'zh_CN',
            '_': int(time.time()),
        }
        content = http_get(WX_URLS['jslogin'] % urllib.urlencode(params))
        regex = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        matches = re.search(regex, content)
        if matches and matches.group(1) == '200':
            self.uuid = matches.group(2)
            return True
        return False

    def gen_qr_code(self):
        qr_code_path = os.path.join(os.getcwd(), 'qrcode.jpg')
        content = http_get(WX_URLS['qrcode'] % self.uuid)
        with open(qr_code_path, 'wb') as f:
            f.write(content)
        image = Image.open(qr_code_path)
        image.show()
        return True

    def wait_for_login(self, tip=1):
        time.sleep(tip)
        content = http_get(WX_URLS['login'] % (tip, self.uuid, str(time.time())))
        matches = re.search(r'window.code=(\d+);', content)
        code = int(matches.group(1))

        if code == 201:  # 手机扫描识别成功
            return True
        if code == 200:  # 确认按钮点击成功
            matches = re.search(r'window.redirect_uri="(\S+?)";', content)
            self.redirect_uri = matches.group(1) + '&fun=new'
            self.base_uri = self.redirect_uri[:self.redirect_uri.rfind('/')]
            return True
        if code == 408:
            self._echo('[登陆超时] ')
            return False
        self._echo('[登陆异常] ')
        return False

    def login(self):
        content = http_get(self.redirect_uri)
        doc = xml.dom.minidom.parseString(content)
        root = doc.documentElement
        for node in root.childNodes:
            if node.nodeName == 'skey':
                self.skey = node.childNodes[0].data
            elif node.nodeName == 'wxsid':
                self.sid = node.childNodes[0].data
            elif node.nodeName == 'wxuin':
                self.uin = node.childNodes[0].data
            elif node.nodeName == 'pass_ticket':
                self.pass_ticket = node.childNodes[0].data

        if all((self.skey, self.sid, self.uin, self.pass_ticket)):
            self.BaseRequest = {'Skey': self.skey, 'Sid': self.sid, 'Uin': int(self.uin), 'DeviceID': self.deviceId}
            return True
        return False

    def wx_init(self):
        url = self.base_uri + '/webwxinit?pass_ticket=%s&skey=%s&r=%s' % (self.pass_ticket, self.skey, int(time.time()))
        content = http_post(url, {'BaseRequest': self.BaseRequest})
        json_data = json.loads(content)
        self.User = json_data['User']  # 我

        self.SyncKey = json_data['SyncKey']
        self.sync_key = '|'.join([str(item['Key']) + '_' + str(item['Val']) for item in self.SyncKey['List']])
        return json_data['BaseResponse']['Ret'] == 0

    def wx_notify(self):
        url = self.base_uri + '/webwxstatusnotify?lang=zh_CN&pass_ticket=%s' % self.pass_ticket
        params = {
            "Code": 3,
            'BaseRequest': self.BaseRequest,
            "FromUserName": self.User['UserName'],
            "ToUserName": self.User['UserName'],
            "ClientMsgId": int(time.time())
        }
        try:
            content = http_post(url, params)
            json_data = json.loads(content)
            return json_data['BaseResponse']['Ret'] == 0
        except:
            return 0

    def wx_group_list(self):
        url = '%s/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.base_uri, self.pass_ticket, self.skey, int(time.time()))
        content = http_get(url)
        json_data = json.loads(content)
        self.group_list = [member for member in json_data['MemberList'] if member['UserName'].startswith('@@')]
        return True

    def wx_group_members(self, group_list=None):
        group_list = group_list or [{'UserName': g['UserName'], 'ChatRoomId': ''} for g in self.group_list]
        url = '%s/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
            self.base_uri, int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'Count': len(group_list),
            'List': group_list
        }
        content = http_post(url, params)
        json_data = json.loads(content)
        old_group_list = [g['UserName'] for g in self.group_list]
        for group in json_data['ContactList']:
            self.group_member_dict[group['UserName']] = group['MemberList']
            if group['UserName'] not in old_group_list:
                del group['MemberList']
                self.group_list.append(group)

        if group_list:
            # TODO: 同步粉丝信息到数据库
            with open(ROBOT_INFO_FILE, 'wb') as fp:
                fp.write(json.dumps(self.__json__()))
        return (json_data['Count']==0 or json_data['BaseResponse']['Ret'] == 0)

    def sync_check(self, host):
        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.deviceId,
            'synckey': self.sync_key,
            '_': int(time.time()),
        }
        url = 'https://%s/cgi-bin/mmwebwx-bin/synccheck?%s' % (host, urllib.urlencode(params))
        content = http_get(url)
        matches = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', content)
        if(matches):
            return matches.group(1), matches.group(2)
        else:
            return -1,-1

    def sync(self):
        sync_host_list = [
            'webpush.weixin.qq.com',
            'webpush2.weixin.qq.com',
            'webpush.wechat.com',
            'webpush1.wechat.com',
            'webpush2.wechat.com',
            'webpush1.wechatapp.com',
            'webpush.wechatapp.com'
        ]
        for host in sync_host_list:
            self.sync_check(host)
            retcode, selector = self.sync_check(host)
            if retcode == '0':
                self.sync_host = host
                return True

    def wx_message_sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': ~int(time.time())
        }
        content = http_post(url, params)
        try:
            json_data = json.loads(content)
            if json_data['BaseResponse']['Ret'] == 0:  # 更新同步键
                self.SyncKey = json_data['SyncKey']
                self.sync_key = '|'.join([str(item['Key']) + '_' + str(item['Val']) for item in self.SyncKey['List']])
            return json_data
        except:
            return None

    def get_nickname(self, group_id, user_id=None, retry=3):
        while retry:
            retry -= 1
            if user_id:
                target = user_id
                check_list = self.group_member_dict.get(group_id, [])
            else:
                target = group_id
                check_list = self.group_list
            for item in check_list:
                if item['UserName'] == target:
                    return item['NickName']
            # 没有记录就去服务器查一遍
            self.wx_group_members([{'UserName': group_id, 'ChatRoomId': ''}])

    def handle_message(self, json_data):
        if not json_data:
            return
        #print json_data
        for message in json_data['AddMsgList']:
            msg_type = message['MsgType']
            content = message['Content'].replace('&lt;', '<').replace('&gt;', '>')
            group_id = message['FromUserName']
            if group_id.startswith('@@'): #群消息
                group_name = self.get_nickname(group_id)
                if(content.find(':<br/>')>0):
                    fans_id, content = content.split(':<br/>')
                    fans_name = self.get_nickname(group_id, fans_id)
                # group_id, fans_id, fans_name, current_time
                if msg_type == 1:  # 消息
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, content), '\n')
                elif msg_type == 3:  # 图片
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'图片'), '\n')
                elif msg_type == 34:  # 语音
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'语音'), '\n')
                elif msg_type == 42:  # 名片
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'名片'), '\n')
                elif msg_type == 47:  # 动画表情
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'表情'), '\n')
                elif msg_type == 51:  # 退出群
                    # TODO: 退出群聊，将该粉丝设置为已经退出
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'退出群聊'), '\n')
                elif msg_type == 62:  # 视频
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'视频'), '\n')
                elif msg_type == 10000:  # 进入群
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'进入群聊'), '\n')
                    self.wx_group_members([{'UserName': group_id, 'ChatRoomId': ''}])
                elif msg_type == 10002:  # 撤回消息
                    self._echo(u'%s@%s: %s' % (fans_name, group_name, u'撤回了一条消息'), '\n')
                else:
                    self._echo(u'%s@%s: 消息类型<%s>' % (fans_name, group_name, str(msg_type)), '\n')
            elif group_id.startswith('@'):  # 个人消息
                fans_name = self.get_nickname(group_id)
                # group_id, fans_id, fans_name, current_time
                if msg_type == 1:  # 消息
                    self._echo(u'%s: %s' % (fans_name, content), '\n')
                    self.wx_sendmsg('<msg><appmsg appid="" sdkver="0"><title>抢红包活动</title><des>分享了浦发红包，快来开红包，天天享鸿运！</des><action></action><type>5</type><showtype>0</showtype><mediatagname></mediatagname><messageext></messageext><messageaction></messageaction><content></content><contentattr>0</contentattr><url>https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do?packetId=PVCDBJ41DQ8417CY463280469-14776534040007d9e6b91&amp;amp;status=share&amp;amp;noCheck=1</url><lowurl></lowurl><dataurl></dataurl><lowdataurl></lowdataurl><appattach><totallen>0</totallen><attachid></attachid><emoticonmd5></emoticonmd5><fileext></fileext><cdnthumburl>304d02010004463044020100020466a4081002033d0af70204768e1e6f020458192f8e0422313530313834303736334063686174726f6f6d323838345f313437383034353537390201000201000400</cdnthumburl><cdnthumbmd5></cdnthumbmd5><cdnthumblength>6576</cdnthumblength><cdnthumbwidth>160</cdnthumbwidth><cdnthumbheight>160</cdnthumbheight><cdnthumbaeskey>37313966666639663966363565376139</cdnthumbaeskey><aeskey>37313966666639663966363565376139</aeskey><encryver>0</encryver></appattach><extinfo></extinfo><sourceusername>spdbccc4008208788</sourceusername><sourcedisplayname>浦发银行信用卡</sourcedisplayname><commenturl></commenturl><thumburl>https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/redpacket_opt/images/skin1/packetShare.PNG</thumburl><md5></md5><statextstr></statextstr></appmsg></msg>',group_id)
                elif msg_type == 49:  # 分享
                    self._echo(u'%s: %s' % (fans_name, content), '\n')
                    self.wx_sendmsg('<appmsg appid="" sdkver="0"><title>抢红包活动</title><des>分享了浦发红包，快来开红包，天天享鸿运！</des><action></action><type>5</type><showtype>0</showtype><mediatagname></mediatagname><messageext></messageext><messageaction></messageaction><content></content><contentattr>0</contentattr><url>https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do?packetId=PVCDBJ41DQ8417CY463280469-14776534040007d9e6b91&amp;amp;status=share&amp;amp;noCheck=1</url><lowurl></lowurl><dataurl></dataurl><lowdataurl></lowdataurl><appattach><totallen>0</totallen><attachid></attachid><emoticonmd5></emoticonmd5><fileext></fileext><cdnthumburl>304d02010004463044020100020466a4081002033d0af70204768e1e6f020458192f8e0422313530313834303736334063686174726f6f6d323838345f313437383034353537390201000201000400</cdnthumburl><cdnthumbmd5></cdnthumbmd5><cdnthumblength>6576</cdnthumblength><cdnthumbwidth>160</cdnthumbwidth><cdnthumbheight>160</cdnthumbheight><cdnthumbaeskey>37313966666639663966363565376139</cdnthumbaeskey><aeskey>37313966666639663966363565376139</aeskey><encryver>0</encryver></appattach><extinfo></extinfo><sourceusername>spdbccc4008208788</sourceusername><sourcedisplayname>浦发银行信用卡</sourcedisplayname><commenturl></commenturl><thumburl>https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/redpacket_opt/images/skin1/packetShare.PNG</thumburl><md5></md5><statextstr></statextstr></appmsg>',group_id)
                elif msg_type == 3:  # 图片
                    self._echo(u'%s: %s' % (fans_name, u'图片'), '\n')
                elif msg_type == 34:  # 语音
                    self._echo(u'%s: %s' % (fans_name, u'语音'), '\n')
                elif msg_type == 42:  # 名片
                    self._echo(u'%s: %s' % (fans_name, u'名片'), '\n')
                elif msg_type == 47:  # 动画表情
                    self._echo(u'%s: %s' % (fans_name, u'表情'), '\n')
                elif msg_type == 62:  # 视频
                    self._echo(u'%s: %s' % (fans_name, u'视频'), '\n')
                elif msg_type == 10002:  # 撤回消息
                    self._echo(u'%s: %s' % (fans_name, u'撤回了一条消息'), '\n')
                else:
                    self._echo(u'%s: 消息类型<%s>' % (fans_name, str(msg_type)), '\n')

    def wx_sendmsg(self,content,ToUserName):
        id = int(time.time());
        msg = {"Type": 1, "Content": content,"ClientMsgId":id,"FromUserName":self.User['UserName'],\
               "ToUserName":ToUserName,"LocalID":id,"Type":1}
        url = self.base_uri + '/webwxsendmsg'#cgi-bin/mmwebwx-bin
        params = {
            'BaseRequest': self.BaseRequest,
            'Msg': msg,
            'Scene': 0
        }
        content = http_post(url, params)
        json_data = json.loads(content)
        print  json_data['MsgID']!=""


    def wx_sync_loop(self):
        self._run(u'[*] 进入消息监听模式 ...', self.sync)
        while True:
            retcode, selector = self.sync_check(self.sync_host)
            if retcode == '0':
                if selector == '0':  # 没有新消息, 也没有异常
                    time.sleep(1)
                elif selector == '2':  # 有新消息
                    self.handle_message(self.wx_message_sync())

    def main(self):
        global ROBOT_COOKIE_FILE, ROBOT_INFO_FILE, DEFAULT_HEADERS
        self._echo(u'微信机器人启动：\n')
        if os.path.exists(ROBOT_INFO_FILE):  # 从文件加载初始化信息
            with open(ROBOT_INFO_FILE) as fp:
                json_data = json.loads(fp.read())
                for field, value in json_data.items():
                    self.__dict__[field] = value
            with open(ROBOT_COOKIE_FILE) as fp:
                DEFAULT_HEADERS['Cookie'] = fp.read()
        else:
            self._run(u'[*] 正在获取 uuid ... ', self.get_uuid)
            self._run(u'[*] 正在获取二维码 ... ', self.gen_qr_code)
            self._run(u'[*] 扫描二维码登录 ... ', self.wait_for_login)
            self._run(u'[*] 确认登录 ... ', self.wait_for_login, 0)
            self._run(u'[*] 正在登录 ... ', self.login)
            self._run(u'[*] 正在初始化 ... ', self.wx_init)
            self._run(u'[*] 正在开启通知 ... ', self.wx_notify)
            self._run(u'[*] 正在获取群聊列表 ... ', self.wx_group_list)
            self._run(u'[*] 正在获取各群成员 ... ', self.wx_group_members)
            with open(ROBOT_INFO_FILE, 'wb') as fp:
                fp.write(json.dumps(self.__json__()))

        self._echo(u'微信机器人成功启动！', '\n')
        try:
            self.wx_sync_loop()
        except KeyboardInterrupt:
            self._echo(u'微信机器人成功退出！', '\n')
            exit()


if __name__ == '__main__':
    WeiXinRobot().main()
