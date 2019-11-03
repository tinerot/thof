import datetime
import json
import os
import re
import smtplib
import ssl
import urllib.error
import urllib.parse
import urllib.request
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from random import randint

from Utils import Utils


class FlatFinder:
    DATA_PATH = 'data'

    def __init__(self):
        self.config = Utils.read_json_file('config.json')
        # Google API key
        self.api_key = self.config['api_key']
        today_datetime = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
        # today_datetime = '2019_11_02_22_53'
        for search_pair in self.config['search_pairs']:
            flat_gumtree_filename = os.path.join(FlatFinder.DATA_PATH,
                                                 'flats_gumtree_{}.json'.format(search_pair['gumtree']['unique_id']))
            flat_gumtree_filename_geo = os.path.join(FlatFinder.DATA_PATH, 'flats_gumtree_geo_{}_{}.json'.format(
                search_pair['gumtree']['unique_id'], today_datetime))

            print('Processing gumtree for https://gumtree.pl{} - {}'.format(search_pair['gumtree']['search_url'],
                                                          search_pair['gumtree']['unique_id']))
            self.get_flats_gumtree(flat_gumtree_filename, search_pair['gumtree'])
            self.get_geolocalization(flat_gumtree_filename, flat_gumtree_filename_geo)

            print('Processing gumtree for https://olx.pl{} - {}'.format(search_pair['olx']['search_url'],
                                                          search_pair['olx']['unique_id']))
            flat_olx_filename = os.path.join(FlatFinder.DATA_PATH,
                                             'flats_olx_{}.json'.format(search_pair['olx']['unique_id']))
            flat_olx_filename_geo = os.path.join(FlatFinder.DATA_PATH, 'flats_olx_geo_{}_{}.json'.format(
                search_pair['olx']['unique_id'], today_datetime))
            self.get_flats_olx(flat_olx_filename, search_pair['olx'])
            self.get_geolocalization(flat_olx_filename, flat_olx_filename_geo)

            print('\nResults:')
            if self.config['email_notification']['enabled']:
                self.send_email(self.config['email_notification'], flat_gumtree_filename_geo, flat_olx_filename_geo)
            else:
                print('Map URL: http://localhost:8000/draw_map.html?key={}&list={}&list={}'.format(self.api_key,
                                                                                          flat_gumtree_filename_geo,
                                                                                          flat_olx_filename_geo))
                print('List URL: http://localhost:8000/print_unknown.html?list={}&list={}'.format(flat_gumtree_filename_geo,
                                                                                        flat_olx_filename_geo))

    def get_flats_gumtree(self, filename, search):
        id_gumtree_filename = os.path.join(FlatFinder.DATA_PATH, 'id_gumtree_{}.json'.format(search['unique_id']))
        url = search['search_url']
        try:
            id_gumtree = Utils.read_json_file(id_gumtree_filename)
        except FileNotFoundError:
            id_gumtree = []
        flats = []
        url_base = 'https://www.gumtree.pl'

        # for index, url_page in enumerate(pages):
        for page_num in range(1, 1000):
            print('Page: ' + str(page_num))
            end_cond = True
            url_page = url_base + url.replace('p1', 'p' + str(page_num), 1)
            html_page = Utils.safe_call(url_page)
            offers = html_page.xpath('//div[@class="view"]/div[@class="tileV1"]')
            for offer in offers:
                flat = {'id': offer.xpath('.//div[@class="reply-action"]/div')[0].attrib['data-short-id']}
                if int(flat['id']) in id_gumtree:
                    id_gumtree.append(int(flat['id']))
                    continue
                id_gumtree.append(int(flat['id']))
                end_cond = False
                title_elem = offer.xpath('.//div[@class="title"]/a')[0]
                flat['link'] = url_base + title_elem.attrib['href']
                flat['title'] = title_elem.text
                print(flat['link'])
                flat = self.process_gumtree(flat, search)
                # skip this offer if it's from blacklisted district
                if not flat or self.blacklisted_district(flat['district']):
                    continue
                if not flat['address']:
                    flat['address'] = FlatFinder.find_address(flat['title'])
                print(
                    '{} {}    |    {}    |    {}'.format(flat['id'], flat['district'], flat['address'], flat['title']))
                flats.append(flat)
            if end_cond:
                break
        flats = sorted(flats, key=lambda k: (k['id']))
        Utils.delete_duplicates(flats)
        Utils.save_json_file(filename, flats)
        id_gumtree = sorted(id_gumtree)
        Utils.save_json_file(id_gumtree_filename, id_gumtree)

    def get_flats_olx(self, filename, search):
        id_olx_filename = os.path.join(FlatFinder.DATA_PATH, 'id_olx_{}.json'.format(search['unique_id']))
        url = search['search_url']
        try:
            id_olx = Utils.read_json_file(id_olx_filename)
        except FileNotFoundError:
            id_olx = []
        flats = []
        url = 'https://www.olx.pl' + url
        html_page = Utils.safe_call(url)
        # get number of pages to search
        try:
            pages = str(html_page.xpath('//div[@class="pager rel clr"]')[0].text_content()).strip()
            number = re.findall(r'.+(\d)', pages, re.DOTALL)[0]
        except IndexError:
            number = 1

        for page in range(0, int(number)):
            url_page = url + '&page=' + str(page + 1)
            html_page = Utils.safe_call(url_page)
            offers = html_page.xpath('//table[@id="offers_table"]/tbody/tr/td[contains(@class,"offer")]')
            for offer in offers:
                flat = {}
                try:
                    flat['id'] = offer.xpath('.//table')[0].attrib['data-id']
                    if int(flat['id']) in id_olx:
                        continue
                        id_olx.append(int(flat['id']))
                except IndexError:
                    continue
                id_olx.append(int(flat['id']))
                a_elem = offer.xpath('.//a')[1]
                flat['link'] = a_elem.attrib['href']
                print(flat['link'])
                flat['title'] = str(a_elem.text_content()).strip()
                p_elems = offer.xpath('.//tr[2]//p//span')
                # find the district
                flat['district'] = str(p_elems[0].text_content()).strip()
                # find an address
                if 'olx.pl' in flat['link']:
                    flat['address'] = FlatFinder.process_olx(flat['title'], flat['link'], flat['district'])
                else:
                    flat['address'] = FlatFinder.process_otodom(flat['link'], flat['district'])
                # skip this offer if it's from blacklisted discrict
                if self.blacklisted_district(flat['district']):
                    continue
                # delete multi-spaces
                if flat['address']:
                    flat['address'] = re.sub(' +', ' ', flat['address'])
                    flat['address'] = self.replace_rules(flat['address'])
                print(
                    '{} {}    |    {}    |    {}'.format(flat['id'], flat['district'], flat['address'], flat['title']))
                flats.append(flat)
        flats = sorted(flats, key=lambda k: (k['id']))
        Utils.delete_duplicates(flats)
        Utils.save_json_file(filename, flats)
        id_olx = sorted(id_olx)
        Utils.save_json_file(id_olx_filename, id_olx)

    @staticmethod
    def process_olx(title, url, district):
        address = FlatFinder.find_address(title)
        if address:
            return '{}, {}'.format(district, address)
        html_page = Utils.safe_call(url)
        description = str(html_page.xpath(r'//div[@id="textContent"]')[0].text_content())
        # garage check
        # if not self.find_garage(description):
        #    return None
        address = FlatFinder.find_address(description)
        if address:
            return '{}, {}'.format(district, address)
        return None

    @staticmethod
    def process_otodom(url, district):
        html_page = Utils.safe_call(url)
        # garage_tab = html_page.xpath(r'//ul[@class="dotted-list"]')
        # check for garage
        # test = str(garage_tab[-1].text_content()).strip()
        # res = test.find('garaż/miejsce parkingowe')
        # if res:
        #     pass
        # if not (len(garage_tab) > 1 and not str(garage_tab[-1].text_content()).find('garaż/miejsce parkingowe')):
        #    return None
        try:
            try:
                json_elem = html_page.xpath('//script[@id="server-app-state"]')
                json_content = json.loads(json_elem[0].text_content())
                address = json_content['initialProps']['data']['advert']['breadcrumb'][-1]['label']
                to_remove = district.split(',')
                for rem in to_remove:
                    address = address.replace(rem.strip(), '')
                if len(address.strip()) > 0:
                    return '{}, {}'.format(district, address)
            except IndexError:
                pass
            address = html_page.xpath('//a[contains(@href, "street_id")]')
            if address:
                address = address[0].text_content()
            else:
                descr = html_page.xpath('//section[@class="section-description"]')[0].text_content()
                address = FlatFinder.find_address(descr)
            if address:
                return '{}, {}'.format(district, address)
            # address = str(html_page.xpath(r'//p[@class="address-links"]')[0].text_content())
            # return address[address.find(self.city_name):address.rfind('-')]
        except IndexError:
            return None

    def process_gumtree_garage(self, flat_struct):
        html_page = Utils.safe_call(flat_struct['link'])
        userid = html_page.xpath('//span[@class="username"]/a/@href')[0]
        userid = userid[userid.rfind('/') + 1:]
        if self.banned_user(userid):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        if ',' in flat_struct['address']:
            # remove postcode
            result = re.findall(r'\d{2}-\d{3}', flat_struct['address'])
            if len(result) > 0:
                flat_struct['address'] = flat_struct['address'].replace(result[0], '')
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = self.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    def process_gumtree(self, flat_struct, search):
        html_page = Utils.safe_call(flat_struct['link'])
        try:
            flat_size = \
                html_page.xpath('//div[@class="attribute"]/span[text()="Wielkość (m2)"]/following-sibling::span')[
                    0].text
            if int(flat_size) < search['min_flat_size']:
                return None
            room_num = html_page.xpath('//div[@class="attribute"]/span[text()="Liczba pokoi"]/following-sibling::span')[
                0].text
            if not any(char.isdigit() for char in room_num):
                return None
            flat_struct['address'] = html_page.xpath('//h5[@class="full-address"]/span[@class="address"]')[0].text
        except IndexError:
            return None
        user_id = html_page.xpath('//span[@class="username"]/a/@href')[0]
        user_id = user_id[user_id.rfind('/') + 1:]
        if self.banned_user(user_id):
            return None
        flat_struct['district'] = re.sub(r'\s{2,}', '',
                                         str(html_page.xpath('//div[@class="location"]')[1].text_content()))
        remove_part = flat_struct['district'].split(',')
        for rem in remove_part:
            flat_struct['address'] = flat_struct['address'].replace(rem.strip(), '')
        flat_struct['address'] = flat_struct['address'].replace(',', '')
        # remove postcode
        result = re.findall(r'\d{2}-\d{3}', flat_struct['address'])
        if len(result) > 0:
            flat_struct['address'] = flat_struct['address'].replace(result[0], '')
        if len(flat_struct['address'].strip()) > 0:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
            return flat_struct
        description = str(html_page.xpath('//div[@class="description"]')[0].text_content())
        flat_struct['address'] = FlatFinder.find_address(description)
        if flat_struct['address']:
            flat_struct['address'] = '{}, {}'.format(flat_struct['district'], flat_struct['address'])
        return flat_struct

    @staticmethod
    def find_address(text):
        address = re.findall(
            r'[uU]l(?:ica|icy){0,1}\.{0,1}\s{0,1}([A-ZŚŻŹŁĆŃ](?:\w{1,2}\.|\w+)(?:-{0,1}\s{0,1}[A-ZŚŻŹŁĆŃ]\w+)*\s{0,1}\d{0,4})',
            text)
        if len(address) > 0:
            return address[0]
        return None

    def blacklisted_district(self, district):
        for item in self.config['districts_blacklist']:
            if item in district:
                return True
        return False

    def banned_user(self, user):
        if user in self.config['gumtree_settings']['banned_users']:
            return True
        return False

    def get_geolocalization(self, filename_src, filename_target):
        flats = Utils.read_json_file(filename_src)
        url_base = 'https://maps.googleapis.com/maps/api/geocode/json?key={}&region=pl&address='.format(self.api_key)
        for flat in flats:
            if not flat['address']:
                continue
            if FlatFinder.has_digit(flat['address']):
                flat['precise'] = True
            else:
                flat['precise'] = False
            address = urllib.parse.quote_plus(flat['address'].strip())
            url = url_base + address
            print('{} {} {}'.format(flat['link'], flat['address'], url))
            # response = urllib.request.urlopen(url)
            response = Utils.safe_call(url, True)
            resp_json = json.loads(response)
            latitude = resp_json['results'][0]['geometry']['location']['lat']
            longitude = resp_json['results'][0]['geometry']['location']['lng']
            if not flat['precise']:
                latitude = latitude + randint(0, 10) * 0.0001
                longitude = longitude + randint(0, 10) * 0.0001
            flat['latitude'] = latitude
            flat['longitude'] = longitude
        Utils.save_json_file(filename_target, flats)

    @staticmethod
    def print_unknown(filename):
        print('\nPrinting flats with uknown location for {}:'.format(filename))
        flats = Utils.read_json_file(filename)
        for flat in flats:
            if flat['address']:
                continue
            print('{} {} {}'.format(flat['title'], flat['link'], flat['district']))

    @staticmethod
    def replace_rules(text):
        text = text.replace('Dolny Mokotów', 'Mokotów')
        text = text.replace('Górny Mokotów', 'Mokotów')
        return text

    @staticmethod
    def find_garage(text):
        garage = re.findall(r'[Gg]araż|[Mm]iejsc[eau]m?\spostojow', text)
        if len(garage) > 0:
            return True
        else:
            return False

    @staticmethod
    def has_digit(text):
        return any(char.isdigit() for char in text)

    def send_email(self, settings, file1, file2):
        content1 = Utils.read_json_file(file1)
        content2 = Utils.read_json_file(file2)
        if not content1 and not content2:
            print("No new results and nothing to send!")
            return

        date_formatted = datetime.datetime.now().strftime("%d.%m.%Y %H:%M")
        smtp_server = settings['smtp_server']
        port = settings['port']
        sender_email = settings['sender_email']
        receiver_email = settings['receiver_email']
        password = settings['password']

        message = MIMEMultipart("alternative")
        message["Subject"] = "Mieszkania z dn. {}".format(date_formatted)
        message["From"] = sender_email
        message["To"] = receiver_email
        receiver_emails = receiver_email.split(',')

        url_flats_map = '{}/draw_map.html?key={}&list={}&list={}'.format(settings['url'], self.api_key, file1, file2)
        url_flats_list = '{}/print_unknown.html?list={}&list={}'.format(settings['url'], file1, file2)

        html = """\
        <html>
          <body>
            <p>Mieszkania z dn. {}</p>
            <p>
        """.format(date_formatted)
        if [True for elem in content1 if elem['address']] or [True for elem in content2 if elem['address']]:
            html = """{}\
                <a href="{}">Mapa mieszkań</a><br>
            """.format(html, url_flats_map)
        if [True for elem in content1 if not elem['address']] or [True for elem in content2 if not elem['address']]:
            html = """{}\
                <a href= "{}">Mieszkania bez lokalizacji</a>
            """.format(html, url_flats_list)
        html = """{}\
            </p>
          </body>
        </html>""".format(html)
        message.attach(MIMEText(html, "html"))

        # Try to log in to server and send email
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_emails, message.as_string())


if __name__ == "__main__":
    flat_finder = FlatFinder()

    # today_date = datetime.datetime.now().strftime("%Y_%m_%d_%H_%M")
    # flats_gumtree_geo = 'flats_gumtree_geo_{}.json'.format(today_date)
    # flats_olx_geo = 'flats_olx_geo_{}.json'.format(today_date)
    # flats_kaw_gumtree_geo = 'flats_kaw_gumtree_geo_{}.json'.format(today_date)
    # flats_kaw_olx_geo = 'flats_kaw_olx_geo_{}.json'.format(today_date)
    # flats_kaw_olx_geo = 'flats_kaw_olx_geo_{}.json'.format(today_date)
    #
    # print('\nChecking gumtree:')
    # flat.get_flats_gumtree('flats_gumtree',
    #                        '/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1?df=ownr&pr=,450000&sort=dt&order=desc',
    #                        'id_gumtree.json', min_flat_size=38)
    # flat.get_geolocalization('flats_gumtree.json', flats_gumtree_geo)
    # print('\nChecking olx:')
    # flat.get_flats_olx('flats_olx',
    #                    '/nieruchomosci/mieszkania/sprzedaz/warszawa/?search%5Bfilter_float_price%3Ato%5D=450000&search%5Bfilter_float_m%3Afrom%5D=38&search%5Bfilter_enum_rooms%5D%5B0%5D=two&search%5Bfilter_enum_rooms%5D%5B1%5D=three&search%5Bfilter_enum_rooms%5D%5B2%5D=four&search%5Bphotos%5D=1&search%5Bprivate_business%5D=private&search%5Border%5D=created_at%3Adesc',
    #                    'id_olx.json')
    # flat.get_geolocalization('flats_olx.json', flats_olx_geo)
    #
    # print('\nKawalerki Checking gumtree:')
    # flat.get_flats_gumtree('flats_kaw_gumtree',
    #                        '/s-mieszkania-i-domy-sprzedam-i-kupie/warszawa/v1c9073l3200008p1?df=ownr&pr=,330000&nr=10&sort=dt&order=desc',
    #                        'id_kaw_gumtree.json', min_flat_size=29)
    # flat.get_geolocalization('flats_kaw_gumtree.json', flats_kaw_gumtree_geo)
    # print('\nKawalerki Checking olx:')
    # flat.get_flats_olx('flats_kaw_olx',
    #                    '/nieruchomosci/mieszkania/sprzedaz/warszawa/?search[filter_float_price%3Ato]=330000&search[filter_float_m%3Afrom]=29&search[filter_enum_rooms][0]=one&search[photos]=1&search[private_business]=private&search[order]=created_at%3Adesc',
    #                    'id_kaw_olx.json')
    # flat.get_geolocalization('flats_kaw_olx.json', flats_kaw_olx_geo)
    #
    # # print flats where the geolocation in unknown
    # flat.print_uknown(flats_olx_geo)
    # flat.print_uknown(flats_gumtree_geo)
    #
    # # print flats where the geolocation in unknown
    # flat.print_uknown(flats_kaw_olx_geo)
    # flat.print_uknown(flats_kaw_gumtree_geo)
    #
    # flat.send_email(flats_gumtree_geo, flats_olx_geo, flats_kaw_gumtree_geo, flats_kaw_olx_geo)
