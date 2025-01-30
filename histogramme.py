import pyvisa
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
import pyqtgraph as pg
from collections import Counter
import threading
import time
import random
n_moy = 50

class FrequencyHistogram(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Histogramme des Fréquences")
        self.setGeometry(100, 100, 800, 600)
        
        # Configuration de la fenêtre
        self.main_widget = QWidget()
        self.layout = QVBoxLayout(self.main_widget)
        self.setCentralWidget(self.main_widget)
        
        # Histogramme
        self.histogram_plot = pg.PlotWidget()
        self.layout.addWidget(self.histogram_plot)
        self.histogram_plot.setLabel('left', 'Proportion (%)')
        self.histogram_plot.setLabel('bottom', 'Fréquence (Hz)')
        self.bar_graph = None
        
        # Désactiver le zoom sur l'axe horizontal
        self.histogram_plot.setMouseEnabled(x=False, y=True)
        self.histogram_plot.getViewBox().setLimits(xMin=-50, xMax=1050) #fenêtrage
        
        # init histogramme
        self.frequency_counts = Counter()
        self.frequency_bins = []
        self.frequency_values = []
        
        # Initialiser PyVISA 
        self.rm = pyvisa.ResourceManager()
        self.instr = self.rm.open_resource('USB0::0x1313::0x8091::M01103986::INSTR') #identifiant de l'instrument
        
        # Thread pour lire les données en temps réel
        self.running = True
        self.data_thread = threading.Thread(target=self.collect_data)
        self.data_thread.start()

    def get_frequency_bin(self, frequency, bin_size=10):
        """Regrouper une fréquence par tranches de `bin_size`"""
        return int(frequency // bin_size) * bin_size

    def collect_data(self):
        try:
            compteur = 0
            moyennes = 0
            while self.running:
                compteur+=1
                
                frequency = int(self.instr.query("MEAS:FREQ?"))#lit la frequence sur le spcnt
                
                binned_freq = self.get_frequency_bin(frequency, bin_size=10)  # Regrouper par paquets (bin_size)
                self.frequency_counts[binned_freq] += 1
                self.update_histogram()
                moyennes = moyennes + frequency
                if compteur == n_moy :
                    
                    print(moyennes / n_moy)
                    compteur=0
                    moyennes=0
                time.sleep(0.01)
                
        except Exception as e:
            print("An error occurred:", e)

    def update_histogram(self):
        # Normaliser les données
        total_count = sum(self.frequency_counts.values())
        if total_count > 0:
            normalized_values = [count / total_count * 100 for count in self.frequency_counts.values()]
        else:
            normalized_values = []

        # Trier les intervalles et leurs valeurs
        if self.frequency_counts:
            self.frequency_bins, self.frequency_values = zip(*sorted(zip(self.frequency_counts.keys(), normalized_values)))
        else:
            self.frequency_bins, self.frequency_values = [], []
        
        # Mettre à jour l'histogramme
        if self.bar_graph is None:
            self.bar_graph = pg.BarGraphItem(x=self.frequency_bins, height=self.frequency_values, width=8, brush='r')
            self.histogram_plot.addItem(self.bar_graph)
        else:
            self.bar_graph.setOpts(x=self.frequency_bins, height=self.frequency_values)

    def closeEvent(self, event):
        # Arrêter le thread proprement
        self.running = False
        self.data_thread.join()
        event.accept()

# Main
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FrequencyHistogram()
    window.show()
    sys.exit(app.exec_())
