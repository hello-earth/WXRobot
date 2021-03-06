# -*- coding:utf-8 -*-


import re
import json
import os
import sys
import time
import random
import urllib
import xml.dom.minidom
import threading
import WXChatApi

WX_URLS = {
    'jslogin': 'https://login.weixin.qq.com/jslogin?%s',
    'qrcode': 'https://login.weixin.qq.com/qrcode/%s',
    'login': 'https://login.weixin.qq.com/cgi-bin/mmwebwx-bin/login?tip=%s&uuid=%s&_=%s',
}

class WeiXinRobot(object):

    def __init__(self, net, dbHelper):
        self.deviceId = 'e' + repr(random.random())[2:17]
        self.uuid = ''
        self.redirect_uri = ''
        self.base_uri = ''
        self.dbHelper = dbHelper
        self.net = net
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

        self.last_update_record = 1.0
        self.interval_update_record = 60.0
        self.isRuning = True

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
        content = self.net.http_get(WX_URLS['jslogin'] % urllib.urlencode(params))
        regex = r'window.QRLogin.code = (\d+); window.QRLogin.uuid = "(\S+?)"'
        matches = re.search(regex, content)
        if matches and matches.group(1) == '200':
            self.uuid = matches.group(2)
            return True
        return False

    def gen_qr_code(self):
        qr_code_path = os.path.join(os.getcwd(), self.net.ROBOT_QRPIC_FILE)
        content = self.net.http_get(WX_URLS['qrcode'] % self.uuid)
        with open(qr_code_path, 'wb') as f:
            f.write(content)

        self.net.update_html()

        print "二维码已生成，请扫码"
        return True

    def get_headimg(self, url):
        content = self.net.http_get(url)
        tmp_fn = r'./config/img_robot.jpg'
        with open(tmp_fn, 'wb') as fp:
            fp.write(content)
        return tmp_fn

    def wait_for_login(self, tip=1):
        times = 0
        while times < 30:
            time.sleep(5)
            content = self.net.http_get(WX_URLS['login'] % (tip, self.uuid, str(time.time())))
            matches = re.search(r'window.code=(\d+);', content)
            code = int(matches.group(1))
            if code == 201:  # 手机扫描识别成功
                return True
            if code == 200:  # 确认按钮点击成功
                matches = re.search(r'window.redirect_uri="(\S+?)";', content)
                self.redirect_uri = matches.group(1) + '&fun=new'
                self.base_uri = self.redirect_uri[:self.redirect_uri.rfind('/')]
                return True
            times += 1
        self._echo('[登陆异常] ')
        return False

    def login(self):
        content = self.net.http_get(self.redirect_uri)
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
        content = self.net.http_post(url, {'BaseRequest': self.BaseRequest})
        json_data = json.loads(content)
        self.User = json_data['User']  # 我
        self.SyncKey = json_data['SyncKey']
        self.sync_key = '|'.join([str(item['Key']) + '_' + str(item['Val']) for item in self.SyncKey['List']])
        self.get_headimg("https://wx.qq.com" + self.User['HeadImgUrl'])
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
            content = self.net.http_post(url, params)
            json_data = json.loads(content)
            return json_data['BaseResponse']['Ret'] == 0
        except:
            return 0

    def wx_group_list(self):
        url = '%s/webwxgetcontact?pass_ticket=%s&skey=%s&r=%s' % (
            self.base_uri, self.pass_ticket, self.skey, int(time.time()))
        try:
            content = self.net.http_get(url)
            json_data = json.loads(content)
            self.group_list = [member for member in json_data['MemberList'] if member['UserName'].startswith('@@')]
            return True
        except:
            return False

    def wx_group_members(self, group_list=None):
        group_list = group_list or [{'UserName': g['UserName'], 'ChatRoomId': ''} for g in self.group_list]
        url = '%s/webwxbatchgetcontact?type=ex&r=%s&pass_ticket=%s' % (
            self.base_uri, int(time.time()), self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'Count': len(group_list),
            'List': group_list
        }
        try:
            content = self.net.http_post(url, params)
            json_data = json.loads(content)
            old_group_list = [g['UserName'] for g in self.group_list]
            for group in json_data['ContactList']:
                self.group_member_dict[group['UserName']] = group['MemberList']
                if group['UserName'] not in old_group_list:
                    del group['MemberList']
                    self.group_list.append(group)

            if group_list:
                # TODO: 同步粉丝信息到数据库
                with open(self.net.ROBOT_INFO_FILE, 'wb') as fp:
                    fp.write(json.dumps(self.__json__()))
            return (json_data['Count'] == 0 or json_data['BaseResponse']['Ret'] == 0)
        except:
            return False

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
        # print json_data
        for message in json_data['AddMsgList']:
            msg_type = message['MsgType']
            content = message['Content'].replace('&lt;', '<').replace('&gt;', '>').replace('amp;', '').replace(' ', '')
            group_id = message['FromUserName']
            if group_id.startswith('@@'):  # 群消息
                group_name = self.get_nickname(group_id)
                if (content.find(':<br/>') > 0):
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
                if (fans_name == ''):
                    return
                # group_id, fans_id, fans_name, current_time
                if msg_type == 1:  # 消息
                    self._echo(u'%s,%s: %s' % (fans_name, group_id, content), '\n')
                    self.wx_sendmsg(content, group_id)
                elif msg_type == 49:  # 分享
                    self._echo(u'%s,%s: %s' % (fans_name, group_id, u'收到分享，可能是浦发红包.'), '\n')
                    rpr = re.compile('<url>(.*?)</url>'.decode('u8')).findall(content)[0]
                    if (rpr.startswith(
                            'https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do') and self.dbHelper):
                        sql = "insert into spd_wxprp(id,url,provider,usetimes,time) values(NULL,'%s','%s','0','%s')" % (
                            rpr, fans_name, time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                        self.dbHelper.runSql(sql)
                        self.wx_sendmsg(u'红包已记录', group_id, 0)
                    else:
                        self.wx_sendmsg(u'别给我这些烂七八糟的东西，红包我只要浦发的！', group_id, 0)
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
                elif msg_type == 10000:  # 红包
                    print u"收到红包"
                    self.wx_sendmsg(u"谢谢老板", group_id)
                elif msg_type == 10002:  # 撤回消息
                    self._echo(u'%s: %s' % (fans_name, u'撤回了一条消息'), '\n')
                else:
                    self._echo(u'%s: 消息类型<%s>, %s' % (fans_name, str(msg_type), content), '\n')

    def wx_sendmsg(self, content, ToUserName, needapi=1):
        if (needapi):
            content = WXChatApi.WXChatApi().getAnswer(content)
        id = int(time.time());
        msg = {"Type": 1, "Content": content, "ClientMsgId": id, "FromUserName": self.User['UserName'], \
               "ToUserName": ToUserName, "LocalID": id}
        url = self.base_uri + '/webwxsendmsg'  # cgi-bin/mmwebwx-bin
        params = {
            'BaseRequest': self.BaseRequest,
            'Msg': msg,
            'Scene': 0
        }
        content = self.net.http_post(url, params)
        json_data = json.loads(content)
        print  json_data['MsgID'] != ""

    def sync_check(self, host):
        print "i am alive %s" % time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))

        params = {
            'r': int(time.time()),
            'sid': self.sid,
            'uin': self.uin,
            'skey': self.skey,
            'deviceid': self.deviceId,
            'synckey': self.sync_key,
            '_': int(time.time()),
        }
        try:
            url = 'https://%s/cgi-bin/mmwebwx-bin/synccheck?%s' % (host, urllib.urlencode(params))
            content = self.net.http_get(url)
            matches = re.search(r'window.synccheck=\{retcode:"(\d+)",selector:"(\d+)"\}', content)
            if (matches):
                return matches.group(1), matches.group(2)
            else:
                print 'get messge fail'
                if (content == ""):
                    print 'get message info fail, waniting 5s.'
                    time.sleep(5)
                    return '0', '0'
                else:
                    print content
                    return '-1', '-1'
        except Exception, e:
            if (e.message.find("httplib2.CertificateHostnameMismatch")):
                print 'session have expired.'
                return '-1', '-1'
            else:
                if (self.dbHelper):
                    sql = "update  wxrobot_status set nickname='%s',status='%s',last_uptime='%s'" % (
                        "Young", '0', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                    self.dbHelper.runSql(sql)
                raise e

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
            retcode, selector = self.sync_check(host)
            if retcode == '0':
                self.sync_host = host
                return True
        return False

    def wx_message_sync(self):
        url = self.base_uri + '/webwxsync?sid=%s&skey=%s&pass_ticket=%s' % (self.sid, self.skey, self.pass_ticket)
        params = {
            'BaseRequest': self.BaseRequest,
            'SyncKey': self.SyncKey,
            'rr': ~int(time.time())
        }
        content = self.net.http_post(url, params)
        try:
            json_data = json.loads(content)
            if json_data['BaseResponse']['Ret'] == 0:  # 更新同步键
                self.SyncKey = json_data['SyncKey']
                self.sync_key = '|'.join([str(item['Key']) + '_' + str(item['Val']) for item in self.SyncKey['List']])
            return json_data
        except:
            return None

    def wx_sync_loop(self):
        flag = self.sync();
        if (flag):
            self._echo(u'[*] 进入消息监听模式 ...')
            t = threading.Thread(target=self.wx_sysnc_loop_threader, args='')
            t.start()
        else:
            print(u'微信机器人重新启动：\n***************************')
            if os.path.exists(self.net.ROBOT_INFO_FILE):
                os.remove(self.net.ROBOT_INFO_FILE)
            if os.path.exists(self.net.ROBOT_COOKIE_FILE):
                os.remove(self.net.ROBOT_COOKIE_FILE)
            if os.path.exists(self.net.ROBOT_QRPIC_FILE):
                os.remove(self.net.ROBOT_QRPIC_FILE)
            self.main();

    def wx_sysnc_loop_threader(self):
        while self.isRuning:
            retcode, selector = self.sync_check(self.sync_host)
            now = time.time()
            if retcode == '0':
                if selector == '0':  # 没有新消息, 也没有异常
                    time.sleep(1)
                elif selector == '2':  # 有新消息
                    self.handle_message(self.wx_message_sync())
                elif (now - self.last_update_record > self.interval_update_record):
                    break

                if (self.dbHelper != None and ((now - self.last_update_record) > self.interval_update_record)):
                    print "更新数据库>>>>>"
                    sql = "update  wxrobot_status set nickname='%s',status='%s',last_uptime='%s'" % (
                        "Young", '1', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
                    self.dbHelper.runSql(sql)
                    self.last_update_record = now
            else:
                print retcode
                break;
            time.sleep(1)

        if (self.dbHelper):
            sql = "update  wxrobot_status set nickname='%s',status='%s',last_uptime='%s'" % (
                "Young", '0', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            self.dbHelper.runSql(sql)

        print(u'清除缓存数据\n=#^^^==+==.=.++===^^^=')
        if os.path.exists(self.net.ROBOT_INFO_FILE):
            os.remove(self.net.ROBOT_INFO_FILE)
        if os.path.exists(self.net.ROBOT_COOKIE_FILE):
            os.remove(self.net.ROBOT_COOKIE_FILE)
        if os.path.exists(self.net.ROBOT_QRPIC_FILE):
            os.remove(self.net.ROBOT_QRPIC_FILE)
        if(self.isRuning):
            print(u'微信机器人重新启动：\n==+.+.==>+======+==.=.++=====')
            self.main();

    def __del__(self):
        if (self.dbHelper):
            sql = "update  wxrobot_status set nickname='%s',status='%s',last_uptime='%s'" % (
                "Young", '0', time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())))
            self.dbHelper.runSql(sql)
            del self.dbHelper

    def main(self):
        if (self.dbHelper):
            sql = "update  wxrobot_status set needrestart=0"
            self.dbHelper.runSql(sql)
        if os.path.exists(self.net.ROBOT_INFO_FILE):  # 从文件加载初始化信息
            with open(self.net.ROBOT_INFO_FILE) as fp:
                json_data = json.loads(fp.read())
                for field, value in json_data.items():
                    self.__dict__[field] = value
            with open(self.net.ROBOT_COOKIE_FILE) as fp:
                self.net.GET_DEFAULT_HEADERS['Cookie'] = fp.read()
                self.net.POST_DEFAULT_HEADERS['Cookie'] = fp.read()
        else:
            self._run(u'[*] 正在获取 uuid ... ', self.get_uuid)
            self._run(u'[*] 正在获取二维码 ... ', self.gen_qr_code)
            self._run(u'[*] 扫描二维码登录 ... ', self.wait_for_login, 1)
            self._run(u'[*] 用户已确认登录 ... ', self.wait_for_login, 0)
            self._run(u'[*] 正在登录 ... ', self.login)
            self._run(u'[*] 正在初始化 ... ', self.wx_init)
            self._run(u'[*] 正在开启通知 ... ', self.wx_notify)
            self._run(u'[*] 正在获取群聊列表 ... ', self.wx_group_list)
            self._run(u'[*] 正在获取各群成员 ... ', self.wx_group_members)
            with open(self.net.ROBOT_INFO_FILE, 'wb') as fp:
                fp.write(json.dumps(self.__json__()))

        self._echo(u'微信机器人成功启动！', '\n')

        try:
            self.wx_sync_loop()
        except KeyboardInterrupt:
            self._echo(u'微信机器人成功退出！', '\n')



if __name__ == '__main__':
    # robot = WeiXinRobot(None)
    import MysqlDBHelper, NetUtils
    dbhp = MysqlDBHelper.MysqlDBHelper()
    net = NetUtils.requestHelper()
    robot = WeiXinRobot(net,dbhp)
    robot.main()

