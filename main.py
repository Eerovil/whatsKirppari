import requests
import os
from bs4 import BeautifulSoup
import pickle
from subprocess import call
import logging
import time
import argparse

import configparser
c = configparser.ConfigParser()
c.read('config.ini')
config = c['main']

sheet_list = []
sale_list = []


headers = { 'DNT': '1',
'Accept-Encoding': 'gzip, deflate, br', 
'Accept-Language': 'en-US,en;q=0.8,fi;q=0.6', 
'Upgrade-Insecure-Requests': '1', 
'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36'
,'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
 'Referer': 'https://www.kirpparikalle.net/sovellus/index.php?page=myreservations',
 'Cookie': 'PHPSESSID=' + config['PHPSESSID'],
 'Connection': 'keep-alive'
}
url = 'https://www.kirpparikalle.net/sovellus/index.php?page=mysales'
login_url = 'https://www.kirpparikalle.net/sovellus/rpc.php?request=json_login&method=username_login&lang=fi&company_id=1&username='+config['username']+'&password=' + config['password']

main_url = 'https://www.kirpparikalle.net/sovellus/'
lists_url = 'https://www.kirpparikalle.net/sovellus/index.php?page=myproducts'
parser = argparse.ArgumentParser(description='Get new sales from kirpparikalle  ')
parser.add_argument('-t','--target', default=config['groupid'], help='Phone number to send', required=False)
parser.add_argument('-r','--resend', default=0, type=int, help='Number of last sales to resend', required=False)
args = vars(parser.parse_args())

logging.basicConfig(filename='example.log', format='%(asctime)s %(levelname)s:%(message)s',level=logging.DEBUG)

class Sale():
    def __init__(self, item_id, name, price, date):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.date = date

def find_sale(item_id, sale_list):
    for sale in sale_list:
        if (sale.item_id == item_id):
            return sale
    return None


class Sheet():
    items = []
    def __init__(self, item_id, name, link):
        self.item_id = item_id
        self.name = name
        self.link = link
        self.items = []
    
    def add_item(self, item_id):
        self.items.append(item_id)

    def contains_item(self, item_id):
        if (item_id in self.items):
            return True
        return False

def getSheet(item_id):
    print("Finding sheet")
    for s in sheet_list:
        if (s.contains_item(item_id)):
            return s
    get_sheets()
    
    for s in sheet_list:
        if (s.contains_item(item_id)):
            return s
    return None

def send_msg(text):
    target = args['target']
    if (len(target) == 0): return
    cmd = '/home/pi/yowsup/yowsup-cli demos --config /home/pi/yowsup/yowsup-cli.config -y -tt ' + target + ' -mm'
    list = cmd.split()
    list.append(text)
    try:
        call(list, timeout=20)
    except Exception as e:
        print("timeout?")
    #p = Popen(list)#, stdout=PIPE, stdin=PIPE, stderr=PIPE)
    #time.sleep(1)
    #res = p.communicate(input=b"/L\n")#/message send \"" + text.encode('utf8') + b"\"\n")
    #print(res[0])    
    #time.sleep(2)
    #try:
    #    p.terminate()
    #except Exception as e:
    #    print("could not terminate")

def get_sheets():
    #try:
        r = requests.get(lists_url, headers=headers, verify=False)
        soup = BeautifulSoup(r.text, 'html.parser')
        tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
        sheet_list[:] = []
        for tr in tr_list:
            td_list = tr.find_all('td')
            sheet_url = main_url + td_list[8].find('a')['href']
            sheet_name = td_list[1].text
            sheet_id = td_list[0].text
            print(sheet_id)
            sheet_list.append(Sheet(sheet_id, sheet_name, sheet_url))
            sheet_r = requests.get(sheet_url, headers=headers, verify=False)
            sheet_soup = BeautifulSoup(sheet_r.text, 'html.parser')
            sheet_tr_list = sheet_soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
            print(sheet_tr_list[0].find('td').text)
            for sheet_tr in sheet_tr_list:
                sheet_td_list = sheet_tr.find_all('td')
                if (len(sheet_td_list) > 0):
                    sheet_list[-1].add_item(sheet_td_list[0].text)
    #except Exception as e:
    #    logging.critical('could not get sheets')
    #    logging.critical(e)


def main():
    r = requests.get(login_url, headers=headers, verify=False)
    print(r.text)
    r = requests.get(url, headers=headers, verify=False)
    #f = open("kirppari.html", 'r')
    try:
        with open("kirppari.pickle", 'rb') as input:
            sale_list = pickle.load(input)
    except:
        with open("kirppari.pickle", 'wb') as output:
            pickle.dump(sale_list, output)
    try:
        with open("kirppari_lists.pickle", 'rb') as output:
            sheet_list = pickle.load(output)
    except:
        with open("kirppari_lists.pickle", 'wb') as output:
            pickle.dump(sheet_list, output)

    #soup = BeautifulSoup(f.read(), 'html.parser')
    soup = BeautifulSoup(r.text, 'html.parser')

    #try: 
    tr_list = soup.find('table', attrs={'class': 'normal'}).find('tbody').find_all('tr')
    for tr in tr_list:
        td_list = tr.find_all('td')
        id = td_list[0].text
        logging.info('  '+td_list[1].text)
        if (find_sale(id, sale_list) == None):
            newsale = Sale(td_list[0].text,td_list[1].text,td_list[2].text,td_list[3].text)
            sale_list.append(newsale)
            s = getSheet(newsale.item_id)
            logging.debug("New sale: " + newsale.name + ", " + s.name)
            send_msg("Myyty!: " + newsale.name + ", " + newsale.price + '. Lista: ' + s.name + ', Nro: ' + newsale.item_id)
            
    #except Exception as e:
    #    logging.critical(e)

    for sale in sale_list:
        print(sale.name)
        print(getSheet(sale.item_id).name)

    c = args['resend']
    if (c > 0):
        m = "Tässä " + str(c) + " viimeisintä myyntiä.\n"
        for sale in reversed(sale_list):
            c = c - 1
            if (c < 0):
                break
            print("RESENDING " + sale.name)    
            s = getSheet(sale.item_id)
            m += sale.name + ", " + sale.price + '. Lista: ' + s.name + ', Nro: ' + sale.item_id + "\n"
        send_msg(m)

    with open("kirppari.pickle", 'wb') as output:
        pickle.dump(sale_list, output)
    with open("kirppari_lists.pickle", 'wb') as output:
        pickle.dump(sheet_list, output)


if __name__ == "__main__": main()
