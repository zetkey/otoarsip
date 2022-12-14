from seleniumwire import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import sys
import config
import pyotp
import requests
import json
from concurrent import futures
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# init
option = Options()
option.headless = True
option.add_argument('--disable-gpu')
option.add_argument('--window-size=1366,768')
driver = webdriver.Chrome(options=option)
wait = WebDriverWait(driver, 30)

# setting
totp = pyotp.TOTP(config.mfa_token)
kukis = ''
# format : DD-MM-YYYY, kosongkan jika tidak mau filter
tanggal_awal = ''
tanggal_akhir = ''
retries = Retry (
    total=5,
    status_forcelist=[408,429, 500, 502, 503, 504],
    backoff_factor=1)
adapter = HTTPAdapter(max_retries=retries)
counter = 0


# method
def arsipkan(object):
    """
    AmplopType: disposisi (_JenisNd = 2) -> patch
    AmplopType: NdMasuk (_JenisNd = 1) -> post
    """

    id = str(object['Id'])
    nd_id = object['NdId']
    perihal = object['Perihal']
    amplop_type = object['AmplopType']

    req = requests.Session()
    req.mount('https://', adapter)
    reqUrl = f"https://office.kemenkeu.go.id/api/Disposisi/UpdateStatus/{nd_id}/2"
    reqUrl2 = f"https://office.kemenkeu.go.id/api/NdKeluars/ArsipND/{nd_id}/{id}"

    headersList = {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "cookie": kukis,
    }

    payload = json.dumps([
            id,
            "-",
            []
        ])
    payload2 = json.dumps({
        "alasan": "-",
        "listTags": []
        })
    
    try:
        if amplop_type == 'disposisi':
            result = req.patch(reqUrl, headers=headersList, data=payload, timeout=30).json()
            print(id, result["Perihal"])
            # print(result)
        elif amplop_type == 'NdMasuk':
            result = req.post(reqUrl2, data=payload2,  headers=headersList, timeout=30).json()
            print(id, result["Perihal"])
            # print(result)

    except Exception as e:
        print(sys.exc_value)


def ambil_data(tanggal_awal, tanggal_akhir):
    req = requests.Session()
    req.mount('https://', adapter)
    reqUrl = f"https://office.kemenkeu.go.id/api/AmplopNd?search&filter&urgensi=All&reset=false&tagnd=All&UnitFilter&StartDateFilter={tanggal_awal}&EndDateFilter={tanggal_akhir}&limit=15&offset=0"
    headersList = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "cookie": kukis,
        "dnt": "1",
        "referer": "https://office.kemenkeu.go.id/nadine/mejaku" 
    }
    response = req.get(reqUrl, headers=headersList, timeout=30).json()
    return response

def mulai_ambil():
    counter = ambil_data(tanggal_awal, tanggal_akhir)['totalItems']
    if counter == 0:
        print("Data habis, tidak ada yang diproses")
    while counter != 0:
        response = []
        response = ambil_data(tanggal_awal, tanggal_akhir)
        counter = response['totalItems']
        print('Total data :' + str(counter))
        with futures.ThreadPoolExecutor() as thread:
            for object in response['listData']:
                thread.submit(arsipkan(object))     

# start
driver.get('https://office.kemenkeu.go.id/index/index')
assert 'KemenkeuID' in driver.title
kue = driver.get_cookies()
username = driver.find_element(By.NAME, 'Username')
password = driver.find_element(By.NAME, 'Password')
username.send_keys(config.username)
password.send_keys(config.password_oa)
password.send_keys(Keys.ENTER)
wait.until(EC.visibility_of_element_located((By.NAME, 'Code')))
assert 'KemenkeuID' in driver.title
print(f'Masuk {driver.title}')
code = driver.find_element(By.NAME, 'Code')
token = totp.now()
code.send_keys(token)
wait.until(EC.visibility_of_element_located((By.NAME, 'button')))
code.send_keys(Keys.ENTER)
wait.until(EC.visibility_of_element_located((By.XPATH, '//*[@id="fuse-shortcuts"]/div[2]/div/span')))
kukis = driver.wait_for_request('https://office.kemenkeu.go.id/Index/UserInfo').headers['cookie']
if kukis != None:
    print('Cookie berhasil didapat, lanjut request')
driver.close()

mulai_ambil()
