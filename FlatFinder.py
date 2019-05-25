from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import time
import json


class FlatFinder:
    def __init__(self):
        self.data = []

    def run(self):
        url_base = 'https://rynekpierwotny.pl'
        url_params = '/oferty/?type=1&region=8647&distance=0&rooms_0=2&rooms_1=3&area_0=40&area_1=70&sort=2'

        driver = webdriver.Firefox()
        url = url_base + url_params
        for page in range(1, 2):
            url = url + "&page=" + str(page)
            driver.get(url)
            if '404' in driver.title:
                break
            self.parse_page(driver)
        self.save_json_file('flats.json', self.data)
        driver.close()

    def parse_page(self, driver):
        driver.implicitly_wait(10)
        offer_elems = driver.find_elements_by_xpath('//div[@class="media mt-0 overflow-vi"]')

        for offer_elem in offer_elems:
            offer = {}
            driver.implicitly_wait(10)
            driver.execute_script("arguments[0].scrollIntoView();", offer_elem)
            # get estate name
            offer['estate_name'] = offer_elem.find_element_by_xpath('.//h2/a').text

            # get developer name
            info_elem = offer_elem.find_element_by_xpath('.//div[@class="media-right tac pt-xl"]')
            offer['dev_name'] = info_elem.find_element_by_xpath('.//img').get_attribute('title')

            # get commissioning date
            offer['commissioning_date'] = offer_elem.find_element_by_xpath(
                './/ul[@class="lsn pt-xl offer-item-list item-xl mb-0"]/li/span').text

            # get geo location
            geo_elem = offer_elem.find_element_by_xpath('.//span[@itemprop="geo"]')
            offer['latitude'] = geo_elem.find_element_by_xpath('./meta[@itemprop="latitude"]').get_attribute('content')[
                                :9].replace(',', '.')
            offer['longitude'] = geo_elem.find_element_by_xpath('./meta[@itemprop="longitude"]').get_attribute(
                'content')[:9].replace(',', '.')

            print('{} | {} | {} | {}:{}'.format(offer['estate_name'], offer['dev_name'], offer['commissioning_date'],
                                                offer['latitude'], offer['longitude']))

            # get available flats
            driver.implicitly_wait(1)
            try:
                driver.find_element_by_xpath('//a[@title="Close"]').click()
                time.sleep(2)
            except NoSuchElementException:
                pass
            driver.implicitly_wait(10)
            info_elem.find_element_by_xpath('.//a[contains(text(), "Mieszkania spełniające kryteria")]').click()

            #TODO
            time.sleep(4)
            print("Getting source code of the table")
            html = driver.execute_script("return document.getElementsByTagName('html')[0].innerHTML")
            #html = driver.execute_script("return document.evaluate('//div[@class=\"dataTables_scroll\"]', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue")
            print(html)
            break

            table_elem = offer_elem.find_elements_by_xpath('.//table')[1]
            flat_elems = table_elem.find_elements_by_xpath('.//tbody/tr[@role="row"]')

            flats = []
            for flat_elem in flat_elems:
                flat_table = flat_elem.find_elements_by_xpath('./td')
                flat = {'flat_no': flat_table[1].text,
                        'flat_rooms': flat_table[2].text,
                        'flat_space': flat_table[3].text,
                        'flat_floor': flat_table[4].text}
                flat_price_text = flat_table[5].find_element_by_xpath('./div/*').text
                if 'zł' in flat_price_text:
                    tmp_array = flat_price_text.split('zł')
                    flat['flat_price'] = "".join(tmp_array[0].split())
                    flat['flat_price_per_meter'] = "".join(tmp_array[1].split())
                flat['flat_url'] = flat_table[7].find_element_by_xpath('./a').get_attribute('href')
                # print('{} | {} | {} | {} | {} | {} | {}'.format(flat_no, flat_rooms, flat_space, flat_floor,
                # flat_price, flat_price_per_meter, flat_url))
                flats.append(flat)
            offer['flats'] = flats
            self.data.append(offer)

    def save_json_file(self, filename, content):
        with open(filename, 'w', encoding='utf8') as outfile:
            json.dump(content, outfile, sort_keys=True, indent=4, ensure_ascii=False)  # sort_keys = True, indent = 4


if __name__ == "__main__":
    flat_finder = FlatFinder()
    flat_finder.run()
