from datetime import timedelta

import requests

from Itinerary import Itinerary
from Itinerary_Driving import Driving
from Itinerary_Transit import Transit
from Itinerary_Walking import Walking
from Place import Place


class Autolib(Itinerary):
    __URL_AUTOLIB = 'https://opendata.paris.fr/api/records/1.0/search/'
    __PARAMETERS = "dataset=autolib-disponibilite-temps-reel&q=status%3Dok+AND+cars%3E0"
    __COMMUTING_DURATION = 60  # La durée de correspondance

    def __init__(self, origin, destination, date=None, transit_mode_type=None, itinerary_index=0):
        Itinerary.__init__(self, origin, destination, date, transit_mode_type, itinerary_index)
        self.transport_mode = "autolib"

        # Station autolib d'origine
        stop = True
        search_size = 1
        while stop:
            parameters = Autolib.__PARAMETERS + "&geofilter.distance=" + "%2C".join(
                [str(destination.lat), str(destination.lng), str(search_size * 1000)])
            r = requests.get(Autolib.__URL_AUTOLIB, parameters)
            raw_data = r.json()
            search_size += 1
            stations_origin = []
            possible_stations = raw_data['records']
            for possible_station in possible_stations:
                available_car = possible_station['fields']['cars']
                if available_car == 0:
                    pass
                else:
                    stop = False
                    stations_origin.append({})
                    stations_origin[-1]['station_address'] = Place(address=(possible_station['fields']['address']
                                                                            + " "
                                                                            + possible_station['fields']['postal_code']
                                                                            + " Paris"),
                                                                   lat=possible_station['fields']['geo_point'][0],
                                                                   lng=possible_station['fields']['geo_point'][1])
                    stations_origin[-1]['nb_auto'] = available_car

        fastest_path_origin = Walking(origin, stations_origin[0]['station_address'], date=self.date)
        for station in stations_origin:
            walk = Walking(origin, station['station_address'], date=self.date)
            if walk.total_duration < fastest_path_origin.total_duration:
                fastest_path_origin = walk


        # station autolib à l'arrivée
        stop = True
        search_size = 1
        while stop:
            parameters = Autolib.__PARAMETERS + "&geofilter.distance=" + "%2C".join(
                [str(destination.lat), str(destination.lng), str(search_size * 1000)])
            r = requests.get(Autolib.__URL_AUTOLIB, parameters)
            raw_data = r.json()
            search_size += 1
            stations_destination = []
            possible_stations = raw_data['records']
            for possible_station in possible_stations:
                empty_slots = possible_station['fields']['slots'] - possible_station['fields']['cars']
                if empty_slots == 0:
                    pass
                else:
                    stop = False
                    stations_destination.append({})
                    stations_destination[-1]['station_address'] = Place(address=(possible_station['fields']['address']
                                                                                 + " "
                                                                                 + possible_station['fields'][
                                                                                     'postal_code']
                                                                                 + " Paris"),
                                                                        lat=possible_station['fields']['geo_point'][0],
                                                                        lng=possible_station['fields']['geo_point'][1])
                    stations_destination[-1]['empty_slots'] = empty_slots

        fastest_path_destination = Walking(stations_destination[0]['station_address'], destination)
        for station in stations_destination:
            walk = Walking(station['station_address'], destination)
            if walk.total_duration < fastest_path_destination.total_duration:
                fastest_path_destination = walk


        # trajet en autolib
        start_date_autolib = self.date + timedelta(0, fastest_path_origin.total_duration + Autolib.__COMMUTING_DURATION)
        autolib = Driving(fastest_path_destination.origin, destination, date=start_date_autolib)

        # Prise en compte du temps pour la dernière étape (station d'arrivée Autolib à destination)
        start_date_last_leg = start_date_autolib + timedelta(0, autolib.total_duration + Autolib.__COMMUTING_DURATION)
        if isinstance(fastest_path_destination, Walking):
            fastest_path_destination = Walking(origin, fastest_path_origin.destination, date=start_date_last_leg)
        else:
            fastest_path_destination = Transit(fastest_path_destination.origin, destination, date=start_date_last_leg)

        # Itineraire total = fastest_path_origin + autolib + fastest_path_destination
        self.total_duration = fastest_path_origin.total_duration \
                              + autolib.total_duration \
                              + fastest_path_destination.total_duration
        self.walking_duration = fastest_path_origin.walking_duration \
                                + autolib.walking_duration \
                                + fastest_path_destination.walking_duration
        self.walking_distance = fastest_path_origin.walking_distance \
                                + autolib.walking_distance \
                                + fastest_path_destination.walking_distance
        self.transit_duration = fastest_path_origin.transit_duration \
                                + autolib.transit_duration \
                                + fastest_path_destination.transit_duration
        self.driving_duration = autolib.driving_duration
        self.driving_distance = autolib.driving_distance
        self.total_polyline = fastest_path_origin.total_polyline \
                              + "\\" + autolib.total_polyline \
                              + "\\" + fastest_path_destination.total_polyline
        self.information_legs = fastest_path_origin.information_legs \
                                + autolib.information_legs \
                                + fastest_path_destination.information_legs


if __name__ == "__main__":
    # Test des différentes portions d'une voyage en Autolib
    org = Place(address="10 rue oswaldo cruz paris 75016")
    des = Place(address="Favella Chic Paris")
    AtoB = Autolib(org, des)
    print(repr(AtoB))

    org = Place(address="Montmartre, Paris")
    des = Place(address="Cité Universitaire, Paris")
    CtoD = Autolib(org, des)
    print(repr(CtoD))
