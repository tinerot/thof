from Utils import Utils


class ResultGenerator:
    @staticmethod
    def dump_json_to_csv(filename):
        json_file = Utils.read_json_file(filename)
        data = []
        header = ['Nazwa dewelopera', 'Nazwa inwestycji', 'Data oddania', 'Data dodania', 'Dzielnica', 'Czas dojazdu 1',
                  'Pojazdy 1', 'Międzyczasy 1', 'URL 1', 'Czas dojazdu 2', 'Pojazdy 2', 'Międzyczasy 2', 'URL 2',
                  'Dystans', 'Czas dojazdu',
                  'Numer', 'Piętro', 'Powierzchnia', 'Liczba pokoi', 'Cena', 'Cena za m^2', 'ID', 'Położenie',
                  'Szerokość', 'Długość', 'Wyszukaj inwestycję', 'Kod pocztowy']
        data.append(header)
        for estate in json_file:
            fields_1 = [estate['developer_name'], estate['estate_name'], estate['commissioning_date'],
                        estate['submit_date'], estate['district']]
            for route in estate['route']:
                fields_1.append(route['time'])
                fields_1.append(route['vehicles'])
                fields_1.append(route['departure_time'])
                fields_1.append(route['url'])
            fields_1.append(str(estate['route_gmaps']['distance']).replace('.', ','))
            fields_1.append(estate['route_gmaps']['duration'])
            fields_2 = [estate['geo_url'], estate['latitude'], estate['longitude'], estate['url'],
                        estate['postal_code']]
            for flat in estate['flat']:
                fields_flat = [flat['number'], flat['floor'], str(flat['area']).replace('.', ','), flat['rooms'], flat['price'],
                               flat['price_per_meter'], flat['id']]
                fields = []
                fields.extend(fields_1)
                fields.extend(fields_flat)
                fields.extend(fields_2)
                data.append(fields)
        Utils.save_csv_file('flats1.csv', data)


if __name__ == "__main__":
    result = ResultGenerator()
    result.dump_json_to_csv('flats_route.json')
