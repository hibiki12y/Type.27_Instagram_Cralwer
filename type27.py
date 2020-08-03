# -*- coding: utf-8 -*-

import warnings
warnings.simplefilter("ignore", UserWarning)
warnings.simplefilter("ignore", FutureWarning)

import json
import argparse
import urllib
import time
import tqdm
import os

import selenium
from selenium import webdriver

def login(id,pw,driver):

    driver.get("https://www.instagram.com/")
    time.sleep(1)

    elem_login = driver.find_element_by_name("username")
    elem_login.clear()
    elem_login.send_keys(id)

    elem_login = driver.find_element_by_name('password')
    elem_login.clear()
    elem_login.send_keys(pw)

    driver.find_element_by_css_selector('#react-root > section > main > article > div.rgFsT > div:nth-child(1) > div > form > div:nth-child(4) > button > div').click()
    print("waiting https request...")
    time.sleep(3)
    try:
        err = driver.find_element_by_xpath('//*[@id="slfErrorAlert"]')
        print(f"login fail : {err.text}")
        raise RuntimeError("login fail")
        
    except selenium.common.exceptions.NoSuchElementException:
        print("login complete!")

def get_driver(args):
    if args.driver == "chrome":
        
        options = webdriver.ChromeOptions()
        if args.headless : options.add_argument('headless')
        options.add_argument("--log-level=2")
        options.add_argument('window-size=1920x1080')

        return webdriver.Chrome(executable_path=args.driver_path,chrome_options=options)
    elif args.driver == "firefox":
        options = webdriver.FirefoxOptions()
        if args.headless : options.add_argument('headless')
        return webdriver.Firefox(executable_path=args.driver_path,firefox_options=options)
    elif args.driver == "phantomjs":
        return webdriver.PhantomJS(executable_path=args.driver_path)
    else:
        print("Invailed driver : use [chrome, firefox, phantomjs]")
        raise AttributeError("Invailed driver")

def query(driver,query,scroll_down,scroll_wait):
    url = f"https://www.instagram.com/explore/tags/{urllib.parse.quote(query)}/"
    print(f"query start : {query}")
    driver.get(url)
    
    print("waiting https request...")
    time.sleep(3)
    
    loader = tqdm.tqdm(range(scroll_down),desc=f"scrolling...")
    for _ in loader:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(scroll_wait)
    loader.close()
    
    urls = []
    for e in driver.find_elements_by_css_selector('#react-root > section > main > article > div > div > div > div > div > a'):
        urls.append(e.get_attribute("href"))
    for e in driver.find_elements_by_css_selector('#react-root > section > main > article > div > div > div > div > a'):
        urls.append(e.get_attribute("href"))

    return urls

def get_contents(driver,url,path):
    driver.get(url)
    user_id = driver.find_element_by_css_selector('#react-root > section > main > div > div > article > div > header > div > div > div > span > a').text
    
    post = driver.find_element_by_css_selector('#react-root > section > main > div > div.ltEKP > article > div > div > div > ul > div > li > div > div > div > span')
    post_text = post.text
    post_hash = {}
    post_mention = {}
    for e in post.find_elements_by_css_selector('a'):
        if e.text[0] == "@" : post_mention[e.text] = e.get_attribute('href')
        elif e.text[0] == "$" : post_hash[e.text] = e.get_attribute('href')
    
    try:
        like = driver.find_element_by_css_selector('#react-root > section > main > div > div > article > div > div.eo2As > section > div > div > button > span').text
    except selenium.common.exceptions.NoSuchElementException : like = "-1"

    reply_list = []
    for e in driver.find_elements_by_css_selector('#react-root > section > main > div > div > article > div > div > div > ul > ul'):
        reply_id = e.find_element_by_css_selector('div > li > div > div > div > h3 > div > span').text
        reply = e.find_element_by_css_selector('div > li > div > div > div > span')
        reply_text = reply.text
        reply_hash = {}
        reply_mention = {}
        for ee in reply.find_elements_by_css_selector('a'):
            if ee.text[0] == "@" : reply_hash[ee.text] = ee.get_attribute('href')
            elif ee.text[0] == "$" : reply_mention[ee.text] = ee.get_attribute('href')
        rereply_list = []
        
        try: 
            ee = e.find_element_by_css_selector('li > ul > li > div > button')
            ee.click()
            for ee in e.find_elements_by_css_selector('li > ul > div'):
                rereply_id = ee.find_element_by_css_selector('div > li > div > div > div > h3 > div > span').text
                rereply = ee.find_element_by_css_selector('div > li > div > div > div > span')
                rereply_text = rereply.text
                rereply_hash = {}
                rereply_mention = {}
                for eee in rereply.find_elements_by_css_selector('a'):
                    if eee.text[0] == "@" : rereply_hash[eee.text] = eee.get_attribute('href')
                    elif eee.text[0] == "$" : rereply_mention[eee.text] = eee.get_attribute('href')
                rereply_list.append({
                    "id" : rereply_id,
                    "text" : rereply_text,
                    "hash" : rereply_hash,
                    "mention" : rereply_mention
                })
        except selenium.common.exceptions.NoSuchElementException: pass
        reply_list.append({
                "id" : reply_id,
                "text" : reply_text,
                "hash" : reply_hash,
                "mention" : reply_mention,
                "rereply" : rereply_list
            })
    
    with open(os.path.join(path,f'{url.split("/p")[-1].replace("/","")}.json'),"w",encoding="utf-8") as f:
        json.dump({
            "id" : user_id,
            "text" : post_text,
            "hash" : post_hash,
            "mention" : post_mention,
            "reply" : reply_list,
            "url" : url,
            "like" : like
        },f)

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='')
    parser.add_argument('query', type=str, nargs='+',help="The query what to crawl")
    parser.add_argument('--insta_id',type=str,help="Instagram account id")
    parser.add_argument('--insta_pw',type=str,help="Instagram account password")
    parser.add_argument('--driver',type=str,default="chrome",help="Crawler driver")
    parser.add_argument('--headless',action="store_true",help="Set headless mode")
    parser.add_argument('--scroll',type=int,default=0,help="Scroll depth of each query")
    parser.add_argument('--scroll_wait',type=float,default=1.0,help="Wait time to get request of scrolling")
    parser.add_argument('--driver_path',type=str,default="./chromedriver.exe",help="Crawler driver path")
    parser.add_argument('--result_path',type=str,default="cache",help="Path to save data")
    

    args = parser.parse_args()
    if not os.path.isdir(args.result_path):
        os.mkdir(args.result_path)
        
    
    driver = get_driver(args)
    login(args.insta_id,args.insta_pw,driver)
    
    for q in args.query:
        urls = query(driver,q,args.scroll,args.scroll_wait)
        for u in urls:
            get_contents(driver,u,args.result_path)
 
    driver.close()
