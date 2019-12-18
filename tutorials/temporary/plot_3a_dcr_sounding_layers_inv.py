# -*- coding: utf-8 -*-
"""
DC Resistivity Sounding
=======================

Here we use the module *SimPEG.electromangetics.static.resistivity* to predict
DC resistivity data. In this tutorial, we focus on the following:

    - How to define sources and receivers
    - How to define the survey
    - How to predict voltage or apparent resistivity data
    - The units of the model and resulting data

For this tutorial, we will simulation sounding data over a layered Earth using
a Wenner array. The end product is a sounding curve which tells us how the
electrical resistivity changes with depth.
    

"""

#########################################################################
# Import modules
# --------------
#

import os
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

from discretize import TensorMesh

from SimPEG import (maps, data, data_misfit, regularization,
    optimization, inverse_problem, inversion, directives
    )
from SimPEG.electromagnetics.static import resistivity as dc
from SimPEG.electromagnetics.static.utils.StaticUtils import plot_layer

# sphinx_gallery_thumbnail_number = 2


#############################################
# Load Data, Define Survey and Plot
# ---------------------------------
#
# Here we load and plot synthetic DCIP data. We a
#

# File names
data_filename = os.path.dirname(dc.__file__) + '\\..\\..\\..\\..\\tutorials\\assets\\dcip1d\\app_res_1d_data.dobs'
model_filename = os.path.dirname(dc.__file__) + '\\..\\..\\..\\..\\tutorials\\assets\\dcip1d\\true_model.txt'
mesh_filename = os.path.dirname(dc.__file__) + '\\..\\..\\..\\..\\tutorials\\assets\\dcip1d\\layers.txt'


# Load data
dobs = np.loadtxt(str(data_filename))

a_electrodes = dobs[:, 0:3]
b_electrodes = dobs[:, 3:6]
m_electrodes = dobs[:, 6:9]
n_electrodes = dobs[:, 9:12]
dobs = dobs[:, -1]

# Define survey
unique_tx, k = np.unique(np.c_[a_electrodes, b_electrodes], axis=0, return_index=True)
n_tx = len(k)
k = np.sort(k)
k = np.r_[k, len(k)+1]

source_list = []
for ii in range(0, n_tx):
    
    m_locations = m_electrodes[k[ii]:k[ii+1], :]
    n_locations = n_electrodes[k[ii]:k[ii+1], :]
    receiver_list = [dc.receivers.Dipole(m_locations, n_locations)]
    
    a_location = a_electrodes[k[ii], :]
    b_location = b_electrodes[k[ii], :]
    source_list.append(dc.sources.Dipole(receiver_list, a_location, b_location))

# Define survey
survey = dc.Survey(source_list)

# Plot the data
survey.getABMN_locations()
electrode_separations = np.sqrt(
        np.sum((survey.m_locations - survey.n_locations)**2, axis=1)
        )

# Plot apparent resistivities on sounding curve
fig = plt.figure(figsize=(11, 5))

ax1 = fig.add_axes([0.05, 0.05, 0.8, 0.9])
ax1.semilogy(electrode_separations, dobs)

plt.show()

###############################################
# Assign Uncertainties
# --------------------

uncertainties = 0.025*dobs


###############################################
# Define Data
# --------------------

data_object = data.Data(survey, dobs=dobs, noise_floor=uncertainties)


###############################################
# Create starting model
# ---------------------
#
# Here, we define the layer thicknesses for our 1D simulation. To do this, we use
# the TensorMesh class.


resistivities = np.r_[1e3, 1e3, 1e3]
layer_thicknesses = np.r_[50., 50., 50.]

mesh = TensorMesh([layer_thicknesses], '0')

print(mesh)

###############################################################
# Mapping
# -----------------------------------------------------
#
# Here we define the resistivity model that will be used to predict DC data.
# For each layer in our 1D Earth, we must provide a resistivity value. For a
# 1D simulation, we assume the bottom layer extends to infinity.
#

wire_map = maps.Wires(('rho', mesh.nC), ('t', mesh.nC-1))
resistivity_map = maps.ExpMap(nP=mesh.nC) * wire_map.rho
layer_map = maps.ExpMap(nP=mesh.nC-1) * wire_map.t

# Define model. A resistivity (Ohm meters) or conductivity (S/m) for each layer.
starting_model = np.r_[np.log(resistivities), np.log(layer_thicknesses[:-1])]


#######################################################################
# Predict DC Resistivity Data
# ---------------------------
#
# Here we predict DC resistivity data. If the keyword argument *sigmaMap* is
# defined, the simulation will expect a conductivity model. If the keyword
# argument *rhoMap* is defined, the simulation will expect a resistivity model.
#

simulation = dc.simulation_1d.DCSimulation_1D(
        mesh, survey=survey, rhoMap=resistivity_map, tMap=layer_map,
        data_type="apparent_resistivity"
        )









dmis = data_misfit.L2DataMisfit(simulation=simulation, data=data_object)
dmis.W = 1./uncertainties







mesh_rho = TensorMesh([mesh.hx.size])
reg_rho = regularization.Simple(
    mesh_rho, alpha_s=1., alpha_x=0.0001,
    mapping=wire_map.rho
)
mesh_t = TensorMesh([mesh.hx.size-1])
reg_t = regularization.Simple(
    mesh_t, alpha_s=1., alpha_x=0.01,
    mapping=wire_map.t    
)
reg = reg_rho + reg_t



opt = optimization.InexactGaussNewton(
    maxIter=50, maxIterCG=30
)



invProb = inverse_problem.BaseInvProblem(dmis, reg, opt)



# Create an inversion object
starting_beta = directives.BetaEstimate_ByEig(beta0_ratio=1e1)
beta_schedule = directives.BetaSchedule(coolingFactor=5., coolingRate=3.)
target_misfit = directives.TargetMisfit(chifact=1.)

#save =  directives.SaveOutputDictEveryIteration()

directives_list = [starting_beta, beta_schedule, target_misfit]

inv = inversion.BaseInversion(invProb, directiveList=directives_list)

MOPT = []

recovered_model = inv.run(starting_model)

fig = plt.figure(figsize=(5, 5))
plotting_mesh = TensorMesh([np.r_[layer_map*recovered_model, layer_thicknesses[-1]]], '0')


true_model = np.loadtxt(str(model_filename))
true_layers = np.loadtxt(str(mesh_filename))
true_layers = TensorMesh([true_layers], '0')

ax1 = fig.add_axes([0.05, 0.05, 0.8, 0.9])
plot_layer(resistivity_map*recovered_model, plotting_mesh, ax=ax1, depth_axis=False)
plot_layer(true_model, true_layers, ax=ax1, depth_axis=False, color='r')


# Plot apparent resistivities on sounding curve
fig = plt.figure(figsize=(11, 5))

ax1 = fig.add_axes([0.05, 0.05, 0.8, 0.9])
ax1.semilogy(electrode_separations, dobs)
ax1.semilogy(electrode_separations, invProb.dpred)

plt.show()




