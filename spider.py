#!/usr/bin/env python
# coding: utf8

import optparse
import sqlite3
import requests
from bs4 import BeautifulSoup

def parse_options():
    parser = optparse.OptionParser()

    parser.add_option("-u", "--url", dest="url",
               help="the url to be crawled.")

    parser.add_option("-d", "--deepth", dest="deepth",
               help="deepth to be crawled.")

    parser.add_option("-f", "--file", dest="file",
               help="the logfile.")

    parser.add_option("-l", "--loglevel", dest="loglevel",
               help="loglevel.")

    parser.add_option("-t", "--threadnum", dest="threadnum",
               help="number of thread in the pool.")

    parser.add_option("-s", "--dbfile", dest="dbfile",
               help="the sqlite database file.")

    parser.add_option("-k", "--key", dest="keyword",
               help="the specified keyword to record.")

    parser.add_option("-e", "--downloadfile", dest="downloadfile",
               help="file extentions to be downloaded.")

    (options, args) = parser.parse_args()

    return options, args

def get_page(url):
    res = requests.get(url)
    soup = BeautifulSoup(res.text)
    urls_in_page = [x['href'].strip() for x in soup.select('a[href]')]
    urls_in_page = [x for x in urls_in_page if x.startswith('http')]

    for urls in urls_in_page:
        print urls

    return urls_in_page

if __name__=='__main__':

    options, args = parse_options()
    root_url = options.url
    deepth = options.deepth
    print "the url you specified is: ", root_url
    print "the deepth to be crawled is: ", deepth

    get_page(root_url)
