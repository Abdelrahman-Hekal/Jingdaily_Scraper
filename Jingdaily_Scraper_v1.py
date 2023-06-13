from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService 
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait as wait
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver import ActionChains
import undetected_chromedriver as uc
import time
import os
import re
from datetime import datetime
import pandas as pd
import warnings
import sys
import xlsxwriter
from multiprocessing import freeze_support
import calendar 
import shutil
warnings.filterwarnings('ignore')

def initialize_bot():

    # Setting up chrome driver for the bot
    chrome_options = uc.ChromeOptions()
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")
    chrome_options.add_argument('--log-level=3')
    chrome_options.add_argument("--enable-javascript")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--lang=en")
    #chrome_options.add_argument("--incognito")
    chrome_options.add_argument('--headless')  
    chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
    # installing the chrome driver
    driver_path = ChromeDriverManager().install()
    chrome_service = ChromeService(driver_path)
    # configuring the driver
    driver = webdriver.Chrome(options=chrome_options, service=chrome_service)
    driver.set_window_size(1920, 1080)
    driver.maximize_window()
    driver.set_page_load_timeout(30)

    return driver

def scrape_articles(driver, output1, page, month, year):

    stamp = datetime.now().strftime("%d_%m_%Y")
    print('-'*75)
    print(f'Scraping The Articles Links from: {page}')
    # getting the full posts list
    links = []
    months = {month: index for index, month in enumerate(calendar.month_abbr) if month}
    full_months = {month: index for index, month in enumerate(calendar.month_name) if month}
    prev_month = month - 1
    if prev_month == 0:
        prev_month = 12
    driver.get(page)
    art_time = ''
    formatted_month = str(prev_month).zfill(2)
    # handling lazy loading
    print('-'*75)
    print("Getting the previous month's articles..." )
    done = False
    obs= 0
    for _ in range(100):  
        try:
            height1 = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script(f"window.scrollTo(0, {height1})")
            time.sleep(0.1)
        except Exception as err:
            pass

        # scraping posts urls 
        try:
            posts = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[class*='article-index']")))  
            for post in posts:
                try:
                    img = wait(post, 2).until(EC.presence_of_element_located((By.TAG_NAME, "img"))).get_attribute('src')
                    match = re.findall(f'/{year}/[0-9]+/', img)[0]
                    img_month = int(match.split('/')[2])
                    if img_month > prev_month: continue
                    elif img_month < prev_month:
                        obs += 1
                        if obs == 10:
                            done = True
                            break
                    else:
                        link = wait(post, 2).until(EC.presence_of_element_located((By.TAG_NAME, "a"))).get_attribute('href')
                        if link not in links:
                            links.append(link)
                except:
                    pass
        except:
            pass
        
        if done: break

        # next page
        try:
            url = wait(driver, 4).until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[rel='next']"))).get_attribute('href')
            driver.get(url)
        except:
            break

    # scraping posts
    print('-'*75)
    print('Scraping Articles details...')
    print('-'*75)

    # reading previously scraped data for duplication checking
    scraped = []
    try:
        df = pd.read_excel(output1)
        scraped = df['articleurl'].values.tolist()
    except:
        pass

    n = len(links)
    data = pd.DataFrame()
    for i, link in enumerate(links):
        try:
            if link in scraped:
                print(f'Article {i+1}\{n} is already scraped, skipping ... ')
                continue
            row = {}
            driver.get(link)  
            date = ''
            try:
                date = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[class='post-date']"))).get_attribute('textContent').strip()
            except:
                pass
            # checking if the article date is correct
            try:
                art_month = months[date.split()[0]]
                art_year = int(date.split()[-1])  
                art_day = int(date.split()[1].replace(',', ''))
                # for articles from previous year
                if art_year < year and prev_month != 12:
                    print(f'skipping article {i+1}\{n} from {art_month}-{art_year}')
                    continue
                # for all months except Jan
                elif art_month < prev_month and prev_month != 12 and art_year == year:
                    print(f'skipping article {i+1}\{n} from {art_month}-{art_year}')
                    continue
                # for Jan
                elif art_month < prev_month and prev_month == 12 and art_year < year:
                    print(f'skipping article {i+1}\{n} from {art_month}-{art_year}')
                    continue                
                elif art_month > prev_month:
                    print(f'skipping article {i+1}\{n} from {art_month}-{art_year}')
                    continue
                else:
                    date = f'{art_day}_{art_month}_{art_year}'
            except:
                continue   
                
            art_id = ''
            try:
                art_id = link.strip('/').split('/')[-1]
            except:
                pass

            # article author
            author = ''             
            try:
                author = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "li[class='author-name']"))).get_attribute('textContent').strip()
            except Exception as err:
                pass
            
             

            row['sku'] = art_id
            row['unique_id'] = art_id
            row['articleurl'] = link

            # lazy loading handling
            try:
                total_height = driver.execute_script("return document.body.scrollHeight")
                height = total_height/30
                new_height = 0
                for _ in range(30):
                    prev_hight = new_height
                    new_height += height             
                    driver.execute_script(f"window.scrollTo({prev_hight}, {new_height})")
                    time.sleep(0.1)
            except:
                pass

            # article title
            title = ''             
            try:
                title = wait(driver, 2).until(EC.presence_of_element_located((By.TAG_NAME, "h1"))).get_attribute('textContent').strip()
            except:
                continue               
                
            row['articletitle'] = title            

            # article description
            des = ''             
            try:
                des_div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class='article-content']")))
                elems = wait(des_div, 2).until(EC.presence_of_all_elements_located((By.TAG_NAME, "p")))
                for elem in elems:
                    try:
                        text = elem.get_attribute('textContent').strip()
                        des += text + '\n'
                    except:
                        pass
                des = des.strip('\n')
            except:
                continue               
                
            row['articledescription'] = des       
            row['articleauthor'] = author
            row['articledatetime'] = date            
            
            # article category
            cat = ''             
            try:
                elems = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[rel='category tag']")))
                for elem in elems:
                    cat += elem.get_attribute('textContent').strip().title() + ', '
            except:
                pass 
            
            row['articlecategory'] = cat.strip(', ')

            # other columns
            row['domain'] = 'Jingdaily'
            row['hype'] = 0   

            tags = ''
            try:
                elems = wait(driver, 2).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "a[rel='tag']")))
                for elem in elems:
                    tags += elem.get_attribute('textContent').strip().title() + ', '
            except:
                pass 

            row['articletags'] = tags.strip(', ')

            # article header
            header = ''             
            try:
                header = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='image-caption']"))).get_attribute('textContent')
                header = header.split('Photo:')[0].split('Image:')[0].strip()
            except:
                pass 

            row['articleheader'] = header

            img = ''
            try:
                div = wait(driver, 2).until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='full-size-featured-image']")))
                img = wait(div, 2).until(EC.presence_of_element_located((By.TAG_NAME, "img"))).get_attribute('src')
            except:
                pass

            row['articleimages'] = img
            row['articlecomment'] = ''
            row['Extraction Date'] = stamp

            # appending the output to the datafame       
            data = pd.concat([data, pd.DataFrame([row.copy()])], ignore_index=True)
            print(f'Scraping Article {i+1}\{n}')

        except Exception as err:
            print(f'Warning: the below error occurred while scraping the article: {link}')
            print(str(err))
           
    # output to excel
    if data.shape[0] > 0:
        data['articledatetime'] = pd.to_datetime(data['articledatetime'],  errors='coerce', format="%d_%m_%Y")
        data['articledatetime'] = data['articledatetime'].dt.date  
        data['Extraction Date'] = pd.to_datetime(data['Extraction Date'],  errors='coerce', format="%d_%m_%Y")
        data['Extraction Date'] = data['Extraction Date'].dt.date   
        df1 = pd.read_excel(output1)
        if df1.shape[0] > 0:
            df1[['articledatetime', 'Extraction Date']] = df1[['articledatetime', 'Extraction Date']].apply(pd.to_datetime,  errors='coerce', format="%Y-%m-%d")
            df1['articledatetime'] = df1['articledatetime'].dt.date 
            df1['Extraction Date'] = df1['Extraction Date'].dt.date 
        df1 = df1.append(data)   
        df1 = df1.drop_duplicates()
        writer = pd.ExcelWriter(output1, date_format='d/m/yyyy')
        df1.to_excel(writer, index=False)
        writer.close()
    else:
        print('-'*75)
        print('No New Articles Found')
        
def get_inputs():
 
    print('-'*75)
    print('Processing The Settings Sheet ...')
    # assuming the inputs to be in the same script directory
    path = os.getcwd()
    if '\\' in path:
        path += '\\Jingdaily_settings.xlsx'
    else:
        path += '/Jingdaily_settings.xlsx'

    if not os.path.isfile(path):
        print('Error: Missing the settings file "Jingdaily_settings.xlsx"')
        input('Press any key to exit')
        sys.exit(1)
    try:
        settings = {}
        urls = []
        df = pd.read_excel(path)
        cols  = df.columns
        for col in cols:
            df[col] = df[col].astype(str)

        inds = df.index
        for ind in inds:
            row = df.iloc[ind]
            link, status = '', ''
            for col in cols:
                if row[col] == 'nan': continue
                elif col == 'Category Link':
                    link = row[col]
                elif col == 'Scrape':
                    status = row[col]
                else:
                    settings[col] = row[col]

            if link != '' and status != '':
                try:
                    status = int(status)
                    urls.append((link, status))
                except:
                    urls.append((link, 0))
    except:
        print('Error: Failed to process the settings sheet')
        input('Press any key to exit')
        sys.exit(1)

    return settings, urls

def initialize_output():

    stamp = datetime.now().strftime("%d_%m_%Y_%H_%M")
    path = os.getcwd() + '\\Scraped_Data\\' + stamp
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

    file1 = f'Jingdaily_{stamp}.xlsx'

    # Windws and Linux slashes
    if os.getcwd().find('/') != -1:
        output1 = path.replace('\\', '/') + "/" + file1
    else:
        output1 = path + "\\" + file1  

    # Create an new Excel file and add a worksheet.
    workbook1 = xlsxwriter.Workbook(output1)
    workbook1.add_worksheet()
    workbook1.close()    

    return output1

def main():

    print('Initializing The Bot ...')
    freeze_support()
    start = time.time()
    output1 = initialize_output()
    settings, urls = get_inputs()
    month = datetime.now().month
    year = datetime.now().year
    try:
        driver = initialize_bot()
    except Exception as err:
        print('Failed to initialize the Chrome driver due to the following error:\n')
        print(str(err))
        print('-'*75)
        input('Press any key to exit.')
        sys.exit()

    for url in urls:
        if url[1] != 1: continue
        link = url[0]
        try:
            scrape_articles(driver, output1, link, month, year)
        except Exception as err: 
            print(f'Warning: the below error occurred:\n {err}')
            driver.quit()
            time.sleep(2)
            driver = initialize_bot()

    driver.quit()
    print('-'*75)
    elapsed_time = round(((time.time() - start)/60), 2)
    input(f'Process is completed in {elapsed_time} mins, Press any key to exit.')
    sys.exit()

if __name__ == '__main__':

    main()


