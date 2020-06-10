#!/usr/bin/env python

from __future__ import print_function

import numpy as np
import scipy.linalg as LA
import ctypes
from numpy.ctypeslib import ndpointer
import glob
import os

#import the c function using ctypes
lib_file = glob.glob('{}/LevinsonTrenchZoharSolve*'.format(os.path.dirname(__file__)))[0] #find the file
LTZSolveC = ctypes.CDLL(lib_file).LevinsonTrenchZoharSolve
#specify the argument and return types
LTZSolveC.argtypes = [ndpointer(ctypes.c_double),ndpointer(ctypes.c_double),\
    ndpointer(ctypes.c_double),ctypes.c_int]
LTZSolveC.restype = ctypes.c_double

#simple wrapper function for solving Toeplitz system in a convenient way
def LTZSolve(a,b,x):
  """
  Ax = b
  a - vector containing the Toeplitz matrix A a->(0-N), 0 being the main diagonal
  b - the input vector (typically the residuals)
  x - the solution space - just an empty matrix, a.size
  """
  #check the vector dimensions are the same
  assert a.size == b.size
  assert a.size == x.size
  
  logdetK = LTZSolveC(a,x,b,a.size)
  return logdetK, x

##########################################################################################

def CovarianceMatrixToeplitz(theta,X,ToeplitzKernel):
  """
  Toeplitz equivelent of the CovarianceMatrix function to construct the Toeplitz matrix
  using the same format - only returns a vector
  
  """
      
  K = ToeplitzKernel(X,X,theta,white_noise=True)
  
  return K

def CovarianceMatrixFullToeplitz(theta,X,ToeplitzKernel):
  """
  Toeplitz equivelent of the CovarianceMatrix function to construct the Toeplitz matrix
  using the same format

  """

  K = LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=True))

  return np.matrix(K)

def CovarianceMatrixBlockToeplitz(theta,X,Y,ToeplitzKernel):
  """
  X - input matrix (q x D) - of training points
  Y - input matrix (n x D) - of predictive points
  theta - hyperparameter array/list
  K - (q x n) covariance matrix block

  Note that this only works when the step sizes are the same for X and Y, toplitz
  usaully 1D!

  """

  a = ToeplitzKernel(X,Y,theta,white_noise=False) #length q
  b = ToeplitzKernel(Y,X,theta,white_noise=False) #length n

  #return q x n matrix block
  K = LA.toeplitz(a,b)

  return np.matrix(K)

def CovarianceMatrixCornerDiagToeplitz(theta,X,ToeplitzKernel,WhiteNoise=True):
  """
  X - input matrix (q x D) - of training points
  theta - hyperparameter array/list
  K - (q x q) covariance matrix corner block - only diagonal terms are returned
    (this function needs optimised as it calculates the whole covariance matrix first...)
  """

  K = np.diag(np.diag(LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=WhiteNoise))))

  return np.matrix(K)

def CovarianceMatrixCornerFullToeplitz(theta,X,ToeplitzKernel,WhiteNoise=True):
  """
  X - input matrix (q x D) - of training points
  theta - hyperparameter array/list
  K - (q x q) covariance matrix corner block
  """

  K = LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=WhiteNoise))

  return np.matrix(K)

##########################################################################################

def CovarianceMatrixFullToeplitzMult(theta,X,ToeplitzKernel,mf,mf_pars,mf_args):
  """
  Toeplitz equivelent of the CovarianceMatrix function to construct the Toeplitz matrix
  using the same format, using multiplicative/affine transform MCMC

  """
  
  #get mean function
  m = mf(mf_pars,mf_args) * np.ones(X.shape[0])
  #full cov matrix
  K = np.mat(LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=False)))

  #calculate the affine transform
  Kp = np.diag(m) * K * np.diag(m)
  
  #Finally add the white noise to the diagonal of the full matrix
  Kp += (np.identity(X.shape[0]) * (theta[-1]**2))

  return np.matrix(Kp)

def CovarianceMatrixBlockToeplitzMult(theta,X,Y,ToeplitzKernel,mf,mf_pars,mf_args_pred,mf_args):
  """
  X - input matrix (q x D) - of training points
  Y - input matrix (n x D) - of predictive points
  theta - hyperparameter array/list
  K - (q x n) covariance matrix block

  Note that this only works when the step sizes are the same for X and Y, toplitz
  usaully 1D!

  """

  a = ToeplitzKernel(X,Y,theta,white_noise=False) #length q
  b = ToeplitzKernel(Y,X,theta,white_noise=False) #length n

  #return q x n matrix block
  K = LA.toeplitz(a,b)
  
  #get mean function
  m = mf(mf_pars,mf_args) * np.ones(Y.shape[0])
  #and predictive mean
  ms = mf(mf_pars,mf_args_pred) * np.ones(X.shape[0])
  #and calculate the affine transform
  Kp = np.diag(ms) * np.matrix(K) * np.diag(m)
  
  return np.matrix(Kp)

def CovarianceMatrixCornerDiagToeplitzMult(theta,X,ToeplitzKernel,mf,mf_pars,mf_args_pred,WhiteNoise=True):
  """
  X - input matrix (q x D) - of training points
  theta - hyperparameter array/list
  K - (q x q) covariance matrix corner block - only diagonal terms are returned
    (this function needs optimised as it calculates the whole covariance matrix first...)
  """
  
  #get covariance matrix
  K = LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=False))
  
  #predictive mean
  ms = mf(mf_pars,mf_args_pred) * np.ones(X.shape[0])

  #get affine transform
  Kp = np.diag(ms) * np.matrix(K) * np.diag(ms)

  #add white noise?
  if WhiteNoise: Kp += (np.identity(X.shape[0]) * (theta[-1]**2))
  
  #diagonalise the cov matrix - needs optimised but not usually a bottleneck...
  Kp = np.diag(np.diag(Kp))

  return np.matrix(Kp)

def CovarianceMatrixCornerFullToeplitzMult(theta,X,ToeplitzKernel,mf,mf_pars,mf_args_pred,WhiteNoise=True):
  """
  X - input matrix (q x D) - of training points
  theta - hyperparameter array/list
  K - (q x q) covariance matrix corner block
  """

  #get normal additive cov matrix
  K = LA.toeplitz(ToeplitzKernel(X,X,theta,white_noise=False))
  
  #predictive mean
  ms = mf(mf_pars,mf_args_pred) * np.ones(X.shape[0])
  #get affine transform
  Kp = np.diag(ms) * np.matrix(K) * np.diag(ms)
  #add white noise?
  if WhiteNoise: Kp += (np.identity(X.shape[0]) * (theta[-1]**2))

  return np.matrix(Kp)

##########################################################################################

#run test
if __name__ == '__main__':
  
  #solve Ax = b, where A is a toeplitz matrix
  # a are the diagonal components of matrix A
  a = np.array([30.,1.,0.3,0.2,0.1,0.2,0.3,15,12,8.])
  b = np.array([1.,1.2,2.3,0.2,1.,2.,1.3,1.,5,.2])
  
  #print the answer from standard/slow inversion
  logdet = np.log(np.linalg.det(LA.toeplitz(a)))
  x = np.mat(LA.toeplitz(a)).I * np.mat(b).T
  print (logdet,"\n",np.mat(x))
  
  #and print the LTZ solution
  logdet,x = LTZSolve(a,b)
  print (logdet,"\n",x)
