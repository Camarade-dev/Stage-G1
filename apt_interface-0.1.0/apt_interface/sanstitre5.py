from apt_interface.KPZ101 import KPZ101
from apt_interface.scan import Scan
from time import sleep
 
def mesure(*args, **kwargs):
    # il faut laisser assez de délais pour que les mouvements ne soient pas trop brusques si le pas est grand
 
    sleep(.01)
    return 1
 
with KPZ101(config_file="conf/x.yaml") as x, KPZ101(config_file="conf/y.yaml") as y:
    # La boucle fermée n'est pas utiliser ici, il aurait fallu instancier des ksg
    # pour les configurer sinon
 
    print(x.conf)
    print(y.conf)
 
 
    x.enable_output()
    y.enable_output()
 
    s = Scan((x, y))
 
    # Launching scan on nanomax
    m = s.scan(mesure)
 
    # m contains the matrix of measurement
    print(m)
 
    while True:
        pass