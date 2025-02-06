# -*- coding: utf-8 -*-
"""
Exemple complet de scan 2D dans une fenêtre globale.
La fenêtre est divisée en deux parties :
  - À gauche : un panneau de paramètres permettant de saisir :
       LX, LY, DX, DY, SETTLE_TIME, GAIN, SLEEP, Tolérance (TOL en µm) et MAX_ITER.
  - À droite : le panneau de contrôle du scan (affichage de la carte 2D, 
       courbe de convergence, boutons Pause/Reprendre et Arrêt).

Le scan s'exécute dans un thread séparé afin de maintenir l'interface réactive.
Les mesures et déplacements sont ici simulés (remplacez-les par vos appels réels).
"""

import time
import csv
import random  # Pour simuler des mesures
import sys
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
from apt_interface.KSG101 import KSG101
from apt_interface.KPZ101 import KPZ101

# --- Paramètres "matériels" fixes ---
MAX_TRAVEL_UM = 20.0     # Plage ~20 µm du piézo
MAX_COUNTS = 32767       # Valeur max du KSG
# COUNTS_PER_UM reste constant (utilisé pour la conversion)
COUNTS_PER_UM = MAX_COUNTS / MAX_TRAVEL_UM  # ~1638

CSV_FILENAME = "scan2D_closed_loop.csv"


# --- Fonctions de conversion ---
def um_to_counts(um: float) -> float:
    return um * COUNTS_PER_UM

def counts_to_um(counts: float) -> float:
    return counts / COUNTS_PER_UM


# --- Fonction de déplacement avec boucle fermée ---
def move_axis_to_um_closed_loop(kpz: KPZ101, ksg: KSG101, target_um: float,
                                  gain: float, tol_um: float, sleep: float, max_iter: int,
                                  update_callback=None):
    """
    Déplace l'axe en boucle fermée jusqu'à atteindre target_um.
    
    - gain       : facteur de correction.
    - tol_um     : tolérance en µm.
    - sleep      : délai entre itérations (en secondes).
    - max_iter   : nombre maximum d'itérations.
    - update_callback : fonction (ou None) appelée à chaque itération avec (lecture, iteration)
    """
    target_counts = um_to_counts(target_um)
    current_voltage = 0.0
    kpz.set_output_voltage(current_voltage)
    iteration = 0
    tol_counts = tol_um * COUNTS_PER_UM
    while iteration < max_iter:
        reading = ksg.get_reading()
        if update_callback is not None:
            update_callback(reading, iteration)
        error = target_counts - reading
        if abs(error) < tol_counts:
            break
        correction = gain * error
        new_voltage = current_voltage + correction
        new_voltage = max(0, min(75, new_voltage))
        kpz.set_output_voltage(new_voltage)
        current_voltage = new_voltage
        time.sleep(sleep)
        iteration += 1
    if update_callback is not None:
        update_callback(ksg.get_reading(), iteration)
    return ksg.get_reading()


# --- Widget d'affichage de la carte 2D ---
class RealTimePlot:
    """
    Affiche la carte 2D du scan.
    Un clic sur l'image affiche en console (et dans le widget) les indices, la position (en µm)
    et la valeur mesurée.
    
    La vue est configurée avec une échelle identique en x et en y et affiche une grille orthogonale.
    """
    def __init__(self, config):
        self.config = config
        self.LX = config["LX"]
        self.LY = config["LY"]
        self.DX = config["DX"]
        self.DY = config["DY"]
        self.nx = int(self.LX / self.DX) + 1
        self.ny = int(self.LY / self.DY) + 1
        self.data = np.zeros((self.ny, self.nx))

        self.widget = pg.GraphicsLayoutWidget()
        self.plot = self.widget.addPlot()
        # Verrouillage de l'aspect pour obtenir la même échelle en x et en y
        self.plot.getViewBox().setAspectLocked(True)
        # Affichage d'une grille orthogonale
        self.plot.showGrid(x=True, y=True, alpha=0.3)

        self.img = pg.ImageItem()
        self.plot.addItem(self.img)
        self.plot.setLabel('left', 'Y (Index)')
        self.plot.setLabel('bottom', 'X (Index)')
        self.plot.setTitle("Carte des mesures en temps réel")
        self.img.setLookupTable(pg.colormap.get("viridis").getLookupTable())

        self.info_text = pg.TextItem("", color="w", anchor=(0, 1))
        self.info_text.setPos(0, self.ny)
        self.plot.addItem(self.info_text)
        self.img.mousePressEvent = self.mouse_clicked

    def update(self, i, j, value):
        self.data[j, i] = value
        self.img.setImage(self.data, autoLevels=True)
        QtWidgets.QApplication.processEvents()

    def mouse_clicked(self, event):
        pos = self.img.mapFromScene(event.scenePos())
        x = int(pos.x())
        y = int(pos.y())
        if 0 <= x < self.nx and 0 <= y < self.ny:
            value = self.data[y, x]
            posX_um = x * self.DX
            posY_um = y * self.DY
            msg = (f"Clic sur la cellule (X_index={x}, Y_index={y}) -> "
                   f"X= {posX_um:.2f} µm, Y= {posY_um:.2f} µm, Valeur= {value:.2f}")
            print(msg)
            self.info_text.setText(msg)
        else:
            print("Clic en dehors de la zone de l'image.")


# --- Worker du scan (exécuté dans un thread séparé) ---
class ScanWorker(QtCore.QObject):
    # Signaux pour mise à jour de l'affichage
    updatePlot = QtCore.pyqtSignal(int, int, float)
    convergenceUpdate = QtCore.pyqtSignal(float, int)
    finished = QtCore.pyqtSignal()
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.LX = config["LX"]
        self.LY = config["LY"]
        self.DX = config["DX"]
        self.DY = config["DY"]
        self.SETTLE_TIME = config["SETTLE_TIME"]
        self.nx = int(self.LX / self.DX) + 1
        self.ny = int(self.LY / self.DY) + 1
        self._isRunning = True
        self._paused = False

    def stop(self):
        self._isRunning = False
        print("Arrêt du scan demandé.")

    def toggle_pause(self):
        self._paused = not self._paused
        if self._paused:
            print("Scan pausé.")
        else:
            print("Scan repris.")

    @QtCore.pyqtSlot()
    def run(self):
        print(f"Début du scan 2D (nx={self.nx}, ny={self.ny})...")
        # Récupération des paramètres utilisateur pour le déplacement
        gain = self.config["GAIN"]
        tol_um = self.config["TOL_UM"]
        sleep_time = self.config["SLEEP"]
        max_iter = self.config["MAX_ITER"]

        with KSG101("conf/config_KSG_X.yaml") as ksgX, \
             KPZ101("conf/config_KPZ_X.yaml") as kpzX, \
             KSG101("conf/config_KSG_Y.yaml") as ksgY, \
             KPZ101("conf/config_KPZ_Y.yaml") as kpzY:

            kpzX.enable_output()
            kpzY.enable_output()
            ksgX.zeroing()
            ksgY.zeroing()

            with open(CSV_FILENAME, "w", newline="") as f:
                writer = csv.writer(f, delimiter=';')
                writer.writerow(["iX", "iY", "targetX_um", "targetY_um", "value"])

                for j in range(self.ny):
                    while self._paused and self._isRunning:
                        time.sleep(0.1)
                    if not self._isRunning:
                        break
                    setY_um = j * self.DY
                    move_axis_to_um_closed_loop(kpzY, ksgY, setY_um,
                                                 gain, tol_um, sleep_time, max_iter)
                    time.sleep(self.SETTLE_TIME)

                    for i in range(self.nx):
                        while self._paused and self._isRunning:
                            time.sleep(0.1)
                        if not self._isRunning:
                            break
                        setX_um = i * self.DX
                        # Callback pour la courbe de convergence
                        def update_cb(reading, iteration):
                            self.convergenceUpdate.emit(reading, iteration)
                        move_axis_to_um_closed_loop(kpzX, ksgX, setX_um,
                                                     gain, tol_um, sleep_time, max_iter,
                                                     update_callback=update_cb)
                        time.sleep(self.SETTLE_TIME)

                        # Mesure simulée (à remplacer par la mesure réelle)
                        value = random.uniform(0, 100)
                        self.updatePlot.emit(i, j, value)
                        writer.writerow([i, j, setX_um, j * self.DY, value])
                        print(f"[i={i}, j={j}] X=~{setX_um:.2f} µm / Y=~{j * self.DY:.2f} µm, Mesure=~{value:.2f}")
        print("Scan terminé.")
        self.finished.emit()


# --- Panneau de paramètres (à gauche) ---
class ParameterPanel(QtWidgets.QWidget):
    startScan = QtCore.pyqtSignal(dict)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Paramètres du scan")
        
        # Champs pour LX, LY, DX, DY, SETTLE_TIME
        self.lx_spin = QtWidgets.QDoubleSpinBox()
        self.lx_spin.setRange(0.1, 1000)
        self.lx_spin.setValue(10.0)
        self.ly_spin = QtWidgets.QDoubleSpinBox()
        self.ly_spin.setRange(0.1, 1000)
        self.ly_spin.setValue(5.0)
        self.dx_spin = QtWidgets.QDoubleSpinBox()
        self.dx_spin.setRange(0.01, 100)
        self.dx_spin.setDecimals(3)
        self.dx_spin.setValue(0.2)
        self.dy_spin = QtWidgets.QDoubleSpinBox()
        self.dy_spin.setRange(0.01, 100)
        self.dy_spin.setDecimals(3)
        self.dy_spin.setValue(0.1)
        self.settle_time_spin = QtWidgets.QDoubleSpinBox()
        self.settle_time_spin.setRange(0.0, 10)
        self.settle_time_spin.setDecimals(2)
        self.settle_time_spin.setValue(0.5)
        
        # Champs pour GAIN, SLEEP, Tolérance (TOL en µm) et MAX_ITER
        self.gain_spin = QtWidgets.QDoubleSpinBox()
        self.gain_spin.setRange(0.0001, 1.0)
        self.gain_spin.setDecimals(4)
        self.gain_spin.setValue(0.002)
        self.sleep_spin = QtWidgets.QDoubleSpinBox()
        self.sleep_spin.setRange(0.001, 10)
        self.sleep_spin.setDecimals(3)
        self.sleep_spin.setValue(0.01)
        self.tol_spin = QtWidgets.QDoubleSpinBox()
        self.tol_spin.setRange(0.1, 10)
        self.tol_spin.setDecimals(2)
        self.tol_spin.setValue(0.5)
        self.max_iter_spin = QtWidgets.QSpinBox()
        self.max_iter_spin.setRange(1, 1000)
        self.max_iter_spin.setValue(200)

        # Organisation dans un formulaire
        form_layout = QtWidgets.QFormLayout()
        form_layout.addRow("LX (µm):", self.lx_spin)
        form_layout.addRow("LY (µm):", self.ly_spin)
        form_layout.addRow("DX (µm):", self.dx_spin)
        form_layout.addRow("DY (µm):", self.dy_spin)
        form_layout.addRow("Settle Time (s):", self.settle_time_spin)
        form_layout.addRow("Gain:", self.gain_spin)
        form_layout.addRow("Sleep (s):", self.sleep_spin)
        form_layout.addRow("Tol (µm):", self.tol_spin)
        form_layout.addRow("Max Iterations:", self.max_iter_spin)

        self.start_button = QtWidgets.QPushButton("Début")
        self.start_button.clicked.connect(self.emit_start)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(form_layout)
        layout.addWidget(self.start_button)
        layout.addStretch()
        self.setLayout(layout)

    def emit_start(self):
        config = {
            "LX": self.lx_spin.value(),
            "LY": self.ly_spin.value(),
            "DX": self.dx_spin.value(),
            "DY": self.dy_spin.value(),
            "SETTLE_TIME": self.settle_time_spin.value(),
            "GAIN": self.gain_spin.value(),
            "SLEEP": self.sleep_spin.value(),
            "TOL_UM": self.tol_spin.value(),
            "MAX_ITER": self.max_iter_spin.value()
        }
        self.startScan.emit(config)
        # Désactivation du panneau pendant l'exécution du scan
        self.setEnabled(False)

    def reset(self):
        """Réactive le panneau et met à jour le texte du bouton en 'Recommencer'."""
        self.setEnabled(True)
        self.start_button.setText("Recommencer")


# --- Panneau de contrôle du scan (à droite) ---
class ScanPanel(QtWidgets.QWidget):
    def __init__(self, config, worker, parent=None):
        super().__init__(parent)
        self.config = config
        self.worker = worker
        self.nx = int(config["LX"] / config["DX"]) + 1
        self.ny = int(config["LY"] / config["DY"]) + 1
        self.setWindowTitle("Scan 2D - Contrôle")

        # Carte 2D
        self.plot = RealTimePlot(config)
        # Courbe de convergence
        self.convergencePlot = pg.PlotWidget(title="Convergence du déplacement (axe X)")
        self.convergencePlot.setLabel('left', "Lecture (counts)")
        self.convergencePlot.setLabel('bottom', "Itération")
        self.convergence_curve = self.convergencePlot.plot(pen='y')
        self.convergence_data = []

        # Boutons de contrôle
        self.pauseButton = QtWidgets.QPushButton("Pause")
        self.stopButton = QtWidgets.QPushButton("Arrêt")
        self.pauseButton.clicked.connect(self.toggle_pause)
        self.stopButton.clicked.connect(self.stop_scan)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.plot.widget)
        layout.addWidget(self.convergencePlot)
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.pauseButton)
        button_layout.addWidget(self.stopButton)
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def toggle_pause(self):
        self.worker.toggle_pause()
        if self.worker._paused:
            self.pauseButton.setText("Reprendre")
        else:
            self.pauseButton.setText("Pause")

    def stop_scan(self):
        self.worker.stop()
        self.pauseButton.setEnabled(False)
        self.stopButton.setEnabled(False)

    def update_convergence(self, reading, iteration):
        if iteration == 0:
            self.convergence_data = []
        self.convergence_data.append(reading)
        self.convergence_curve.setData(np.arange(len(self.convergence_data)), self.convergence_data)


# --- Fenêtre globale ---
class GlobalWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scan 2D - Application Globale")
        self.resize(1200, 800)
        self.worker = None
        self.thread = None
        self.scanPanel = None

        self.paramPanel = ParameterPanel()
        self.paramPanel.startScan.connect(self.start_scan)

        # Utilisation d'un QSplitter pour disposer le panneau de paramètres (gauche)
        # et le panneau de contrôle du scan (droite)
        self.splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        self.splitter.addWidget(self.paramPanel)
        self.scanContainer = QtWidgets.QWidget()
        self.scanLayout = QtWidgets.QVBoxLayout()
        self.scanContainer.setLayout(self.scanLayout)
        self.splitter.addWidget(self.scanContainer)
        self.splitter.setSizes([300, 900])

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.splitter)
        self.setLayout(layout)

    def start_scan(self, config):
        # Si un scan précédent existe, on le supprime pour repartir sur une page vierge.
        if self.scanPanel is not None:
            self.scanLayout.removeWidget(self.scanPanel)
            self.scanPanel.deleteLater()
            self.scanPanel = None

        # Création du worker et du thread pour le scan
        self.thread = QtCore.QThread()
        self.worker = ScanWorker(config)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.updatePlot.connect(self.handle_update_plot)
        self.worker.convergenceUpdate.connect(self.handle_convergence_update)
        # Lorsqu'un scan est terminé, on récupère le signal pour réactiver le panneau de paramètres.
        self.worker.finished.connect(self.scan_finished)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.start()

        # Création et ajout du panneau de contrôle du scan dans la partie droite
        self.scanPanel = ScanPanel(config, self.worker)
        self.scanLayout.addWidget(self.scanPanel)

    def handle_update_plot(self, i, j, value):
        if self.scanPanel:
            self.scanPanel.plot.update(i, j, value)

    def handle_convergence_update(self, reading, iteration):
        if self.scanPanel:
            self.scanPanel.update_convergence(reading, iteration)

    def scan_finished(self):
        """Méthode appelée lorsque le scan est terminé afin de réactiver le panneau de paramètres."""
        print("Scan terminé, vous pouvez recommencer l'expérience.")
        self.paramPanel.reset()


def main():
    app = QtWidgets.QApplication(sys.argv)
    globalWindow = GlobalWindow()
    globalWindow.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
