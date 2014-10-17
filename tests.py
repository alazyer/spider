#!/usr/bin/env python
# coding: utf-8

import unittest
import requests


class BasicTest(unittest.TestCase):
    """ 测试类, 这里简单的测试了参数必须为真值, 
    以及网络链接的可用性.
    """
    def __init__(self, url, depth, num_workers, log_file, log_level):
        super(BasicTest, self).__init__('main')
        self.url = url
        self.depth = depth
        self.num_workers = num_workers
        self.log_file = log_file
        self.log_level = log_level
        
    def arguments_test(self):
        """ 参数测试
        """
        self.assertTrue(self.url)
        self.assertTrue(self.depth)
        self.assertTrue(self.num_workers)
        self.assertTrue(self.log_file)
        self.assertTrue(self.log_level)
        
    def connection_test(self):
        """网络链接测试
        """
        res = requests.get(self.url)
        self.assertEqual(res.status_code, 200)
        
    def main(self):
        """主测试函数, 为了传给重载TestCase.__init__(self, methodName='runTest')方法
        super(BasicTest, self).__init__(methodName='runTest'), 否则self.assertEqual出错.
        """
        self.arguments_test()
        self.connection_test()
        
    