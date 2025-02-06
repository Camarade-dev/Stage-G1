import time
from apt_interface.KSG101 import KSG101
from apt_interface.KPZ101 import KPZ101

# Paramètres de la boucle
TARGET = 1000     # valeur désirée en counts KSG (ex. 1000)
TOL = 1          # tolérance : on estime être à la bonne position si |error| < 1
GAIN = 0.002     # gain proportionnel (ajustez selon votre montage)
SLEEP = 0.2      # pause entre itérations (secondes)
MAX_ITER = 100    # nombre max d'itérations pour éviter de boucler à l'infini

def main():
    # Ouvre la jauge KSG et le contrôleur KPZ en open_loop
    with KSG101("conf/config_KSG.yaml") as ksg, KPZ101("conf/config_KPZ.yaml") as kpz:
        
        # Active la sortie haute tension du KPZ (prudence !)
        kpz.enable_output()
        # Mets à zéro la jauge (tare)
        ksg.zeroing()
        
        print("=== Boucle fermée logicielle (Python) ===")
        print(f"Objectif KSG: {TARGET} counts, tolérance: ±{TOL}")
        
        # On initialise la tension à 0 V (donc 'pos' = 0 en échelle de l'appareil)
        current_voltage = 0.0
        kpz.set_output_voltage(current_voltage)
        
        for i in range(MAX_ITER):
            # Lire la valeur de la jauge KSG
            reading = ksg.get_reading()  # renvoie un int (counts)
            
            # Calculer l'erreur
            error = TARGET - reading
            
            if abs(error) <= TOL:
                print(f"[Iteration {i}] On est dans la tolérance ! reading={reading}")
                break
            
            # Correction proportionnelle
            correction = GAIN * error
            new_voltage = current_voltage + correction
            
            # Saturation entre 0 V et la limite (75 V par ex.)
            if new_voltage < 0:
                new_voltage = 0
            elif new_voltage > kpz.conf.voltage_limit:
                new_voltage = kpz.conf.voltage_limit
            
            # Appliquer la nouvelle tension
            kpz.set_output_voltage(new_voltage)
            current_voltage = new_voltage
            
            print(f"[Iteration {i}] reading={reading}, error={error}, new_voltage={current_voltage}")
            
            time.sleep(SLEEP)
        
        print("Boucle terminée.")
        
        # Optionnel : ramener la tension à 0 avant de quitter
        # kpz.set_output_voltage(0)
        # time.sleep(1.0)

if __name__ == "__main__":
    main()
