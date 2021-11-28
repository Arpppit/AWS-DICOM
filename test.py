import os 
import subprocess
import sys

dataset_folder = '/home/arppit/Pictures/dataset/'
files = os.listdir(dataset_folder)
for f in files:
    dicoms = os.listdir(f'/home/arppit/Pictures/dataset/{f}')
    for dicom in dicoms:
        os.system(f'python3 -m pynetdicom storescu 35.170.78.135 11112 {dataset_folder}/{f}/{dicom} -v -cx')
        #print(dicom)

    
