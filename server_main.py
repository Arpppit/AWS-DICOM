import os
import sqlite3 
import json
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
db = sqlite3.connect('PACS.db' , check_same_thread=False)
cursor = db.cursor()

# cursor.execute('CREATE TABLE DICOMDATA( ID INTEGER PRIMARY KEY AUTOINCREMENT,PATIENTUID STR UNIQUE NOT NULL,  STUDYINSTANCEUID  STR NOT NULL UNIQUE,FRAMEOFREFERENCEUID STR NOT NULL, PATH STR NOT NULL );')
# cursor.execute('CREATE TABLE STUDYTABLE( ID INTEGER PRIMARY KEY AUTOINCREMENT,STUDYINSTANCEUID STR NOT NULL, SERIESINSTANCEUID  STR NOT NULL UNIQUE );')
# cursor.execute('CREATE TABLE IMAGES( ID INTEGER PRIMARY KEY AUTOINCREMENT, SERIESINSTANCEUID STR NOT NULL,SOPINSTANCEUID STR NOT NULL UNIQUE, FILENAME STR NOT NULL UNIQUE);')
# #db.commit()

def write_to_db(pid, studyid, seriesid,sopid,frameid,path, fname):
    global cursor
    global db
    print('[SUCCESS] Connected to db' )
    cursor.execute(f'INSERT OR IGNORE INTO DICOMDATA (PATIENTUID,STUDYINSTANCEUID,FRAMEOFREFERENCEUID, PATH) VALUES ("{str(pid)}", "{str(studyid)}", "{str(frameid)}", "{str(path)}")')
    cursor.execute(f'INSERT OR IGNORE INTO STUDYTABLE( STUDYINSTANCEUID, SERIESINSTANCEUID) VALUES ("{studyid}", "{seriesid}")')
    cursor.execute(f'INSERT OR IGNORE INTO IMAGES( SERIESINSTANCEUID, SOPINSTANCEUID ,FILENAME) VALUES ("{seriesid}", "{sopid}", "{fname}")' )
    db.commit()
    #cursor.close()


def dicom_to_json(dataset, folder):
    start_key=0 
    json_obj = []
    dict={}
    ds=  dataset
    dds=ds.to_json_dict() 
    dict[ds[0x0008,0x0016].name]=ds[0x0008,0x0016].value
    dict[ds[0x0008,0x0020].name]=ds[0x0008,0x0020].value
    #dict[ds[0x0008,0x002a].name]=ds[0x0008,0x002a].value
    dict[ds[0x0008,0x0070].name]=ds[0x0008,0x0070].value
    #dict[ds[0x0008,0x0090].name]=ds[0x0008,0x0090].value
    dict[ds[0x0008,0x103e].name]=ds[0x0008,0x103e].value
    dict[ds[0x0008,0x1090].name]=ds[0x0008,0x1090].value
    dict[ds[0x0010,0x0010].name]=str(ds[0x0010,0x0010].value)
    dict[ds[0x0010,0x0020].name]=ds[0x0010,0x0020].value
    dict[ds[0x0010,0x0030].name]=ds[0x0010,0x0030].value
    dict[ds[0x0010,0x0040].name]=ds[0x0010,0x0040].value 
    json_obj.append(dict)
    payload = json.dumps(json_obj)
    fname = ds.SOPInstanceUID
    with open(f'{folder}/{fname}.json', 'w') as f:
        json.dump(payload, f)
    print('json file saved')


def handle_store(event, storage_dir):
    """Handle EVT_C_STORE events."""
    #print('inside store' )
    #print(event.dataset.Modality)
    #ds = event.request.DataSet.getvalue()
    #ds.get_attr('UID')
    pid  = event.dataset.PatientID
    studyid = event.dataset.StudyInstanceUID
    seriesid = event.dataset.SeriesInstanceUID
    sopid = event.dataset.SOPInstanceUID
    # frameid = event.dataset.FrameOfReferenceUID
    frameid = event.dataset.Manufacturer
    if event.dataset.Modality =='SR':
        storage_dir ='/home/ubuntu/storage/SR'
        # rootf = storage_dir + f'/{pid}'
        # os.makedirs(rootf, exist_ok=True)
        # studyidf = rootf + f'/{studyid}'
        # os.makedirs(studyidf, exist_ok=True)
        # seriesidf = studyidf + f'/{seriesid}'
        # os.makedirs(seriesidf,exist_ok=True)
        # jsonFolder = seriesidf+ f'/{sopid}'
        
       
        foldername = storage_dir +'/'+ str(event.request.AffectedSOPInstanceUID)
        os.makedirs(foldername, exist_ok=True)
        jsonfname =  foldername+'/JSON'
        os.makedirs(jsonfname,exist_ok=True)
        dicom_to_json(event.dataset, jsonfname)
        fname = os.path.join(foldername, event.request.AffectedSOPInstanceUID)
        #storage_dir = '/home/Music/SR'
    else:
        try:
            storage_dir = '/home/ubuntu/storage/CT'
            rootf = storage_dir + f'/{pid}'
            os.makedirs(rootf, exist_ok=True)
            studyidf = rootf + f'/{studyid}'
            os.makedirs(studyidf, exist_ok=True)
            seriesidf = studyidf + f'{seriesid}'
            os.makedirs(seriesidf,exist_ok=True)
            fname = os.path.join(seriesidf, event.request.AffectedSOPInstanceUID)
        except:
            # Unable to create output dir, return failure status
            print('[FAILED] error creating output directory .. maybe permission error')
            return 0xC001
    #print(event.dataset)

    # We rely on the UID from the C-STORE request instead of decoding
    
    write_to_db(str(pid),str(studyid), str(seriesid) ,str(sopid) ,str(frameid) ,str(storage_dir) ,str(fname))
    with open(fname, 'wb') as f:
        # Write the preamble, prefix and file meta information elements
        f.write(b'\x00' * 128)
        f.write(b'DICM')
        write_file_meta_info(f, event.file_meta)
        # Write the raw encoded dataset
        f.write(event.request.DataSet.getvalue())

    return 0x0000

def main():
    handlers = [(evt.EVT_C_STORE, handle_store, ['out'])]

    ae = AE()
    ae.ae_title = b'VAPALS_ELCAP_DICOM'
    #ae.requested_contexts = StoragePresentationContexts
    storage_sop_classes = [
        cx.abstract_syntax for cx in AllStoragePresentationContexts
    ]
    #ae.add_supported_context(
        
    for uid in storage_sop_classes:
        ae.add_supported_context(uid, ALL_TRANSFER_SYNTAXES)
    ae.add_requested_context(CTImageStorage)

    #ae.add_requested_context('CT Image Storage')
    ae.start_server(('', 11112), block=True, evt_handlers=handlers)


if __name__ == '__main__':
    main()

