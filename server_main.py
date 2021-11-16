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
os.makedirs('/home/ubuntu/LOGS',exist_ok=True)
# os.makedirs('/home/arppit/Music/LOGS',exist_ok=True)
LOG_FILE = os.path.join('/home/ubuntu/LOGS',  f'{datetime.today()}_logs.txt')
#LOG_FILE = os.path.join('/home/arppit/Music/LOGS',f'{datetime.today()}_logs.txt')
db = sqlite3.connect('pacs.db' , check_same_thread=False)
cursor = db.cursor()

cursor.execute('CREATE TABLE IF NOT EXISTS DICOMDATA( ID INTEGER PRIMARY KEY AUTOINCREMENT,TIME INTEGER, PATIENTUID STR UNIQUE NOT NULL,  STUDYINSTANCEUID  STR NOT NULL UNIQUE,MANUFACTURER STR NOT NULL, PATH STR NOT NULL );')
cursor.execute('CREATE TABLE IF NOT EXISTS STUDYTABLE( ID INTEGER PRIMARY KEY AUTOINCREMENT,STUDYINSTANCEUID STR NOT NULL, SERIESINSTANCEUID  STR NOT NULL UNIQUE );')
cursor.execute('CREATE TABLE IF NOT EXISTS IMAGES( ID INTEGER PRIMARY KEY AUTOINCREMENT, SERIESINSTANCEUID STR NOT NULL,SOPINSTANCEUID STR NOT NULL UNIQUE, FILENAME STR NOT NULL UNIQUE);')
cursor.execute('CREATE TABLE IF NOT EXISTS JOBS( ID INTEGER PRIMARY KEY AUTOINCREMENT,SOPINSTANCEUID STR NOT NULL UNIQUE, PATH STR NOT NULL UNIQUE, SENT BOOLEAN );')
cursor.execute('CREATE TABLE IF NOT EXISTS SR( ID INTEGER PRIMARY KEY AUTOINCREMENT,SOPINSTANCEUID STR NOT NULL UNIQUE, PATH STR NOT NULL UNIQUE, PID STR NOT NULL);')
#db.commit()






def write_to_db(pid, studyid, seriesid,sopid,frameid,path, fname):
    global cursor
    global db
    logging.info('[SUCCESS] Connected to db' )
    #TO GET TIME USE SELECT DATETIME(TIME, 'unixepoch')
    cursor.execute(f'INSERT OR IGNORE INTO DICOMDATA (TIME, PATIENTUID,STUDYINSTANCEUID,MANUFACTURER, PATH) VALUES (strftime("%s","now"), "{str(pid)}", "{str(studyid)}", "{str(frameid)}", "{str(path)}")')
    cursor.execute(f'INSERT OR IGNORE INTO STUDYTABLE( STUDYINSTANCEUID, SERIESINSTANCEUID) VALUES ("{studyid}", "{seriesid}")')
    cursor.execute(f'INSERT OR IGNORE INTO IMAGES( SERIESINSTANCEUID, SOPINSTANCEUID ,FILENAME) VALUES ("{seriesid}", "{sopid}", "{fname}")' )
    db.commit()
    logging.info('[FINISHED] Saved values in Database ')
    #cursor.close()

def schedule(path,sopid,pid):
  global cursor
  global db
  cursor.execute(f'INSERT OR IGNORE INTO JOBS(SOPINSTANCEUID, PATH, SENT) VALUES ("{sopid}", "{path}", {False})')
  cursor.execute(f'INSERT OR IGNORE INTO SR(SOPINSTANCEUID, PATH,PID) VALUES ("{sopid}", "{path}", "{pid}")')
  db.commit()


def handle_store(event, storage_dir):
    """Handle EVT_C_STORE events."""
 
    pid  = event.dataset.PatientID
    studyid = event.dataset.StudyInstanceUID
    seriesid = event.dataset.SeriesInstanceUID
    sopid = event.dataset.SOPInstanceUID
    logging.basicConfig(filename=LOG_FILE,  level=logging.INFO)
    logging.info(f'[CONNECTION REQUEST]{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} PatientUID:{pid} StudyUID:{studyid}    Begin Saving file for {event.file_meta}')
    # frameid = event.dataset.FrameOfReferenceUID
    frameid = event.dataset.Manufacturer
    storage_path = '/home/ubuntu/storage/'
    # storage_path = '/home/arppit/Music/storage/'
    folder_name = storage_path+pid
    os.makedirs(folder_name, exist_ok=True)
    study_folder = folder_name + '/' + studyid
    os.makedirs(study_folder,exist_ok=True)
   
    if event.dataset.Modality =='SR':
        print('inside SR')
        storage_dir = study_folder + '/SR' 
        os.makedirs(storage_dir, exist_ok=True)
        fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
    else:
        try:
            if event.dataset.SeriesDescription =='AI-Rad Companion Pulmonary Lesion Thumbnails':
              print('going  in thumbnails')
              storage_dir = study_folder+ '/Thumbnails' # image-series data
              thumb_f = storage_dir
  
              os.makedirs(storage_dir, exist_ok=True)
           
              fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
            else:
              storage_dir = study_folder+ '/CT' # image-series data
              os.makedirs(storage_dir, exist_ok=True)
              fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
        except:
              storage_dir = study_folder+ '/CT' # image-series data
              os.makedirs(storage_dir, exist_ok=True)
              fname = os.path.join(storage_dir+'/', event.request.AffectedSOPInstanceUID)
              logging.error('Maybe Dataset is corrupted or not part of SR CT or thumbnails')
              

    # We rely on the UID from the C-STORE request instead of decoding
    logging.info('[START] writing to database')
   
    with open(fname, 'wb') as f:
        # Write the preamble, prefix and file meta information elements
        f.write(b'\x00' * 128)
        f.write(b'DICM')
        write_file_meta_info(f, event.file_meta)
        # Write the raw encoded dataset
        f.write(event.request.DataSet.getvalue())
    logging.info(f'[SUCCESS] File saved in {storage_dir}')
    if event.dataset.Modality =='SR':
      schedule(study_folder,sopid, pid)
    #   ExtractNodulesFromJson(event.dataset,fname+'.json',True,study_folder+'/Thumbnails',study_folder+'/CT', study_folder)
    write_to_db(str(pid),str(studyid), str(seriesid) ,str(sopid) ,str(frameid) ,str(storage_dir) ,str(study_folder))
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

