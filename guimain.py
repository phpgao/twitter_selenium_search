#!/usr/bin/env python
# encoding:utf-8
"""twitter selenium search
@author pGhApo www.phpgao.com & sjRyan
@date 2014-12-23
@version 0.3
"""
from selenium import webdriver
from selenium.webdriver.common.proxy import *
from selenium.webdriver.common.desired_capabilities import *
import time
import Tkinter
import datetime
import calendar
import tkMessageBox
import platform

try:
    import MySQLdb
except ImportError:
    import cymysql as MySQLdb

def is_linux():
    if platform.system() == 'Linux':
        return True
    else:
        return False

dbus=''
dbpw=''
dbname=''
dbtable=''
dblogtable=''
class Browser():
    def __init__(self, driver_name="firefox", use_proxy=0):
        """重试次数"""
        self.retry = 3
        """保存临时数据"""
        self.data = {}
        """保存新采集数目"""
        self.data_count = 0
        # 保存数据库
        self.db = Database()
        self.urls = []
        self.wait_second = 6
        if driver_name.lower() == "chrome":
            if use_proxy != 0:
                capabilities = dict(DesiredCapabilities.CHROME)
                if "chromeOptions" not in capabilities:
                    capabilities['chromeOptions'] = {
                        'args': [],
                        'binary': "",
                        'extensions': [],
                        'prefs': {}
                    }
                proxy_address = "127.0.0.1"
                proxy_port = 7777
                capabilities['proxy'] = {
                    'httpProxy': "%s:%i" % (proxy_address, proxy_port),
                    'ftpProxy': "%s:%i" % (proxy_address, proxy_port),
                    'sslProxy': "%s:%i" % (proxy_address, proxy_port),
                    'noProxy': None,
                    'proxyType': "MANUAL",
                    'autodetect': False
                }
                self.driver = webdriver.Chrome(desired_capabilities=capabilities)
            else:
                self.driver = webdriver.Chrome()
        elif driver_name == "firefox":
            if use_proxy != 0:
                my_proxy = "127.0.0.1:7777"
                proxy = Proxy({
                    'proxyType': ProxyType.MANUAL,
                    'httpProxy': my_proxy,
                    'ftpProxy': my_proxy,
                    'sslProxy': my_proxy,
                    'noProxy': ''})
                firefox_profile = FirefoxProfile()
                # Disable CSS
                firefox_profile.set_preference('permissions.default.stylesheet', 2)
                # Disable images
                firefox_profile.set_preference('permissions.default.image', 2)
                # Disable Flash
                firefox_profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
                self.driver = webdriver.Firefox(firefox_profile=firefox_profile, proxy=proxy)
            else:
                self.driver = webdriver.Firefox()

    def get(self, url):
        if url != '':
            self.driver.implicitly_wait(10)
            self.driver.get(url)
            self.analysis_html()
        else:
            raise ValueError('Empty url!')

    def close(self):
        self.driver.close()

    def wait(self, sec):
        """设置等待时间"""
        self.wait_second = sec

    def get_browser(self):
        return self.driver

    def all_twitter(self):
        self.scroll_to_bottom()
        try:
            self.driver.find_element_by_link_text("查看所有推文").click()
            time.sleep(self.wait_second)
        except:
            time.sleep(self.wait_second)

    def analysis_html(self):
        """分析html"""
        append_list = []
        self.all_twitter()
        
        print 'get all tweets'
        
        new_count = self.get_content()
        old_count = 0
        while new_count > old_count:
            print "%dth tweets" % new_count
            print "got %d tweets，scrolling to bottom" % (new_count - old_count)
            for x in range(old_count, new_count):
                # 装载数据
                try:
                    dtext=self.data['texts'][x].text
                except:
                    dtext=" "
                try:
                    dauthors=self.data['authors'][x].text
                except:
                    dauthors=" "
                try:
                    dtime=self.data['times'][x].text
                except:
                    dtime=" "
                try:
                    dreply=self.data['reply'][x]
                except:
                    dreply=" "
                try:
                    dret=self.data['retweets'][x]
                except:
                    dret=" "
                t_dict = {'text': dtext,
                          'author': dauthors,
                          'time': dtime,
                          'reply':dreply,
                          'retweets':dret
                          }
                append_list.append(t_dict)

            print "this time got "+str(len(append_list))+"th data in fact!"
            self.db.batch_insert(append_list)
            
            append_list = []
            old_count = new_count
            self.scroll_to_bottom()
            time.sleep(10)
            new_count = self.get_content()
            """多一次下拉判断"""
            for i in range(self.retry):
                if new_count == old_count:
                    if i==2 :
                        print "data collect is done!"
                        break
                    print "滚动到底没有发现新数据，重试一次"
                    self.scroll_to_bottom()
                    time.sleep(9)
                    new_count=self.get_content()
            if new_count>40000:
                break

        


    def get_cookies(self):
        return self.driver.get_cookies()
        
    def scroll_to_bottom(self):
        print "scrolling to bottom!"
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def load_url(self, path):
        print 'getting url'
        with open(path, 'r') as _f:
            self.urls = [_i.strip('\n') for _i in _f.readlines()]

    def execute_url(self, url):
        """抓取一条url"""
        print "inentifying url %s" % url
        if self.db.is_done(url):
            print "%s already got this url!" % url
        else:
            print "scanning this url %s" % url
            self.db.logger('begin', url)
            self.get(url)
    def get_content(self):
        
        t_texts = self.driver.find_elements_by_class_name('tweet-text')
        t_authors = self.driver.find_elements_by_class_name('show-popup-with-id')
        t_times = self.driver.find_elements_by_class_name('js-short-timestamp')
        reply = self.driver.find_elements_by_class_name('js-actionReply')
        retweets=self.driver.find_elements_by_class_name('js-actionRetweet')
        t_reply=[]
        t_retweets=[]
        for i in reply:
            if cmp(i.text,'')!=0:
                if len(i.text.split('\n'))==2:
                    t_reply.append(i.text.split('\n')[1])
                else:
                    t_reply.append('0')
        for i in retweets:
            if cmp(i.text,'')!=0:
                if len(i.text.split('\n'))==2:
                    t_retweets.append(i.text.split('\n')[1])
                else:
                    t_retweets.append('0')
        self.data = {"texts": t_texts, "authors": t_authors, "times": t_times, "reply":t_reply, "retweets":t_retweets}
        self.data_count = len(t_texts)
        return self.data_count


class Database():
    
    def __init__(self, host="127.0.0.1", user='root', password='1234', port=3306, charset="utf8"):
        try:
            self._db_conn = MySQLdb.connect(host=host, user=dbus, passwd=dbpw, port=port, charset=charset)
            self._db_conn.autocommit(1)
            self._db_cursor = self._db_conn.cursor()
            print "Successfully connect to MySql!"
        except MySQLdb.Error, msg:
            print "MySQL Error %d: %s" % (msg.args[0], msg.args[1])
        
    def set_database(self, database_name):
        """设置数据库"""
        sql = "use %s" % database_name
        self._db_cursor.execute(sql)

    def insert_twitter(self, text='', t_time='', author='', t_replys='', t_retweet='',):
        """插入一条twitter"""
        crawl_time = int(time.time())
        sql = "INSERT INTO "+dbname+"."+dbtable+" (`text`, `time`, `author`,`crawl_time`, `reply`, `retweet`) VALUES (%s, %s, %s, %s, %s, %s)"

        param = (text, t_time, author, crawl_time,t_replys, t_retweet)
        self._db_cursor.execute(sql, param)

    def batch_insert(self, t_dict):
        """插入多条twitter"""
        print 'start insertting data'
        for t in t_dict:
            text = t['text']
            author = t['author']
            t_time = t['time']
            t_replys=t['reply']
            t_retweet=t['retweets']
            self.insert_twitter(text, t_time, author,t_replys,t_retweet)

    def logger(self, log_type='', url='', count=0):
        """日志操作"""
        sql = "INSERT INTO "+dbname+"."+dblogtable+" (`type`, `time`, `url`, `count`) VALUES (%s, %s, %s, %s)"
        current_time = time.strftime('%Y-%m-%d %H:%I:%S', time.localtime(time.time()))
        param = (log_type, current_time, url, count)
        self._db_cursor.execute(sql, param)

    def is_done(self, url):
        """判断是否已抓取完毕"""
        sql = "SELECT 1 FROM "+dbname+".`crawl_log` WHERE type = 'end' " \
              "AND url = '%s' ORDER BY id DESC LIMIT 1" % url
        _n = self._db_cursor.execute(sql)
        return _n

class Datagui():
    def __init__(self):
        self.root=Tkinter.Tk()
        self.root.wm_title("twitter数据抓取程序")
        self.root.geometry('600x400')
        self.dbuser=Tkinter.Entry(self.root)
        self.dbuser.grid(row=0,column=2,sticky='E')
        Tkinter.Label(self.root,text="数据库用户名: ").grid(row=0,column=1,sticky='W')
        self.dbpwd=Tkinter.Entry(self.root)
        self.dbpwd['show']='*'
        self.dbpwd.grid(row=1,column=2,sticky='E')
        Tkinter.Label(self.root,text="数据库密码: ").grid(row=1,column=1,sticky='W')
        Tkinter.Button(self.root,text='测试数据库连接',command=self.dbtest).grid(row=2,column=1)
        self.keywords=Tkinter.Entry(self.root)
        self.keywords.grid(row=0,column=6,sticky='E')
        Tkinter.Label(self.root,text="关键词: ").grid(row=0,column=5,sticky='W')
        self.sttime=Tkinter.Entry(self.root)
        self.sttime.grid(row=1,column=6,sticky='E')
        Tkinter.Label(self.root,text="起始日期: ").grid(row=1,column=5,sticky='W')
        self.endtime=Tkinter.Entry(self.root)
        self.endtime.grid(row=2,column=6,sticky='E')
        Tkinter.Label(self.root,text="截止日期: ").grid(row=2,column=5,sticky='W')
        self.lan = Tkinter.StringVar(self.root)
        self.lan.set("en") # default value
        self.w = Tkinter.OptionMenu(self.root,self.lan,"en", "zh")
        self.w.grid(row=3,column=6,sticky='W')
        Tkinter.Label(self.root,text="语种: ").grid(row=3,column=5,sticky='W')
        Tkinter.Button(self.root,text='开始抓取',command=self.start).grid(row=8,column=1)
        Tkinter.Label(self.root,text="选择写入数据库: ").grid(row=3,column=1,sticky='W')
        Tkinter.Label(self.root,text="选择数据表: ").grid(row=4,column=1,sticky='W')
        Tkinter.Label(self.root,text="选择日志表: ").grid(row=5,column=1,sticky='W')
        #Tkinter.Button(root,text='初始化数据库').grid(row=2,column=1)
        Tkinter.mainloop()
        
    def dbtest(self):
        try:
            db=MySQLdb.connect(host="127.0.0.1", user=self.dbuser.get(), passwd=self.dbpwd.get(), port=3306, charset="utf8")
            tkMessageBox.showinfo(title='数据库连接测试',message='连接成功')
            self.dbcursor = db.cursor()
            try:
                #获取数据库名
                self.dbcursor.execute("SELECT `SCHEMA_NAME` FROM `information_schema`.`SCHEMATA`")
                schema1=[]
                
                self.schema=[]
                for term in self.dbcursor.fetchall():
                    schema1.append(term[0])
                for i in range(5,len(schema1)):
                    self.schema.append(schema1[i])
                
                self.comdb = Tkinter.StringVar(self.root)
                self.comdb.set(self.schema[0]) # default value
                self.comdbpac = apply(Tkinter.OptionMenu,(self.root,self.comdb)+tuple(self.schema))
                self.comdbpac.grid(row=3,column=2,sticky='W')
                #获取数据表
                self.dbtable=['选择数据表']
                self.comtab = Tkinter.StringVar(self.root)
                self.comtab.set(self.dbtable[0]) # default value
                self.comtabpac = apply(Tkinter.OptionMenu,(self.root,self.comtab)+tuple(self.dbtable))
                self.comtabpac.bind('<Button-1>',self.getdbtab)
                self.comtabpac.grid(row=4,column=2,sticky='W')
                #获取数据表
                self.dblogtable=['选择日志表']
                self.comlogtab = Tkinter.StringVar(self.root)
                self.comlogtab.set(self.dblogtable[0]) # default value
                self.comlogtabpac = apply(Tkinter.OptionMenu,(self.root,self.comlogtab)+tuple(self.dblogtable))
                self.comlogtabpac.bind('<Button-1>',self.getdblogtab)
                self.comlogtabpac.grid(row=5,column=2,sticky='W')
            except:
                tkMessageBox.showinfo(title='获取数据库名',message='获取数据库名失败')
        except:
            tkMessageBox.showinfo(title='数据库连接测试',message='连接失败')

    def getdbtab(self,uselessness):
        self.dbtable=[]
        self.dbcursor.execute("SELECT TABLE_NAME,TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA= '%s'"%(self.comdb.get()))
        for terms in self.dbcursor.fetchall():
            self.dbtable.append(terms[0])
        self.comtab.set(self.dbtable[0]) # default value
        self.comtabpac = apply(Tkinter.OptionMenu,(self.root,self.comtab)+tuple(self.dbtable))
        self.comtabpac.bind('<Button-1>',self.getdbtab)
        self.comtabpac.grid(row=4,column=2,sticky='W')

    def getdblogtab(self,uselessness):
        self.dblogtable=[]
        self.dbcursor.execute("SELECT TABLE_NAME,TABLE_ROWS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA= '%s'"%(self.comdb.get()))
        for terms in self.dbcursor.fetchall():
            self.dblogtable.append(terms[0])
        self.comlogtab.set(self.dblogtable[0]) # default value
        self.comlogtabpac = apply(Tkinter.OptionMenu,(self.root,self.comlogtab)+tuple(self.dblogtable))
        self.comlogtabpac.bind('<Button-1>',self.getdblogtab)
        self.comlogtabpac.grid(row=5,column=2,sticky='W')
        
    def generate(self):
        urllist=[]
        #print keywords.get()
        d1= self.sttime.get().split('-')
        d2= self.endtime.get().split('-')
        timecha=(datetime.datetime(int(d2[0]), int(d2[1]), int(d2[2]))-datetime.datetime(int(d1[0]), int(d1[1]), int(d1[2]))).days
        #print variable.get()
        for months in range(int(d1[1]),int(d2[1])):
            d1day=range(calendar.monthrange(int(d1[0]), months)[1]+1)[1:]
            d2day=range(calendar.monthrange(int(d1[0]), months)[1]+1)[1:]
            for day in range(int(d1[2]),calendar.monthrange(int(d1[0]), months)[1]):
                s="https://twitter.com/search?q="+self.keywords.get()+"%20lang%3A"+self.lan.get()+"%20since%3A"+d1[0]+"-"+str(months)+"-"+str(day)+"%20until%3A"+d1[0]+"-"+str(months)+"-"+str(int(day)+1)+"&src=typd"
                urllist.append(s)
            d1[2]=1
        for day in range(int(d1[2]),int(d2[2])):
            s="https://twitter.com/search?q="+self.keywords.get()+"%20lang%3A"+self.lan.get()+"%20since%3A"+d1[0]+"-"+d2[1]+"-"+str(day)+"%20until%3A"+d1[0]+"-"+d2[1]+"-"+str(int(day)+1)+"&src=typd"
            urllist.append(s)
        return urllist
    def start(self):
        # 初始化浏览器
        global dbus
        global dbpw
        global dbname
        global dbtable
        global dblogtable
        dbname=self.comdb.get()
        dbtable=self.comtab.get()
        dblogtable=self.comlogtab.get()
        dbus=self.dbuser.get()
        dbpw=self.dbpwd.get()
        urllist=self.generate()
        test = Browser()
        # test.load_url('D:\datacollect\url.txt')
        for u in urllist:
            print u
            test.execute_url(u)
'''
class start():
    def __init__(self):
        self.gui=Datagui()
'''

if __name__ == '__main__':
    test= Datagui()
    # test.get_html("https://twitter.com/search?q=h7n9%20lang%3Aen%20since%3A2013-04-01%20until%3A2013-04-02&src=typd")
    # test.close()
    # 获取元素


