#from objgraph import 
import math
import logging
import sqlite3
import time
from urllib.parse import urlparse
from html.parser import HTMLParser
from sqlalchemy.orm import Session
import random
import urllib.request
import threading

MAX_TO_STORE = 100000000
MAX_TO_REQUEST = 100000000

STOP_WORD_FILE = 'stop_words.txt'


class Webpage(HTMLParser):
    stop_words = set()
    stop_word_std = 1 
    sn = 0
    sx=  0
    sxx =0
    __tablename__ = 'webpage'
    
    def __init__(self, url='',text =''):
        HTMLParser.__init__(self)        
        self.words = []
        self.links = []
        
        self.url = url
        self.text = text
        uri = urlparse(url)
        self.scheme = uri.scheme
        self.netloc = uri.netloc
        self.domain = '{uri.scheme}://{uri.netloc}'.format(uri = uri)
        self.title = url 
        self._on_title = False

    def is_english(self):
        if self.words:
            i=0
            for w in self.words:
                if w in self.stop_words:
                    i += 1
            freq = i/len(self.words)
            #keep track of varaibles for iterative standard deviation.
            Webpage.sx += freq
            Webpage.sxx += freq**2
            Webpage.sn += 1
            if Webpage.sn>1:
                if self.stop_word_std() > freq:
                    return False

            return True
        else:
            return False
    
    def stop_word_std(self):
        return math.sqrt((1/(Webpage.sn))*Webpage.sxx - ((1/(Webpage.sn))*Webpage.sx)**2) * math.sqrt(Webpage.sn/(Webpage.sn - 1))

    def fill(self, timeout = 5):
        self.text = urllib.request.urlopen(url = self.url,timeout = timeout).read().decode('utf-8')
        
    def parse(self):
        self.feed(self.text)
        self.english = self.is_english()
    
    def get_link_pages(self):
        return list(map(Webpage,self.links))
    
    def handle_starttag(self,tag,attrs):
        if tag == 'a':
            for attrib in attrs:
                if attrib[0] == 'href':
                    url = urllib.parse.urljoin(self.url,attrib[1])
                    self.links.append(url)
        if tag =='title':
            self._on_title = True
    
    def handle_endtag(self, tag):
        if tag == 'title':
            self._on_title = False

    def handle_data(self, data):
        if self._on_title:
            self.title = data.lower()
        self.words += map(str.lower, filter(str.isalpha,data.split()))
    
    def init_stop_words():
        Webpage.stop_words |= set(open(STOP_WORD_FILE,'r').read().split())

    def __str__(self):
        return ' '.join(self.words)
    

class Queue(list):
    def __init__(self):
        self.lock = threading.RLock()
    
    def append(self, item):
        with self.lock:
            return super(Queue, self).append(item)
    
    def randpop(self):
        with self.lock:
            if not len(self):
                return None
            return super(Queue, self).pop( random.randint(0,len(self)-1) if len(self)!=1 else 0)


class RequestManager(threading.Thread):
    def __init__(self, unprocessed, processed, use_init = True, init_urls_file = 'init_urls.txt', lf='RequestManager.log', domain_once = False, restricted_domains = None):
        super(RequestManager, self).__init__()
        self.logfile = open(lf,'a')
        self.errors = 0
        self.unprocessed = unprocessed
        if use_init:
            self.unprocessed+= map(Webpage,open(init_urls_file,'r').read().split())
        self.processed = processed
        self.closed_domains = set()
        self.closed_pages = set()
        self.do = domain_once
        self._stop_event = threading.Event()
        Webpage.init_stop_words()
        self.restricted_domains = restricted_domains

    def run(self):
        i = 0
        while(not self._stop_event.is_set()):
            if len(self.processed) <= MAX_TO_STORE and self.unprocessed:  
                page= self.unprocessed.randpop()
                if page and page.url not in self.closed_pages and ((self.restricted_domains ==None) or page.domain in self.restricted_domains):
                    try:
                        page.fill()
                        self.processed.append(page)

                        self.closed_domains.add(page.domain)
                        self.closed_pages.add(page.url)
                        if page.text:
                            print('Request Manager: crawled ' + page.url + '   ' + str(i))
                            i += 1
                    except Exception as e:
                        pass
                        #logging.exception("message") 
        self.close()

    def close(self):
        self.logfile.close()

    def stop(self):
        self._stop_event.set()

class Storage(threading.Thread):
    def __init__(self, processed=Queue(), unprocessed=Queue(), logfile='storage.log',dbfile = 'db/webpages.db', non_english = False):
        super(Storage, self).__init__()
        self.conn = sqlite3.connect(dbfile, check_same_thread = False)
        self.conn.row_factory = sqlite3.Row
        c = self.conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS webpage (id INTEGER PRIMARY KEY AUTOINCREMENT, \
                  text MEDIUMTEXT, url varchar(256), domain varchar(128), title varchar(128))')
        self.logfile = open(logfile, 'a')
        self.processed = processed
        self.unprocessed = unprocessed
        self._stop_event = threading.Event()
        self.seen = set()
        self.non_english = non_english
        self.dbfile = dbfile

    def run(self):
        while(not self._stop_event.is_set()):
            if (len(self.processed) <= MAX_TO_REQUEST) and self.unprocessed:
                page = self.unprocessed.randpop()

                page.parse()
                
                for linked_page in page.get_link_pages():
                    if linked_page.url not in self.seen:
                        self.processed.append(linked_page)
                        self.seen.add(linked_page.url)
                if page.english or self.non_english:
                    try:
                        self.add_page(page)
                        print('storing... '+ page.url)
                        del page
                    except Exception as e:
                        logging.exception("message") 
                else:
                    print(page.url + ' not english')
        self.close()

    def close(self):
        self.conn.close()
        self.logfile.close()

    def stop(self):
        self._stop_event.set()

    def count_pages(self):
        c = self.conn.cursor()
        c.execute('SELECT count(*) from webpage')
        result = cursor.fetchone()
        return result
    
    def update_page(self, page):
        c = self.conn.cursor()
        c.execute('UPDATE webpage SET (text,url,domain,title) VALUES(\''+page.text.replace("'","''")+'\',\'{page.url}\',\'{page.domain}\',\'{page.title}\')'.format(page=page))
        self.conn.commit()

    def add_page(self, page):
        c = self.conn.cursor()
        c.execute('INSERT INTO webpage (text,url,domain,title) VALUES(\''+page.text.replace("'","''")+'\',\'{page.url}\',\'{page.domain}\',\'{page.title}\')'.format(page=page))
        self.conn.commit()
    def read_pages(self):
        c = self.conn.cursor()
        rows = c.execute('SELECT * FROM webpage')
        return list(rows)

    def read_pages_iter(self):
        c = self.conn.cursor()
        c.execute('SELECT * FROM webpage')
        row = c.fetchone()
        while row:
            page =  Webpage(url = row['url'], text = row['text'])
            page.parse()
            yield page
            row = c.fetchone()
        
    def read_pages_strings(self):
        for page in self.read_pages_iter():
            yield str(page)
    
    def read_pages_title(self):
        for page in self.read_pages_iter():
            yield page.title
    
    def read_pages_url(self):
        for page in self.read_pages_iter():
            yield page.url

    def truncate_table(self):
        c = self.conn.cursor()
        c.execute('DELETE FROM webpage')

if __name__ == "__main__":
    q0 = Queue()
    q1 = Queue()
    r = RequestManager(q0,q1,restricted_domains = ['https://en.wikipedia.org','https://www.wikipedia.org'])
    s = Storage(q0,q1)
    s.truncate_table()
    r.daemon = True
    s.daemon = True
    r.start()
    s.start()
    #print("Starting crawling.")
    while(r.isAlive() and s.isAlive()):
        time.sleep(1)
    print('R isAlive: ' + str(r.isAlive()))
    print('S isAlive: ' + str(s.isAlive()))
