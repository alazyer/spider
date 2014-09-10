#!/usr/bin/env python
# coding: utf8

import optparse

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

if __name__=='__main__':

    options, args = parse_options()
    root_url = options.url
    deepth = options.deepth
    print "the url you specified is: ", root_url
    print "the deepth to be crawled is:", deepth
