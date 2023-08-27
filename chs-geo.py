import tbapy
import os
import googlemaps
from TbaConsts import EventType
import csv
from datetime import datetime
import math
import statistics

tba = tbapy.TBA(os.getenv("TBA_KEY"))
gmaps = googlemaps.Client(key=os.getenv("MAPS_KEY"))

years = [2016, 2017, 2018, 2019, 2020, 2022, 2023]


def saveListOfDict(filename, list):
    with open(filename, 'w', newline='') as out_file:
        dict_writer = csv.DictWriter(out_file, list[0].keys())
        dict_writer.writeheader()
        dict_writer.writerows(list)


def readListOfDict(filename):
    return list(csv.DictReader(open(filename, 'r')))


def getEventData():
    for year in years:
        event_data = []
        for event in tba.district_events(str(year) + "chs"):
            if event["event_type"] == EventType.DISTRICT:
                loc = gmaps.geocode(event["address"])[
                    0]['geometry']['location']
                event_data.append({
                    "code": event["key"],
                    "lat": loc["lat"],
                    "lng": loc["lng"],
                    "address": event["address"]
                })

        saveListOfDict('CHS_EVENTS_' + str(year) + '.csv', event_data)


def getTeamData():
    for year in years:
        team_data = []
        for team in tba.district_teams(str(year) + "chs"):
            team_postal = team['postal_code'] if team['postal_code'] is not None else ""
            addr = team['city'] + ", " + team['state_prov'] + " " + team_postal

            loc = gmaps.geocode(addr)[0]['geometry']['location']

            team_data.append({
                'team': team['team_number'],
                "lat": loc["lat"],
                "lng": loc["lng"],
                'addr': addr
            })

        saveListOfDict('CHS_TEAMS_' + str(year) + '.csv', team_data)


def getYearDurations(year):
    origins = []
    destinations = []

    teamData = readListOfDict('CHS_TEAMS_' + str(year) + '.csv')
    teams = [team['team'] for team in teamData]
    origins = [(team['lat'], team['lng']) for team in teamData]

    eventData = readListOfDict('CHS_EVENTS_' + str(year) + '.csv')
    events = [event['code'] for event in eventData]
    destinations = [(event['lat'], event['lng']) for event in eventData]

    MAX_ELEMENTS = 100
    rowsPerChunk = math.floor(MAX_ELEMENTS / len(events))
    numChunks = math.ceil(len(teams) / rowsPerChunk)

    dur_data = []

    for chunk in range(0, numChunks):
        startIdx = chunk * rowsPerChunk
        stopIdx = (chunk + 1) * rowsPerChunk
        stopIdx = len(teams) if stopIdx > len(teams) else stopIdx
        print(startIdx, stopIdx)

        matrix = gmaps.distance_matrix(
            origins[startIdx:stopIdx],
            destinations,
            mode="driving",
            language="en-US",
            units="imperial",
            departure_time=datetime.now(),
            traffic_model="optimistic",
        )

        for team_idx, row in enumerate(matrix['rows']):
            team_dists = {'team': teams[startIdx + team_idx]}
            for evt_idx, elem in enumerate(row['elements']):
                team_dists[events[evt_idx]] = elem['duration']['value']

            dur_data.append(team_dists)

    saveListOfDict('CHS_DURATIONS_' + str(year) + '.csv', dur_data)


for year in years:
    durations = readListOfDict('CHS_DURATIONS_' + str(year) + '.csv')
    events = [event['code']
              for event in readListOfDict('CHS_EVENTS_' + str(year) + '.csv')]

    print(str(year), "Travel Times (minutes)")
    print("EVENT \t MEAN \t MEDIAN")
    for event in events:
        time_list = []
        for team in tba.event_teams(event):
            for entry in durations:
                if int(entry['team']) == team['team_number']:
                    time_list.append(int(entry[event]))
        print(event.upper()[4:], "\t", round(statistics.mean(time_list) / 60, 1),
              "\t", round(statistics.median(time_list) / 60, 1))
    print("\n")
