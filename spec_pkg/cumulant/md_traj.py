#! /usr/bin/env python

import os.path
import numpy as np
import math
import cmath
from scipy import integrate
import time
from numba import jit
from ..constants import constants as const
import cumulant

@jit
def ensemble_response_for_given_t(fluctuations,dipole_mom_sq,mean,t):
	response_val=0.0
	icount=0
        while icount<fluctuations.shape[0]:
           	jcount=0
              	while jcount<fluctuations.shape[1]:
			response_val=response_val+dipole_mom_sq[icount,jcount]*cmath.exp(-1j*(fluctuations[icount,jcount]+mean)*t)
                     	jcount=jcount+1
             	icount=icount+1
	return response_val/(fluctuations.shape[0]*fluctuations.shape[1]*1.0)
	
def construct_full_ensemble_response(fluctuations,dipole_mom_sq, mean, max_t,num_steps):
	response_func=np.zeros((num_steps,2),dtype=complex)
	tcount=0
	t_step=max_t/num_steps
	while tcount<num_steps:
		response_func[tcount,0]=tcount*t_step
		response_func[tcount,1]=ensemble_response_for_given_t(fluctuations,dipole_mom_sq,mean,response_func[tcount,0])
		tcount=tcount+1

	return response_func

def construct_full_cumulant_response(g2,g3,mean,is_3rd_order,is_emission):
	response_func=np.zeros((g2.shape[0],2),dtype=complex)
	counter=0
	while counter<response_func.shape[0]:
		response_func[counter,0]=g2[counter,0]
		if is_emission:
			if is_3rd_order:
				g3_temp=1j*g3[counter,1]
				response_func[counter,1]=cmath.exp(-1j*mean*g2[counter,0]-np.conj(g2[counter,1])-1j*np.conj(g3_temp))
			else:
				response_func[counter,1]=cmath.exp(-1j*mean*g2[counter,0]-np.conj(g2[counter,1]))
		else:
			if is_3rd_order:
				response_func[counter,1]=cmath.exp(-1j*mean*g2[counter,0]-g2[counter,1]-g3[counter,1])
			else:
				response_func[counter,1]=cmath.exp(-1j*mean*g2[counter,0]-g2[counter,1])

		counter=counter+1
	return response_func

# return dipole moment squared for all transitions 
def get_dipole_mom(oscillators,trajs):
        # compute fluctuations for each trajectory around the common mean
        icount=0
        while icount<trajs.shape[0]:
                jcount=0
                while jcount<trajs.shape[1]:
                        oscillators[icount,jcount]=oscillators[icount,jcount]/(trajs[icount,jcount]/const.Ha_to_eV)*3.0/2.0
                        jcount=jcount+1
                icount=icount+1

        return trajs

def get_fluctuations(trajs,mean):
        # compute fluctuations for each trajectory around the common mean
        icount=0
        while icount<trajs.shape[0]:
                jcount=0
                while jcount<trajs.shape[1]:
                        trajs[icount,jcount]=trajs[icount,jcount]/const.Ha_to_eV-mean
                        jcount=jcount+1
                icount=icount+1

        return trajs

# calculate the total mean of a batch of trajectory functions
def mean_of_func_batch(func):
        mean=0.0
        for x in func:
                for y in x:
                        mean=mean+y

        return mean/(func.shape[0]*func.shape[1])/const.Ha_to_eV

# generate an array of trajectory functions from files
def get_all_trajs(num_trajs,name_list):
        traj1=np.genfromtxt(name_list[0])
        num_points=traj1.shape[0]
        trajs=np.zeros((num_points,num_trajs))
        traj_count=1
        while traj_count<num_trajs:
                traj_current=np.genfromtxt(name_list[traj_count])
                icount=0
                while icount<traj_current.shape[0]:
                        trajs[icount,traj_count-1]=traj_current[icount,0]/const.Ha_to_eV
                        icount=icount+1
                traj_count=traj_count+1

        return trajs


#-----------------------------------------------------------
# Class definitions

class MDtrajs:
	def __init__(self,trajs,oscillators,tau,num_trajs,time_step):
		self.num_trajs=num_trajs
		self.mean=mean_of_func_batch(trajs)
		self.fluct=get_fluctuations(trajs,self.mean)
		self.dipole_mom=get_dipole_mom(oscillators,trajs)
		self.time_step=time_step # time between individual snapshots. Only relevant
		# for cumulant approach
		self.tau=tau    # Artificial decay length applied to correlation funcs

		# funtions needed to compute the cumulant response
		self.corr_func_cl=np.zeros((1,1))
		self.spectral_dens=np.zeros((1,1))
		self.corr_func_3rd_cl=np.zeros((1,1))
		self.corr_func_3rd_qm_freq=np.zeros((1,1))

		# cumulant lineshape functions
		self.g2=np.zeros((1,1))
		self.g3=np.zeros((1,1))

		# 2DES 3rd order cumulant lineshape functions
		self.h1=np.zeros((1,1,1))
		self.h2=np.zeros((1,1,1))
		self.h4=np.zeros((1,1,1))
		self.h5=np.zeros((1,1,1))
	
		# response functions
		self.ensemble_response=np.zeros((1,1))
		self.cumulant_response=np.zeros((1,1))

	def calc_2nd_order_corr(self):
		self.corr_func_cl=cumulant.construct_corr_func(self.fluct,self.num_trajs,self.tau,self.time_step)

	def calc_3rd_order_corr(self,corr_length):
		self.corr_func_3rd_cl=cumulant.construct_corr_func_3rd(self.fluct,self.num_trajs,corr_length,self.tau,self.time_step)

	def calc_spectral_dens(self,temp):
		kbT=temp*const.kb_in_Ha
		sampling_rate=1.0/self.time_step*math.pi*2.0   # angular frequency associated with the sampling time step
		self.spectral_dens=cumulant.compute_spectral_dens(self.corr_func_cl,kbT, sampling_rate,self.time_step)

	def calc_g2(self,temp,max_t,num_steps):
		kbT=temp*const.kb_in_Ha
		self.g2=cumulant.compute_2nd_order_cumulant_from_spectral_dens(self.spectral_dens,kbT,max_t,num_steps)

	def calc_corr_func_3rd_qm_freq(self,temp):
		kbT=temp*const.kb_in_Ha
		sampling_rate_in_fs=1.0/(self.time_step*const.fs_to_Ha)
		self.corr_func_3rd_qm_freq=cumulant.construct_corr_func_3rd_qm_freq(self.corr_func_3rd_cl,kbT,sampling_rate_in_fs)


	def calc_g3(self,temp,max_t,num_steps):
		kbT=temp*const.kb_in_Ha
		sampling_rate_in_fs=1.0/(self.time_step*const.fs_to_Ha)
		self.g3=cumulant.compute_lineshape_func_3rd(self.corr_func_3rd_cl,kbT,sampling_rate_in_fs,max_t,num_steps)

	def calc_h1(self,max_t,num_steps):
		self.h1=cumulant.compute_h1_func(self.corr_func_3rd_qm_freq,max_t,num_steps)

	def calc_h2(self,max_t,num_steps):
		self.h2=cumulant.compute_h2_func(self.corr_func_3rd_qm_freq,max_t,num_steps)

	def calc_h4(self,max_t,num_steps):
		self.h4=cumulant.compute_h4_func(self.corr_func_3rd_qm_freq,max_t,num_steps)

	def calc_h5(self,max_t,num_steps):
		self.h5=cumulant.compute_h5_func(self.corr_func_3rd_qm_freq,max_t,num_steps)

	def calc_cumulant_response(self,is_3rd_order,is_emission):
		self.cumulant_response=construct_full_cumulant_response(self.g2,self.g3,self.mean,is_3rd_order,is_emission)	

	def calc_ensemble_response(self,max_t,num_steps):
		self.ensemble_response=construct_full_ensemble_response(self.fluct,self.dipole_mom, self.mean, max_t,num_steps)


