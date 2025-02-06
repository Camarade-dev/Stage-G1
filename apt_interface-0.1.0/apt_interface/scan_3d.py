import time
from apt_interface.scan import Scan

# Initialisation du scan
s = Scan((None, None), config_file="conf/scan.yaml")

# Limite de temps en secondes
time_limit = 10
start_time = time.time()

# Exécuter le scan
while time.time() - start_time < time_limit:
    s.visualize()

print("Scan terminé.")
