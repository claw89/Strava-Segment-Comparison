# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 12:32:11 2019

@author: Chris

Displays elevation comparison chart for routes specified by strava segment ids
and individual contour maps
Requires SRTM tiles for the region to be downloaded and extracted to the folder:
\\tiles\\
"""

import numpy as np
import matplotlib.pyplot as plt
import math
import requests
import strava_comp, strava_map
from gmalthgtparser import HgtParser
import polyline
import gpxpy
import os

def get_elevation(lat, long):
    """
    Returns the elevation for a specified location 
    (latitude, longitude) 
    (SRTM dataset)
    """
    N, E = int(lat), int(long)
    tile = f'N{N}E{E}.hgt'
    with HgtParser(os.getcwd() + '\\tiles\\' + tile) as parser:
        alt = parser.get_elevation((lat, long))
    return alt[2]

def get_response(segment_id, access_token):
    """
    Requests segment data from the strava api
    """
    url = 'https://www.strava.com/api/v3/segments/' + segment_id + '?access_token=' + access_token
    return requests.get(url)

def main():
    route_info = input("Please enter the segment IDs e.g. 638886, 7506566, 1982925 or GPX files: ")
    routes = {}
    route_identifiers = route_info.split(", ")
    access_token = False
    for route_identifier in route_identifiers:
        print(route_identifier)
        if route_identifier.split(".")[-1] == "gpx":
            gpx = True
        else:
            gpx = False
        
        if gpx:
            with open(route_identifier, 'r') as file:
                gpx_file = gpxpy.parse(file)
            points = []
            for point in gpx_file.tracks[0].segments[0].points:
                points.append((point.latitude, point.longitude))
            route_name = os.path.split(route_identifier)[1]
            routes[route_name] = points
        else:
            if not access_token:
                access_token = input("Please enter access token: ")
            response = get_response(route_identifier, access_token)
            print("Status code", response.status_code)
            if response.status_code == 200:
                points = polyline.decode(response.json()["map"]["polyline"])
                route_name = response.json()["name"]
                routes[route_name] = points
    #Set the number of subplots
    num_plots = len(routes.keys()) + 1
    v_plots = math.ceil(num_plots / math.ceil(math.sqrt(num_plots)))
    h_plots = math.ceil(math.sqrt(num_plots))
    fig, ax = plt.subplots(v_plots, h_plots)
    
    #Determine clearest viewing order
    av_alt = []
    route_names = routes.keys()
    for route_name in route_names:
        av_alt.append(np.mean([get_elevation(lat, long) for (lat, long) in routes[route_name]]))
    route_names = [x for _,x in sorted(zip(av_alt,route_names))]
    
    #Arange segment IDs to fit subplots
    grid = np.array(["comp"] + route_names)
    if len(grid) != v_plots * h_plots:
        grid = np.concatenate((grid, np.array([None] * ((v_plots * h_plots) - len(grid)))))
    grid = grid.reshape(v_plots, h_plots)
    
    #Add charts for each required subplot
    for i,row in enumerate(grid):
        for j, route_name in enumerate(row):
            if route_name:
                if route_name == "comp":
                    color_dict = strava_comp.get_comp(ax[0,0], [(route_name, routes[route_name]) for route_name in route_names])
                else:
                    strava_map.get_map(ax[i,j], routes[route_name], route_name, route_color=color_dict[route_name])
            else:
                ax[i,j].axis("off")
    plt.show()
    
if  __name__ =='__main__':
    main()
