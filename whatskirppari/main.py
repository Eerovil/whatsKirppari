#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import logging
import argparse
import configparser
from .stack import YowsupKirppariStack
import time
import schedule
from datetime import datetime

logging.basicConfig(filename='example.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
global_config = None

class KirppariHTTP():
    headers = {
        'DNT': '1', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.8,fi;q=0.6', 'Upgrade-Insecure-Requests': '1', 
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'http://www.kirpparikalle.net/sovellus/index.php?page=myreservations',  'Connection': 'keep-alive'
        }
    main_url = 'http://www.kirpparikalle.net/sovellus/'
    login_url = 'http://www.kirpparikalle.net/sovellus/rpc.php?request=json_login&method=username_login&lang=fi&company_id=1'
    sales_url = 'http://www.kirpparikalle.net/sovellus/index.php?page=mysales'
    lists_url = 'http://www.kirpparikalle.net/sovellus/index.php?page=myproducts'

    def __init__(self, phpsessid, username, password):
        self.headers['Cookie'] = 'PHPSESSID=' + phpsessid
        self.login_url += '&username=' + username + '&password=' + password
        self.login()

    def getSheets(self):
        return requests.get(self.lists_url, headers=self.headers, verify=False)

    def getURL(self, url):
        return requests.get(self.main_url + url, headers=self.headers, verify=False)

    def getSales(self):
        return requests.get(self.sales_url, headers=self.headers, verify=False)

    def login(self):
        return requests.get(self.login_url, headers=self.headers, verify=False)

    def getSaldo(self):
        r = requests.get(self.sales_url, headers=self.headers, verify=False)
        try:
            soup = BeautifulSoup(r.text, 'html.parser')
            return soup.find('td', attrs={'id':'maincont'}).find_all('td')[1].text
        except Exception as e:
            return ""
class Kirppari():

    http = None
    config = None
    target = ""
    stack = None
    sheet_list = {}
    sale_list = {}

    def __init__(self, target, stack, http):
        self.stack = stack
        self.http = http
        self.target = target
        self.getLists()

    def getSheet(self, item_id):
        logger.info("Finding sheet")
        for key, value in self.sheet_list.items():
            if (item_id in value['items']):
                return value
        self.getSheets()
        
        for key, value in self.sheet_list.items():
            if (item_id in value['items']):
                return value
        logger.info("DID NOT FIND SHEET")
        logger.info(self.sheet_list)
        return None

    # TODO: Try to use itertools
    def getSheets(self, amount = 999):
        r = self.http.getSheets()
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        self.sheet_list = {}
        for tr in tr_list:
            amount -= 1
            if (amount < 0):
                return
            td_list = tr.find_all('td')
            sheet_url = td_list[8].find('a')['href']
            sheet_name = td_list[1].text
            sheet_id = td_list[0].text
            logger.info(sheet_id)
            self.sheet_list[sheet_id] = {'name': sheet_name, 'link': sheet_url, 'items': {}}
            sheet_r = self.http.getURL(sheet_url)
            sheet_soup = BeautifulSoup(sheet_r.text, 'html.parser')
            sheet_tr_list = sheet_soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
            logger.info(sheet_tr_list[0].find('td').text)
            for sheet_tr in sheet_tr_list:
                sheet_td_list = sheet_tr.find_all('td')
                if (len(sheet_td_list) > 0):
                    item_id = sheet_td_list[0].text
                    self.sheet_list[sheet_id]['items'][item_id] = sheet_td_list[1].text

    def getLists(self):
        try:
            with open("kirppari.json", 'r') as input:
                self.sale_list = json.load(input)
        except:
            with open("kirppari.json", 'w') as output:
                json.dump(self.sale_list, output)
        try:
            with open("kirppari_lists.json", 'r') as input:
                self.sheet_list = json.load(input)
        except:
            with open("kirppari_lists.json", 'w') as output:
                json.dump(self.sheet_list, output)

    def saveLists(self):
        with open("kirppari.json", 'w') as output:
            json.dump(self.sale_list, output, ensure_ascii=False)
        with open("kirppari_lists.json", 'w') as output:
            json.dump(self.sheet_list, output, ensure_ascii=False)

    def getSales(self):
        r = self.http.getSales()
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        trCount = 0
        for tr in tr_list:
            trCount += 1
            td_list = tr.find_all('td')
            sale_id = td_list[0].text
            logger.info('  '+td_list[1].text)
            if (sale_id not in self.sale_list):
                newsale = {'row': trCount, 'name': td_list[1].text, 'price': td_list[2].text, 'date': td_list[3].text}
                self.sale_list[sale_id] = newsale
                self.stack.send(self.target, "Myyty! " + self.makeSaleString(sale_id))
            else:
                self.sale_list[sale_id]['row'] = trCount
        return self.sale_list

    def makeSaleString(self, sale_id):
        sale = self.sale_list[sale_id]
        s = self.getSheet(sale_id)
        sheetName = s['name']
        nameFromSheet = s['items'][sale_id]
        logger.debug("New sale: " + nameFromSheet + ", " + sheetName)
        return nameFromSheet + ", " + sale['price'] + ', ' + sheetName + ', ' + sale_id + ', ' + sale['date']


def getConfig(configpath):
    global global_config
    c = configparser.ConfigParser()
    c.read(configpath)
    if ('main' in c and 'yowsup' in c):
        global_config = c
        return c
    else:
        c.add_section('main')
        c['main'] = {
            'PHPSESSID': '',
            'username': '',
            'password': '',
            'groupid': '',
        }
        c.add_section('yowsup')
        c['main'] = {
            'cc': '',
            'phone': '',
            'id': '',
            'password': ''
        }
        with open('config.ini', 'w') as f:
            c.write(f)
    raise Exception("No config")

def resend(c, kirppari):
    if (c > 0):
        m = "Tässä " + str(c) + " viimeisintä myyntiä.\n"
        sortedValues = sorted(kirppari.sale_list.items(), key=lambda x: x[1]['row'], reverse=False)
        logger.info(sortedValues)
        for key, sale in sortedValues:
            c = c - 1
            if (c < 0):
                break
            logger.info("RESENDING " + sale['name'])    
            m += kirppari.makeSaleString(key) + "\n"
        kirppari.stack.send(kirppari.target, m)

def testTime():
    now = datetime.now().strftime('%H%M')
    if '0855' <= now <= '1905':
        return True
    logger.info("Not open: not checking.")
    return False

def loop(target, stack, kirppari_http):
    if (not testTime()):
        return

    kirppari = Kirppari(
        target=target, 
        stack=stack, 
        http=kirppari_http)
    kirppari.getSales()
    kirppari.saveLists()

    sortedValues = sorted(kirppari.sale_list.items(), key=lambda x: x[1]['row'], reverse=True)
    logger.info(sortedValues)
    for key, sale in sortedValues:
        logger.info(str(sale['row']) + ": " + kirppari.getSheet(key)['items'][key] + ", " + str(sale['price']))

    return kirppari


def main():
    parser = argparse.ArgumentParser(description='Get new sales from kirpparikalle  ')
    parser.add_argument('-t', '--target', default='', 
        help='Phone number to send', 
        required=False)
    parser.add_argument('-r', '--resend', default=0, type=int, 
        help='Number of last sales to resend', 
        required=False)
    args = vars(parser.parse_args())

    cfg = getConfig('config.ini')

    kirppari_http = KirppariHTTP(
        cfg['main']['PHPSESSID'], 
        cfg['main']['username'], 
        cfg['main']['password'])

    credentials = (
        cfg['yowsup']['phone'], 
        cfg['yowsup']['password'])
    stack = YowsupKirppariStack(credentials, kirppari_http)
    logger.info("Stack start...")
    stack.start()
    logger.info("Stack start... Done")
    time.sleep(15)


    target = args['target']
    if (target == ""):
        target = cfg['main']['groupid']

    kirppari = loop(
        target=target, 
        stack=stack, 
        kirppari_http=kirppari_http)

    c = args['resend']
    if (c > 0):
        if (not kirppari):
            kirppari = Kirppari(
                target=target, 
                stack=stack, 
                http=kirppari_http)
            kirppari.getSales()
        resend(c, kirppari)
        time.sleep(5)

    schedule.every(5).minutes.do(loop, 
        target=target, 
        stack=stack, 
        kirppari_http=kirppari_http)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        stack.stop()
        logger.info("End")
    except Exception as e:
        logging.exception("Error happened within loop")
        if 'debugtarget' in cfg['main']:
            stack.send(cfg['main']['debugtarget'], "Error: " + str(e))
            time.sleep(20)
        stack.stop()

if __name__ == "__main__":
    main()
