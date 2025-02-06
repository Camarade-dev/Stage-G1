# -*- coding: utf-8 -*-
"""
Created on Thu Jan 30 17:30:45 2025

@author: stris
"""

from pyftdi.ftdi import Ftdi

print("Liste des appareils FTDI connectés :")
Ftdi.show_devices()
