import pandas as pd
import numpy as np
import os

indataPath = os.path.join(os.pardir, "indata")

ddfRootPath = os.path.join(indataPath, "ddf--sodertornsmodellen")
ddfSrcPath = os.path.join(ddfRootPath, "ddf--sodertornsmodellen--src")

superPath = os.path.join(indataPath, "supermappen")

ddfOutputPath = os.path.join(os.pardir, 'ddf--sodertornsmodellen-output', 'ddf--sodertornsmodellen--src')

# Ta året ur filnamnen i supermappen
def getYear(fileName):
    return fileName[-8:-4]

# Ta bort fil, strunta i det om den inte finns
# https://stackoverflow.com/a/10840586
import os, errno

def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

def appendNewDatapoints(concept, _df):
    filename = 'ddf--datapoints--{concept}--by--basomrade--year.csv'.format(concept=concept)
    previousPath = os.path.join(ddfSrcPath, filename)
    previousData = pd.read_csv(previousPath)
    _df = _df[['basomrade', 'year', 'value']]
    _df = _df.rename(columns = {'value': concept})
    combined = pd.concat([previousData, _df], sort=False)
    path = os.path.join(ddfOutputPath, filename)
    silentremove(path)
    combined.to_csv(path, index=False)
    print('Saved {concept} to {path}\n'.format(concept=concept, path=path))

def byGender(concept, _df):
    genders = _df['Kön'].cat.categories.tolist()

    for gender in genders:
        conceptgender = '{concept}_{gender}'.format(concept=concept,gender=gender)

        dfgen = _df[_df['Kön'] == gender]
        dfgen = dfgen[['basomrade', 'year', 'value']]

        appendNewDatapoints(conceptgender, dfgen)


baskodkey = pd.read_excel(os.path.join(ddfRootPath, 'etl', 'source', '161115 A7 utan formler.xlsx'), skiprows=[0,1,2,3,4,5,6], converters={2010: lambda x: str(x)})
baskodkey = baskodkey[[2010, 'BASKOD2000']]
baskodkey = baskodkey.rename(columns={2010: 'BASKOD2010'})
baskodkey['BASKOD2010'] = baskodkey['BASKOD2010'].astype(str).astype(int)


entityKey = pd.read_csv(os.path.join(ddfOutputPath, 'ddf--entities--basomrade.csv'))
entityKey = entityKey.rename(columns={'baskod2000': 'BASKOD2000'})
entityKey['basomrade'] = entityKey['basomrade'].astype(str)

entityKey = entityKey[['basomrade', 'BASKOD2000']]

def baskod2010tobasomrade(_df):
    _df = pd.merge(_df, baskodkey, on='BASKOD2010', how='left')
    _df = pd.merge(_df, entityKey[['BASKOD2000', 'basomrade']], on='BASKOD2000', how='left')
    _df = _df.dropna(how='any')
    return _df