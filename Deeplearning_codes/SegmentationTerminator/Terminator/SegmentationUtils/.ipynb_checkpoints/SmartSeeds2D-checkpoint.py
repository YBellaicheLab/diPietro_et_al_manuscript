#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Sep 30 14:38:04 2019

@author: aimachine
"""

import numpy as np
from SegmentationUtils import helpers
from keras import callbacks
from keras.layers import Flatten
import os
import glob
from tifffile import imread, imwrite
from csbdeep.utils import axes_dict
from scipy.ndimage.morphology import  binary_dilation
from scipy.ndimage.morphology import binary_fill_holes
from scipy.ndimage.measurements import find_objects
from keras import backend as K
import matplotlib.pyplot as plt
from csbdeep.data import RawData, create_patches
from csbdeep.io import load_training_data
from csbdeep.utils import axes_dict
from csbdeep.models import Config, CARE
from skimage.measure import label
from csbdeep.utils import Path, normalize
#from IPython.display import clear_output
from keras import optimizers
from stardist.models import Config3D, StarDist3D, StarDistData3D
from sklearn.utils import class_weight
from keras.preprocessing.image import ImageDataGenerator
from sklearn.utils.class_weight import compute_class_weight
from csbdeep.io import load_training_data
from scipy.ndimage.morphology import binary_fill_holes
from tqdm import tqdm
from csbdeep.utils import Path, normalize
import sys
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path

try:
    import tempfile
    tempfile.TemporaryDirectory

except (ImportError,AttributeError):
    from backports import tempfile
    
    
def _raise(e):
    raise e

def _fill_label_holes(lbl_img, **kwargs):
    lbl_img_filled = np.zeros_like(lbl_img)
    for l in (set(np.unique(lbl_img)) - set([0])):
        mask = lbl_img==l
        mask_filled = binary_fill_holes(mask,**kwargs)
        lbl_img_filled[mask_filled] = l
    return lbl_img_filled
def fill_label_holes(lbl_img, **kwargs):
    """Fill small holes in label image."""
    # TODO: refactor 'fill_label_holes' and 'edt_prob' to share code
    def grow(sl,interior):
        return tuple(slice(s.start-int(w[0]),s.stop+int(w[1])) for s,w in zip(sl,interior))
    def shrink(interior):
        return tuple(slice(int(w[0]),(-1 if w[1] else None)) for w in interior)
    objects = find_objects(lbl_img)
    lbl_img_filled = np.zeros_like(lbl_img)
    for i,sl in enumerate(objects,1):
        if sl is None: continue
        interior = [(s.start>0,s.stop<sz) for s,sz in zip(sl,lbl_img.shape)]
        shrink_slice = shrink(interior)
        grown_mask = lbl_img[grow(sl,interior)]==i
        mask_filled = binary_fill_holes(grown_mask,**kwargs)[shrink_slice]
        lbl_img_filled[sl][mask_filled] = i
    return lbl_img_filled


def dilate_label_holes(lbl_img, iterations):
    lbl_img_filled = np.zeros_like(lbl_img)
    for l in (range(np.min(lbl_img), np.max(lbl_img) + 1)):
        mask = lbl_img==l
        mask_filled = binary_dilation(mask,iterations = iterations)
        lbl_img_filled[mask_filled] = l
    return lbl_img_filled    
    
class SmartSeeds2D(object):






     def __init__(self, BaseDir, NPZfilename, model_name, model_dir, n_patches_per_image, GenerateNPZ = True,copy_model_dir = None, PatchX=256, PatchY=256,  use_gpu = True,unet_n_first = 48,  batch_size = 4, depth = 3, kern_size = 7, n_rays = 16, epochs = 400, learning_rate = 0.0001):
         
         
         
         
         self.NPZfilename = NPZfilename
         self.BaseDir = BaseDir
         self.model_dir = model_dir
         self.copy_model_dir = copy_model_dir
         self.model_name = model_name
         self.GenerateNPZ = GenerateNPZ
         self.epochs = epochs
         self.learning_rate = learning_rate
         self.depth = depth
         self.n_rays = n_rays
         self.kern_size = kern_size
         self.PatchX = PatchX
         self.PatchY = PatchY
         self.batch_size = batch_size
         self.use_gpu = use_gpu
         self.unet_n_first = unet_n_first 
         self.n_patches_per_image =  n_patches_per_image
        
         
         
         #Load training and validation data
         self.Train()
        
         
         
     def Train(self):
         
                    X_train = []
                    Y_train = []
                    
                    Raw = sorted(glob.glob(self.BaseDir + '/DenoisedRaw/' + '*.tif'))
                    Path(self.BaseDir + '/BinaryMask/').mkdir(exist_ok=True)
                    Path(self.BaseDir + '/RealMask/').mkdir(exist_ok=True)
                    RealMask = sorted(glob.glob(self.BaseDir + '/RealMask/' + '*.tif'))
                    
                    
                    print('Instance segmentation masks:', len(RealMask))
                    if len(RealMask)== 0:
                        
                        print('Making labels')
                        Mask = sorted(glob.glob(self.BaseDir + '/BinaryMask/' + '*.tif'))
                        
                        for fname in Mask:
                    
                           image = imread(fname)
                    
                           Name = os.path.basename(os.path.splitext(fname)[0])
                    
                           Binaryimage = label(image) 
                    
                           imwrite((self.BaseDir + '/RealMask/' + Name + '.tif'), Binaryimage)
                           
                
                    Mask = sorted(glob.glob(self.BaseDir + '/BinaryMask/' + '*.tif'))
                    print('Semantic segmentation masks:', len(Mask))
                    if len(Mask) == 0:
                        print('Generating Binary images')
               
                               
                        RealfilesMask = sorted(glob.glob(self.BaseDir + '/RealMask/' + '*tif'))  
                
                
                        for fname in RealfilesMask:
                    
                            image = imread(fname)
                    
                            Name = os.path.basename(os.path.splitext(fname)[0])
                    
                            Binaryimage = image > 0
                    
                            imwrite((self.BaseDir + '/BinaryMask/' + Name + '.tif'), Binaryimage)
                    
                    
                    
                    
                    if self.GenerateNPZ:
                        
                      raw_data = RawData.from_folder (
                      basepath    = self.BaseDir,
                      source_dirs = ['DenoisedRaw/'],
                      target_dir  = 'BinaryMask/',
                      axes        = 'YX',
                       )
                    
                      X, Y, XY_axes = create_patches (
                      raw_data            = raw_data,
                      patch_size          = (self.PatchY,self.PatchX),
                      n_patches_per_image = self.n_patches_per_image,
                      save_file           = self.BaseDir + self.NPZfilename + '.npz',
                      )
                    
                  


                    print('Training StarDistModel model with unet backbone')
         
                    axis_norm = (0,1)   # normalize channels independently
                    X_train = list(map(imread,Raw))
                    Y_train = list(map(imread,RealMask))
                    self.Y = [fill_label_holes(y) for y in tqdm(Y_train)]
                    self.X = [normalize((x),1,99.8,axis=axis_norm) for x in tqdm(X_train)]
                    
                     

                    
                    assert len(self.X) > 1, "not enough training data"
                    print(len(self.X))
                    rng = np.random.RandomState(42)
                    ind = rng.permutation(len(self.X))
                    n_val = max(1, int(round(0.15 * len(ind))))
                    ind_train, ind_val = ind[:-n_val], ind[-n_val:]
                    self.X_val, self.Y_val = [self.X[i] for i in ind_val]  , [self.Y[i] for i in ind_val]
                    self.X_trn, self.Y_trn = [self.X[i] for i in ind_train], [self.Y[i] for i in ind_train] 
                    print('number of images: %3d' % len(self.X))
                    print('- training:       %3d' % len(self.X_trn))
                    print('- validation:     %3d' % len(self.X_val))
                      
      
                    print(Config2D.__doc__)
                    
                    conf = Config2D (
                      n_rays       = self.n_rays,
                      train_epochs = self.epochs,
                      train_learning_rate = self.learning_rate,
                      unet_n_depth = self.depth ,
                      train_patch_size = (self.PatchY,self.PatchX),
                      n_channel_in = 1,
                      train_checkpoint= self.model_dir + self.model_name +'.h5',
                      grid         = (2,2),
                      train_loss_weights=(1, 0.05),
                      use_gpu      = self.use_gpu
                      
                      )
                    print(conf)
                    vars(conf)
                 
                
                    Starmodel = StarDist2D(conf, name=self.model_name, basedir=self.model_dir)
                    if self.copy_model_dir is not None:   
                      if os.path.exists(self.copy_model_dir + self.copy_model_name + '/' + 'weights_now.h5') and os.path.exists(self.model_dir + self.model_name + '/' + 'weights_now.h5') == False:
                         print('Loading copy model')
                         Starmodel.load_weights(self.copy_model_dir + self.copy_model_name + '/' + 'weights_now.h5')   
                    
                    if os.path.exists(self.model_dir + self.model_name + '/' + 'weights_now.h5'):
                        print('Loading checkpoint model')
                        Starmodel.load_weights(self.model_dir + self.model_name + '/' + 'weights_now.h5')
                 
                    Starmodel.train(self.X_trn, (self.Y_trn), validation_data=(self.X_val,(self.Y_val)), epochs = self.epochs)
                    Starmodel.optimize_thresholds(self.X_val, self.Y_val)
                   # Training UNET model
                    
                    print('Training UNET model')
                    load_path = self.BaseDir + self.NPZfilename + '.npz'

                    (X,Y), (X_val,Y_val), axes = load_training_data(load_path, validation_split=0.1, verbose=True)
                    c = axes_dict(axes)['C']
                    n_channel_in, n_channel_out = X.shape[c], Y.shape[c]
                    
                    config = Config(axes, n_channel_in, n_channel_out, unet_n_depth= self.depth,train_epochs= self.epochs, train_batch_size = self.batch_size, unet_kern_size = self.kern_size,unet_n_first = self.unet_n_first, train_learning_rate = self.learning_rate, train_reduce_lr={'patience': 5, 'factor': 0.5})
                    print(config)
                    vars(config)
                    
                    model = CARE(config , name = 'UNET' + self.model_name, basedir = self.model_dir)
                    
                    if self.copy_model_dir is not None:   
                      if os.path.exists(self.copy_model_dir + 'UNET' + self.copy_model_name + '/' + 'weights_now.h5') and os.path.exists(self.model_dir + 'UNET' + self.model_name + '/' + 'weights_now.h5') == False:
                         print('Loading copy model')
                         model.load_weights(self.copy_model_dir + 'UNET' + self.copy_model_name + '/' + 'weights_now.h5')   
                    
                    if os.path.exists(self.model_dir + 'UNET' + self.model_name + '/' + 'weights_now.h5'):
                        print('Loading checkpoint model')
                        model.load_weights(self.model_dir + 'UNET' + self.model_name + '/' + 'weights_now.h5')
                    
                    history = model.train(X,Y, validation_data=(X_val,Y_val))
                 
                 
         
         
         
         
         
         
         
         
         