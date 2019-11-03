import csv
import json
import socket
import time
import urllib.error
import urllib.parse
import urllib.request

from lxml import html


class Utils:
    @staticmethod
    def save_json_file(filename, content):
        with open(filename, 'w', encoding='utf8') as outfile:
            json.dump(content, outfile, sort_keys=True, indent=4, ensure_ascii=False)  # sort_keys = True, indent = 4

    @staticmethod
    def read_json_file(filename):
        file = open(filename, 'r', encoding='utf8')
        return json.load(file)

    @staticmethod
    def save_file(filename, content):
        with open(filename, 'w', encoding='utf8') as outfile:
            outfile.write(content)

    @staticmethod
    def read_file(filename):
        file = open(filename, 'r', encoding='utf8')
        return file.read()

    @staticmethod
    def save_csv_file(filename, data):
        with open(filename, mode='w', encoding='utf8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(data)

    @staticmethod
    def delete_duplicates(items):
        i = 1
        while i < len(items):
            if items[i]['id'] == items[i - 1]['id']:
                items.pop(i)
                i -= 1
            i += 1

    @staticmethod
    def safe_call(url, geo=None):
        headers = {'User-Agent': "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:48.0) Gecko/20100101 Firefox/48.0"}
        done = False
        content = None
        while not done:
            try:
                request = urllib.request.Request(url, headers=headers)
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
