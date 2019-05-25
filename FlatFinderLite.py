from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from lxml import html
from jsmin import jsmin
import time
import json
import datetime
import urllib.request
import urllib.parse
import urllib.error
from Utils import Utils


class FlatFinderLite:
    def __init__(self):
        self.data = []
        self.end = False

    def run(self):
        url_base = 'https://rynekpierwotny.pl'
        url_params = '/oferty/?rooms_0=3&region=8647&rooms_1=4&distance=0&area_0=55&construction_end_date=12' \
                     '&area_1=75&sort=2'

        try:
            self.data = Utils.read_json_file('flats_route.json')
        except FileNotFoundError:
            pass
        driver = webdriver.Firefox()
        url_full = url_base + url_params
        for page in range(1, 100):
            url = url_full + "&page=" + str(page)
            print('Parsing page number {}...'.format(page))
            driver.get(url)
            # page doesn't exist so it reached the end
            if '404' in driver.title:
                break
            # main parsing method
            self.parse_page(driver)
            # if condition is met then it means the last new estate is already added
            if self.end:
                break
        Utils.save_json_file('flats_route.json', self.data)
        driver.close()

    def run_v2(self):
        url = 'https://rynekpierwotny.pl/oferty/?rooms_0=2&region=8647&rooms_1=4&distance=0&area_0=55&construction_end_date=12&area_1=75&sort=2'
        headers = {'authority': 'rynekpierwotny.pl', 'cache-control': 'max-age=0', 'upgrade-insecure-requests': '1', 'user-agent': 'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36'}
        submit_date = datetime.datetime.now().strftime('%d.%m.%y')
        try:
            self.data = Utils.read_json_file('flats_route_v2.json')
        except FileNotFoundError:
            pass
        for page in range(1, 100):
            url_call = url + "&page=" + str(page)
            print('Parsing page number {}...'.format(page))
            request = urllib.request.Request(url_call, headers=headers)
            try:
                response = urllib.request.urlopen(request, timeout=20)
            except urllib.error.HTTPError:
                break
            # extract offer JSON table
            content = response.read().decode('utf-8')
            index_start = content.find('Config.gtmOfferListProductImpressionsListing')
            index_start = content.find('impressions', index_start)
            index_start = content.find('[', index_start)
            index_end = content.find(']', index_start)+1
            json_str = content[index_start:index_end]
            offer_list = json.loads(json_str)
            for offer_elem in offer_list:
                offer = {}
                offer['id'] = offer_elem['id'][2:]
                offer['developer_name'] = offer_elem['brand'][offer_elem['brand'].find('/')+1:]
                offer['estate_name'] = offer_elem['category'][offer_elem['category'].find('/')+1:]
                # checking if the estated has already been added earlier
                estate = next((estate for estate in self.data if estate['id'] == offer['id']), None)
                if estate:
                    self.end = True
                    return
                offer['district'] = offer_elem['dimension3']
                offer['commissioning_date'] = offer_elem['dimension6']
                offer['url'] = 'https://www.google.pl/search?q=rynekpierwotny.pl+{}+{}'.format(offer['developer_name'], offer['estate_name'])
                if offer_elem['dimension12'] != 'na':
                    offer['price_m2_from'] = offer_elem['dimension12'][:offer_elem['dimension12'].find('-')]
                    offer['price_m2_to'] = offer_elem['dimension12'][offer_elem['dimension12'].find('-')+1:]
                # get langitude and latitude
                index_start = content.find('Config.reactFavouriteButton{}'.format(offer['id']))
                index_start = content.find('coordinates', index_start)
                index_start = content.find('[', index_start)
                offer['longitude'] = float(content[index_start+1:content.find(',', index_start)])
                offer['latitude'] = float(content[content.find(',', index_start)+1:content.find(']', index_start)].strip())
                offer['geo_url'] = 'https://www.google.pl/maps?q={},{}'.format(str(offer['latitude']), str(offer['longitude']))

                offer['submit_date'] = submit_date
                # get flats info
                request = urllib.request.Request('https://rynekpierwotny.pl/api/properties/property/?area_0=55&area_1=75&construction_end_date=12&for_sale=True&limited_presentation=False&offer={}&rooms_0=2&rooms_1=4'.format(offer['id']), headers=headers)
                response = urllib.request.urlopen(request, timeout=20)
                flats_json = json.loads(response.read().decode('utf-8'))
                flats = []
                for flat_json in flats_json['results']['properties']:
                    flat = {'number': flat_json['number'],
                            'id': int(flat_json['id']),
                            'rooms': int(flat_json['rooms']),
                            'area': float(flat_json['area'])}
                    if flat_json['floor'] is None:
                        flat['floor'] = int(flat_json['floor'])
                    if flat_json['price']:
                        flat['price'] = float(flat_json['price'])
                        flat['price_per_meter'] = flat['price'] / flat['area']
                    flats.append(flat)
                offer['flat'] = flats
                self.data.append(offer)
            if self.end:
                break
        Utils.save_json_file('flats_route_v2.json', self.data)


    def parse_document(self, content=None):
        if not content:
            content = Utils.read_file('section_source.html')
        html_page = html.fromstring(content)
        offer_elems = html_page.xpath('//div[@class="offer-item panel psr"]')
        submit_date = datetime.datetime.now().strftime("%d.%m.%y")

        for offer_elem in offer_elems:
            offer = {}
            json_elems = offer_elem.xpath('.//script')
            # get developer info
            product_json = self.format_to_json(json_elems[0].text, 3)
            product_json = jsmin(product_json)
            product_json = json.loads(product_json)
            product_json = product_json['ecommerce']['impressions'][0]
            offer['developer_name'] = product_json['brand'][product_json['brand'].find('/') + 1:]
            offer['estate_name'] = product_json['category'][product_json['category'].find('/') + 1:]
            # checking if the estated has already been added earlier
            estate = next((estate for estate in self.data if estate['estate_name'] == offer['estate_name']), None)
            if estate:
                self.end = True
                return
            offer['district'] = product_json['dimension3']
            offer['commissioning_date'] = product_json['dimension6']
            offer['postal_code'] = product_json['dimension7']
            offer['url'] = 'https://www.google.pl/search?q=rynekpierwotny.pl+' + offer['developer_name'] + '+' + offer[
                'estate_name']
            # get geo localization
            for line in json_elems[4].text.splitlines():
                if 'offer_latitude' in line:
                    latitude = line.split(':')[1]
                    offer['latitude'] = float("".join(latitude.split())[:9])
                if 'offer_longitude' in line:
                    longitude = line.split(':')[1]
                    offer['longitude'] = float("".join(longitude.split())[:9])
            offer['geo_url'] = 'https://www.google.pl/maps?q=' + str(offer['latitude']) + ',' + str(offer['longitude'])
            offer['submit_date'] = submit_date
            # get flats info
            flats_json = self.format_to_json(json_elems[2].text, 3)
            flats_json = jsmin(flats_json)
            flats_json = json.loads(flats_json)
            flats_json = flats_json['ecommerce']['impressions']
            flats = []
            for flat_json in flats_json:
                flat = {'number': int(''.join(filter(str.isdigit, flat_json['name']))),
                        'id': int(''.join(filter(str.isdigit, flat_json['id']))),
                        'rooms': int(flat_json['dimension13']),
                        'area': float(flat_json['dimension7'])}
                if flat_json['dimension8'].isdigit():
                    flat['floor'] = int(flat_json['dimension8'])
                else:
                    flat['floor'] = 0
                if flat_json['dimension11'] != 'na':
                    flat['price'] = int(flat_json['dimension11'])
                else:
                    flat['price'] = 9999999
                if flat_json['dimension12'] != 'na':
                    flat['price_per_meter'] = int(flat_json['dimension12'])
                else:
                    flat['price_per_meter'] = 99999
                flats.append(flat)
            offer['flat'] = flats
            self.data.append(offer)

    @staticmethod
    def format_to_json(data, no_of_brackets):
        for index in range(1, no_of_brackets + 1):
            data = data[data.find('{', 1):]
            data = data[:data.rfind('}', len(data) - 20, len(data))]
        data = data + '}'
        # print(data)
        return data

    def parse_page(self, driver):
        driver.implicitly_wait(10)
        # driver.find_element_by_xpath('//button[@id="onesignal-popover-cancel-button"]').click()
        # time.sleep(1)
        offer_elems = driver.find_elements_by_xpath('//div[@class="media mt-0 overflow-vi"]')
        driver.implicitly_wait(1)
        for offer_elem in offer_elems:
            # flat_elem = offer_elem.find_element_by_xpath('.//a[contains(text(), "Mieszkania spełniające kryteria")]')
            try:
                flat_elem = offer_elem.find_element_by_xpath('.//button[@data-testid="flat-property-list-dropdown-button"]')
            except NoSuchElementException:
                continue
            driver.execute_script("arguments[0].scrollIntoView();", offer_elem)
            try:
                driver.find_element_by_xpath('//a[@title="Close"]').click()
                time.sleep(2)
            except NoSuchElementException:
                pass
            flat_elem.click()

        time.sleep(4)
        content = driver.execute_script("return document.getElementsByClassName('offer-list')[0].innerHTML")
        self.parse_document(content)

    def fix_dates(self):
        self.data = Utils.read_json_file('flats_route.json')
        submit_date = datetime.datetime.now().strftime("%d.%m.%y")
        # submit_date = '06.02.2018'
        for estate in self.data:
            estate['submit_date'] = submit_date
        Utils.save_json_file('flats_route.json', self.data)


if __name__ == "__main__":
    flat_finder = FlatFinderLite()
    # flat_finder.fix_dates()
    flat_finder.run_v2()
