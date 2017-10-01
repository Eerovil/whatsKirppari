#!/usr/bin/env python
import requests
from bs4 import BeautifulSoup
import json
from subprocess import call
import logging
import argparse
import configparser

logging.basicConfig(filename='example.log', format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)


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
    sheet_list = {}
    sale_list = {}

    def __init__(self, config_path, target=""):
        config = self.getConfig(config_path)
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

    def send_msg(self, text):
        if (len(self.target) == 0):
            return
        cmd = '/home/pi/yowsup/yowsup-cli demos --config /home/pi/yowsup/yowsup-cli.config -y -tt ' + self.target + ' -mm'
        list = cmd.split()
        list.append(text)
        try:
            call(list, timeout=20)
        except Exception as e:
            print("timeout?")

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

    def getConfig(self, configpath):
        global config
        c = configparser.ConfigParser()
        c.read(configpath)
        if ('main' in c):
            self.config = c['main']
            return self.config
        else:
            c.add_section('main')
            c['main'] = {
                'PHPSESSID': '',
                'username': '',
                'password': '',
                'groupid': '',
            }
            with open('config.ini', 'w') as f:
                c.write(f)
        raise Exception("No config")

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
        for tr in tr_list:
            td_list = tr.find_all('td')
            id = td_list[0].text
            logging.info('  '+td_list[1].text)
            if (id not in self.sale_list):
                newsale = {'name': td_list[1].text, 'price': td_list[2].text, 'date': td_list[3].text}
                self.sale_list[id] = newsale
                s = self.getSheet(id)
                sheetName = s['name']
                nameFromSheet = s['items'][id]
                logging.debug("New sale: " + nameFromSheet + ", " + sheetName)
                self.send_msg("Myyty!: " + nameFromSheet + ", " + newsale['price'] + '. Lista: ' + sheetName + ', Nro: ' + id)
        
        return self.sale_list
            

def main():
    parser = argparse.ArgumentParser(description='Get new sales from kirpparikalle  ')
    parser.add_argument('-t', '--target', default='', help='Phone number to send', required=False)
    parser.add_argument('-r', '--resend', default=0, type=int, help='Number of last sales to resend', required=False)
    args = vars(parser.parse_args())

    kirppari = Kirppari('config.ini', target=args['target'])
    kirppari.login()
    kirppari.getSales()
    kirppari.saveLists()

    for key, sale in kirppari.sale_list.items():
        print(sale['name'])
        print(kirppari.getSheet(key)['items'][key])

    c = args['resend']
    if (c > 0):
        m = "Tässä " + str(c) + " viimeisintä myyntiä.\n"
        for key, sale in reversed(kirppari.sale_list.items()):
            c = c - 1
            if (c < 0):
                break
            print("RESENDING " + sale['name'])    
            s = kirppari.getSheet(sale['item_id'])
            m += sale['name'] + ", " + sale['price'] + '. Lista: ' + s['name'] + ', Nro: ' + sale['item_id'] + "\n"
        kirppari.send_msg(m)


if __name__ == "__main__":
    main()
