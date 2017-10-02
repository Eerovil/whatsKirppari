#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import logging
import argparse
import configparser
from stack import YowsupKirppariStack
import time
import schedule

logging.basicConfig(filename='example.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)
global_config = None

class Kirppari():
    headers = {
        'DNT': '1', 'Accept-Encoding': 'gzip, deflate, br', 'Accept-Language': 'en-US,en;q=0.8,fi;q=0.6', 'Upgrade-Insecure-Requests': '1', 
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Referer': 'https://www.kirpparikalle.net/sovellus/index.php?page=myreservations',  'Connection': 'keep-alive'
        }
    main_url = 'https://www.kirpparikalle.net/sovellus/'
    login_url = 'https://www.kirpparikalle.net/sovellus/rpc.php?request=json_login&method=username_login&lang=fi&company_id=1'
    sales_url = 'https://www.kirpparikalle.net/sovellus/index.php?page=mysales'
    lists_url = 'https://www.kirpparikalle.net/sovellus/index.php?page=myproducts'

    config = None
    target = ""
    stack = None
    sheet_list = {}
    sale_list = {}

    def __init__(self, config, stack, target=""):
        self.stack = stack
        self.headers['Cookie'] = 'PHPSESSID=' + config['PHPSESSID']
        self.login_url += '&username=' + config['username'] + '&password=' + config['password']
        if (len(target) == 0):
            self.target = config['groupid']
        else:
            self.target = target
        self.getLists()

    def getSheet(self, item_id):
        print("Finding sheet")
        for key, value in self.sheet_list.items():
            if (item_id in value['items']):
                return value
        self.getSheets()
        
        for key, value in self.sheet_list.items():
            if (item_id in value['items']):
                return value
        print("DID NOT FIND SHEET")
        print(self.sheet_list)
        return None

    def getSheets(self):
        r = requests.get(self.lists_url, headers=self.headers, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        self.sheet_list = {}
        for tr in tr_list:
            td_list = tr.find_all('td')
            sheet_url = self.main_url + td_list[8].find('a')['href']
            sheet_name = td_list[1].text
            sheet_id = td_list[0].text
            print(sheet_id)
            self.sheet_list[sheet_id] = {'name': sheet_name, 'link': sheet_url, 'items': {}}
            sheet_r = requests.get(sheet_url, headers=self.headers, verify=False)
            sheet_soup = BeautifulSoup(sheet_r.text, 'html.parser')
            sheet_tr_list = sheet_soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
            print(sheet_tr_list[0].find('td').text)
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

    def login(self):
        requests.get(self.login_url, headers=self.headers, verify=False)

    def getSales(self):
        r = requests.get(self.sales_url, headers=self.headers, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        trCount = 0
        for tr in tr_list:
            trCount += 1
            td_list = tr.find_all('td')
            sale_id = td_list[0].text
            logging.info('  '+td_list[1].text)
            if (sale_id not in self.sale_list):
                newsale = {'row':trCount ,'name': td_list[1].text, 'price': td_list[2].text, 'date': td_list[3].text}
                self.sale_list[sale_id] = newsale
                self.stack.send(self.target, self.makeSaleString(sale_id))
        return self.sale_list

    def makeSaleString(self, sale_id):
        sale = self.sale_list[sale_id]
        s = self.getSheet(sale_id)
        sheetName = s['name']
        nameFromSheet = s['items'][sale_id]
        logging.debug("New sale: " + nameFromSheet + ", " + sheetName)
        return "Myyty!: " + nameFromSheet + ", " + sale['price'] + '. Lista: ' + sheetName + ', Nro: ' + sale_id


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
        sortedValues = sorted(kirppari.sale_list.items(), key=lambda x: x[1]['row'], reverse=True)
        print(sortedValues)
        for key, sale in sortedValues:
            c = c - 1
            if (c < 0):
                break
            print("RESENDING " + sale['name'])    
            m += kirppari.makeSaleString(key) + "\n"
        kirppari.stack.send(kirppari.target, m)

def loop(cfg, args, stack):
    kirppari = Kirppari(cfg['main'], stack, target=args['target'])
    kirppari.login()
    kirppari.getSales()
    kirppari.saveLists()

    for key, sale in kirppari.sale_list.items():
        print(sale['name'])
        print(kirppari.getSheet(key)['items'][key])

    return kirppari


def main():
    parser = argparse.ArgumentParser(description='Get new sales from kirpparikalle  ')
    parser.add_argument('-t', '--target', default='', help='Phone number to send', required=False)
    parser.add_argument('-r', '--resend', default=0, type=int, help='Number of last sales to resend', required=False)
    args = vars(parser.parse_args())

    cfg = getConfig('config.ini')

    credentials = (cfg['yowsup']['phone'], cfg['yowsup']['password'])
    stack = YowsupKirppariStack(credentials)
    print("Stack start...")
    stack.start()
    print("Stack start... Done")
    time.sleep(3)

    kirppari = loop(cfg, args, stack)

    c = args['resend']
    if (c > 0):
        resend(c, kirppari)
        time.sleep(5)
        stack.stop()
        return

    schedule.every(5).minutes.do(loop, cfg, args, stack)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        stack.stop()
        print("End")

if __name__ == "__main__":
    main()
