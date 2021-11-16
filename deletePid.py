import os
import sqlite3
import os
from shutil import rmtree
import sys
db = sqlite3.connect('pacs.db' , check_same_thread=False)
cursor = db.cursor()

def deletePID(id):
    """
     delete pid completely from database and storage
     
    """
    global cursor
    global db
    try:
        studyids = [i for i in cursor.execute(f'SELECT STUDYINSTANCEUID FROM DICOMDATA WHERE PATIENTUID = "{id}"')]
        seriesids =[]
        for i in studyids:
            print(i)
            seriesids.append([i for i in cursor.execute(f'SELECT SERIESINSTANCEUID FROM STUDYTABLE WHERE STUDYINSTANCEUID = "{i}"')])
        for i in seriesids:
            for j in i:
                cursor.execute(f'DELETE FROM IMAGES WHERE SERIESINSTANCEUID =  "{j}"')
        for i in studyids:
            cursor.execute(f'DELETE FROM STUDYTABLE WHERE STUDYINSTANCEUID = "{id}"')
        cursor.execute(f'DELETE FROM DICOMDATA WHERE PATIENTUID = "{id}"')
        db.commit()
        #rmtree(f'/home/arppit/Music/storage/{id}')
        rmtree(f'/home/ubuntu/storage/{id}')
        json = [i for i in cursor.execute(f'SELECT SOPINSTANCEUID FROM SR WHERE PID = "{id}"')]
        #os.remove(f'/home/arppit/Music/JSON/{json[0][0]}.json')
        os.remove(f'/home/ubuntu/JSON/{json[0][0]}.json')
        return 1
    except Exception as e:
        print(e)
        return 0



def main():
    id = sys.argv[1]
    r=deletePID(id)
    if(r):print(f'Deleted {id} from database and storage.')




if __name__ == '__main__':
    main()
