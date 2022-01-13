"""Example of PAM-4 operation with FFE"""

import serdespy as sdp
import skrf as rf
import numpy as np
import scipy as sp
import matplotlib.pyplot as plt

#define network
network = rf.Network('./DPO_4in_Meg7_THRU.s4p')

#set up port definition of network
port_def = np.array([[0, 1],[2, 3]])

#get TF of differential network
H,f,h,t = sdp.four_port_to_diff(network,port_def)

#Nyquist frequency
nyquist_f = 26.56e9/2

#Period of clock at nyquist frequency
nyquist_T = 1/nyquist_f

#desired number of samples per clock period
oversampling_ratio = 64

#timesteps per bit
steps_per_symbol = int(round(oversampling_ratio/2))

#Desired time-step
t_d = nyquist_T/oversampling_ratio

#compute response of zero-padded TF
H, f, h, t = sdp.zero_pad(H,f,t_d)

#%%create TX waveform

#compute input data using PRQS10
data_in = sdp.prqs10(1)

#take first 10k bits for faster simulation
data_in = data_in[:10000]

#define voltage levels for 0 and 1 bits
voltage_levels = np.array([-0.75, -0.25, 0.25, 0.75])

#convert data_in to time domain signal
signal_in = sdp.pam4_input(steps_per_symbol, data_in, voltage_levels)

#%%compute channel response to signal_in

h_zero_pad = np.hstack((h, np.zeros(signal_in.size-h.size)))

#do convolution to get differential channel response
signal_output = sp.signal.fftconvolve(h_zero_pad, signal_in)
signal_output = signal_output[0:h_zero_pad.size]

#define signal object for this signal, crop out first bit of signal which is 0 due to channel latency
sig = sdp.Receiver(signal_output[5000:], steps_per_symbol, t[1], voltage_levels)


#%% measure precursor and postcursor from pulse response

n_taps_post = 2
n_taps_pre = 1
n_taps = n_taps_post+n_taps_pre+1

pulse_input = np.ones(steps_per_symbol)

pulse_response = np.convolve(h, pulse_input,mode='same')

channel_coefficients =  sdp.channel_coefficients(pulse_response, t, steps_per_symbol, n_taps_pre, n_taps_post) 

#%% solve for zero-forcing FFE tap weights
    
A = np.zeros((n_taps,n_taps))

for i in range(n_taps):
    A += np.diag(np.ones(n_taps-abs(i-n_taps_pre))*channel_coefficients[i],(n_taps_pre-i) )

c = np.zeros((n_taps,1))
c[n_taps_pre] = 1

b = np.linalg.inv(A)@c

b = b/np.sum(abs(b))

ffe_tap_weights = b.T[0]
#%% plot eye diagrams with FFE 

#no FFE
sig.reset()
sdp.simple_eye(sig.signal, sig.steps_per_symbol*2, 1000, sig.t_step, "PAM-4 Eye, 53 Gbit/s")

#with FFE and computed weights
sig.reset()
sig.FFE(ffe_tap_weights,1)
sdp.simple_eye(sig.signal, sig.steps_per_symbol*2, 1000, sig.t_step, "PAM-4 Eye, 53 Gbit/s with Zero-Forcing FFE (1 Precursor Tap, 2 Postcursor Taps)")