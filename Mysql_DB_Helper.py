# -*- coding: utf8 -*-
import MySQLdb
conn=MySQLdb.connect(host='vjtv4pkd.zzcdb.dnstoo.com',
                    user='mblog_f',
                    passwd='TjbqtXI01cefX',
                    db='mblog')
cursor = conn.cursor()
cursor.execute ("insert into spd_wxprp values(NULL,'https://weixin.spdbccc.com.cn/spdbcccWeChatPageRedPackets/StatusDistrubServlet.do?packetId=PVCDBJ41DQ8417CY463280469-14776534040007d9e6b91&amp;amp;status=share&amp;amp;noCheck=1','clxy','0','2016-11-23 00:00:00');")
# row = cursor.fetchone ()
# print "server version:", row
cursor.close()
conn.close()