import sys
import os
import numpy as np
from numpy import hamming
from math import ceil

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
from pylab import convolve
import matplotlib.gridspec as gridspec

from .DataViewGUI import DataViewGUI
from .paramrw import usingEvokedInputs, usingOngoingInputs, usingPoissonInputs, get_output_dir
from .spikefn import ExtInputs
from .qt_lib import getmplDPI

from hnn_core import read_params, read_spikes

#plt.rcParams['lines.markersize'] = 15
plt.rcParams['lines.linewidth'] = 1
fontsize = plt.rcParams['font.size'] = 10
rastmarksz = 5 # raster dot size
binsz = 5.0
smoothsz = 0 # no smoothing

# colors for the different cell types
dclr = {'L2_pyramidal' : 'g',
        'L5_pyramidal' : 'r',
        'L2_basket' : 'w', 
        'L5_basket' : 'b'}

# box filter
def boxfilt (x, winsz):
  win = [1.0/winsz for i in range(int(winsz))]
  return convolve(x,win,'same')

# convolve with a hamming window
def hammfilt (x, winsz):
  win = hamming(winsz)
  win /= sum(win)
  return convolve(x,win,'same')


# adjust input gids for display purposes
def adjustinputgid (extinputs, gid):
  if gid == extinputs.gid_prox:
    return 0
  elif gid == extinputs.gid_dist:
    return 1
  elif extinputs.is_prox_gid(gid):
    return 2
  elif extinputs.is_dist_gid(gid):
    return 3
  return gid

def gid_to_type(extinputs, gid):
  for gidtype, gids in extinputs.gid_ranges.items():
      if gid in gids:
          return gidtype

def getdspk(spikes, extinputs, tstop):
  ddat = {}
  ddat['spk'] = np.r_[spikes.spike_times, spikes.spike_gids].T

  dspk = {'Cell':([],[],[]),'Input':([],[],[])}
  dhist = {}
  for ty in dclr.keys(): dhist[ty] = []
  haveinputs = False
  for (t,gid) in ddat['spk']:
    ty = gid_to_type(extinputs,gid)
    if ty in dclr:
      dspk['Cell'][0].append(t)
      dspk['Cell'][1].append(gid)
      dspk['Cell'][2].append(dclr[ty])
      dhist[ty].append(t)
    else:
      dspk['Input'][0].append(t)
      dspk['Input'][1].append(adjustinputgid(extinputs, gid))
      if extinputs.is_prox_gid(gid):
        dspk['Input'][2].append('r')
      elif extinputs.is_dist_gid(gid):
        dspk['Input'][2].append('g')
      else:
        dspk['Input'][2].append('orange')
      haveinputs = True
  for ty in dhist.keys():
    dhist[ty] = np.histogram(dhist[ty],range=(0,tstop),bins=int(tstop/binsz))
    if smoothsz > 0:
      #dhist[ty] = boxfilt(dhist[ty][0],smoothsz)
      dhist[ty] = hammfilt(dhist[ty][0],smoothsz)
    else:
      dhist[ty] = dhist[ty][0]
  return dspk,haveinputs,dhist

def drawhist(dhist, fig, G, ntrial, tstop):
  ax = fig.add_subplot(G[-4:-1,:])
  fctr = 1.0
  if ntrial > 0: fctr = 1.0 / ntrial
  for ty in dhist.keys():
    ax.plot(np.arange(binsz/2,tstop+binsz/2,binsz),dhist[ty]*fctr,dclr[ty],linestyle='--')
  ax.set_xlim((0,tstop))
  ax.set_ylabel('Cell Spikes')
  return ax


def drawrast(params, dspk, extinputs, haveinputs, fig, G, tstop, bDrawHist, sz=8):
  lax = []
  lk = ['Cell']
  row = 0

  if haveinputs:
    lk.append('Input')
    lk.reverse()

  dinput = extinputs.inputs

  for _, k in enumerate(lk):
    if k == 'Input': # input spiking

      bins = ceil(150. * tstop / 1000.) # bins needs to be an int

      EvokedInputs = usingEvokedInputs(params)
      OngoingInputs = usingOngoingInputs(params)
      PoissonInputs = usingPoissonInputs(params)
      haveEvokedDist = (EvokedInputs and len(dinput['evdist'])>0)
      haveOngoingDist = (OngoingInputs and len(dinput['dist'])>0)
      haveEvokedProx = (EvokedInputs and len(dinput['evprox'])>0)
      haveOngoingProx = (OngoingInputs and len(dinput['prox'])>0)

      if haveEvokedDist or haveOngoingDist:
        ax = fig.add_subplot(G[row:row+2,:]); row += 2
        lax.append(ax)
        if haveEvokedDist: extinputs.plot_hist(ax,'evdist',0,bins,(0,tstop),color='g',hty='step')
        if haveOngoingDist: extinputs.plot_hist(ax,'dist',0,bins,(0,tstop),color='g')
        ax.invert_yaxis()
        ax.set_ylabel('Distal Input')

      if haveEvokedProx or haveOngoingProx:
        ax2 = fig.add_subplot(G[row:row+2,:]); row += 2
        lax.append(ax2)
        if haveEvokedProx: extinputs.plot_hist(ax2,'evprox',0,bins,(0,tstop),color='r',hty='step')
        if haveOngoingProx: extinputs.plot_hist(ax2,'prox',0,bins,(0,tstop),color='r')
        ax2.set_ylabel('Proximal Input')

      if PoissonInputs and len(dinput['pois']):
        axp = fig.add_subplot(G[row:row+2,:]); row += 2
        lax.append(axp)
        extinputs.plot_hist(axp,'pois',0,bins,(0,tstop),color='orange')
        axp.set_ylabel('Poisson Input')

    else: # local circuit neuron spiking
      ncell = len(extinputs.gid_ranges['L2_pyramidal']) + \
              len(extinputs.gid_ranges['L2_basket']) + \
              len(extinputs.gid_ranges['L5_pyramidal']) + \
              len(extinputs.gid_ranges['L5_basket'])

      endrow = -1
      if bDrawHist: endrow = -4

      ax = fig.add_subplot(G[row:endrow,:])
      lax.append(ax)

      ax.scatter(dspk[k][0],dspk[k][1],c=dspk[k][2],s=sz**2) 
      ax.set_ylabel(k + ' ID')
      white_patch = mpatches.Patch(color='white', label='L2/3 Basket')
      green_patch = mpatches.Patch(color='green', label='L2/3 Pyr')
      red_patch = mpatches.Patch(color='red', label='L5 Pyr')
      blue_patch = mpatches.Patch(color='blue', label='L5 Basket')
      ax.legend(handles=[white_patch,green_patch,blue_patch,red_patch],loc='best')
      ax.set_ylim((-1,ncell+1))
      ax.invert_yaxis()

  return lax

class SpikeCanvas (FigureCanvas):
  def __init__ (self, params, sim_data, index, parent=None, width=12, height=10, dpi=120, title='Spike Viewer'):
    FigureCanvas.__init__(self, Figure(figsize=(width, height), dpi=dpi))
    self.title = title
    self.setParent(parent)
    self.index = index
    FigureCanvas.setSizePolicy(self,QSizePolicy.Expanding,QSizePolicy.Expanding)
    FigureCanvas.updateGeometry(self)
    self.params = params
    self.sim_data = sim_data
    self.alldat = {}

    self.invertedhistax = False
    self.bDrawHist = True  # whether to draw histograms (spike counts per time)
    self.G = gridspec.GridSpec(16,1)
    self.plot()

  def clearaxes(self):
      for ax in self.lax:
          ax.set_yticks([])
          ax.cla()

  def loadspk(self, idx):
    if idx in self.alldat:
      return
    self.alldat[idx] = {}

    trials = [trial_idx for trial_idx in range(self.params['N_trials'])]
    self.extinputs = ExtInputs(self.sim_data['spikes'],
                               self.sim_data['gid_ranges'],
                               trials, self.params)

    dspk,haveinputs,dhist = getdspk(self.sim_data['spikes'],
                                    self.extinputs, self.params['tstop'])
    self.alldat[idx]['dspk'] = dspk
    self.alldat[idx]['haveinputs'] = haveinputs
    self.alldat[idx]['dhist'] = dhist
    self.alldat[idx]['extinputs'] = self.extinputs


  def plot (self):
    self.loadspk(self.index)

    idx = self.index
    dspk = self.alldat[idx]['dspk']
    haveinputs = self.alldat[idx]['haveinputs']
    dhist = self.alldat[idx]['dhist']
    extinputs = self.alldat[idx]['extinputs']

    self.lax = drawrast(self.params, dspk, extinputs, haveinputs, self.figure, self.G, rastmarksz, self.params['tstop'], self.bDrawHist)
    if self.bDrawHist: self.lax.append(drawhist(dhist,self.figure,self.G,self.params['N_trials'],self.params['tstop']))

    for ax in self.lax: 
      ax.set_facecolor('k')
      ax.grid(True)
      if self.params['tstop'] != -1:
        ax.set_xlim((0, self.params['tstop']))

    if idx == 0:
      self.lax[0].set_title('All Trials')
    else:
      self.lax[0].set_title('Trial ' + str(self.index))

    self.lax[-1].set_xlabel('Time (ms)')

    self.figure.subplots_adjust(bottom=0.0, left=0.06, right=1.0,
                                top=0.97, wspace=0.1, hspace=0.09)

    self.draw()

class SpikeViewGUI(DataViewGUI):
  def __init__(self, CanvasType, params, sim_data, title):
    super(SpikeViewGUI, self).__init__(CanvasType, params, sim_data, title)
    self.addViewHistAction()

  def addViewHistAction(self):
    """Add 'Toggle Histograms' to view menu"""
    drawHistAction = QAction('Toggle Histograms',self)
    drawHistAction.setStatusTip('Toggle Histogram Drawing.')
    drawHistAction.triggered.connect(self.toggleHist)
    self.viewMenu.addAction(drawHistAction)

  def toggleHist (self):
    self.m.bDrawHist = not self.m.bDrawHist
    self.initCanvas()
    self.m.plot()
