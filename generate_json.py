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
import pause 
import json
import time
from datetime import datetime 
import logging
import requests
import SimpleITK as sitk
from pydicom.filewriter import write_file_meta_info
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelGet,
    CTImageStorage
)


def ExtractNodulesFromJson(input, output:Path,radlex: bool, dataset_folder,thickness_fr_of_ref_folder, olay_folder): 
  # try:
  start_key=0 
  nested_dict={}
  logging.info(f'[START] Begin SR to JSON conversion')
  dict1={}
  ds = input
  #ds=  pydicom.dataset.Dataset.from_json(json.load(open(input)))
  dds=ds.to_json_dict() 
  #dict1['Frame of reference UID']=dds['0040A730']['Value'][3]['0040A730']['Value'][0]['0040A730']['Value'][3]['30060024']['Value'][0]
  dict1[ds[0x0008,0x0016].name]=ds[0x0008,0x0016].value
  dict1[ds[0x0008,0x0020].name]=ds[0x0008,0x0020].value
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
          dict[attr]=str(subdict['00700022']['Value'])
          

        elif attr== 'Attenuation Characteristic' or attr=='Radiographic Lesion Margin' or attr=='Lung-RADS assessment' or attr=='Finding' or attr=='Finding site':
          dict[attr]=str(subdict['0040A168']['Value'][0]['00080104']['Value'][0])
          if radlex:
            dict[attr]+=' ('+subdict['0040A043']['Value'][0]['00080100']['Value'][0]+','+subdict['0040A043']['Value'][0]['00080102']['Value'][0]+')'  

      if i==0:
        nested_dict['patient_study_details']=dict1 
        nested_dict['nodules']=[]  
      
      dict[dss1[0x0018,0x0060].name]=dss1[0x0018,0x0060].value
      
    
      for element in dss1:
        if element.name=='Pixel Data':
          num='0x'+str(element)[1:5]
          
          im=dss1.pixel_array
          new=im/(   np.int32(im.max())-np.int32(im.min()))
          new=new*(1400)
          center=-500
          width=1400
          lower_bound = center - (width - 1)/2
          upper_bound = center + (width - 1)/2
          sit_m=sitk.GetImageFromArray(im)
          contr_sitm = sitk.Cast(sitk.IntensityWindowing(sit_m,np.float64(im.min()),np.float64(im.max()),lower_bound, upper_bound),sitk.sitkUInt8)
          contr_im=sitk.GetArrayFromImage(contr_sitm)
          fpath=str(olay_folder)+"/CT_%2d" %i+".jpg"
          matplotlib.image.imsave(fpath,new,cmap=cm.gray)

          with open(fpath,'rb') as img1:

            f=img1.read()
            
            imagedata1 = { "mimeType": "image/jpg",
                    "content": " ",
                    "fileName": f"CT_key_image{i}.jpg"
                    }
            imagedata1["content"]=base64.b64encode((f)).decode("utf-8")
            dict[f'CT details_{i}']=imagedata1
            nested_dict['nodules'].append(dict)
          logging.info('[SUCCESS] saving generated image successfull')
 
   
    with open(fpath,'rb') as img1:

            f=img1.read()
            
            imagedata1 = { "mimeType": "image/jpg",
                    "content": " ",
                    "fileName": f"CT_key_image{1}.jpg"
                    }
            imagedata1["content"]=base64.b64encode((f)).decode("utf-8")
            dict[f'CT details_{i}']=imagedata1
            nested_dict['nodules'].append(dict)
  except:
    #logging.error('[ERROR] Required images not present at moment')
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
      return 1
  return 0


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

            study_folder = i[2]
            input  = study_folder + '/SR' + f'/{i[1]}'
            if os.path.exists(input):
              ds=  pydicom.read_file(input)
              output = study_folder + '/SR' + f'/{i[1]}.json'
              flag = ExtractNodulesFromJson(ds,output,False,study_folder+'/Thumbnails',study_folder+'/CT', study_folder)
              if not(i[3]):
                
                with open(input, 'rb') as f:
                    r = requests.post('http://demo.va-pals.org/dcmin?siteid=PHO&returngraph=1', files={f'{input}': f})
                #print(r)
                cursor.execute(f'UPDATE JOBS SET SENT = {True} where ID = "{i[0]}"')
                db.commit()
              if flag:
                  cursor.execute(f'DELETE FROM JOBS WHERE id = {i[0]}')
                  #print(f'deleted {i[0]}')
                  with open(input, 'rb') as f:
                    r = requests.post('http://demo.va-pals.org/dcmin?siteid=PHO&returngraph=1', files={f'{input}': f})
                 
                  db.commit()
    #time.sleep(60)
    
def main():
    print('server started')
    while(1):
        time.sleep(10)
        job_scheduler()

if __name__ == '__main__':
    main()