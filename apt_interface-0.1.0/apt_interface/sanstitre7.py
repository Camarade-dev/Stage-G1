import sys
from apt_interface.KSG101 import KSG101
from apt_interface.KPZ101 import KPZ101
from time import sleep

def main():
    # Ouvre les deux instruments en même temps via un context manager
    with KSG101("conf/config_KSG.yaml") as ksg, KPZ101("conf/config_KPZ.yaml") as kpz:
        print("Configuration KSG101 :", ksg.conf)
        print("Configuration KPZ101 :", kpz.conf)
        
        # Exemple : récupérer l'identifiant ou la version firmware
        # (à adapter selon les méthodes disponibles dans votre wrapper)
        # print("KSG Info:", ksg.get_info())
        # print("KPZ Info:", kpz.get_info())
        
        # Récupération d'infos de base
        io_info = ksg.get_io()
        max_travel = ksg.get_max_travel()
        print("IO info:", io_info)
        print("Max travel:", max_travel)
        
        # Active la sortie du KPZ et fait le 'zéro' (tare) du KSG
        kpz.enable_output()
        print("Sortie KPZ activée.")
        
        ksg.zeroing()
        print("KSG mis à zéro (tare).")
        
        # Boucle de commande interactive
        try:
            while True:
                p = input("Entrez la position désirée (0..32767) ou 'q' pour quitter : ")
                if p.lower() == 'q':
                    print("Arrêt de la boucle.")
                    break
                
                try:
                    p_val = int(p)
                except ValueError:
                    print("Valeur invalide ! Veuillez entrer un entier.")
                    continue
                
                if not (0 <= p_val <= 32767):
                    print("Position hors limites ! Entrez une valeur entre 0 et 32767.")
                    continue
                
                # Envoi de la commande de position
                kpz.set_position(p_val)
                print(f"Position demandée : {p_val}")
                
                # Attente pour laisser le temps au contrôleur d’atteindre la consigne
                sleep(2)
                
                # Lecture du feedback via KSG
                reading = ksg.get_reading()
                print("Lecture KSG (−32768..32767) :", reading)
        
        except KeyboardInterrupt:
            print("\nInterruption clavier, on quitte proprement.")
    
    print("Fermeture des instruments terminée.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Erreur dans l'exécution :", e)
        sys.exit(1)
