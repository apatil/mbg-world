from numpy.testing import *
import mbgw
from mbgw import EP
import nose,  warnings
from numpy import *
from pymc import normal_like
from scipy import integrate

n_digits = 4
iter = 10000
tol = .0001

def geto_observe(M, C, V, val):
    sig = linalg.cholesky(C+diag(V))
    C_sig = linalg.solve(sig, C)
    C_post = C - dot(C_sig.T, C_sig)
    M_post = M + dot(linalg.solve(sig.T, C_sig).T, val-M)
    return M_post, C_post

def standard_EP_t(M_pri, C_pri, nugs, obs_mus, obs_Vs, mu_guess=None, V_guess=None):    
    N = len(M_pri)
    lps = [lambda x, m=obs_mus[i], v=obs_Vs[i]: array([normal_like(xi, m, 1./v) for xi in x]) for i in xrange(N)]

    # print obs_mus, obs_Vs
    # Independently observe with the inferred 'mean' and 'variance'.
    M_post, C_post = geto_observe(M_pri, C_pri, obs_Vs + nugs, obs_mus)
    # print M_post
    # print C_post
    # print

    # Do EP algorithm
    E = EP.EP(M_pri, C_pri, lps, nugs, mu_guess, V_guess)
    E.fit(iter, tol=tol)        
    
    # Make sure the observing arithmetic is going right.
    assert_almost_equal(M_post, E.M, n_digits)
    assert_almost_equal(C_post, E.C, n_digits)
    
    # Make sure it's correctly finding mu and V
    assert_almost_equal(E.mu, obs_mus, n_digits)
    assert_almost_equal(E.V*0+1., (obs_Vs+nugs)/(E.V+nugs), n_digits)
        
    return E, M_post, C_post
    
# class test_mbgw(TestCase):
class test_EP(object):
    
    N = 3
    M_pri = random.normal(size=N)
    sig_pri = random.normal(size=(N, N))
    C_pri = dot(sig_pri.T, sig_pri)
    # print M_pri, '\n', C_pri
    
    def test_expectations(self):
        f = lambda x: normal_like(x, -pi, 1./2)
        lo, hi = EP.estimate_envelopes(f, -pi, sqrt(10), 13., ftol=.000000001)
        
        funs=[lambda x:x, lambda x:x**2]
        
        x = linspace(lo, hi, 1000)
        dx=x[2]-x[1]
        post_vec = exp([f(xi) for xi in x])

        p = integrate.simps(post_vec, dx=dx)
        
        # Return E_pri [like_fn(x)] and the posterior expectations of funs(x).        
        moments = []
        for fun in funs:
            moments.append(integrate.simps(post_vec * fun(x), dx=dx) / p)
        
        # print moments[1]-moments[0]**2-2
        assert_almost_equal(moments[0], -pi, 3)
        assert_almost_equal(moments[1]-moments[0]**2, 2, 2)
            
    def test_low_V(self):
        
        # Moderate-sized positive variance and nugget.
        obs_Vs = random.normal(size=self.N)**2 * .1
        nugs = random.normal(size=self.N)**2 * .3
        
        # 'mean' and log-probability functions.
        obs_mus = random.normal(size=self.N)
        
        standard_EP_t(self.M_pri, self.C_pri, nugs, obs_mus, obs_Vs, obs_mus, obs_Vs)
        
    def test_neg_V(self):
        # Moderate-sized negative variance and nugget.
        obs_Vs = -diag(self.C_pri)*.2
        nugs = -diag(self.C_pri)*.2
        
        # 'mean' and log-probability functions.
        obs_mus = random.normal(size=self.N)
        
        standard_EP_t(self.M_pri, self.C_pri, nugs, obs_mus, obs_Vs)
        
    def test_hi_V(self):
        # High variance and nugget.
        obs_Vs = ones(self.N)*100000
        nugs = ones(self.N)*100000
        
        # 'mean' and log-probability functions.
        obs_mus = random.normal(size=self.N)
        
        E, M_post, C_post = standard_EP_t(self.M_pri, self.C_pri, nugs, obs_mus, obs_Vs)
        
        assert_almost_equal(M_post, self.M_pri, n_digits)
        assert_almost_equal(C_post, self.C_pri, n_digits-2)
        
    def test_tiny_V(self):
        # Moderate-sized positive variance and nugget.
        obs_Vs = random.normal(size=self.N)**2 * .00001
        nugs = random.normal(size=self.N)**2 * .00003
        
        # 'mean' and log-probability functions.
        obs_mus = random.normal(size=self.N)
        
        standard_EP_t(self.M_pri, self.C_pri, nugs, obs_mus, obs_Vs)
        
if __name__ == '__main__':
    tester = test_EP()
    tester.test_expectations()
    tester.test_low_V()
    tester.test_hi_V()
    # tester.test_neg_V()
    tester.test_tiny_V()
    # nose.runmodule()

