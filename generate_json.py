import matplotlib.image
from json import dumps
from pprint import pprint
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import argparse
from skimage import color
import os, sys
import textwrap
import numpy as np
from pathlib import Path
import pydicom
import json    
import base64   
import sqlite3
import traceback
import pause 
import json
import time
from datetime import datetime 
import logging
import glob
import requests
import dicom2nifti
import SimpleITK as sitk
from PIL import Image, ImageDraw
from pydicom.filewriter import write_file_meta_info
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelGet,
    CTImageStorage
)


def ExtractNodulesFromJson(input, output:Path,radlex: bool, dataset_folder,thickness_fr_of_ref_folder, olay_folder): 
  # try:
  start_key=0 
  nested_dict={}
  dict1={}
  #need all ct slices to convert to json
  print(dataset_folder,thickness_fr_of_ref_folder,olay_folder,output)
  nii_dir = '/'.join(dataset_folder.split('/')[:-1])
  #json file of SR is read into 
  #ds=  pydicom.dataset.Dataset.from_json(json.load(open(input)))
  ds = input
  dds=ds.to_json_dict() 
  #dict1['Frame of reference UID']=dds['0040A730']['Value'][3]['0040A730']['Value'][0]['0040A730']['Value'][3]['30060024']['Value'][0]
  dict1[ds[0x0008,0x0016].name]=ds[0x0008,0x0016].value
  dict1[ds[0x0008,0x0020].name]=ds[0x0008,0x0020].value
  dict1[ds[0x0020,0x0011].name]=ds[0x0020,0x0011].value
  dict1[ds[0x0008,0x0070].name]=ds[0x0008,0x0070].value
  dict1[ds[0x0008,0x103e].name]=ds[0x0008,0x103e].value
  dict1[ds[0x0008,0x1090].name]=ds[0x0008,0x1090].value
  dict1[ds[0x0010,0x0010].name]=str(ds[0x0010,0x0010].value)
  dict1[ds[0x0010,0x0020].name]=ds[0x0010,0x0020].value
  dict1[ds[0x0010,0x0030].name]=ds[0x0010,0x0030].value
  dict1[ds[0x0010,0x0040].name]=ds[0x0010,0x0040].value
  flag =1
  try:
    
  # select any CT image for reference
    reference_file = os.listdir(thickness_fr_of_ref_folder)
    fpath=str(thickness_fr_of_ref_folder)+'/'+str(reference_file[0])
    dss=pydicom.dcmread(fpath)
    #print('reading ...')
    dicom2nifti.convert_directory(thickness_fr_of_ref_folder, nii_dir, compression=True, reorient=True)
    fil=glob.glob(nii_dir+'/'+'*.nii.gz')
  
    #print(os.path.isfile(fil))
    print('fil',fil, 'args',nii_dir+'/'+'*.nii.gz', os.path.isfile(fil[0]))
    nii_image=sitk.ReadImage(fil[0])
    #print('done reading')
    #reader = sitk.ImageSeriesReader()
    #dicom_names = reader.GetGDCMSeriesFileNames(thickness_fr_of_ref_folder)
    #reader.SetFileNames(dicom_names)
    #nii_image = reader.Execute()

    dict1[dss[0x0018,0x0050].name]=dss[0x0018,0x0050].value
    dict1[dss[0x0020,0x0052].name]=dss[0x0020,0x0052].value

    for i in range(len(dds['0040A730']['Value'])):
      if (dds['0040A730']['Value'][i]['0040A043']['Value'][0]['00080104']['Value'][0]!='Image Measurements'):
        start_key+=1
    thumbnail_files = os.listdir(dataset_folder)
    # if no corresponding thumbnail files are present just work with what we have 
    if len(thumbnail_files) < len(dds['0040A730']['Value'][start_key]['0040A730']['Value']):
      logging.error(f'[ERROR] Cannot find corresponding CT images... only {thumbnail_files} are present')
      rem = len(dds['0040A730']['Value'][start_key]['0040A730']['Value']) - len(thumbnail_files)
      # if len(thumbnail_files)!=0:
      #   thumbnail_files+=[thumbnail_files[0]]*rem
    for i in range(len(dds['0040A730']['Value'][start_key]['0040A730']['Value'])):

      input1 = dataset_folder+'/'+ thumbnail_files[i]
      dss1=pydicom.dcmread(input1)
      
      k=0
      dict={}
      #temp = []
      #GET required values 
      for j in range(len(dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'])):
        subdict=dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'][j]
        attr=subdict['0040A043']['Value'][0]['00080104']['Value'][0]
      
        k+=1
        if attr=='Lesion Review Status':
          dict[attr]=str(subdict['0040A160']['Value'][0])
          if radlex:
            dict[attr]+=' ('+subdict['0040A043']['Value'][0]['00080100']['Value'][0]+','+subdict['0040A043']['Value'][0]['00080102']['Value'][0]+')'
      
        elif attr=='Tracking Identifier':
          dict1[attr]=str(subdict['0040A160']['Value'][0])
      
        elif attr=='Tracking Unique Identifier':
          dict1[attr]=str(subdict['0040A124']['Value'][0])
        
        elif (attr== 'Maximum 2D diameter' or attr=='Maximum 3D diameter' or attr=='Maximum perpendicular 2D diameter' or attr=='Mean   2D diameter' or attr=='Volume'):
          dict[attr]=str(subdict['0040A300']['Value'][0]['0040A30A']['Value'][0])
          if radlex:
            dict[attr]+=' ('+subdict['0040A043']['Value'][0]['00080100']['Value'][0]+','+subdict['0040A043']['Value'][0]['00080102']['Value'][0]+')'       

        elif attr== 'Lesion Epicenter':
          print('jjasd')
          dict[attr]=str(subdict['00700022']['Value'])
          les_center=subdict['00700022']['Value']
          print('lsc',les_center)
          
	
        elif attr== 'Attenuation Characteristic' or attr=='Radiographic Lesion Margin' or attr=='Lung-RADS assessment' or attr=='Finding' or attr=='Finding site':
          dict[attr]=str(subdict['0040A168']['Value'][0]['00080104']['Value'][0])
          if radlex:
            dict[attr]+=' ('+subdict['0040A043']['Value'][0]['00080100']['Value'][0]+','+subdict['0040A043']['Value'][0]['00080102']['Value'][0]+')'  
        #temp.append(attr)
      #print('attrs',set(temp))
      for j in range(4):
        gg=dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'][2]['0040A730']['Value'][j]['0040A043']['Value'][0]['00080104']['Value'][0]
        pp=dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'][2]['0040A730']['Value'][j]['0040A168']['Value'][0]['00080104']['Value'][0]
        dict[gg]=pp
        
      gg=dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'][2]['0040A730']['Value'][4]['0040A043']['Value'][0]['00080104']['Value'][0]
      pp=dds['0040A730']['Value'][start_key]['0040A730']['Value'][i]['0040A730']['Value'][2]['0040A730']['Value'][4]['0040A160']['Value'][0]
      dict[gg]=pp
      if i==0:
        nested_dict['patient_study_details']=dict1 
        nested_dict['nodules']=[]  
      
      dict[dss1[0x0018,0x0060].name]=dss1[0x0018,0x0060].value
      dict[dss1[0x0018,0x1210].name]=dss1[0x0018,0x1210].value
      print('tt',nii_image.GetOrigin()[2])
      print('gg',nii_image.GetSpacing()[2])
      sl_num=np.floor((les_center[2]-nii_image.GetOrigin()[2])/nii_image.GetSpacing()[2])
      print('sl1', sl_num)
      sl_num=sitk.GetArrayFromImage(nii_image).shape[0]-sl_num
      print('sl2', sl_num)
      dict['slice number of lesion epicenter']=abs(int(sl_num))
      half_num_of_nodule_slices=float(dict['Maximum 2D diameter'])/(2*nii_image.GetSpacing()[2])
      dict['nodule starting slice number']=int(float(dict['slice number of lesion epicenter'])-half_num_of_nodule_slices)
      dict['nodule ending slice number']=int(float(dict['slice number of lesion epicenter'])+half_num_of_nodule_slices)
      
      olay_count=0
      l = [i for i in dss1]
      for i in l:
        if i.name == 'Overlay Data':
          print(type(i),i)
          print(str(i)[1:5])
      num = '6000'
      for element in dss1:
        if element.name=='Overlay Data':  
          num=str(element)[1:5]
          print('num:',num)
          hexa=hex(int(num,16))
          #last overlay, you get in the last iteration (just the overlay)
          arr=dss1.overlay_array(int(num,16))
        if olay_count==0:
          #first overlay (has dimensions too)
          olay_dim=dss1.overlay_array(int(num,16))
        olay_count+=1
    
      c=0
      for element in dss1:
        if element.name=='Pixel Data':
          window1=int(dss1[0x0028,0x1050].value)
          window0=int(dss1[0x0028,0x1051].value)
          im=dss1.pixel_array
          img = im.astype(float)
          img = img*dss1.RescaleSlope + dss1.RescaleIntercept
          im = (img-window1+0.5*window0)/window0
          im[im<0] = 0
          im[im>1] = 1
     
          img_bbox = Image.fromarray((255*im).astype('uint8'))
          img_bbox = img_bbox.convert('RGB')
          image_new = np.array(img_bbox)
        #save the contrast enhanced CT slice image
          only_CT=image_new.astype(np.uint8)
          fpath=str(olay_folder)+"/CT_%d" %c+".jpg"
          c+=1
          matplotlib.image.imsave(fpath,only_CT)
          with open(fpath,'rb') as img1:

            f=img1.read()
        
            imagedata1 = { "mimeType": "image/jpg",
                  "content": " ",
                  "fileName": "nod_with_msrmnts.jpg"
                  }
          imagedata1["content"]=base64.b64encode((f)).decode("utf-8")
          # CT slice image with overlay and dimensions
          dict['nodule_with_measurements']=imagedata1
          
          
        #fix the overlay (only) on the contrast enhanced CT slice image
          CT_olay_dim=image_new.astype(np.uint8)     
          for ii in range(arr.shape[0]):
            for jj in range(arr.shape[1]):
              if arr[ii,jj]==1:
                CT_olay_dim[ii,jj,0]=255
                CT_olay_dim[ii,jj,1]=0
                CT_olay_dim[ii,jj,2]=0      
          
          fpath=str(olay_folder)+"/CT_olay_dim_%d" %c+".jpg"
          c+=1
          matplotlib.image.imsave(fpath,CT_olay_dim)
        
        
    #encode the CT slice image overlayed using base64 and store it in dictionary   
    with open(fpath,'rb') as img1:
      f=img1.read()
      imagedata1 = { "mimeType": "image/jpg",
                "content": " ",
                "fileName": "nodule.jpg"
                 }
      imagedata1["content"]=base64.b64encode((f)).decode("utf-8")
    
    dict['Nodule']=imagedata1
    nested_dict['nodules'].append(dict)

  except Exception as e:
    traceback.print_exc()
    logging.error('[ERROR] Required images not present at moment')
    nested_dict['patient_study_details']= dict1
    flag =0
  filename_json = output.split('/')[-1] 
  with open(output,'w') as jsonFile:
    json.dump(nested_dict, jsonFile)
  #create a copy of json in another folder for easy query  
  os.makedirs('/home/ubuntu/JSON', exist_ok=True)
  json_copy= '/home/ubuntu/JSON'+'/' + f'{filename_json}'
  # os.makedirs('/home/arppit/Music/JSON', exist_ok=True)
  # json_copy= '/home/arppit/Music/JSON'+'/' + f'{filename_json}'
  with open(json_copy,'w') as jsonFileCopy:
    json.dump(nested_dict, jsonFileCopy)
  logging.info('[SUCCESS] Finished saving json file')
  if flag:
      logging.info('[SUCCESS] JSON is generated with thumnails for :', dict1[ds[0x0008,0x0016].name])
      print('[SUCCESS] JSON is generated with thumnails for :', dict1[ds[0x0008,0x0016].name])
      #print(nested_dict)
      return 1,nested_dict
  print('[ERROR] JSON is generated with thumnails for :', dict1[ds[0x0008,0x0016].name])
  #print(nested_dict)
  return 0,nested_dict


db = sqlite3.connect('pacs.db' , check_same_thread=False)
cursor = db.cursor()
c=0

def job_scheduler():
    global cursor
    global db
    global c
    li =[i for i in cursor.execute('select * from  JOBS')]
    #print(li)
    sent = [False]* len(li)

    if len(li)!=0:
      
        for i in li:
            loc = [i[0] for i in cursor.execute(f'SELECT FILENAME FROM IMAGES WHERE PATIENTID = "{i[1]}"')]
            
            study_folder = '/'.join(i[3].split('/')[:-1])
            #print('olay:',study_folder)
            for j in loc:
                if j.split('/')[-1]=='Thumbnails':
                  thumbnail_f = j 
                if j.split('/')[-1]=='CT':
                  ct_f = j 
                if j.split('/')[-1]=='SR':
                  sr_f = j
      
            input  = sr_f + f'/{i[2]}'
            #print('pr',os.path.exists(input), input)
            if os.path.exists(input):
              ds=  pydicom.read_file(input)
              output = sr_f + f'/{i[2]}.json'
              
              
              flag,js = ExtractNodulesFromJson(ds,output,False,thumbnail_f,ct_f, study_folder)
              if not(i[-1]):
                url = 'http://demo.va-pals.org/dcmin?siteid=XXX&returngraph=1'
                r =json.load(open(f'{input}.json'))
                res = requests.post(url, json = r)
                logging.info(f'[SENT] json sent to server and it returns {res} ')
               
               
                cursor.execute(f'UPDATE JOBS SET SENT = {True} where ID = "{i[0]}"')
                db.commit()
              if flag:
                  cursor.execute(f'DELETE FROM JOBS WHERE id = {i[0]}')
                  
                  
                  url = 'http://demo.va-pals.org/dcmin?siteid=XXX&returngraph=1'
                  r =json.load(open(f'{input}.json'))
                  res = requests.post(url, json = r)
                  logging.info(f'[SENT] json sent to server and it returns {res} ')
                
                  db.commit()
    #time.sleep(60)
    
def main():
    print('server started')
    while(1):
        
        job_scheduler()
        time.sleep(10)

if __name__ == '__main__':
    main()
