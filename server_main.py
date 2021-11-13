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
from datetime import datetime 
import logging
import SimpleITK as sitk
from pydicom.filewriter import write_file_meta_info
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelGet,
    CTImageStorage
)
from pynetdicom import (
    AE, debug_logger, evt, AllStoragePresentationContexts,
    ALL_TRANSFER_SYNTAXES,StoragePresentationContexts
)

debug_logger()
LOG_FILE = f'home/ubuntu/{datetime.today()}_logs.txt'
db = sqlite3.connect('PACS.db' , check_same_thread=False)
cursor = db.cursor()
#TO GET TIME USE SELECT DATETIME(TIME, 'unixepoch')
cursor.execute('CREATE TABLE IF NOT EXISTS DICOMDATA( ID INTEGER PRIMARY KEY AUTOINCREMENT,TIME INTEGER, PATIENTUID STR UNIQUE NOT NULL,  STUDYINSTANCEUID  STR NOT NULL UNIQUE,FRAMEOFREFERENCEUID STR NOT NULL, PATH STR NOT NULL );')
cursor.execute('CREATE TABLE IF NOT EXISTS STUDYTABLE( ID INTEGER PRIMARY KEY AUTOINCREMENT,STUDYINSTANCEUID STR NOT NULL, SERIESINSTANCEUID  STR NOT NULL UNIQUE );')
cursor.execute('CREATE TABLE IF NOT EXISTS IMAGES( ID INTEGER PRIMARY KEY AUTOINCREMENT, SERIESINSTANCEUID STR NOT NULL,SOPINSTANCEUID STR NOT NULL UNIQUE, FILENAME STR NOT NULL UNIQUE);')
#db.commit()




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
    print('#'*100)
    print(dict1)
    print('#'*100)
    thumbnail_files = os.listdir(dataset_folder)
    # if no corresponding thumbnail files are present just work with what we have 
    if len(thumbnail_files) < len(dds['0040A730']['Value'][start_key]['0040A730']['Value']):
      logging.error(f'[ERROR] Cannot find corresponding CT images... only {thumbnail_files} are present')
      rem = len(dds['0040A730']['Value'][start_key]['0040A730']['Value']) - len(thumbnail_files)
      if len(thumbnail_files)!=0:
        thumbnail_files+=[thumbnail_files[0]]*rem
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
          print(new.max())
          print(new.min())
          center=-500
          width=1400
          lower_bound = center - (width - 1)/2
          upper_bound = center + (width - 1)/2
          sit_m=sitk.GetImageFromArray(im)
          contr_sitm = sitk.Cast(sitk.IntensityWindowing(sit_m,np.float64(im.min()),np.float64(im.max()),lower_bound, upper_bound),sitk.sitkUInt8)
          contr_im=sitk.GetArrayFromImage(contr_sitm)
          fpath=str(olay_folder)+"/CT_%2d" %i+".jpg"
          matplotlib.image.imsave(fpath,new,cmap=cm.gray)
          logging.info('[SUCCESS] saving generated image successfull')
 
         
    with open(fpath,'rb') as img1:

      f=img1.read()
      
      imagedata1 = { "mimeType": "image/jpg",
                "content": " ",
                "fileName": "CT_key_image.jpg"
                }
      imagedata1["content"]=base64.b64encode((f)).decode("utf-8")
    dict['CT details']=imagedata1
    nested_dict['nodules'].append(dict)
  except:
    logging.error('[ERROR] Required images not present at moment')
    nested_dict['patient_study_details']= dict1
  filename_json = output.split('/')[-1] 
  with open(output,'w') as jsonFile:
    json.dump(nested_dict, jsonFile)
  #create a copy of json in another folder for easy query  
  os.makedirs('/home/arppit/Music/JSON', exist_ok=True)
  json_copy= '/home/arppit/Music/JSON'+'/' + f'{filename_json}'
  with open(json_copy,'w') as jsonFileCopy:
    json.dump(nested_dict, jsonFileCopy)
  logging.info('[SUCCESS] Finished saving json file')


def write_to_db(pid, studyid, seriesid,sopid,frameid,path, fname):
    global cursor
    global db
    logging.info('[SUCCESS] Connected to db' )
    cursor.execute(f'INSERT OR IGNORE INTO DICOMDATA (TIME, PATIENTUID,STUDYINSTANCEUID,FRAMEOFREFERENCEUID, PATH) VALUES (strftime("%s","now"), "{str(pid)}", "{str(studyid)}", "{str(frameid)}", "{str(path)}")')
    cursor.execute(f'INSERT OR IGNORE INTO STUDYTABLE( STUDYINSTANCEUID, SERIESINSTANCEUID) VALUES ("{studyid}", "{seriesid}")')
    cursor.execute(f'INSERT OR IGNORE INTO IMAGES( SERIESINSTANCEUID, SOPINSTANCEUID ,FILENAME) VALUES ("{seriesid}", "{sopid}", "{fname}")' )
    db.commit()
    logging.info('[FINISHED] Saved values in Database ')
    #cursor.close()




def handle_store(event, storage_dir):
    """Handle EVT_C_STORE events."""
 
    pid  = event.dataset.PatientID
    studyid = event.dataset.StudyInstanceUID
    seriesid = event.dataset.SeriesInstanceUID
    sopid = event.dataset.SOPInstanceUID
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO)
    logging.info(f'[CONNECTION REQUEST]{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} PatientUID:{pid} StudyUID:{studyid}    Begin Saving file for {event.file_meta}')
    # frameid = event.dataset.FrameOfReferenceUID
    frameid = event.dataset.Manufacturer
    storage_path = '/home/ubuntu/storage/'
    folder_name = storage_path+pid
    os.makedirs(folder_name, exist_ok=True)
    study_folder = folder_name + '/' + studyid
    os.makedirs(study_folder,exist_ok=True)
    if event.dataset.Modality =='SR':
  
        storage_dir = study_folder + '/SR' 
        os.makedirs(storage_dir, exist_ok=True)
        fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
    else:
        try:
            if event.dataset.SeriesDescription =='AI-Rad Companion Pulmonary Lesion Thumbnails':
              
              storage_dir = study_folder+ '/Thumbnails' # image-series data
              thumb_f = storage_dir
  
              os.makedirs(storage_dir, exist_ok=True)
           
              fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
            else:
              storage_dir = study_folder+ '/CT' # image-series data
              os.makedirs(storage_dir, exist_ok=True)
              fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
        except:
              logging.error('Maybe Dataset is corrupted or not part of SR CT or thumbnails')
                

    # We rely on the UID from the C-STORE request instead of decoding
    logging.info('[START] writing to database')
    write_to_db(str(pid),str(studyid), str(seriesid) ,str(sopid) ,str(frameid) ,str(storage_dir) ,str(fname))
    with open(fname, 'wb') as f:
        # Write the preamble, prefix and file meta information elements
        f.write(b'\x00' * 128)
        f.write(b'DICM')
        write_file_meta_info(f, event.file_meta)
        # Write the raw encoded dataset
        f.write(event.request.DataSet.getvalue())
    logging.info(f'[SUCCESS] File saved in {storage_dir}')
    if event.dataset.Modality =='SR':
      ExtractNodulesFromJson(event.dataset,fname+'.json',False,study_folder+'/Thumbnails',study_folder+'/CT', study_folder)
    logging.info(f'[FINISHED] {pid} + {studyid} + {sopid} File recieved and exiting the process ')
    return 0x0000

def main():
    handlers = [(evt.EVT_C_STORE, handle_store, ['out'])]

    ae = AE()
    ae.ae_title = b'SPLUS'
    #ae.requested_contexts = StoragePresentationContexts
    storage_sop_classes = [
        cx.abstract_syntax for cx in AllStoragePresentationContexts
    ]
    #ae.add_supported_context(
        
    for uid in storage_sop_classes:
        ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)
    ae.add_requested_context(CTImageStorage)

    #ae.add_requested_context('CT Image Storage')
    ae.start_server(('', 11112),  evt_handlers=handlers)


if __name__ == '__main__':
    main()

