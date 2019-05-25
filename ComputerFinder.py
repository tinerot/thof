import re
import socket
import urllib.request
import urllib.parse
from lxml import html
from Utils import Utils
import time
import os
from random import randint
import json
import datetime


class ComputerFinder:
    def __init__(self):
        self.headers = {'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"}
        self.blacklist = ['Białołęka', 'Wilanów', 'Wesoła', 'Wawer', 'Ursus', 'Rembertów', 'Targówek', 'Tarchomin']
        # self.blacklist = []
        self.banned_users = ['v1u114307443p1', 'v1u104708683p1', 'v1u110031518p1', 'v1u112951387p1', 'v1u112279346p1',
                             'v1u104758381p1', 'v1u104714794p1', 'v1u109432260p1', 'v1u104747383p1', 'v1u113773662p1',
                             'v1u106273094p1', 'v1u108900708p1', 'v1u112799929p1', 'v1u113446522p1', 'v1u113932676p1',
                             'v1u113729863p1', 'v1u111780756p1', 'v1u114087830p1', 'v1u114097713p1', 'v1u104729696p1',
                             'v1u104780607p1']
        try:
            self.id_olx = Utils.read_json_file('pc_id_olx.json')
        except FileNotFoundError:
            self.id_olx = []

    def get_pc_olx(self):
        self.flats = []
        url = 'https://www.olx.pl/elektronika/komputery/komputery-stacjonarne/warszawa/?search%5Bfilter_float_price%3Afrom%5D=1099&search%5Bfilter_float_price%3Ato%5D=2300&search%5Bdist%5D=50'
        html_page = self.safe_call(url)
        # get number of pages to search
        pages = str(html_page.xpath('//div[@class="pager rel clr"]')[0].text_content()).strip()
        number = re.findall(r'\d+', pages, re.DOTALL)[-1]

        for page in range(0, int(number)):
            url_page = url + '&page=' + str(page + 1)
            html_page = self.safe_call(url_page)
            offers = html_page.xpath('//table[@id="offers_table"]/tbody/tr/td[contains(@class,"offer")]')
            header = True
            for offer in offers:
                item = {}
                try:
                    item['id'] = offer.xpath('.//table')[0].attrib['data-id']
                    if item['id'] in self.id_olx:
                        self.id_olx.append(item['id'])
                        continue
                except Exception:
                    continue
                self.id_olx.append(item['id'])
                a_elem = offer.xpath('.//a')[1]
                item['link'] = a_elem.attrib['href']
                item['title'] = str(a_elem.text_content()).strip()
                item['price'] = str(offer.xpath('.//p[@class="price"]')[0].text_content()).strip()
                if 'apple' in item['title'].lower():
                    continue
                print('{} {} {}'.format(item['price'], item['link'], item['title']))
                self.process_olx(item)
                # delete multi-spaces
                if 1 == 0:
                    item['address'] = re.sub(' +', ' ', item['address'])
                    item['address'] = self.replace_rules(item['address'])
                # print(
                #     '{} {}    |    {}    |    {}'.format(item['id'], item['district'], item['address'], item['title']))
                self.flats.append(item)
        self.flats = sorted(self.flats, key=lambda k: (k['id']))
        Utils.deleteDuplicates(self.flats)
        # Utils.save_json_file('flats_olx.json', self.flats)
        sorted(self.id_olx)
        Utils.save_json_file('pc_id_olx.json', self.id_olx)

    def process_olx(self, item):
        html_page = self.safe_call(item['link'])
        description = str(html_page.xpath(r'//div[@id="textContent"]')[0].text_content())
        elem1 = re.findall(r'(?:GTX|[Nn][Vv][iI]|[Kk][Aa][Rr][Tt][Aa]|[Gg]rafika|[Rr]adeon).*', description)
        if len(elem1) > 0:
            print('Karta graficzna: {}'.format(elem1))
        elem2 = re.findall(r'(?:Intel|[Pp][Rr][Oo][Cc]|CPU|AMD).*', description)
        if len(elem2) > 0:
            print('Procesor: {}'.format(elem2))
        elem3 = re.findall(r'.*(?:[Pp][Aa][Mm][Ii]|R[Aa][Mm]).*', description)
        if len(elem3) > 0:
            print('Pamięć: {}'.format(elem3))
        # elem = re.findall(
        #     r'[uU]l(?:ica|icy){0,1}\.{0,1}\s{0,1}([A-ZŚŻŹŁĆŃ](?:\w{1,2}\.|\w+)(?:-{0,1}\s{0,1}[A-ZŚŻŹŁĆŃ]\w+)*\s{0,1}\d{0,4})',
        #     description)
        return None

    def process_otodom(self, title, url, district):
        html_page = self.safe_call(url)
        garage_tab = html_page.xpath(r'//ul[@class="dotted-list"]')
        # check for garage
        # test = str(garage_tab[-1].text_content()).strip()
        # res = test.find('garaż/miejsce parkingowe')
        # if res:
        #     pass
        # if not (len(garage_tab) > 1 and not str(garage_tab[-1].text_content()).find('garaż/miejsce parkingowe')):
        #    return None
        try:
            address = str(html_page.xpath(r'//p[@class="address-links"]')[0].text_content())
            return address[address.find('Warszawa'):address.rfind('-')]
        except IndexError:
            return None

    def process_gumtree_garage(self, flat_struct):
        html_page = self.safe_call(flat_struct['link'])
        userid = html_page.xpath('//span[@class="username"]/a/@href')[0]
        userid = userid[userid.rfind('/') + 1:]
        if self.banned_user(userid):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        if ',' in flat_struct['address']:
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = self.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    def process_gumtree(self, flat_struct):
        html_page = self.safe_call(flat_struct['link'])
        try:
            flat_size = \
                html_page.xpath('//div[@class="attribute"]/span[text()="Wielkość (m2)"]/following-sibling::span')[
                    0].text
            if int(flat_size) < 55:
                return None
        except IndexError:
            return None
        userid = html_page.xpath('//span[@class="username"]/a/@href')[0]
        userid = userid[userid.rfind('/') + 1:]
        if self.banned_user(userid):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        if ',' in flat_struct['address']:
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = self.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    def find_garage(self, text):
        garage = re.findall(r'[Gg]araż|[Mm]iejsc[eau]m?\spostojow', text)
        if len(garage) > 0:
            return True
        else:
            return False

    def find_address(self, text):
        address = re.findall(
            r'[uU]l(?:ica|icy){0,1}\.{0,1}\s{0,1}([A-ZŚŻŹŁĆŃ](?:\w{1,2}\.|\w+)(?:-{0,1}\s{0,1}[A-ZŚŻŹŁĆŃ]\w+)*\s{0,1}\d{0,4})',
            text)
        if len(address) > 0:
            return address[0]
        address = re.findall(r'róg\s[A-ZŚŻŹŁĆŃ]\w+\s(?:-|i\s)?[A-ZŚŻŹŁĆŃ]\w+', text)  # róg Skierniewickiej i Wolskiej
        if len(address) > 0:
            return address[0]
        # (?<!^)(?<!\.)(?<!\.\s)([A-ZŚŻŹŁĆŃ]\w+(?:-{0,1}\s{0,1}[A-ZŚŻŹŁĆŃ]\w+)*\s{0,1}\d{0,4})
        return None

    def blacklisted_discrict(self, district):
        for item in self.blacklist:
            if item in district:
                return True
        return False

    def banned_user(self, user):
        if user in self.banned_users:
            return True
        return False

    def safe_call(self, url, geo=None):
        done = False
        while not done:
            try:
                request = urllib.request.Request(url, headers=self.headers)
                response = urllib.request.urlopen(request, timeout=20)
                resp_code = int(str(response.code)[0])
                if resp_code != 2:
                    print('Error returned {} for URL: {}'.format(response.code, url))
                    time.sleep(2)
                    continue
            except urllib.error.HTTPError:
                print('Error returned for URL: {}'.format(url))
                time.sleep(2)
                continue
            except urllib.error.URLError:
                print('Timeout')
                continue
            except socket.timeout:
                print('Timeout')
                continue
            try:
                content = response.read()
            except socket.timeout:
                print('Timeout')
                continue
            done = True
        if not geo:
            return html.fromstring(content)
        else:
            return content

    def get_geolocalization(self, filename_src, filename_target):
        api_key = 'f'
        self.flats = Utils.read_json_file(filename_src)
        url_base = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&region=pl&address='.format(api_key)
        for flat in self.flats:
            if not flat['address']:
                continue
            if self.has_digit(flat['address']):
                flat['precise'] = True
            else:
                flat['precise'] = False
            address = urllib.parse.quote_plus(flat['address'].strip())
            url = url_base + address
            print('{} {} {}'.format(flat['link'], flat['address'], url))
            response = self.safe_call(url, True)
            resp_json = json.loads(response)
            latitude = resp_json['results'][0]['geometry']['location']['lat']
            longitude = resp_json['results'][0]['geometry']['location']['lng']
            if not flat['precise']:
                latitude = latitude + randint(0, 10) * 0.0001
                longitude = longitude + randint(0, 10) * 0.0001
            flat['latitude'] = latitude
            flat['longitude'] = longitude
        Utils.save_json_file(filename_target, self.flats)

    def has_digit(self, text):
        return any(char.isdigit() for char in text)

    def print_uknown(self, filename):
        print('\nPrinting flats with uknown location for {}:'.format(filename))
        self.flats = Utils.read_json_file(filename)
        for flat in self.flats:
            if flat['address']:
                continue
            print('{} {} {}'.format(flat['title'], flat['link'], flat['district']))

    def prepare_id_tab(self):
        self.flats = Utils.read_json_file('flats_olx_geo.json')
        ids = []
        for flat in self.flats:
            ids.append(flat['id'])
        sorted(ids)
        Utils.save_json_file('id_olx.json', ids)

    def replace_rules(self, text):
        text = text.replace('Dolny Mokotów', 'Mokotów')
        text = text.replace('Górny Mokotów', 'Mokotów')
        return text


if __name__ == "__main__":
    flat = ComputerFinder()
    print('Checking olx:')
    flat.get_pc_olx()

    # flat.prepare_id_tab()
