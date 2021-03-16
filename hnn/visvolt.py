import sys, os
import numpy as np
import pickle

from PyQt5.QtWidgets import QMainWindow, QAction, qApp, QApplication, QToolTip, QPushButton, QFormLayout
from PyQt5.QtWidgets import QMenu, QSizePolicy, QMessageBox, QWidget, QFileDialog, QComboBox, QTabWidget
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QGroupBox, QDialog, QGridLayout, QLineEdit, QLabel
from PyQt5.QtWidgets import QCheckBox, QInputDialog
from PyQt5.QtGui import QIcon, QFont, QPixmap
from PyQt5.QtCore import QCoreApplication, QThread, pyqtSignal, QObject, pyqtSlot
from PyQt5 import QtCore
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
from hnn_core import read_params

from .qt_lib import getmplDPI
from .paramrw import get_output_dir
from .DataViewGUI import DataViewGUI

fontsize = plt.rcParams['font.size'] = 10

# colors for the different cell types
dclr = {'L2_pyramidal' : 'g',
        'L5_pyramidal' : 'r',
        'L2_basket' : 'w', 
        'L5_basket' : 'b'}

maxperty = 10 # how many cells of a type to draw

if ntrial <= 1:
  voltpath = os.path.join(get_output_dir(), 'data', params['sim_prefix'], 'vsoma.pkl')
else:
  voltpath = os.path.join(get_output_dir(), 'data', params['sim_prefix'], 'vsoma_1.pkl')

class VoltCanvas (FigureCanvas):
  def __init__ (self, paramf, index, parent=None, width=12, height=10, dpi=120, title='Voltage Viewer'):
    FigureCanvas.__init__(self, Figure(figsize=(width, height), dpi=dpi))
    self.title = title
    self.setParent(parent)
    self.gui = parent
    self.index = index
    self.invertedax = False
    FigureCanvas.setSizePolicy(self,QSizePolicy.Expanding,QSizePolicy.Expanding)
    FigureCanvas.updateGeometry(self)
    self.paramf = paramf
    self.G = gridspec.GridSpec(10,1)
    self.plot()

  def drawvolt (self, dvolt, fig, G, sz=8, ltextra=''):
    row = 0
    ax = fig.add_subplot(G[row:-1,:])
    lax = [ax]
    dcnt = {} # counts number of times cell of a type drawn  
    vtime = dvolt['vtime']
    yoff = 0
    # print(dvolt.keys())
    for gid,it in dvolt.items():
      ty,vsoma = it[0],it[1]
      # print('ty:',ty,'gid:',gid)
      if type(gid) != int: continue
      if ty not in dcnt: dcnt[ty] = 1
      if dcnt[ty] > maxperty: continue
      #ax.plot(vtime, -vsoma + yoff, dclr[ty], linewidth = self.gui.linewidth)
      ax.plot(vtime, -vsoma + yoff, dclr[ty], linewidth = self.gui.linewidth)
      yoff += max(vsoma) - min(vsoma)
      dcnt[ty] += 1

    white_patch = mpatches.Patch(color='white', label='L2/3 Basket')
    green_patch = mpatches.Patch(color='green', label='L2/3 Pyr')
    red_patch = mpatches.Patch(color='red', label='L5 Pyr')
    blue_patch = mpatches.Patch(color='blue', label='L5 Basket')
    ax.legend(handles=[white_patch,green_patch,blue_patch,red_patch])

    if not self.invertedax: 
      ax.set_ylim(ax.get_ylim()[::-1])
      self.invertedax = True
    #if not self.invertedax: 
    #  ax.invert_yaxis()
    #  self.invertedax = True

    ax.set_yticks([])

    ax.set_facecolor('k')
    ax.grid(True)
    if tstop != -1: ax.set_xlim((0,tstop))
    if i ==0: ax.set_title(ltextra)
    ax.set_xlabel('Time (ms)')

    self.figure.subplots_adjust(bottom=0.01, left=0.01, right=0.99, top=0.99, wspace=0.1, hspace=0.09)

    return lax

  def plot (self):
    if self.index == 0:
      if ntrial == 1:
        dvolt = pickle.load(open(voltpath,'rb'))
      else:
        dvolt = pickle.load(open(voltpath,'rb'))
      self.lax = self.drawvolt(dvolt,self.figure, self.G, 5, ltextra='All Trials')
    else:
      voltpathtrial = os.path.join(get_output_dir(), 'data', params['sim_prefix'], 'vsoma_'+str(self.index)+'.pkl')
      dvolttrial = pickle.load(open(voltpathtrial,'rb'))
      self.lax=self.drawvolt(dvolttrial,self.figure, self.G, 5, ltextra='Trial '+str(self.index))
    self.draw()

class VoltGUI(DataViewGUI):
  def __init__(self, CanvasType, params, title):
      self.params = params
      super(VoltGUI, self).__init__(CanvasType, self.params, title)
      self.addLoadDataActions()
      self.loadDisplayData()

  def initCanvas (self):
    self.invertedax = False
    # to avoid memory leaks remove any pre-existing widgets before adding new ones
    self.grid.removeWidget(self.m)
    self.grid.removeWidget(self.toolbar)
    self.m.setParent(None)
    self.toolbar.setParent(None)
    self.m = self.toolbar = None

    self.m = VoltCanvas(paramf, self.index, parent = self, width=12, height=10, dpi=getmplDPI())
    # this is the Navigation widget
    # it takes the Canvas widget and a parent
    self.toolbar = NavigationToolbar(self.m, self)
    self.grid.addWidget(self.toolbar, 0, 0, 1, 4)
    self.grid.addWidget(self.m, 1, 0, 1, 4)

  def initUI (self):
    self.initMenu()
    self.statusBar()
    self.setGeometry(300, 300, 1300, 1100)
    self.setWindowTitle('Volt Viewer - ' + paramf)
    self.grid = grid = QGridLayout()
    self.index = 0
    self.initCanvas()
    self.cb = QComboBox(self)
    self.grid.addWidget(self.cb,2,0,1,4)

    for i in range(ntrial): self.cb.addItem('Trial ' + str(i+1))
    self.cb.activated[int].connect(self.onActivated) 

    # need a separate widget to put grid on
    widget = QWidget(self)
    widget.setLayout(grid)
    self.setCentralWidget(widget)

    self.setWindowIcon(QIcon(os.path.join('res','icon.png')))

    self.show()

  def onActivated(self, idx):
    if idx != self.index:
      self.index = idx
      self.statusBar().showMessage('Loading data from trial ' + str(self.index+1) + '.')
      self.m.index = self.index
      self.initCanvas()
      self.m.plot()
      self.statusBar().showMessage('')
