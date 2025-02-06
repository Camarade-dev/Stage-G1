# -*- coding: utf-8 -*-
"""
Created on Wed Feb  5 15:13:05 2025

@author: stris
"""

from apt_interface.KSG101 import KSG101, KSG101Config
from time import sleep
 
with KSG101(config_file="conf/config_KSG.yaml") as ksg:
    print(ksg.conf)
    print(ksg.get_max_travel())
 
    ksg.identify()
 
    while True:
        print(ksg.get_reading()) 
        sleep(1)