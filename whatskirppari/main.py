#!/usr/bin/env python
# -*- coding: utf-8 -*-
import requests
from bs4 import BeautifulSoup
import json
import logging
import argparse
import configparser
import time
import schedule
import smtplib
from datetime import datetime

logging.basicConfig(filename='example.log', format='%(asctime)s - %(name)s %(lineno)d - %(levelname)s:%(message)s', level=logging.DEBUG)
logger = logging.getLogger(__name__)
global_config = None
DEBUG_MODE = False

class Email():
    def __init__(self, user, password, sender, recipient):
        self.user = user
        self.password = password
        self.sender = sender
        self.recipient = recipient
    
    def send(self, message):
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(self.user, self.password)
        message_lines = message.split("\n")
        message = "Subject:[Kirppari] " + message_lines[0] + "\n\n" + "\n".join(message_lines[1:])
        logger.info('Sending mail to %s: %s ', self.recipient, message)
        server.sendmail(self.sender, self.recipient, message.encode('utf8'))
        server.close()
        logger.info('successfully sent the mail')


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
    sheet_list = {}
    sale_list = {}

    def __init__(self, http, email):
        self.http = http
        self.email = email
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
            sheet_url = td_list[9].find('a')['href']
            sheet_name = td_list[1].text
            sheet_id = td_list[0].text
            logger.info(sheet_id)
            self.sheet_list[sheet_id] = {'name': sheet_name, 'link': sheet_url, 'items': {}}
            sheet_r = self.http.getURL(sheet_url)
            sheet_soup = BeautifulSoup(sheet_r.text, 'html.parser')
            try:
                sheet_tr_list = sheet_soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
            except Exception:
                logger.warning('Could not read sheet %s', sheet_url)
                continue
            logger.info(sheet_tr_list[0].find('td').text)
            for sheet_tr in sheet_tr_list:
                sheet_td_list = sheet_tr.find_all('td')
                if (len(sheet_td_list) > 0):
                    item_id = sheet_td_list[0].text
                    self.sheet_list[sheet_id]['items'][item_id] = sheet_td_list[1].text
        logger.debug("self.sheet_list: %s", self.sheet_list)
        self.saveLists()

    def getLists(self):
        try:
            with open("kirppari.json", 'r') as input:
                self.sale_list = json.load(input)
        except:
            with open("kirppari.json", 'w') as output:
                json.dump(self.sale_list, output, indent=4)
        try:
            with open("kirppari_lists.json", 'r') as input:
                self.sheet_list = json.load(input)
        except:
            with open("kirppari_lists.json", 'w') as output:
                json.dump(self.sheet_list, output, indent=4)

    def saveLists(self):
        with open("kirppari.json", 'w') as output:
            json.dump(self.sale_list, output, ensure_ascii=False, indent=4)
        with open("kirppari_lists.json", 'w') as output:
            json.dump(self.sheet_list, output, ensure_ascii=False, indent=4)

    def getSales(self):
        r = self.http.getSales()
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        trCount = 0
        new_sales = {}
        for tr in tr_list:
            trCount += 1
            td_list = tr.find_all('td')
            sale_id = td_list[0].text
            logger.info('  '+td_list[1].text)
            if (sale_id not in self.sale_list):
                newsale = {'row': trCount, 'name': td_list[1].text, 'price': td_list[2].text, 'date': td_list[3].text}
                self.sale_list[sale_id] = newsale
                new_sales[sale_id] = newsale
            else:
                self.sale_list[sale_id]['row'] = trCount
        return new_sales

    def makeSaleString(self, sale_id):
        sale = self.sale_list[sale_id]
        s = self.getSheet(sale_id)
        sheetName = s['name']
        nameFromSheet = s['items'][sale_id]
        logger.info("New sale: " + nameFromSheet + ", " + sheetName)
        return nameFromSheet + ", " + sale['price'] + ', ' + sheetName + ', ' + sale_id + ', ' + sale['date']


def getConfig(configpath):
    global global_config
    c = configparser.ConfigParser()
    c.read(configpath)
    if ('main' in c):
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
        c.add_section('email')
        c['email'] = {
            'user': '',
            'password': '',
            'sender': '',
            'recipient': '',
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
        logger.info(m)
        kirppari.email.send(m)

def testTime():
    now = datetime.now().strftime('%H%M')
    if '0855' <= now <= '1905':
        return True
    logger.info("Not open: not checking.")
    return False

def loop(kirppari_http, email):
    if (not testTime()):
        return

    kirppari = Kirppari(
        http=kirppari_http,
        email=email)
    new_sales = kirppari.getSales()
    kirppari.saveLists()

    for key, value in new_sales.items():
        print("New sale! {}: {}".format(value['name'], value['price']))
        kirppari.email.send(kirppari.makeSaleString(key))

    sortedValues = sorted(kirppari.sale_list.items(), key=lambda x: x[1]['row'], reverse=True)
    logger.info(sortedValues)
    for key, sale in sortedValues:
        logger.info(str(sale['row']) + ": " + kirppari.getSheet(key)['items'][key] + ", " + str(sale['price']))

    return kirppari


def main():
    parser = argparse.ArgumentParser(description='Get new sales from kirpparikalle  ')
    parser.add_argument('-r', '--resend', default=0, type=int, 
        help='Number of last sales to resend', 
        required=False)
    parser.add_argument('-d', '--debug', action='store_true', 
        help='Debug mode', 
        required=False)
    args = vars(parser.parse_args())

    global DEBUG_MODE
    DEBUG_MODE = args['debug']

    cfg = getConfig('config.ini')

    kirppari_http = KirppariHTTP(
        cfg['main']['PHPSESSID'], 
        cfg['main']['username'], 
        cfg['main']['password'])

    email = Email(
        cfg['email']['user'], 
        cfg['email']['password'], 
        cfg['email']['sender'], 
        json.loads(cfg['email']['recipient']),
    )

    kirppari = loop(
        kirppari_http=kirppari_http,
        email=email)

    c = args['resend']
    if (c > 0):
        if (not kirppari):
            kirppari = Kirppari(
                http=kirppari_http,
                email=email)
            kirppari.getSales()
        resend(c, kirppari)
        time.sleep(5)

    schedule.every(5).minutes.do(loop, 
        kirppari_http=kirppari_http,
        email=email)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("End")
    except Exception as e:
        logging.exception("Error happened within loop")

if __name__ == "__main__":
    main()
