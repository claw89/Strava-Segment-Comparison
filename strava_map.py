# -*- coding: utf-8 -*-
"""
Created on Mon Jun 10 21:04:54 2019

@author: Chris

Displays contour map with route for the specified strava segment id
Requires SRTM tiles for the region to be downloaded and extracted to the folder:
C:\\Users\\Chris\\AnacondaProjects\\strava_seg_comp\\tiles\\
"""

from gmalthgtparser import HgtParser
import numpy as np
import requests
import polyline
import matplotlib.pyplot as plt
from scipy.ndimage import zoom
from matplotlib.font_manager import FontProperties
import gpxpy
import os
import matplotlib.colors as colors
import math

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

def find_nearest(lat, lon):
    for i in range(12):
        if get_elevation(lat, math.floor(lon * (10**(i))) / (10**(i))):
            down_lon = math.floor(lon * (10**(i))) / (10**(i))
        if get_elevation(lat, math.ceil(lon * (10**(i))) / (10**(i))):
            up_lon = math.ceil(lon * (10**(i))) / (10**(i))
        if get_elevation(math.floor(lat * (10**(i))) / (10**(i)), lon):
            down_lat = math.floor(lat * (10**(i))) / (10**(i))
        if get_elevation(math.ceil(lat * (10**(i))) / (10**(i)), lon):
            up_lat = math.ceil(lat * (10**(i))) / (10**(i))
    lat_grad = (get_elevation(up_lat, lon) - get_elevation(down_lat, lon)) / (up_lat - down_lat)
    lat_est = (lat_grad * lat) + get_elevation(down_lat, lon) - (lat_grad * down_lat)
    lon_grad = (get_elevation(lat, up_lon) - get_elevation(lat, down_lon)) / (up_lon - down_lon)
    lon_est = (lon_grad * lon) + get_elevation(lat, down_lon) - (lon_grad * down_lon)
        
    return (down_lat, up_lat, down_lon, up_lon, lat_est, lon_est)

        

def get_elevations(X, Y):
    """
    Returns an elevation grid for the specified meshgrid (X, Y)
    """
    elevations = np.zeros(X.shape)
    for i in range(X.shape[0]):
        for j in range(X.shape[1]):
            E, N = int(X[i][j]), int(Y[i][j])
            tile = f'N{N}E{E}.hgt'
            with HgtParser(os.getcwd() + '\\tiles\\' + tile) as parser:
                alt = parser.get_elevation((Y[i][j], X[i][j]))
            elevations[i][j] = alt[2]
    return elevations

def get_response(segment_id, access_token):
    """
    Requests segment data from the strava api
    """
    url = 'https://www.strava.com/api/v3/segments/' + segment_id + '?access_token=' + access_token
    return requests.get(url)



def gradients(x, y, Z):
    Gx = np.zeros((Z.shape[0], Z.shape[1]))
    Gy = np.zeros((Z.shape[0], Z.shape[1]))
    for i in range(1, Z.shape[0] - 1):
        for j in range(1, Z.shape[1] - 1):
            Gx[i][j] = (Z[i][j+1] - Z[i][j-1]) / (x[j+1] - x[j-1])
            Gy[i][j] =  (Z[i+1][j] - Z[i-1][j]) / (y[i+1] - y[i-1])
    sign = np.add(Gx, Gy) *-1
    return (Gx, Gy, sign)

def truncate_colormap(cmap, minval=0.0, maxval=1.0, n=100):
    """
    https://stackoverflow.com/questions/18926031/how-to-extract-a-subset-of-a-colormap-as-a-new-colormap-in-matplotlib
    """
    new_cmap = colors.LinearSegmentedColormap.from_list(
        'trunc({n},{a:.2f},{b:.2f})'.format(n=cmap.name, a=minval, b=maxval),
        cmap(np.linspace(minval, maxval, n)))
    return new_cmap

def get_map(ax, points, route_name, route_color='red'):
    """
    Renders the contour map on the provided axis (ax)
    Contour map covers the square around the route specified by the strava 
    segment id
    """
    fontP = FontProperties(fname='C:\\Windows\\Fonts\\msjh.ttc')
    
    #Set data limits
    x_max = max([long for (lat, long) in points])
    x_min = min([long for (lat, long) in points])
    y_max = max([lat for (lat, long) in points])
    y_min = min([lat for (lat, long) in points])
    x_border = max([int((x_max-x_min) * 50) / 1000, 0.001])
    y_border = max([int((y_max-y_min) * 50) / 1000, 0.001])
    x_max = x_max + x_border
    x_min = x_min - x_border
    y_max = y_max + y_border
    y_min = y_min - y_border
    
   
    x = np.linspace(x_min, x_max, int(x_max*1000) - int(x_min*1000))
    y = np.linspace(y_min, y_max, int(y_max*1000) - int(y_min*1000))
    X, Y = np.meshgrid(x, y)
    Z = get_elevations(X, Y)
    
    #Interpolate contour data
    Xi, Yi, Zi = zoom(X, 6), zoom(Y, 6), zoom(Z, 6)
    
    #Calculate gradients
    G = gradients(x, y, Z)
    
    #Define contour levels
    major_contour_levels = np.arange(Zi.min() - (Zi.min() % 50), Zi.max() - (Zi.max() % 50) + 50, 50)
    minor_contour_levels = np.arange(Zi.min() - (Zi.min() % 10), Zi.max() - (Zi.max() % 10) + 10, 10)
    color_levels = np.linspace(Z.min(), Z.max(), Z.max()-Z.min() + 1)
    
    cmap = plt.get_cmap("gist_earth")
    new_cmap = truncate_colormap(cmap, 0.4, 0.9)
    
    #Plot contour map and route
    #ax.contourf(X, Y, Z, color_levels, cmap='pink')
    ax.contourf(X, Y, Z, color_levels, cmap=new_cmap)
    ax.contourf(X, Y, G[2], cmap='Greys_r', levels=np.linspace(G[2].min(), G[2].max(), 50), alpha=0.4)
    major_contours = ax.contour(Xi, Yi, Zi, major_contour_levels, colors='black', alpha=0.7)
    ax.clabel(major_contours, major_contour_levels, fmt='%d')
    ax.contour(Xi, Yi, Zi, minor_contour_levels, colors='black', alpha=0.5, linewidths=0.5)
    ax.plot([y for (x, y) in points], [x for (x, y) in points], color=route_color)
    ax.xaxis.set_major_locator(plt.NullLocator())
    ax.yaxis.set_major_locator(plt.NullLocator())
    ax.set_title(route_name, fontproperties=fontP, fontsize=16)
    ax.axis('scaled')

def main():
    fig, ax = plt.subplots()
    route_info = input("Please enter the segment ID or GPX file: ")
    if route_info.split(".")[-1] == "gpx":
        gpx = True
    else:
        gpx = False
    if gpx:
        with open(route_info, 'r') as file:
            gpx_file = gpxpy.parse(file)
        points = []
        for point in gpx_file.tracks[0].segments[0].points:
            points.append((point.latitude, point.longitude))
        route_name = os.path.split(route_info)[1]
    else:
        access_token = input("Please enter access token: ")
        response = get_response(route_info, access_token)
        if response.status_code == 200:
            points = polyline.decode(response.json()["map"]["polyline"])
            route_name = response.json()["name"]
    get_map(ax, points, route_name)
    plt.show()

if  __name__ =='__main__':
    main()
