import os
import random
import time


def proxy_txt(site=None):
    file = 'proxy.txt' if site == None else 'proxy_Б_Аптека.txt'
    with open(file) as f:
        return [x.strip() for x in f.readlines()]


def select_proxies(site, db=None):
    count = 0
    if site != 'Б-Аптека':

        return proxy_txt()
    else:

        return proxy_txt('Б-Аптека')
