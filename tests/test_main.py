# -*- coding: utf-8 -*-
import unittest
from whatsKirppari.main import getConfig
from whatsKirppari.main import testTime
from whatsKirppari.main import Kirppari
from whatsKirppari.main import KirppariHTTP
from whatsKirppari.stack import YowsupKirppariStack
import os

class KirppariHTTPTestCase(unittest.TestCase):
    http = None

    def setUp(self):
        cfg = getConfig(
            os.path.join(os.path.dirname(__file__), 
            'test_config.ini'))
        self.http = KirppariHTTP(
        cfg['main']['PHPSESSID'], 
        cfg['main']['username'], 
        cfg['main']['password'])

    def test_getSaldo(self):
        ret = self.http.getSaldo()
        self.assertIn(',', ret)


class UnicodeTestCase(unittest.TestCase):

    def test_printUnicode(self):
        import sys
        print(sys.version)
        print("sys.stdout.encoding: " + sys.stdout.encoding)
        #print("PYTHONENCODING: " + os.environ["PYTHONENCODING"])
        print('ö')

class KirppariTestCase(unittest.TestCase):
    kirppari = None
    def setUp(self):
        cfg = getConfig(
            os.path.join(os.path.dirname(__file__), 
            'test_config.ini'))
        credentials = (
            cfg['yowsup']['phone'], 
            cfg['yowsup']['password'])
        http = KirppariHTTP(
            cfg['main']['PHPSESSID'], 
            cfg['main']['username'], 
            cfg['main']['password'])
        stack = YowsupKirppariStack(
            credentials, 
            http)
        self.kirppari = Kirppari(
            cfg['main']['groupid'],
            stack,
            http
        )

    def test_getSheets(self):
        ret = self.kirppari.getSheets(amount = 1)
        #print(self.kirppari.sheet_list)
        self.kirppari.saveLists()
        #self.asss

    def test_getSales(self):
        ret = self.kirppari.getSales()
        self.kirppari.saveLists()
        #self.asss


if __name__ == '__main__':
    unittest.main()
