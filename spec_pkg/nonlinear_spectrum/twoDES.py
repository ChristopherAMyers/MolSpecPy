#! /usr/bin/env python

import os.path
import numpy as np
import math
import cmath
from scipy import integrate
import time
from numba import jit
from ..cumulant import cumulant as cumul
from ..GBOM import gbom_cumulant_response as cumul_gbom

# basic analysis routines. Printing full 2DES, printing slices through the full 2DES along xaxis, yaxis and diagonal.

@jit
def print_2D_spectrum(filename,spectrum_2D,is_imag):
	outfile=open(filename, 'w')
	icount=0
	jcount=0
	while icount<spectrum_2D.shape[0]:
        	jcount=0
        	while jcount<spectrum_2D.shape[1]:
			if not is_imag:
                		outline=str(spectrum_2D[icount,jcount,0].real)+'\t'+str(spectrum_2D[icount,jcount,1].real)+'\t'+str(spectrum_2D[icount,jcount,2].real)+'\n'
			else:
				outline=str(spectrum_2D[icount,jcount,0].real)+'\t'+str(spectrum_2D[icount,jcount,1].real)+'\t'+str(spectrum_2D[icount,jcount,2].imag)+'\n'
                	outfile.write(outline)

                	jcount=jcount+1
        	outfile.write('\n')
        	icount=icount+1

@jit
def read_2D_spectrum(filename,num_points):
        line_data=open(filename,"r")
        lines=line_data.readlines()
        outarray=np.zeros((num_points,num_points,3))
        icount=0
        jcount=0
        while icount<num_points:
                jcount=0
                while jcount<num_points:
                        line_count=icount*(num_points+1)+jcount
                        current_line=lines[line_count].split()
                        outarray[icount,jcount,0]=float(current_line[0])
                        outarray[icount,jcount,1]=float(current_line[1])
                        outarray[icount,jcount,2]=float(current_line[2])

                        jcount=jcount+1
                icount=icount+1

        return outarray

# compute a transient absorption spectrum from 2DES data. This involves integrating over the omega1 axis of
# the X(omega1,t_delay,omega2) plot
@jit
def transient_abs_from_2DES(spec):
	num_points=spec.shape[0]
	transient_data=np.zeros((num_points,2))
	icount=0
	while icount<num_points:
		integrant=np.zeros((num_points,2))
		integrant[:,0]=spec[:,icount,0]
		integrant[:,1]=spec[:,icount,2]
		transient_data[icount,0]=spec[0,icount,1]
		transient_data[icount,1]=integrate.simps(integrant[:,1],dx=integrant[1,0]-integrant[0,0])
		icount=icount+1

	return transient_data


# 2DES time series for a batch of spectra
def calc_2DES_time_series_batch(q_batch,num_batches,E_min1,E_max1,E_min2,E_max2,num_points_2D,rootname,num_times,time_step,mean):
        averaged_val=np.zeros((num_times,2))
        transient_abs=np.zeros((num_times,num_points_2D,3))

        # make sure chosen delay times break down into an integer number of timesteps in the response function
        step_length_t=((q_batch[0])[1,0]-(q_batch[0])[0,0]).real
        eff_time_index_2DES=int(round(time_step/step_length_t))
        eff_time_step_2DES=eff_time_index_2DES*step_length_t

        current_delay=0.0
        current_delay_index=0
        counter=0
	while counter<num_times:
                print(counter,current_delay)
		spectrum_2D=np.zeros((num_points_2D,num_points_2D,3))
		batch_count=0 
		while batch_count<num_batches:
			print('Processing batch number '+str(batch_count+1))
                	spectrum_2D_temp=calc_2D_spectrum(q_batch[batch_count],current_delay,current_delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean)
			if batch_count==0:
				spectrum_2D=spectrum_2D+spectrum_2D_temp
			else:
				spectrum_2D[:,:,2]=spectrum_2D[:,:,2]+spectrum_2D_temp[:,:,2]
			
			batch_count=batch_count+1
		spectrum_2D[:,:,2]=spectrum_2D[:,:,2]/(1.0*num_batches)
                print_2D_spectrum(rootname+'_2DES_'+str(counter)+'.dat',spectrum_2D,False)

                #compute transient absorption contribution here:
                transient_temp=transient_abs_from_2DES(spectrum_2D)
                transient_abs[counter,:,0]=current_delay
                transient_abs[counter,:,1]=transient_temp[:,0]
                transient_abs[counter,:,2]=transient_temp[:,1]


                averaged_val[counter,0]=current_delay
                averaged_val[counter,1]=cumul.simpson_integral_2D(spectrum_2D)
                #averaged_val[counter,1]=np.sum(spectrum_2D[:,:,2])/(spectrum_2D.shape[0]*2.0)
                print averaged_val[counter,1]
                counter=counter+1
                current_delay=current_delay+eff_time_step_2DES
                current_delay_index=current_delay_index+eff_time_index_2DES

        print_2D_spectrum(rootname+'_2nd_order_cumulant_transient_absorption_spec.txt',transient_abs,False)
        np.savetxt(rootname+'_2DES_2nd_order_cumulant_averaged_spectrum.txt',averaged_val)




# basic calculation routines:
# calculate a full series of 2DES spectra, sampled with a certain delay time step
def calc_2DES_time_series(q_func,E_min1,E_max1,E_min2,E_max2,num_points_2D,rootname,num_times,time_step,mean):
	averaged_val=np.zeros((num_times,2))
	transient_abs=np.zeros((num_times,num_points_2D,3))

	# make sure chosen delay times break down into an integer number of timesteps in the response function
        step_length_t=(q_func[1,0]-q_func[0,0]).real
	eff_time_index_2DES=int(round(time_step/step_length_t))
	eff_time_step_2DES=eff_time_index_2DES*step_length_t

	current_delay=0.0
        current_delay_index=0
	counter=0
	while counter<num_times:
		print(counter,current_delay)
		spectrum_2D=calc_2D_spectrum(q_func,current_delay,current_delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean)
		print_2D_spectrum(rootname+'_2DES_'+str(counter)+'.dat',spectrum_2D,False)

		#compute transient absorption contribution here:
		transient_temp=transient_abs_from_2DES(spectrum_2D)
		transient_abs[counter,:,0]=current_delay
		transient_abs[counter,:,1]=transient_temp[:,0]
		transient_abs[counter,:,2]=transient_temp[:,1]


		averaged_val[counter,0]=current_delay
		averaged_val[counter,1]=cumul.simpson_integral_2D(spectrum_2D)
		#averaged_val[counter,1]=np.sum(spectrum_2D[:,:,2])/(spectrum_2D.shape[0]*2.0)
		print averaged_val[counter,1]
		counter=counter+1
		current_delay=current_delay+eff_time_step_2DES
		current_delay_index=current_delay_index+eff_time_index_2DES

	print_2D_spectrum(rootname+'_2nd_order_cumulant_transient_absorption_spec.txt',transient_abs,False)
	np.savetxt(rootname+'_2DES_2nd_order_cumulant_averaged_spectrum.txt',averaged_val)

# basic calculation routines:
# calculate a full series of 2DES spectra, sampled with a certain delay time step
# this routine is specifficaly for the 3rd order cumulant correction and an MD time series
def calc_2DES_time_series_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,corr_func_freq_qm,E_min1,E_max1,E_min2,E_max2,num_points_2D,rootname,num_times,time_step,mean):
	averaged_val=np.zeros((num_times,2))
	transient_abs=np.zeros((num_times,num_points_2D,3))

	# make sure chosen delay times break down into an integer number of timesteps in the response function
        step_length_t=(q_func[1,0]-q_func[0,0]).real
        eff_time_index_2DES=int(round(time_step/step_length_t))
        eff_time_step_2DES=eff_time_index_2DES*step_length_t

        current_delay=0.0
        current_delay_index=0

        counter=0
        while counter<num_times:
                print(counter,current_delay)
                spectrum_2D=calc_2D_spectrum_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,corr_func_freq_qm,current_delay,current_delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean)
                print_2D_spectrum(rootname+'_2DES_'+str(counter)+'.dat',spectrum_2D,False)

		#compute transient absorption contribution here:
                transient_temp=transient_abs_from_2DES(spectrum_2D)
                transient_abs[counter,:,0]=current_delay
                transient_abs[counter,:,1]=transient_temp[:,0]
                transient_abs[counter,:,2]=transient_temp[:,1]

		averaged_val[counter,0]=current_delay
                averaged_val[counter,1]=cumul.simpson_integral_2D(spectrum_2D)

                counter=counter+1
		current_delay=current_delay+eff_time_step_2DES
                current_delay_index=current_delay_index+eff_time_index_2DES

	print_2D_spectrum(rootname+'_3rd_order_cumulant_transient_absorption_spec.txt',transient_abs,False)
	np.savetxt(rootname+'2DES_3rd_order_cumulant_averaged_spectrum.txt',averaged_val)

# basic calculation routines:
# calculate a full series of 2DES spectra, sampled with a certain delay time step
# this routine is specifically for the 3rd order cumulant correction and the GBOM
#def calc_2DES_time_series_GBOM_3rd(q_func,g_func,h1_func,h2_func,freqs_gs,Omega_sq,gamma,kbT,E_min1,E_max1,E_min2,E_max2,num_points_2D,rootname,num_times,time_step,mean,is_cl):
#	averaged_val=np.zeros((num_times,2))
#	transient_abs=np.zeros((num_times,num_points_2D,3))
#
#        current_delay=0.0
#        counter=0
#        while counter<num_times:
#                print(counter,current_delay)
#                spectrum_2D=calc_2D_spectrum_GBOM_3rd(q_func,g_func,h1_func,h2_func,freqs_gs,Omega_sq,gamma,kbT,current_delay,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean,is_cl)
#                print_2D_spectrum(rootname+'_2DES_'+str(counter)+'.dat',spectrum_2D,False)

#		#compute transient absorption contribution here:
#                transient_temp=transient_abs_from_2DES(spectrum_2D)
#                transient_abs[counter,:,0]=current_delay
#                transient_abs[counter,:,1]=transient_temp[:,0]
#                transient_abs[counter,:,2]=transient_temp[:,1]

#   	 	 averaged_val[counter,0]=current_delay
#                averaged_val[counter,1]=cumul.simpson_integral_2D(spectrum_2D)

#                counter=counter+1
#                current_delay=current_delay+time_step

#	print_2D_spectrum(rootname+'_3rd_order_cumulant_transient_absorption_spec.txt',transient_abs,False)
#	np.savetxt(rootname+'2DES_3rd_order_cumulant_averaged_spectrum.txt',averaged_val)

# STUPID TEST: TRY WITH H4 and H5
# basic calculation routines:
# calculate a full series of 2DES spectra, sampled with a certain delay time step
# this routine is specifically for the 3rd order cumulant correction and the GBOM
def calc_2DES_time_series_GBOM_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,freqs_gs,Omega_sq,gamma,kbT,E_min1,E_max1,E_min2,E_max2,num_points_2D,rootname,num_times,time_step,mean,is_cl):
        averaged_val=np.zeros((num_times,2))
        transient_abs=np.zeros((num_times,num_points_2D,3))

	# make sure chosen delay times break down into an integer number of timesteps in the response function
        step_length_t=(q_func[1,0]-q_func[0,0]).real
        eff_time_index_2DES=int(round(time_step/step_length_t))
        eff_time_step_2DES=eff_time_index_2DES*step_length_t

	current_delay=0.0
	current_delay_index=0
        counter=0
        while counter<num_times:
                print(counter,current_delay)
                spectrum_2D=calc_2D_spectrum_GBOM_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,freqs_gs,Omega_sq,gamma,kbT,current_delay,current_delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean,is_cl)
                print_2D_spectrum(rootname+'_2DES_'+str(counter)+'.dat',spectrum_2D,False)

                #compute transient absorption contribution here:
                transient_temp=transient_abs_from_2DES(spectrum_2D)
                transient_abs[counter,:,0]=current_delay
                transient_abs[counter,:,1]=transient_temp[:,0]
                transient_abs[counter,:,2]=transient_temp[:,1]

                averaged_val[counter,0]=current_delay
                averaged_val[counter,1]=cumul.simpson_integral_2D(spectrum_2D)

                counter=counter+1
		current_delay=current_delay+eff_time_step_2DES
                current_delay_index=current_delay_index+eff_time_index_2DES


        print_2D_spectrum(rootname+'_3rd_order_cumulant_transient_absorption_spec.txt',transient_abs,False)
        np.savetxt(rootname+'2DES_3rd_order_cumulant_averaged_spectrum.txt',averaged_val)

# pump probe spectrum. this is essentially a 2DES spectrum, but where the excitation energy is fixed to just
# a single frequency. Is this really correct though? 2DES is computed from the sum of rephasing and non-
# rephasing diagrams. Is this the right basis for pump-probe? Double check
def calc_pump_probe_time_series(q_func,E_min,E_max,num_points_2D,rootname,pump_energy,num_times,time_step,mean):
	pump_probe_spectrum=np.zeros((num_times,num_points_2D,3))
	counter=0
	current_delay=0.0
	while counter<num_times:
		print counter,current_delay,pump_energy
#		current_spec=calc_2D_spectrum_y_slice(q_func,current_delay,E_min,E_max,num_points_2D,pump_energy,mean)
		pump_probe_spectrum[counter,:,0]=current_delay
		pump_probe_spectrum[counter,:,1]=current_spec[:,0]
		pump_probe_spectrum[counter,:,2]=current_spec[:,1]
		counter=counter+1
		current_delay=current_delay+time_step

	print_2D_spectrum(rootname+'_pump_probe.dat',pump_probe_spectrum,False)

#@jit
# calculate slice along the diagonal axis of the 2DES spectrum (i.e. Omega1=omega2
#def calc_2D_spectrum_diag_slice(q_func,delay_time,E_min,E_max,num_points_2D,mean):
#        full_2D_spectrum=np.zeros((num_points_2D,2))
#        counter1=0
#        step_length=((E_max-E_min)/num_points_2D)
#
#	step_length_t=(q_func[1,0]-q_func[0,0]).real
#	
#
#	rfunc=calc_Rfuncs_tdelay(q_func,delay_time)
#        while counter1<num_points_2D:
#                omega2=E_min+counter1*step_length
#                full_2D_spectrum[counter1,0]=omega2
#                integrant=twoD_spectrum_integrant(rfunc,q_func,omega2-mean,omega2-mean,delay_time)
#                full_2D_spectrum[counter1,1]=cumul.simpson_integral_2D(integrant).real
#                counter1=counter1+1
#        return full_2D_spectrum



#@jit
# calculate slice along the y axis of the 2DES spectrum (i.e. Omega1 is a constant
#def calc_2D_spectrum_y_slice(q_func,delay_time,E_min,E_max,num_points_2D,omega1,mean):
#        full_2D_spectrum=np.zeros((num_points_2D,2))
#        counter1=0
#        step_length=((E_max-E_min)/num_points_2D)
#        rfunc=calc_Rfuncs_tdelay(q_func,delay_time)
#        while counter1<num_points_2D:
#                omega2=E_min+counter1*step_length
#                full_2D_spectrum[counter1,0]=omega2
#                integrant=twoD_spectrum_integrant(rfunc,q_func,omega1-mean,omega2-mean,delay_time)
#                full_2D_spectrum[counter1,1]=cumul.simpson_integral_2D(integrant).real
#                counter1=counter1+1
#        return full_2D_spectrum

#@jit
# calculate slice along the x axis of the 2DES spectrum (i.e. Omega2 is a constant
#def calc_2D_spectrum_x_slice(q_func,delay_time,E_min,E_max,num_points_2D,omega2,mean):
#	full_2D_spectrum=np.zeros((num_points_2D,2))
#	counter1=0
#	step_length=((E_max-E_min)/num_points_2D)
#        rfunc=calc_Rfuncs_tdelay(q_func,delay_time)
#    	while counter1<num_points_2D:
#		omega1=E_min+counter1*step_length
#		full_2D_spectrum[counter1,0]=omega1
#		integrant=twoD_spectrum_integrant(rfunc,q_func,omega1-mean,omega2-mean,delay_time)
#		full_2D_spectrum[counter1,1]=cumul.simpson_integral_2D(integrant).real
#		counter1=counter1+1
#	return full_2D_spectrum

# Calculation rotuine for the 2DES spectrum at a given point. This is important if we want to follow how cross peaks develop
#@jit
#def calc_2D_spectrum_point(q_func,delay_time,E_min,E_max,omega1,omega2):
#	rfunc=calc_Rfuncs_tdelay(q_func,delay_time)
# 	full_2D_integrant=twoD_spectrum_integrant(rfunc,omega1,omega2,delay_time)
#	return cumul.simpson_integral_2D(full_2D_integrant).real


# Calculation routine for the full spectrum in the 2nd order cumulant approximation 
@jit
def calc_2D_spectrum(q_func,delay_time,delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean):
    full_2D_spectrum=np.zeros((num_points_2D,num_points_2D,3))
    counter1=0
    counter2=0
    step_length=((E_max1-E_min1)/num_points_2D)


    rfunc=calc_Rfuncs_tdelay(q_func,delay_time,delay_index)
    while counter1<num_points_2D:
        counter2=0
        omega1=E_min1+counter1*step_length
        while counter2<num_points_2D:
                omega2=E_min2+counter2*step_length
                full_2D_integrant=twoD_spectrum_integrant(rfunc,q_func,omega1-mean,omega2-mean,delay_time)
                full_2D_spectrum[counter1,counter2,0]=omega1
                full_2D_spectrum[counter1,counter2,1]=omega2
                full_2D_spectrum[counter1,counter2,2]=cumul.simpson_integral_2D(full_2D_integrant).real
                counter2=counter2+1
        counter1=counter1+1

    return full_2D_spectrum


# Calculation routine for the full spectrum in the 3rd order cumulant approximation 
@jit
def calc_2D_spectrum_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,corr_func_freq_qm,delay_time,delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean):
    full_2D_spectrum=np.zeros((num_points_2D,num_points_2D,3))
    counter1=0
    counter2=0
    step_length=((E_max1-E_min1)/num_points_2D)
    print 'Compute rfunc'
    rfunc=calc_Rfuncs_tdelay(q_func,delay_time,delay_index)
    print 'Compute rfunc 3rd'
    rfunc_3rd=calc_Rfuncs_3rd_tdelay(g_func,h1_func,h2_func,h4_func,h5_func,corr_func_freq_qm,delay_time,delay_index)
    print 'DONE'
    print 'DIMENSIONS of RFUNC and RFUNC_3rd:'
    print rfunc.shape[0],rfunc_3rd.shape[0]
    while counter1<num_points_2D:
        counter2=0
        omega1=E_min1+counter1*step_length
        while counter2<num_points_2D:
                omega2=E_min2+counter2*step_length
                full_2D_integrant=twoD_spectrum_integrant_3rd(rfunc,rfunc_3rd,q_func,omega1-mean,omega2-mean,delay_time)
                full_2D_spectrum[counter1,counter2,0]=omega1
                full_2D_spectrum[counter1,counter2,1]=omega2
                full_2D_spectrum[counter1,counter2,2]=cumul.simpson_integral_2D(full_2D_integrant).real
                counter2=counter2+1
        counter1=counter1+1

    return full_2D_spectrum


# Calculation routine for the full spectrum in the 3rd order cumulant approximation for a GBOM
#@jit
#def calc_2D_spectrum_GBOM_3rd(q_func,g_func,h1_func,h2_func,freqs_gs,Omega_sq,gamma,kbT,delay_time,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean,is_cl):
#    full_2D_spectrum=np.zeros((num_points_2D,num_points_2D,3))
#    counter1=0
#    counter2=0
#    step_length=((E_max1-E_min1)/num_points_2D)
#    print 'Compute rfunc'
#    rfunc=calc_Rfuncs_tdelay(q_func,delay_time)
#    print 'Compute rfunc 3rd'
#    rfunc_3rd=calc_Rfuncs_3rd_GBOM_tdelay(g_func,h1_func,h2_func,freqs_gs,Omega_sq,gamma,kbT,delay_time,is_cl)
#    print 'DONE'
#    while counter1<num_points_2D:
#        counter2=0
#        omega1=E_min1+counter1*step_length
#        while counter2<num_points_2D:
#                omega2=E_min2+counter2*step_length
#                full_2D_integrant=full_2D_integrant=twoD_spectrum_integrant_3rd(rfunc,rfunc_3rd,q_func,omega1-mean,omega2-mean,delay_time)
#                full_2D_spectrum[counter1,counter2,0]=omega1
#                full_2D_spectrum[counter1,counter2,1]=omega2
#                full_2D_spectrum[counter1,counter2,2]=cumul.simpson_integral_2D(full_2D_integrant).real
#                counter2=counter2+1
#        counter1=counter1+1
#
#    return full_2D_spectrum


# Calculation routine for the full spectrum in the 3rd order cumulant approximation for a GBOM
@jit
def calc_2D_spectrum_GBOM_3rd(q_func,g_func,h1_func,h2_func,h4_func,h5_func,freqs_gs,Omega_sq,gamma,kbT,delay_time,delay_index,E_min1,E_max1,E_min2,E_max2,num_points_2D,mean,is_cl):
    full_2D_spectrum=np.zeros((num_points_2D,num_points_2D,3))
    counter1=0
    counter2=0
    step_length=((E_max1-E_min1)/num_points_2D)
    print 'Compute rfunc'
    rfunc=calc_Rfuncs_tdelay(q_func,delay_time,delay_index)
    print 'Compute rfunc 3rd'
    rfunc_3rd=calc_Rfuncs_3rd_GBOM_tdelay(g_func,h1_func,h2_func,h4_func,h5_func,freqs_gs,Omega_sq,gamma,kbT,delay_time,delay_index,is_cl)
    print 'DONE'
    print 'Dimensions RFunc and Rfunc 3rd'
    print rfunc.shape[0], rfunc_3rd.shape[0]

    while counter1<num_points_2D:
        counter2=0
        omega1=E_min1+counter1*step_length
        while counter2<num_points_2D:
                omega2=E_min2+counter2*step_length
                full_2D_integrant=twoD_spectrum_integrant_3rd(rfunc,rfunc_3rd,q_func,omega1-mean,omega2-mean,delay_time)
                full_2D_spectrum[counter1,counter2,0]=omega1
                full_2D_spectrum[counter1,counter2,1]=omega2
                full_2D_spectrum[counter1,counter2,2]=cumul.simpson_integral_2D(full_2D_integrant).real
                counter2=counter2+1
        counter1=counter1+1

    return full_2D_spectrum




# this function computes the R1,R2,R3 and R4 functions for a given delay time tdelay.
# function works in the 2nd order cumulant approximation
@jit
def calc_Rfuncs_tdelay(q_func,t_delay,steps_in_t_delay):
    # first find the effective step_length
    step_length=q_func[1,0].real-q_func[0,0].real
#    steps_in_t_delay=int(round(t_delay/step_length))  # NOTE: delay time is rounded to match with steps in the response function
    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs.
    # try to adjust steps_in_tdelay:
    max_index=0
    temp_max_index=q_func.shape[0]-steps_in_t_delay
    if (temp_max_index%2) ==0:
	# even.
	max_index=temp_max_index/2
    else:
	# odd
	max_index=(temp_max_index-1)/2

    #max_index=int((((q_func.shape[0]-steps_in_t_delay)/2.0)))
    rfuncs=np.zeros((max_index,max_index,6),dtype=np.complex_) # first and 2nd number are the times, 3rd number is R1, 4th number is R2 etc.
    count1=0
    count2=0
    while count1<max_index:
        count2=0
        while count2<max_index:
		#print count1,count2
                rfuncs[count1,count2,0]=q_func[count1,0]
                rfuncs[count1,count2,1]=q_func[count2,0]
                R1_phase=-q_func[count1,1]-q_func[steps_in_t_delay,1].conjugate()-q_func[count2,1].conjugate()+q_func[count1+steps_in_t_delay,1]+q_func[count2+steps_in_t_delay,1].conjugate()-q_func[count1+count2+steps_in_t_delay,1]
                R2_phase=-q_func[count1,1].conjugate()+q_func[steps_in_t_delay,1]-q_func[count2,1].conjugate()-q_func[count1+steps_in_t_delay,1].conjugate()-q_func[count2+steps_in_t_delay,1]+q_func[count1+count2+steps_in_t_delay,1].conjugate()
                R3_phase=-q_func[count1,1].conjugate()+q_func[steps_in_t_delay,1].conjugate()-q_func[count2,1]-q_func[count1+steps_in_t_delay,1].conjugate()-q_func[count2+steps_in_t_delay,1].conjugate()+q_func[count1+count2+steps_in_t_delay,1].conjugate()
                R4_phase=-q_func[count1,1]-q_func[steps_in_t_delay,1]-q_func[count2,1]+q_func[count1+steps_in_t_delay,1]+q_func[count2+steps_in_t_delay,1]-q_func[count1+count2+steps_in_t_delay,1]
		rfuncs[count1,count2,2]=R1_phase
		rfuncs[count1,count2,3]=R2_phase
		rfuncs[count1,count2,4]=R3_phase
		rfuncs[count1,count2,5]=R4_phase
		count2=count2+1
	count1=count1+1
    return rfuncs

#STUPID TEST: H4 H5 files
@jit
def calc_Rfuncs_3rd_GBOM_tdelay(g_func,h1_func,h2_func,h4_func,h5_func,freqs_gs,Omega_sq,gamma,kbT,t_delay,steps_in_t_delay,is_cl):
    # first find the effective step_length
    print 'Entering Rfuncs_3rd'
    step_length=g_func[1,0].real-g_func[0,0].real
    #steps_in_t_delay=int(round(t_delay/step_length))  # NOTE: delay time is rounded to match with steps in the response function
    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs.
    temp_max_index=g_func.shape[0]-steps_in_t_delay
    max_index=0
    if (temp_max_index%2) ==0:
       	# even.
        max_index=temp_max_index/2
    else:
        # odd
        max_index=(temp_max_index-1)/2
#    max_index=int(((g_func.shape[0]-steps_in_t_delay)/2.0))
    rfuncs=np.zeros((max_index,max_index,6),dtype=np.complex_) # first and 2nd number are the times, 3rd number is R1, 4th number is R2 etc.

    print 'step_length, steps_in_t_delay,t_delay, eff_tdelay'
    print step_length,steps_in_t_delay,t_delay,steps_in_t_delay*step_length
    count1=0
    count2=0
    # if this is a calculation based on the exact quantum correlation function, need to precompute n_i_vec
    n_i_vec=np.zeros(freqs_gs.shape[0])
    if not is_cl:
        icount=0
        while icount<n_i_vec.shape[0]:
                n_i_vec[icount]=cumul_gbom.bose_einstein(freqs_gs[icount],kbT)
                icount=icount+1

    while count1<max_index:
        count2=0
        while count2<max_index:
                # set all required indices and parameters.
                rfuncs[count1,count2,0]=g_func[count1,0]
                rfuncs[count1,count2,1]=g_func[count2,0]
                t1=g_func[count1,0]
                t12=t1+t_delay
                t123=t12+g_func[count2,0]
		# INCONSISTENCY BETWEEN t12 and t12_index potentially?
                t1_index=count1
                t12_index=count1+steps_in_t_delay
                t123_index=t12_index+count2
		#print 'INDICES:'
		#print t12,(count1+steps_in_t_delay)*step_length
                # now compute required h3 functions
                if is_cl:
                        h31=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t1,t12,t123)
                        h32=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t12,t123,t1)
                        h33=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t1,t123,t12)
                        h34=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t123,t12,t1)
                else:
                        h31=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t1,t12,t123)
                        h32=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t12,t123,t1)
                        h33=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t1,t123,t12)
                        h34=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t123,t12,t1)


# FLIP SIGN OF g_func conjugate term! This is due to of our redefinition of g
		rfuncs[count1,count2,2]=-g_func[t1_index,1]-g_func[t12_index,1].conjugate()-g_func[t123_index,1]+h31+h1_func[t1_index,t12_index,2]-h1_func[t1_index,t123_index,2]-h2_func[t12_index,t123_index,2]-h4_func[t1_index,t123_index,2]+h4_func[t12_index,t123_index,2]-h5_func[t1_index,t12_index,2]


		rfuncs[count1,count2,3]=-g_func[t12_index,1].conjugate()-g_func[t123_index,1]-g_func[t1_index,1].conjugate()-h32-h2_func[t12_index,t123_index,2]+h2_func[t12_index,t1_index,2]+h1_func[t123_index,t1_index,2]+h4_func[t12_index,t123_index,2]+h5_func[t12_index,t1_index,2]-h5_func[t123_index,t1_index,2]


		rfuncs[count1,count2,4]=-g_func[t1_index,1].conjugate()-g_func[t123_index,1]-g_func[t12_index,1].conjugate()-h33-h2_func[t1_index,t123_index,2]+h2_func[t1_index,t12_index,2]+h1_func[t123_index,t12_index,2]+h4_func[t1_index,t123_index,2]+h5_func[t1_index,t12_index,2]-h5_func[t123_index,t12_index,2]


		rfuncs[count1,count2,5]=-g_func[t123_index,1]-g_func[t12_index,1].conjugate()-g_func[t1_index,1]+h34+h1_func[t123_index,t12_index,2]-h1_func[t123_index,t1_index,2]-h2_func[t12_index,t1_index,2]-h4_func[t123_index,t1_index,2]+h4_func[t12_index,t1_index,2]-h5_func[t123_index,t12_index,2]


                count2=count2+1
        count1=count1+1

    return rfuncs



# this function computes the 3rd order cumulant correction for R1, R2, R3 and R4 functions for a given
# delay time t_delay. Note that this function is specifically for use with a GBOM parameterized model, 
# rather than a correlation function constructed from a time-series
#@jit
#def calc_Rfuncs_3rd_GBOM_tdelay(g_func,h1_func,h2_func,freqs_gs,Omega_sq,gamma,kbT,t_delay,is_cl):
#    # first find the effective step_length
#    step_length=g_func[1,0].real-g_func[0,0].real
#    steps_in_t_delay=int(t_delay/step_length)  # NOTE: delay time is rounded to match with steps in the response function
#    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs.
#    max_index=int((g_func.shape[0]-steps_in_t_delay)/2.0)
#    rfuncs=np.zeros((max_index,max_index,6),dtype=np.complex_) # first and 2nd number are the times, 3rd number is R1, 4th number is R2 etc.
#    count1=0
#    count2=0
#    # if this is a calculation based on the exact quantum correlation function, need to precompute n_i_vec
#    n_i_vec=np.zeros(freqs_gs.shape[0])
#    if not is_cl:
#	icount=0
#	while icount<n_i_vec.shape[0]:
#		n_i_vec[icount]=cumul_gbom.bose_einstein(freqs_gs[icount],kbT)
#                icount=icount+1
#
#    while count1<max_index:
#        count2=0
#        while count2<max_index:
##                # set all required indices and parameters.
#                rfuncs[count1,count2,0]=g_func[count1,0]
#                rfuncs[count1,count2,1]=g_func[count2,0]
#                t1=g_func[count1,0]
#                t12=t1+t_delay
#                t123=t12+g_func[count2,0]
#                t1_index=count1
#                t12_index=count1+steps_in_t_delay
#                t123_index=t12_index+count2
#                # now compute required h3 functions
#		if is_cl:
##                	h31=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t1,t12,t123)
#                	h32=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t12,t123,t1)
#                	h33=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t1,t123,t12)
#                	h34=cumul_gbom.h3_func_cl_t(freqs_gs,Omega_sq,gamma,kbT,t123,t12,t1)
#		else:
#			h31=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t1,t12,t123)
#                        h32=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t12,t123,t1)
#                        h33=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t1,t123,t12)
#                        h34=cumul_gbom.h3_func_qm_t(freqs_gs,Omega_sq,n_i_vec,gamma,kbT,t123,t12,t1)
#
                # now build rfuncs
#                rfuncs[count1,count2,2]=-g_func[t1_index,1]+g_func[t12_index,1].conjugate()-g_func[t123_index,1]+h31-h1_func[t12_index,t1_index,2].conjugate()-h2_func[t123_index,t1_index,2].conjugate()+h1_func[t1_index,t12_index,2]-h1_func[t1_index,t123_index,2]+h2_func[t123_index,t12_index,2].conjugate()-h2_func[t12_index,t123_index,2]

#                rfuncs[count1,count2,3]=g_func[t12_index,1].conjugate()-g_func[t123_index,1]+g_func[t1_index,1].conjugate()-h32+h2_func[t123_index,t12_index,2].conjugate()+h1_func[t1_index,t12_index,2].conjugate()-h2_func[t12_index,t123_index,2]+h2_func[t12_index,t1_index,2]-h1_func[t1_index,t123_index,2].conjugate()+h1_func[t123_index,t1_index,2]

#                rfuncs[count1,count2,4]=g_func[t1_index,1].conjugate()-g_func[t123_index,1]+g_func[t12_index,1].conjugate()-h33+h2_func[t123_index,t1_index,2].conjugate()+h1_func[t12_index,t1_index,2].conjugate()-h2_func[t1_index,t123_index,2]+h2_func[t1_index,t12_index,2]-h1_func[t12_index,t123_index,2].conjugate()+h1_func[t123_index,t12_index,2]

#                rfuncs[count1,count2,5]=-g_func[t123_index,1]+g_func[t12_index,1].conjugate()-g_func[t1_index,1]+h34-h1_func[t12_index,t123_index,2].conjugate()-h2_func[t1_index,t123_index,2].conjugate()+h1_func[t123_index,t12_index,2]-h1_func[t123_index,t1_index,2]+h2_func[t1_index,t12_index,2].conjugate()-h2_func[t12_index,t1_index,2]
#
#                count2=count2+1
#        count1=count1+1
#
#    return rfuncs



# this function computes the 3rd order cumulant correction for R1, R2, R3 and R4 functions for a given
# delay time t_delay
@jit
def calc_Rfuncs_3rd_tdelay(g_func,h1_func,h2_func,h4_func,h5_func, qm_corr_func_freq,t_delay,steps_in_t_delay):
    print('Entering Rfuncs_3rd')
    step_length=g_func[1,0].real-g_func[0,0].real
    #steps_in_t_delay=int(round(t_delay/step_length))  # NOTE: delay time is rounded to match with steps in the response function
    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs.
    temp_max_index=g_func.shape[0]-steps_in_t_delay
    max_index=0
    if (temp_max_index%2)==0:
        # even.
        max_index=temp_max_index/2
    else:
        # odd
        max_index=(temp_max_index-1)/2
#    max_index=int(((g_func.shape[0]-steps_in_t_delay)/2.0))
    rfuncs=np.zeros((max_index,max_index,6),dtype=np.complex_) # first and 2nd number are the times, 3rd number is R1, 4th number is R2 etc.

    print('step_length, steps_in_t_delay,t_delay, eff_tdelay')
    print(step_length,steps_in_t_delay,t_delay,steps_in_t_delay*step_length)

    count1=0
    count2=0
    while count1<max_index:
        count2=0
        while count2<max_index:
		# set all required indices and parameters.
		rfuncs[count1,count2,0]=g_func[count1,0]
		rfuncs[count1,count2,1]=g_func[count2,0]
		t1=g_func[count1,0]
		t12=t1+t_delay
		t123=t12+g_func[count2,0]
		t1_index=count1
		t12_index=count1+steps_in_t_delay
		t123_index=t12_index+count2

		print(t1,t12,t123,t1_index,t12_index,t123_index)
		print('Entering h3')
                # now compute required h3 functions
 		h31=cumul.compute_h3_val(qm_corr_func_freq,t1,t12,t123)
		print('computed first h3')
		h32=cumul.compute_h3_val(qm_corr_func_freq,t12,t123,t1)
		h33=cumul.compute_h3_val(qm_corr_func_freq,t1,t123,t12)
		h34=cumul.compute_h3_val(qm_corr_func_freq,t123,t12,t1)
		print('computed H3')
		
		# now build rfuncs
                rfuncs[count1,count2,2]=-g_func[t1_index,1]-g_func[t12_index,1].conjugate()-g_func[t123_index,1]+h31+h1_func[t1_index,t12_index,2]-h1_func[t1_index,t123_index,2]-h2_func[t12_index,t123_index,2]-h4_func[t1_index,t123_index,2]+h4_func[t12_index,t123_index,2]-h5_func[t1_index,t12_index,2]

                rfuncs[count1,count2,3]=-g_func[t12_index,1].conjugate()-g_func[t123_index,1]-g_func[t1_index,1].conjugate()-h32-h2_func[t12_index,t123_index,2]+h2_func[t12_index,t1_index,2]+h1_func[t123_index,t1_index,2]+h4_func[t12_index,t123_index,2]+h5_func[t12_index,t1_index,2]-h5_func[t123_index,t1_index,2]

                rfuncs[count1,count2,4]=-g_func[t1_index,1].conjugate()-g_func[t123_index,1]-g_func[t12_index,1].conjugate()-h33-h2_func[t1_index,t123_index,2]+h2_func[t1_index,t12_index,2]+h1_func[t123_index,t12_index,2]+h4_func[t1_index,t123_index,2]+h5_func[t1_index,t12_index,2]-h5_func[t123_index,t12_index,2]

                rfuncs[count1,count2,5]=-g_func[t123_index,1]-g_func[t12_index,1].conjugate()-g_func[t1_index,1]+h34+h1_func[t123_index,t12_index,2]-h1_func[t123_index,t1_index,2]-h2_func[t12_index,t1_index,2]-h4_func[t123_index,t1_index,2]+h4_func[t12_index,t1_index,2]-h5_func[t123_index,t12_index,2]


		count2=count2+1
	count1=count1+1

    print('Done with rfuncs 3rd')

    return rfuncs

# integrant of the 3rd order response function in the 2nd order cumulant approximation. Need to include possibility to add pulse shape
# omega_av is already incorporated in the function q. No need to account for the mean in the equation below
@jit
def twoD_spectrum_integrant(rfuncs,q_func,omega1,omega2,t_delay):
    step_length=rfuncs[1,0,0]-rfuncs[0,0,0]
    steps_in_t_delay=int(t_delay/step_length)  # NOTE: delay time is rounded to match with steps in the response function
    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs. 
    max_index=int((q_func.shape[0]-steps_in_t_delay)/2.0)

    integrant=np.zeros((max_index,max_index,3),dtype=np.complex_)

    count1=0
    count2=0
    while count1<max_index:
        count2=0
        while count2<max_index:
                integrant[count1,count2,0]=rfuncs[count1,0,0]
                integrant[count1,count2,1]=rfuncs[count2,0,0]
                # rephasing diagrams=2,3. Non-rephasing=1,4. Rephasing has a negative sign, non-rephasing a positive sign. 
      		integrant[count1,count2,2]=np.exp(1j*(rfuncs[count1,0,0]*(omega1)+rfuncs[count2,0,0]*(omega2)))*(np.exp(rfuncs[count1,count2,2])+np.exp(rfuncs[count1,count2,5]))+np.exp(1j*(-rfuncs[count1,0,0]*(omega1)+rfuncs[count2,0,0]*(omega2)))*(np.exp(rfuncs[count1,count2,3])+np.exp(rfuncs[count1,count2,4]))

                count2=count2+1
        count1=count1+1
    return integrant


# integrant of the 3rd order response function in the 3rd order cumulant approximation. Need to include possibility to add pulse shape
# omega_av is already incorporated in the function q. No need to account for the mean in the equation below
@jit
def twoD_spectrum_integrant_3rd(rfuncs,rfuncs_3rd,q_func,omega1,omega2,t_delay):
    step_length=rfuncs[1,0,0]-rfuncs[0,0,0]
    steps_in_t_delay=int(t_delay/step_length)  # NOTE: delay time is rounded to match with steps in the response function
    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs. 
    max_index=int((q_func.shape[0]-steps_in_t_delay)/2.0)

    integrant=np.zeros((max_index,max_index,3),dtype=np.complex_)

    count1=0
    count2=0
    while count1<max_index:
        count2=0
        while count2<max_index:
                integrant[count1,count2,0]=rfuncs[count1,0,0]
                integrant[count1,count2,1]=rfuncs[count2,0,0]
                # rephasing diagrams=2,3. Non-rephasing=1,4. Rephasing has a negative sign, non-rephasing a positive sign. 
		integrant[count1,count2,2]=np.exp(1j*(rfuncs[count1,0,0]*(omega1)+rfuncs[count2,0,0]*(omega2)))*(np.exp(rfuncs[count1,count2,2]+rfuncs_3rd[count1,count2,2])+np.exp(rfuncs[count1,count2,5]+rfuncs_3rd[count1,count2,5]))+np.exp(1j*(-rfuncs[count1,0,0]*(omega1)+rfuncs[count2,0,0]*(omega2)))*(np.exp(rfuncs[count1,count2,3]+rfuncs_3rd[count1,count2,3])+np.exp(rfuncs[count1,count2,4]+rfuncs_3rd[count1,count2,4]))
                count2=count2+1
        count1=count1+1
    return integrant

# FASTER VERSION IMPLEMENTED THAT USES RFUNCS!
# integrant of the 3rd order response function in the 2nd order cumulant approximation. Need to include possibility to add pulse shape
# omega_av is already incorporated in the function q. No need to account for the mean in the equation below
#@jit
#def twoD_spectrum_integrant(q_func,omega1,omega2,t_delay):
#    # first find the effective step_length
#    step_length=q_func[1,0].real-q_func[0,0].real
#    steps_in_t_delay=int(t_delay/step_length)  # NOTE: delay time is rounded to match with steps in the response function
#    # this means that by default, the resolution of delay time in the 2DES spectrum is 1 fs. 
#    max_index=int((q_func.shape[0]-steps_in_t_delay)/2.0)
#
#    integrant=np.zeros((max_index,max_index,3),dtype=np.complex_)
#
#    count1=0
#    count2=0
#    while count1<max_index:
#        count2=0
#        while count2<max_index:
#                integrant[count1,count2,0]=q_func[count1,0]
#                integrant[count1,count2,1]=q_func[count2,0]
#                R1_phase=-q_func[count1,1]-q_func[steps_in_t_delay,1].conjugate()-q_func[count2,1].conjugate()+q_func[count1+steps_in_t_delay,1]+q_func[count2+steps_in_t_delay,1].conjugate()-q_func[count1+count2+steps_in_t_delay,1]
#                R2_phase=-q_func[count1,1].conjugate()+q_func[steps_in_t_delay,1]-q_func[count2,1].conjugate()-q_func[count1+steps_in_t_delay,1].conjugate()-q_func[count2+steps_in_t_delay,1]+q_func[count1+count2+steps_in_t_delay,1].conjugate()
#                R3_phase=-q_func[count1,1].conjugate()+q_func[steps_in_t_delay,1].conjugate()-q_func[count2,1]-q_func[count1+steps_in_t_delay,1].conjugate()-q_func[count2+steps_in_t_delay,1].conjugate()+q_func[count1+count2+steps_in_t_delay,1].conjugate()
#                R4_phase=-q_func[count1,1]-q_func[steps_in_t_delay,1]-q_func[count2,1]+q_func[count1+steps_in_t_delay,1]+q_func[count2+steps_in_t_delay,1]-q_func[count1+count2+steps_in_t_delay,1]

                # stupid test: flip sign of omega1,omega2, Wait: We should use a different sign for the pump pulse omega in the rephasing vs the non-rephasing diagrams.
                # rephasing diagrams=2,3. Non-rephasing=1,4. Rephasing has a negative sign, non-rephasing a positive sign. 
#                integrant[count1,count2,2]=(np.exp(1j*(q_func[count1,0]*(omega1)+q_func[count2,0]*(omega2)))*(np.exp(R1_phase)+np.exp(R4_phase))+np.exp(1j*(-q_func[count1,0]*(omega1)+q_func[count2,0]*(omega2)))*(np.exp(R2_phase)+np.exp(R3_phase)))
#                count2=count2+1
#        count1=count1+1
#    return integrant
