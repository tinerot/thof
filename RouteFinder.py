from selenium import webdriver
from Utils import Utils
import datetime
import time
import urllib.request
import json


class RouteFinder:
    def __init__(self):
        self.data = []

    def jakdojade_route(self):
        url_base = 'https://jakdojade.pl/warszawa/trasa/trasa?'
        target_geo = '52.237052:20.996032'
        day = self.next_weekday(datetime.datetime.now(), 0)
        hour = '08:00'
        url_params = ['&ia=true&aro=1&t=1&rc=3&ri=2&r=0', '&ia=true&aac=true&aro=1&aab=true&t=1&rc=3&ri=1&r=0']

        print('Jak Dojadę route finder:')
        self.data = Utils.read_json_file('flats_route.json')
        driver = webdriver.Firefox()
        iteration = 0
        for estate in self.data:
            if 'route' in estate:
                continue
            print('\n{} | {}'.format(estate['developer_name'], estate['estate_name']))
            routes = []
            for url_param in url_params:
                url = url_base + 'tc=' + target_geo + '&fc=' + str(estate['latitude']) + ':' + \
                      str(estate['longitude']) + '&ft=LOCATION_TYPE_ADDRESS&tt=LOCATION_TYPE_ADDRESS&d=' + \
                      day + '&h=' + hour + url_param
                print(url)
                iteration = iteration + 1
                if iteration % 60 == 0:
                    driver.close()
                    time.sleep(2)
                    driver = webdriver.Firefox()
                driver.get(url)
                driver.implicitly_wait(20)
                route = {'time': 9999,
                         'url': url}
                for route_elem in driver.find_elements_by_xpath('//div[@class="cn-vehicle-info"]'):
                    time_tmp = route_elem.find_element_by_xpath('.//div[@class="cn-travel-time"]').text
                    time_tmp = RouteFinder.convert_to_minutes(time_tmp)
                    if time_tmp >= route['time']:
                        continue
                    route['time'] = time_tmp
                    route['vehicles'] = route_elem.find_element_by_xpath(
                        './/div[@class="route-vehicles"]').text.replace(' ', ' - ')
                    while not route['vehicles'] or route['vehicles'] == '':
                        time.sleep(2)
                        print('Delay occurred...')
                        route['vehicles'] = route_elem.find_element_by_xpath(
                            './/div[@class="route-vehicles"]').text.replace(' ', ' - ')
                    route['departure_time'] = route_elem.find_element_by_xpath(
                        './/div[@class="cn-departure-time"]').text.replace('\n', ' - ')
                print('{} | {} | {}'.format(route['time'], route['vehicles'], route['departure_time']))
                routes.append(route)
            estate['route'] = routes
        Utils.save_json_file('flats_route.json', self.data)
        driver.close()

    def googlemaps_route(self, filename):
        api_key = ''
        target_geo = '52.237052,20.996032'
        mode = 'bicycling'
        url_base = 'https://maps.googleapis.com/maps/api/distancematrix/json?mode={}&key={}'.format(mode, api_key)

        print('Google Maps route finder:')
        self.data = Utils.read_json_file(filename)
        for estate in self.data:
            route = {}
            if 'route_gmaps' in estate:
                continue
            url = '{}&origins={},{}&destinations={}'.format(url_base, estate['latitude'], estate['longitude'], target_geo)
            print('\n{} | {} | {}'.format(estate['developer_name'], estate['estate_name'], url))
            response = urllib.request.urlopen(url)
            resp_json = json.loads(response.read())
            route_elem = resp_json['rows'][0]['elements'][0]
            distance = float('{0:.2f}'.format(float(route_elem['distance']['value']) / 1000))
            duration = int(float(route_elem['duration']['value']) / 60)
            route['distance'] = distance
            route['duration'] = duration
            route['url'] = url
            estate['route_gmaps'] = route
        Utils.save_json_file(filename, self.data)

    @staticmethod
    def convert_to_minutes(data):
        times = [int(s) for s in data.split() if s.isdigit()]
        if len(times) == 2:
            return times[0] * 60 + times[1]
        else:
            return times[0]

    @staticmethod
    def next_weekday(d, weekday):
        days_ahead = weekday - d.weekday()
        if days_ahead <= 0:  # Target day already happened this week
            days_ahead += 7
        date = d + datetime.timedelta(days_ahead)
        return date.strftime("%d.%m.%y")


if __name__ == "__main__":
    route_finder = RouteFinder()
    route_finder.googlemaps_route('flats_route_v2.json')
    # route_finder.jakdojade_route()
