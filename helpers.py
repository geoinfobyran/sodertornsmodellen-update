import pandas as pd
import numpy as np
import os

# Set up input and output directories
# input
indataPath = os.path.join(os.pardir, "indata")
ddfRootPath = os.path.join(indataPath, "ddf--sodertornsmodellen")
ddfSrcPath = os.path.join(ddfRootPath, "ddf--sodertornsmodellen--src")
superPath = os.path.join(indataPath, "supermappen")
# output
ddfOutputPath = os.path.join(os.pardir, 'ddf--sodertornsmodellen-new', 'ddf--sodertornsmodellen--src')

# Ta året ur filnamnen i supermappen
def getYear(fileName):
    return fileName[-8:-4]

# Remove file, without throwing errors if the file does not exist
# https://stackoverflow.com/a/10840586
import os, errno
def silentremove(filename):
    try:
        os.remove(filename)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

# Read and format the MASTER*.xlsx file
def readMaster():
    master = pd.read_excel(os.path.join(indataPath, 'MASTER_00-17.xlsx'))
    # byt namn på kolumner för att matcha namnen i ddf-filerna
    master = master.rename(columns={
        'område': 'name',
        'Basområde': 'BASKODER', # kolumnen Basområde blandar BK2010 och BK2000
        'tid': 'year'
    })
    master['year'] = pd.to_datetime(master['year'].astype(str))
    return master

# Append new data to concept. Return the combined datasets for plotting.
# new: are there existing datapoints that should be updated, or is this a new dataset
def appendNewDatapoints(concept, _df, new=False, write=True):
    filename = 'ddf--datapoints--{concept}--by--basomrade--year.csv'.format(concept=concept)
    _df = _df[['basomrade', 'year', 'value']]
    # _df = _df.groupby(['basomrade', 'year']).sum(numeric_only=True, skipna=False).reset_index() # Make sure that split basomraden gets summed to one
    _df = _df.rename(columns = {'value': concept})
    if new:
        df = _df
    else:
        previousPath = os.path.join(ddfSrcPath, filename)
        previousData = pd.read_csv(previousPath)
        df = pd.concat([previousData, _df], sort=False)
    path = os.path.join(ddfOutputPath, filename)
    if(write):
        silentremove(path)
        df.to_csv(path, index=False)
    # print('Saved {concept} to {path}\n'.format(concept=concept, path=path))
    df = df.rename(columns={concept: 'value'})
    return df

# Append new data to concept by gender.
def byGender(concept, _df, new=False):
    genders = _df['Kön'].cat.categories.tolist()

    combinedGenders = []
    for gender in genders:
        conceptgender = '{concept}_{gender}'.format(concept=concept,gender=gender)

        dfgen = _df[_df['Kön'] == gender]
        dfgen = dfgen[['basomrade', 'year', 'value']]

        combined = appendNewDatapoints(conceptgender, dfgen, new)
        combinedGenders.append(combined)
    return combinedGenders[0], combinedGenders[1]

# Lookup tables between BASKOD2000 and BASKOD2010
baskodkey = pd.read_excel(os.path.join(ddfRootPath, 'etl', 'source', '161115 A7 utan formler.xlsx'), skiprows=[0,1,2,3,4,5,6], converters={2010: lambda x: str(x)})
baskodkey = baskodkey[[2010, 'BASKOD2000']]
baskodkey = baskodkey.rename(columns={2010: 'BASKOD2010'})
baskodkey['BASKOD2010'] = baskodkey['BASKOD2010'].astype(str).astype(int)

# Lookup table between BASKOD2000 and the baskod entity id.
entityKey = pd.read_csv(os.path.join(ddfOutputPath, 'ddf--entities--basomrade.csv'))
entityKey = entityKey.rename(columns={'baskod2010': 'BASKOD2000'})
entityKey['basomrade'] = entityKey['basomrade'].astype(str)
entityKey = entityKey[['basomrade', 'BASKOD2000']]

# Use the above lookup tables to go from BASKOD2010 to baskod entity id.
def sumByBasomradeYear(_df,  n_numeric):
    _df = _df.groupby(list(_df.columns[:-n_numeric])).sum(numeric_only=True).reset_index() # Make sure that split basomraden gets summed to one
    return _df

def moveColumns(_df, n_numeric=1):
    # move columns around, numeric columns must be last
    baskoder = list(_df.columns[-2:])
    kolumner = list(_df.columns[:-2])
    kolumner[-n_numeric:-n_numeric] = baskoder
    _df = _df[kolumner]
    return _df

def baskod2010tobasomrade(_df, n_numeric=1):
    _df = pd.merge(_df, baskodkey, on='BASKOD2010', how='left')
    _df = pd.merge(_df, entityKey[['BASKOD2000', 'basomrade']], on='BASKOD2000', how='left')
    _df = _df.dropna(subset=['basomrade'])
    # # move columns around
    # baskoder = list(_df.columns[-2:])
    # kolumner = list(_df.columns[:-2])
    # kolumner[-n_numeric:-n_numeric] = baskoder
    # _df = _df[kolumner]
    _df = moveColumns(_df, n_numeric)
    _df = _df.drop(['BASKOD2010', 'BASKOD2000'], axis=1, errors='ignore')
    _df = sumByBasomradeYear(_df, n_numeric)
    return _df

def baskod2000tobasomrade(_df, n_numeric=1):
    _df = pd.merge(_df, entityKey[['BASKOD2000', 'basomrade']], on='BASKOD2000', how='left')
    _df = _df.dropna(subset=['basomrade'])
    _df = moveColumns(_df, n_numeric)
    _df = _df.drop(['BASKOD2010', 'BASKOD2000'], axis=1, errors='ignore')
    _df = sumByBasomradeYear(_df, n_numeric)
    return _df

# Plot timeseries of the combined old+update dataframes.
# The point is to get a quick visual indication of errors, such as sudden jumps between last year in old data and first year in the new data.
def plotcombined(combined, name='value', title=''):
    combined = combined.rename(columns={'value': name})
    combined['year'] = pd.to_datetime(combined['year'].astype('str'))
    (combined.groupby('year').mean()[name]).plot(legend=True, title='{title} (mean per basomrade)'.format(title=title))