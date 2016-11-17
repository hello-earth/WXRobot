# -*- coding: utf8 -*-
import MySQLdb

class MysqlDBHelper(object):

    def __init__(self):
        self.conn = MySQLdb.connect(host='',user='',passwd='',db='',charset='')
        self.cursor = self.conn.cursor()

    def __del__(self):
        print 'delete mysql connect'
        if(self.cursor):
            self.cursor.close()
        if (self.conn):
            self.conn.close()

    def runSql(self, sql):
        n = self.cursor.execute(sql)
        self.conn.commit()
        #print n

    def query(self,sql):
        n = self.cursor.execute(sql)
        result = self.cursor.fetchone();
        return result

if __name__ == '__main__':
    sql = "select needrestart from wxrobot_status limit 0,1"
    MysqlDBHelper().query(sql)
