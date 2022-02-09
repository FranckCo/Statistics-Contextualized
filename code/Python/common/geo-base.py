# Constants ----
import json
import logging

import pandas as pd
import requests
from prefect import Flow, Parameter, task

PUSH_TO_PREFECT_CLOUD_DASHBOARD = False

FTP_URL = 'FTP_URL'
FTP_USERNAME = 'FTP_USERNAME'
FTP_PASSWORD = 'FTP_PASSWORD'

WORK_DIRECTORY = '../../../work/'
USE_LOCAL_FILES = True
VISUALIZE_FLOW = False

REF_YEAR = '2019'

# The LAU-NUTS files are taken from https://ec.europa.eu/eurostat/web/nuts/local-administrative-units
# The names of the files for the different years are in the GEO_FILE_NAMES JSON file
GEO_FILE_NAMES = '../../../pilots/resources/geo_files.json'
BASE_URL = 'https://ec.europa.eu/eurostat/documents/345175/501971/'
LOCAL_CSV = WORK_DIRECTORY + f'lau-nuts3-{REF_YEAR}.csv'


# Tasks ----

@task(name='Download Excel file')
def get_eurostat_file(geo_url, geo_file):
    """Downloads the Excel LAU file from the Eurostat website.

    Args:
    geo_url (str): URL of the file containing geographic reference data from Eurostat.
    geo_file (str): Local name for saving the file.
    """
    logging.info(f'Downloading from {geo_url} and saving to {geo_file}')
    data = requests.get(geo_url)
    with open(geo_file, 'wb') as file:
        file.write(data.content)


@task(name='Create LAU-NUTS table')
def get_lau_nuts(geo_file_name):
    """Creates the LAU-NUTS3 correspondence.

    Args:
        geo_file_name (str): name of the file containing geographic reference data.
    Returns:
        DataFrame: Table indexed by LAU with a 'NUTS3' column, containing both French and Italian LAUs.
    Raises:
        AssertionError: If duplicate values of LAU are found in the concatenated table.
    """
    logging.info(f'Reading LAU-NUTS3 correspondence from {geo_file_name}')
    # NUTS3 is in the first column and LAU in the second
    geo_dfs = pd.read_excel(geo_file_name, sheet_name=['FR', 'IT'], dtype=str, usecols=[0, 1], names=['NUTS3', 'LAU'])

    # Merge French and Italian data
    geo_df = pd.concat(geo_dfs)
    # Check uniqueness of LAU values and index the data frame
    assert geo_df['LAU'].is_unique, 'There are duplicate values for the LAU'
    geo_df.set_index('LAU', inplace=True)
    logging.info(f'LAU-NUTS3 correspondence created, {geo_df.shape[0]} LAU found')

    geo_df.to_csv(LOCAL_CSV)
    logging.info(f'LAU-NUTS3 correspondence saved to {LOCAL_CSV}')

    return geo_df


with Flow('get_geo') as flow:

    with open(GEO_FILE_NAMES) as geo_json:
        file_names = json.load(geo_json)
        print(file_names)
        file_name = file_names["file_names"][REF_YEAR]

    remote_file_url = Parameter('lau_url', default=BASE_URL + file_name)
    local_file_name = Parameter('lau_file name', default=WORK_DIRECTORY + file_name)

    if not USE_LOCAL_FILES:
        get_eurostat_file(remote_file_url, local_file_name)

    get_lau_nuts(local_file_name)


if __name__ == '__main__':
    logging.basicConfig(filename=WORK_DIRECTORY + 'geo-base.log', encoding='utf-8', level=logging.DEBUG)
    if PUSH_TO_PREFECT_CLOUD_DASHBOARD:
        flow.register(project_name='sep-aq')
    else:
        flow.run()

    if VISUALIZE_FLOW:
        flow.visualize()