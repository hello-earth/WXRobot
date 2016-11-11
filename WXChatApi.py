# -*- coding: UTF-8 -*-
#

import httplib2,json


def http_get(url):
    conn = httplib2.Http(timeout=37)
    response, content = conn.request(uri=url, method='GET')
    return content


class WXChatApi(object):

    def __init__(self):
        self.CHAT_BSSE = "http://api.qingyunke.com/api.php?key=free&appid=0&msg="

    def getAnswer(self,question):
        url = self.CHAT_BSSE+question
        encoded_json = http_get(url)
        decode_json = json.loads(encoded_json)
        return decode_json['content'].encode('u8')


if __name__ == '__main__':
    print WXChatApi().getAnswer("你好".decode('u8'))