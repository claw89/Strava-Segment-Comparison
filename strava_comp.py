# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 14:35:26 2019

@author: Chris

Displays elevation comparison chart for routes specified by strava segment ids
Requires SRTM tiles for the region to be downloaded and extracted to the folder:
\\tiles\\
"""

import numpy as np
import requests
import polyline
import math
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import scipy.interpolate
import gpxpy
import os
from gmalthgtparser import HgtParser

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
 
def smooth_n(li, n):
    """
    4 point moving average of list to reduce noise in elevation data
    """
    def smooth(li):
        """
        4 point moving average of list to reduce noise in elevation data
        """
        average = [np.mean(li[i:i+5]) for i in range(len(li) - 4)]
        average = np.concatenate((average[:2], average, average[-2:]))
        return average
    for i in range(n):
        li = smooth(li)
    return li

def distance(origin, destination):
    """
    Calculate the distance between two points (latitude, longitude) in meters
    From: 
    """
    lat1, lon1 = origin
    lat2, lon2 = destination
    radius = 6371 # km

    dlat = math.radians(lat2-lat1)
    dlon = math.radians(lon2-lon1)
    a = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dlon/2) * math.sin(dlon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = radius * c

    return d

def get_response(segment_id, access_token):
    """
    Requests segment data from the strava api
    """
    url = 'https://www.strava.com/api/v3/segments/' + segment_id + '?access_token=' + access_token
    return requests.get(url)

def gradients(x, y):
     grad = []
     for i in range(len(x)-1):
         grad.append((y[i+1] - y[i])/(x[i+1] - x[i]))
     return grad


def plot_gradients(ax, x, y, sect_len=100, lines=[]):
    def c_lookup(n):
        if n < 0:
            color="green"
        elif n < 0.1:
            color="orange"
        elif n < 0.2:
            color="red"
        else:
            color="black"
        return color
    f = scipy.interpolate.interp1d(x, y)
    xi = np.arange(min(x), max(x), sect_len)
    yi = f(xi)
    grad = gradients(xi, yi)
    chart_line = ax.plot(xi,yi)
    for i in range(len(xi) - 1):
        if len(lines) > 0:
            maximums = []
            for line in lines:
                if len(line)-1 > i:
                    maximums.append(line[i:i+2].max())
                else:
                    maximums.append(0)
            max_line_index = np.argmax(maximums)
            #max_line_index = np.argmax(np.array([line[i:i+2].max() for line in lines]))
            if max(maximums) > 0:
                l_bound = lines[max_line_index][i:i+2] + 2
            else:
                l_bound = y.min()
        else:
            l_bound = y.min()
        if yi[i:i+2].min() > l_bound.max():
            ax.fill_between(xi[i:i+2], yi[i:i+2], l_bound, color=c_lookup(grad[i]), alpha=0.5, linewidth=0.0)
            #ax.text(xi[i], yi[i]+10, str(int(grad[i]*100))+"%", rotation=90)
    lines.append(yi)
    return (ax, chart_line[0].get_color(), lines)


def get_comp(ax, routes):
    """
    Renders elevation comparison chart for the list of segment ids
    """
    fontP = FontProperties(fname='C:\\Windows\\Fonts\\msjh.ttc')
    colors = []
    lines = []
    for route in routes:
        points = route[1]
        altitudes = [get_elevation(lat, long) for (lat, long) in points]
        positions = [0]
        for i in range(len(points) - 1):
            positions.append(positions[-1] + distance(points[i], points[i+1]))
        smoothed = smooth_n(altitudes, 5)
        
        positions_m = [1000 * p for p in positions]
        ax, color, lines = plot_gradients(ax, positions_m, smoothed, sect_len=100, lines=lines)
        
        #line = ax.plot(positions, smoothed, label=response.json()["name"])
        ax.annotate(route[0], xy=(positions_m[-1], smoothed[-1]), xycoords='data', color=color, fontproperties=fontP, fontsize=14)
        colors.append(color)
        
        #Add contour under line to show gradient
        #grad = np.gradient(altitudes)
        #X, Y = np.meshgrid(np.linspace(min(positions), max(positions), len(positions)),
        #                   np.linspace(min(altitudes), max(altitudes), 100))
        #Z = np.array([grad.tolist()] * 100)
        #color_levels = np.linspace(Z.min(), Z.max(), 100)
        #plt.contourf(X, Y, Z, cmap="Reds", levels=color_levels)
        #plt.fill_between(positions, smoothed, max(altitudes), color="white")
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    route_names = [name for (name, points) in routes]
    return dict(zip(route_names, colors))

def main():
    fig, ax = plt.subplots()
    route_info = input("Please enter the segment IDs e.g. 638886, 7506566, 1982925 or GPX files: ")
    routes = []
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
            routes.append((route_name, points))
        else:
            if not access_token:
                access_token = input("Please enter access token: ")
            response = get_response(route_identifier, access_token)
            if response.status_code == 200:
                points = polyline.decode(response.json()["map"]["polyline"])
                route_name = response.json()["name"]
                routes.append((route_name, points))
    get_comp(ax, routes)
    plt.show()

if  __name__ =='__main__':
    main()
