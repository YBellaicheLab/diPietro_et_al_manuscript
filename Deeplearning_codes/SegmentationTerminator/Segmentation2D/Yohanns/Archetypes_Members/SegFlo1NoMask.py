## StarDistSeedsV2_NoMask.py

#!/usr/bin/env python
# coding: utf-8


from __future__ import print_function, unicode_literals, absolute_import, division

#In[0]:

import os
import time
TriggerName = '/home/sancere/NextonDisk_1/TimeTrigger/TTTTT'
TimeCount = 0
TimeThreshold = 3600*0
while os.path.exists(TriggerName) == False and TimeCount < TimeThreshold :
   time.sleep(60*5)
   TimeCount = TimeCount + 60*5


# In[1]:


import sys
import os
sys.path.append('/home/sancere/anaconda3/envs/tensorflowGPU/lib/python3.6/site-packages/')
sys.path.append('../../Terminator/')


#To run the prediction on the GPU, else comment out this line to use the CPU
os.environ["CUDA_VISIBLE_DEVICES"]="1"


import csbdeep
from csbdeep.utils.tf import limit_gpu_memory
from skimage.filters import threshold_otsu
import numpy as np
import matplotlib.pyplot as plt
#get_ipython().run_line_magic('matplotlib', 'inline')
#get_ipython().run_line_magic('config', "InlineBackend.figure_format = 'retina'")
#from IPython.display import clear_output
import glob
import cv2
from tifffile import imread
import tqdm
from csbdeep.utils import Path, normalize
from stardist import random_label_cmap, _draw_polygons,dist_to_coord
from stardist.models import StarDist2D
from TerminatorUtils.helpers import normalizeFloat, OtsuThreshold2D, save_8bit_tiff_imagej_compatible, save_16bit_tiff_imagej_compatible,Integer_to_border,SeedStarDistWatershed
from TerminatorUtils.helpers import Prob_to_Binary, zero_pad, WatershedwithoutMask
from TerminatorUtils.helpers import save_tiff_imagej_compatible
from csbdeep.models import Config, CARE
np.random.seed(6)
lbl_cmap = random_label_cmap()

from skimage.morphology import remove_small_objects
from skimage.morphology import skeletonize
import time 


# **Movie 1 + model importation**

# In[2]:


basedir = '/run/user/1000/gvfs/smb-share:server=isiserver.curie.net,share=u934/equipe_bellaiche/mf_di-pietro/Florencia_to_Lucas/DegrFP-Data_for_segmentation-correction_or_measurement/27-8-8hr_after/Regions_of_interests_cropped/ToProject/Projected'

basedir_StardistWater_NoMask = basedir + '/StarWat_NoMask/'
basedir_StardistWater_NoMask_RTGPipeline =  basedir +  '/StarWat_NoMask_RTGPipeline/'

Model_Dir = '/run/media/sancere/DATA/Lucas_Model_to_use/Segmentation/'     


# In[3]:


StardistModelName = 'DrosophilaSegmentationSmartSeedsMatureMacroElongatedLargePatchBoris_29Jan2021_Grid11_PreviousHP'

modelstar = StarDist2D(config = None, name = StardistModelName, basedir = Model_Dir)
Model_is_for_Bin2 = True


# In[5]:


Path(basedir_StardistWater_NoMask).mkdir(exist_ok = True)
Raw_path = os.path.join(basedir, '*tif') #tif or TIF be careful
axis_norm = (0,1)   # normalize channels independently
axes = 'XY'
filesRaw = glob.glob(Raw_path)
filesRaw.sort


# In[6]:


for fname in filesRaw:
 
    if os.path.exists((basedir_StardistWater_NoMask + 'StarWat_NoMask_' + os.path.basename(os.path.splitext(fname)[0]))) == False :
        
            # Name = os.path.basename(os.path.splitext(fname)[0])
            x = imread(fname)
            y = normalizeFloat(x,1,99.8, axis = axis_norm)
            originalX = x.shape[0]
            originalY = x.shape[1]
        
            #zero pad (Never do 8bit conversion when applying prediction on an image, only float32)
            y = zero_pad(y, 32, 32)
            print('Processing file', fname)              
           
            #Stardist, label image, details, probability map, distance map 
            segmentationImage, details = modelstar.predict_instances(y)
            prob, dist = modelstar.predict(y)
            grid = modelstar.config.grid
            prob = cv2.resize(prob,  dsize=(prob.shape[1] * grid[1],prob.shape[0] * grid[0]))
            
            
            #Seeds from Stardist + Whatershed, segmentation on probability map 
            Watershed, markers = WatershedwithoutMask(prob, segmentationImage.astype('uint16'), modelstar.config.grid)   
                                                                   
            
            #Convert Integer image to binary
            Binary_Watershed = Integer_to_border(Watershed[:originalX, :originalY])
           
            
            #Skeletonization and deletion of non closed cells. Has to be done AFTER logical and operation 
            z = Binary_Watershed 
            z = skeletonize(z) 
            z = np.float32(z)
            z2 = z.copy()
            mask = np.zeros((np.array(z.shape)+2), np.uint8)
            cv2.floodFill(z, mask, (0,0), (255))
            z = cv2.erode(z, np.ones((3,3)))
            z = cv2.bitwise_not(z)
            z = cv2.bitwise_and(z,z2)
            StardistWater_NoMask = z 
    
            #Save different method segmentations
            save_8bit_tiff_imagej_compatible((basedir_StardistWater_NoMask + 'StarWat_NoMask_' + os.path.basename(os.path.splitext(fname)[0]) ) , StardistWater_NoMask, axes)


# In[7]:


import png

Path(basedir_StardistWater_NoMask_RTGPipeline).mkdir(exist_ok = True)

Raw_path_2 = os.path.join(basedir_StardistWater_NoMask, '*') #tif or TIF be careful
axis_norm = (0,1)   # normalize channels independently
axes = 'XY'
filesRaw_2 = glob.glob(Raw_path_2)

    
for fname in filesRaw_2:
    z = imread(fname)
    z = 255 * z
    z = cv2.bitwise_not(z)
    name = str(os.path.basename(os.path.splitext(fname)[0])).rstrip(".tif")
    png.from_array(z, mode="L").save(basedir_StardistWater_NoMask_RTGPipeline + name.replace("StarWat_NoMask_",'seg_') + '.png') 




# In[12]:



from csbdeep.utils import Path

TriggerName = '/home/sancere/NextonDisk_1/TimeTrigger/TTSegFlo1NoMask'
Path(TriggerName).mkdir(exist_ok = True)
