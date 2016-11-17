# -*- coding: UTF-8 -*-
#

import MysqlDBHelper,NetUtils,WXRobot,time
import threading


def watchDog():
    time.sleep(60)
    while dbhp:
        print 'watchdog is alive.'
        sql = "select needrestart from wxrobot_status limit 0,1"
        result = dbhp.query(sql)
        if (result[0] == 1):
            print 'restarting....'
            net.GET_DEFAULT_HEADERS['Cookie'] = ''
            net.POST_DEFAULT_HEADERS['Cookie'] = ''
            restartWXRBT()
        time.sleep(5)


def startWXRBT():
    global robot
    robot = WXRobot.WeiXinRobot(net, dbhp)
    robot.isRuning = True
    robot.main()


task=[]

def restartWXRBT():
    if(len(task)==2 and task[0]):
        print 'stop wxrobot service'
        global  robot,net,dbhp
        del dbhp,net
        dbhp = MysqlDBHelper.MysqlDBHelper()
        net = NetUtils.requestHelper()
        robot.isRuning = False
        time.sleep(3)

    print 'restart wxrobot service'
    task[0] = threading.Thread(target=startWXRBT)
    task[0].start()


if __name__ == '__main__':
    dbhp = MysqlDBHelper.MysqlDBHelper()
    net = NetUtils.requestHelper()
    robot = None
    task.append(0)
    restartWXRBT()
    task.append(threading.Thread(target=watchDog))
    task[1].start()


