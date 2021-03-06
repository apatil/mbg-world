# Author: Anand Patil
# Date: 6 Feb 2009
# License: Creative Commons BY-NC-SA
####################################

#Change
import pymc as pm
import numpy as np
import os
from copy import copy
from correction_factors import age_corr_likelihoods, age_corr_factors, two_ten_factors
from scipy import interpolate as interp
from st_cov_fun import *
import time
import auxiliary_data
# import MAPData
import gc
# from get_covariates import extract_environment_to_hdf5
from tables import ObjectAtom
from generic_mbg import *

__all__ = ['make_model']

continent = 'Africa'
with_stukel = False
chunk = 2

# Prior parameters specified by Simon, Pete and Andy
Af_scale_params = {'mu': -2.54, 'tau': 1.42, 'alpha': -.015}
Af_amp_params = {'mu': .0535, 'tau': 1.79, 'alpha': 3.21}

Am_scale_params = {'mu': -2.58, 'tau': 1.27, 'alpha': .051}
Am_amp_params = {'mu': .607, 'tau': .809, 'alpha': -1.17}

As_scale_params = {'mu': -2.97, 'tau': 1.75, 'alpha': -.143}
As_amp_params = {'mu': .0535, 'tau': 1.79, 'alpha': 3.21}

# Poor man's sparsification
if continent == 'Americas':
    scale_params = Am_scale_params
    amp_params = Am_amp_params
    disttol = 0/6378.
    ttol = 0
elif continent == 'Asia':
    scale_params = As_scale_params
    amp_params = As_amp_params    
    disttol = 5./6378.
    ttol = 1./12
elif continent == 'Africa':
    scale_params = Af_scale_params
    amp_params = Af_amp_params    
    disttol = 5./6378.
    ttol = 1./12
else:
    scale_params = Af_scale_params
    amp_params = Af_amp_params
    disttol = 0./6378.
    ttol = 0.

def make_model(lon,lat,t,covariate_values,pos,neg,lo_age=None,up_age=None,cpus=1,with_stukel=with_stukel, chunk=chunk, disttol=disttol, ttol=ttol):

    if np.any(pos+neg==0):
        where_zero = np.where(pos+neg==0)[0]
        raise ValueError, 'Pos+neg = 0 in the rows (starting from zero):\n %s'%where_zero
        
    C_time = [0.]
    f_time = [0.]
    M_time = [0.]
    
    # =============================
    # = Preprocess data, uniquify =
    # =============================
    
    data_mesh = combine_st_inputs(lon,lat,t)
    if lo_age is None:
        lo_age = 2.*np.ones(data_mesh.shape[0])
    if up_age is None:
        up_age = 10.*np.ones(data_mesh.shape[0])
    
    # Find near spatiotemporal duplicates.
    ui = []
    fi = []
    ti = []
    dx = np.empty(1)
    for i in xrange(data_mesh.shape[0]):
        match=False
        for j in xrange(len(ui)):
            pm.gp.geo_rad(dx, data_mesh[i,:2].reshape((1,2)), data_mesh[ui[j],:2].reshape((1,2)))
            dt = abs(t[ui[j]]-t[i])
            
            if dx[0]<disttol and dt<ttol:
                match=True
                fi.append(j)
                ti[j].append(i)
                break

        if not match:
            fi.append(len(ui))            
            ui.append(i)
            ti.append([i])
    ui=np.array(ui)
    ti = [np.array(tii) for tii in ti]
    fi = np.array(fi)   
    logp_mesh = data_mesh[ui,:]
        
    # =====================
    # = Create PyMC model =
    # =====================
    
    init_OK = False
    while not init_OK:
        M, M_eval = trivial_means(logp_mesh)
    
        # Inverse-gamma prior on nugget variance V.
        tau = pm.Gamma('tau', value=2., alpha=.001, beta=.001/.25)
        V = pm.Lambda('V', lambda tau=tau:1./tau)
    
        vars_to_writeout = ['V', 'm_const', 't_coef']
        
        # Lock down parameters of Stukel's link function to obtain standard logit.
        # These can be freed by removing 'observed' flags, but mixing gets much worse.
        if with_stukel:
            a1 = pm.Uninformative('a1',.5)
            a2 = pm.Uninformative('a2',.8)
        else:
            a1 = pm.Uninformative('a1',0,observed=True)
            a2 = pm.Uninformative('a2',0,observed=True)        

        inc = pm.CircVonMises('inc', 0, 0)

        # Use a uniform prior on sqrt ecc (sqrt ???). Using a uniform prior on ecc itself put too little
        # probability mass on appreciable levels of anisotropy.
        sqrt_ecc = pm.Uniform('sqrt_ecc', value=.1, lower=0., upper=1.)
        ecc = pm.Lambda('ecc', lambda s=sqrt_ecc: s**2)

        # Subjective skew-normal prior on amp (the partial sill, tau) in log-space.
        # Parameters are passed in in manual_MCMC_supervisor.
        log_amp = pm.SkewNormal('log_amp',value=amp_params['mu'],**amp_params)
        amp = pm.Lambda('amp', lambda log_amp = log_amp: np.exp(log_amp))

        # Subjective skew-normal prior on scale (the range, phi_x) in log-space.
        log_scale = pm.SkewNormal('log_scale',value=-1,**scale_params)
        scale = pm.Lambda('scale', lambda log_scale = log_scale: np.exp(log_scale))

        # Exponential prior on the temporal scale/range, phi_t. Standard one-over-x
        # doesn't work bc data aren't strong enough to prevent collapse to zero.
        scale_t = pm.Exponential('scale_t', .1,value=.1)

        # Uniform prior on limiting correlation far in the future or past.
        t_lim_corr = pm.Uniform('t_lim_corr',0,1,value=.01)

        # # Uniform prior on sinusoidal fraction in temporal variogram
        sin_frac = pm.Uniform('sin_frac',0,1,value=.01)
        
        vars_to_writeout.extend(['inc','ecc','amp','scale','scale_t','t_lim_corr','sin_frac'])
    
        # Collect stochastic variables with observed=False for the adaptive Metropolis stepper.
        trial_stochs = [tau, a1, a2, sqrt_ecc, log_amp, log_scale, scale_t, t_lim_corr, sin_frac]
        nondata_stochs = []
        for stoch in trial_stochs:
            if not stoch.observed:
                nondata_stochs.append(stoch)

        # Create covariance and MV-normal F if model is spatial.   
        try:
            # A constraint on the space-time covariance parameters that ensures temporal correlations are 
            # always between -1 and 1.
            @pm.potential
            def st_constraint(sd=.5, sf=sin_frac, tlc=t_lim_corr):    
                if -sd >= 1./(-sf*(1-tlc)+tlc):
                    return -np.Inf
                else:
                    return 0.

            # A Deterministic valued as a Covariance object. Uses covariance my_st, defined above. 
            @pm.deterministic
            def C(amp=amp,scale=scale,inc=inc,ecc=ecc,scale_t=scale_t, t_lim_corr=t_lim_corr, sin_frac=sin_frac):
                return pm.gp.FullRankCovariance(my_st, amp=amp, scale=scale, inc=inc, ecc=ecc,st=scale_t, sd=.5,
                                                tlc=t_lim_corr, sf = sin_frac)

            covariate_dict, C_eval = cd_and_C_eval(covariate_values, C, data_mesh, ui)

            # The field evaluated at the uniquified data locations
            f = pm.MvNormalCov('f',M_eval,C_eval,value=M_eval.value)
            
            # The field evaluated at all the data locations
            @pm.deterministic(trace=False)
            def f_eval(f=f):
                return f[fi]
            
            init_OK = True
        except pm.ZeroProbability, msg:
            print 'Trying again: %s'%msg
            init_OK = False
            gc.collect()

    # ===========================
    # = Create likelihood layer =
    # ===========================
        
    eps_p_f_list = []
    N_pos_list = []
    
    # Obtain the spline representation of the log of the Monte Carlo-integrated 
    # likelihood function at each datapoint. The nodes are at .01,.02,...,.98,.99 .
    junk, splreps = age_corr_likelihoods(lo_age, up_age, pos, neg, 10000, np.arange(.01,1.,.01))
    for i in xrange(len(splreps)):
        splreps[i] = list(splreps[i])

    # Don't worry, these are just reasonable initial values...
    if with_stukel:
        val_now = pm.stukel_logit((pos+1.)/(pos+neg+2.), a1.value, a2.value)
    else:
        val_now = pm.logit((pos+1.)/(pos+neg+2.))
    
    if data_mesh.shape[0] % chunk == 0:
        additional_index = 0
    else:
        additional_index = 1
    
    for i in xrange(0,data_mesh.shape[0] / chunk + additional_index):
        
        this_slice = slice(chunk*i, min((i+1)*chunk, data_mesh.shape[0]))

        # epsilon plus f, given f.
        @pm.stochastic(trace=False, dtype=np.float)
        def eps_p_f_now(value=val_now[this_slice], f=f_eval, V=V, this_slice = this_slice):
            return pm.normal_like(value, f[this_slice], 1./V)
        eps_p_f_now.__name__ = "eps_p_f%i"%i
        eps_p_f_list.append(eps_p_f_now)
        
        # The number positive: the data. Uses the spline interpolations of the likelihood
        # functions to compute them.
        try:
            @pm.data
            @pm.stochastic(dtype=np.int)
            def N_pos_now(value = pm.utils.round_array(pos[this_slice]), splrep = splreps[this_slice], eps_p_f = eps_p_f_now, a1=a1, a2=a2):
                p_now = pm.flib.stukel_invlogit(eps_p_f, a1, a2)
                out = 0.
                for i in xrange(len(value)):
                    out += interp.splev(p_now[i], splrep[i])
                return out
        except ValueError:
            raise ValueError, 'Log-likelihood is nan at chunk %i'%i

    # Combine the eps_p_f values. This is stupid, I should have just used a Container.
    # I guess this makes it easier to keep traces.
    @pm.deterministic
    def eps_p_f(eps_p_f_list=eps_p_f_list):
        out = np.zeros(data_mesh.shape[0])
        for i in xrange(len(eps_p_f_list)):
            out[chunk*i:min((i+1)*chunk, data_mesh.shape[0])] = eps_p_f_list[i]
        return out
    
    covariate_dicts = {'eps_p_f':covariate_dict}

    out = locals()
    for v in covariate_dict.iteritems():
        out[v[0]] = v[1][0]
    return out
    
