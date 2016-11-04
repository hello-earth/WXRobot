# -*- coding: utf8 -*-
import MySQLdb

class MysqlDBHelper(object):

    def __init__(self):
        self.conn=MySQLdb.connect(host='',user="",passwd="",db="",charset="utf8")
        self.cursor = self.conn.cursor()

    def __del__(self):
        print 'delete myself'
        if(self.cursor):
            self.cursor.close()
        if (self.conn):
            self.conn.close()

    def runSql(self, sql):
        n = self.cursor.execute(sql)
        self.conn.commit()
        print n


if __name__ == '__main__':
    sql = sql = "insert into spd_wxprp(id,url,provider,usetimes,time) values(NULL,'https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do?packetId=PVCDBJ41DQ8417CY463280469-14776534040007d9e6b91&amp;amp;status=share&amp;amp;noCheck=1','clxy','0','2016-11-23 00:00:00')"
    MysqlDBHelper().runSql(sql)
