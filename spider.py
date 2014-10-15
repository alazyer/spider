#!/usr/bin/env python
# coding: utf8

import re
import os
import sys
import time
import Queue
import logging
import weakref
import datetime
import urlparse
import optparse
import requests
import threading
from bs4 import BeautifulSoup

from tests import BasicTest

HREF_REGEX = re.compile(r'^http|^/')

logger = logging.getLogger()

def parse_options():
    parser = optparse.OptionParser()

    parser.add_option("-u", "--url", dest="url", type="string",
               help="the url to be crawled.")

    parser.add_option("-d", "--depth", dest="depth", type="int",
               help="deepth to be crawled.")

    parser.add_option("-f", "--file", dest="log_file", type="string",
               help="the logfile.")

    parser.add_option("-l", "--loglevel", dest="log_level", type="int",
               help="loglevel.")

    parser.add_option("-t", "--threadnum", dest="thread_num", type="int",
               help="number of thread in the pool.")

    parser.add_option("-s", "--dbfile", dest="db_file", type="string",
               help="the sqlite database file.")

    parser.add_option("-k", "--key", dest="keyword", type="string",
               help="the specified keyword to record.")

    parser.add_option("-e", "--downloadfile", dest="download_file", type="string",
               help="file extentions to be downloaded.")
    
    parser.add_option("--testself", action="store_true", dest="testself",
               help="the program test itself")

    (options, args) = parser.parse_args()

    return options

def config_logger(log_file, log_level):
    if os.path.isfile(log_file):
        os.remove(log_file)
        
    logger.setLevel(log_level)
    file_handler = logging.FileHandler(log_file)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


class WorkRequest:
    def __init__(self, url, get_url=True):
        self.url = url
        self.get_url = get_url

    def work(self):
        try:
            res = requests.get(self.url)
        except UnicodeError, e:
            logger.warning(e)
            res = requests.get(self.url.encode('raw_unicode_escape'))
        except requests.exceptions.ConnectionError, e:
            logger.warning(e)
            return [self.url, ]
        except Exception, e:
            logger.warning(e)
            return list()
        else:
            content = res.text
            if self.get_url:
                url_parsed = urlparse.urlparse(self.url)
                url_base = url_parsed.scheme + '://' + url_parsed.netloc

                soup = BeautifulSoup(content)
                anchors_in_page = soup.findAll('a', href=HREF_REGEX)
                urls_in_page = []

                for anchor in anchors_in_page:
                    anchor_url = anchor['href']
                    if anchor_url.startswith('/'):
                        urls_in_page.append(urlparse.urljoin(url_base, anchor_url))
                    else:
                        urls_in_page.append(anchor_url)

                return urls_in_page

            return list()  # only crawl content, the urls is ignored.


class Worker(threading.Thread):
    def __init__(self, thread_pool):
        threading.Thread.__init__(self)
        self.thread_pool = thread_pool
        self.setDaemon(True)
        self.start()

    def run(self):
        while True:
            try:
                request = self.thread_pool.request_queue.get()
            except Queue.Empty:
                continue
            else:
                urls_in_page = request.work()
                self.thread_pool.result_queue.put(urls_in_page)
                self.thread_pool.request_queue.task_done()


class ThreadPool:
    def __init__(self, num_workers):
        self.request_queue = Queue.Queue()
        self.result_queue = Queue.Queue()
        self.num_workers = num_workers
        self.workers = []

    def put_request(self, request):
        self.request_queue.put(request)

    def start(self):
        for _ in xrange(self.num_workers):
            worker = Worker(self)
            # worker = Worker(weakref.proxy(self))
            # worker = weakref.proxy(Worker(self))
            self.workers.append(worker)

    def stop(self):
        self.request_queue.join()
        while self.workers:
            worker = self.workers.pop()
            del worker


class Mover:
    """辅助类, 用于将线程池的结果队列中的urls_in_page列表中url存放到crawler的urls_queue队列中.
    """
    def __init__(self, source_queue, target_queue):
        self.source_queue = source_queue
        self.target_queue = target_queue

    def move(self):
        while not self.source_queue.empty():
            urls_in_page = self.source_queue.get()
            for url in urls_in_page:
                self.target_queue.put(url)


class Crawler:
    """爬虫类, 用于爬取内容.
    """
    def __init__(self, url, depth, num_workers):
        """初始化爬虫类, 指定初始urls, 以及需要爬取的深度, 
        线程池中线程的数量.
        """
        self.url = url
        self.depth = depth
        self.working = True
        self.urls_visited = set()
        self.urls_queue = Queue.Queue()
        self.thread_pool = ThreadPool(num_workers)
        self.mover = Mover(self.thread_pool.result_queue, self.urls_queue)

    def crawl(self):
        """爬虫类的主体部分.负责控制爬取深度.
        """
        cur_depth = 0
        self.urls_queue.put(self.url)
        self.thread_pool.start()
        
        # 没有到达指定的深度的最后一层, 爬取页面内容, 以及页面中包含的链接.
        while cur_depth < self.depth:
            while not self.urls_queue.empty():
                url = self.urls_queue.get()
                if url not in self.urls_visited:
                    self.urls_visited.add(url)
                    request = WorkRequest(url)
                    self.thread_pool.put_request(request)

            self.thread_pool.request_queue.join()
            self.mover.move()
            cur_depth += 1
        
        # 最后一层只爬取内容, 不记录页面上存在的链接.
        while not self.urls_queue.empty():
            url = self.urls_queue.get()
            if url not in self.urls_visited:
                self.urls_visited.add(url)
                request = WorkRequest(url, get_url=False)
                self.thread_pool.put_request(request)

        self.stop()

    def stop(self):
        """调用线程池的停止方法, 设置运行状态为停止(working=False).
        """
        self.thread_pool.stop()
        self.working = False
        print "Job done."

class Recorder(threading.Thread):
    """打印信息线程, 每10秒打印一次完成链接数, 以及线程池中剩余请求数量.
    结束前, 统计运行时间, 以及完成链接总数量.
    """
    
    def __init__(self, crawler):
        """线程初始化, 指定要统计信息的crawler实例.
        """
        threading.Thread.__init__(self)
        self.start_time = datetime.datetime.now()
        self.daemon = True
        self.crawler = crawler
        self.start()

    def run(self):
        """当crawler在工作(working=True), 则每10秒中输出当前完成链接数量, 以及线程池中剩余请求数量.
        当crawler停止工作后(working=False), 则输出运行时间以及完成的所有链接数量.
        """
        while True:
            if self.crawler.working:
                time.sleep(10)
                all_count = len(self.crawler.urls_visited)
                unfinished_tasks = self.crawler.thread_pool.request_queue.unfinished_tasks
                done_count = all_count - unfinished_tasks
                print 'Visited %d Links till now. There are %d unfinished tasks in the request queue.' % (done_count, unfinished_tasks)
            else:
                break

        self.stop()

    def stop(self):
        self.end_time = datetime.datetime.now()
        print 'Start at: %s' % self.start_time
        print 'End at  : %s' % self.end_time
        print 'Totally, crawled %d links, with %s seconds.' % (len(self.crawler.urls_visited), (self.end_time - self.start_time))


if __name__=='__main__':
    

    options = parse_options()
    root_url = options.url or 'http://www.sohu.com'
    depth = options.depth or 1
    num_workers = options.thread_num or 20
    log_file = options.log_file or 'spider.log'
    log_level = options.log_level or 5
    testself = options.testself
    print "the url you specified is: ", root_url
    print "the depth to be crawled is: ", depth
    print "the number of workers is: ", num_workers
    print "The log file is: ", log_file
    print "The log level is: ", log_level
    
    if testself:
    
        tester = BasicTest(root_url, depth, num_workers, log_file, log_level)
        tester.main()
    
    config_logger(log_file, log_level)

    crawler = Crawler(root_url, depth, num_workers)
    recorder = Recorder(crawler)
    crawler.crawl()
    recorder.stop()
