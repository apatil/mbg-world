from numpy import array

# set start and end month slice (python array index of months in block to aggregate over - 0 is earliest month in block)
MonthsSlice = slice(0,12,None)
 
# standard path to utility function directory (used to source generic R functions)
utilFolder = '/root/map_utils/map_utils/'
 
# set path to file containg keys for amazon S3
keyPath = '/root/s3code.txt' 
 
# main input hdf5  file of simulated realisations of f
realisations_path = '/mnt/qrypfpr220708_americas_run_1.9.2008/realizations_mem_100000000_QRYPFPR220708_Americas_Run_1.9.2008_iterations_FILESTARTREL_FILEENDREL.hdf5'

# hdf 5 file containng traces for burden function
burdentrace_path='/mnt/burdentraces/CSE_Asia_and_Americas_scale_0.6_model_exp.hdf5'
 
# location for export of raw extractions (as they come off each distributed instance)
exportPathDistributed_country = '/mnt/distributedoutput_country_am/'
exportPathDistributed_perpixel = '/mnt/distributedoutput_perpixel_am/'
 
# location for export of combined extractions (after distributed files joined by extract_combineDistribExtractions.py)
exportPathCombined_country = '/mnt/combinedoutput_country_am/'
exportPathCombined_perpixel = '/mnt/combinedoutput_perpixel_am/'
 
# input 1km salb raster of unique spatial IDs
salblim1km_path="/mnt/auxiliary_data/salblim1km-e_y-x+_AM.hdf5"
salb1km_path="/mnt/auxiliary_data/salb1km-e2_y-x+_AM.hdf5"
#salblim1km_path="/home/pwg/mbg-world/datafiles/auxiliary_data/salblim1km-e_ken.hdf5"
 
# input 1km and 5km raster of population per cell
grump1km_path="/mnt/auxiliary_data/gr071km_y-x+_AM.hdf5" 
grump5km_path="/mnt/auxiliary_data/gr075km_y-x+_AM.hdf5"
#gr001km_path="/home/pwg/mbg-world/datafiles/auxiliary_data/gr001km_ken.hdf5"
 
# location of 5km hdf5  limits mask
lim5kmbnry_path="/mnt/auxiliary_data/st_mask5km-e_y-x+_AM.hdf5"
#lim5kmbnry_path="/home/pwg/mbg-world/datafiles/auxiliary_data/lim5kmbnry-e_y-x+_ken.hdf5"
 
# files containing list of unique salb IDs in input raster and pixels per ID : generated as ouptut from FUNexamineSalb
examineSalbFolder='examinesalb'
uniqueSalb_path='/mnt/examineSalb/uniqueSalb_am.txt'
uniqueSalbwholecountries_path='/mnt/examineSalb/uniqueSalbwholecountries_am.txt'
pixelN_path='/mnt/examineSalb/pixelN_am.txt'
pixelNwholecountries_path='/mnt/examineSalb/pixelNwholecountries_am.txt'
 
# class definition dictionaries
breaks_MBGW={"BREAKS":[0.,0.05,0.40,1.1],"BREAKNAMES":["lte05","gt05lte40","gt40lte100"],"NAME":"MBGW"}
#breaks_MVI={"BREAKS":[0.,0.05,0.30,0.40,0.60,1.1],"BREAKNAMES":["lte05","gt05lte30","gt30lte40","gt40lte60","gt60lte100"],"NAME":"MVI"}
#breaks_NOORKENYA={"BREAKS":[0.,0.01,0.05,0.4,1.1],"BREAKNAMES":["lte1","gt1lte0","gt5lte40","gt40lte100"],"NAME":"NOORKENYA"}
#breaks_LYSENKO={"BREAKS":[0.,0.1,0.5,0.75,1.1],"BREAKNAMES":["lte10","gt10lte50","gt50lte75","gt75lte100"],"NAME":"LYSENKO"}
#breaks_one={"BREAKS":[0.,1.1],"BREAKNAMES":["all"],"NAME":"ONE"}
#breaksDict={"MBGW":breaks_MBGW,"MVI":breaks_MVI,"LYSENKO":breaks_LYSENKO,"ONE":breaks_one}
 
breaksDict={"MBGW":breaks_MBGW}
#breaksDict={}
 
# ratio of high to low resolution
HiResLowResRatio=5

# how many rows of the 5km PR surface will we deal with at a time in extractSummaries_country()
rowsPerChunk=1
 
# parameter determining number of rows of the coarser grid (5km) to process at a time. Default is 1. (currently unsupported)
rowsInslice5km=5 
 
# what summary stats do we want to generate for meanPR, PAR etc in each country? If none, then set to None
summaryStats={'mean':'mean','SD':'SD','quantiles':array([0,0.025,0.25,0.5,0.75,0.975,1])}
#summaryStats=None
 
 