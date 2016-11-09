import ftplib

class FTPHelper(object):

    def __init__(self):
        self.session = ftplib.FTP('vhost163.cloudvhost.cn','webmaste','(*f')

    def upload_file(self,spath,tpath):
        file = open(spath,'rb')
        self.session.storbinary('STOR %s'%tpath, file)
        file.close()

    def __del__(self):
        self.session.quit()


if __name__ == '__main__':
    FTP = FTPHelper()
    FTP.upload_file("./config/base31aa32.css","/WEB/base31aa32.css")
