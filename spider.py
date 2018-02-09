from urllib.parse import urlencode

from lxml.etree import XMLSyntaxError
from requests.exceptions import ConnectionError
import requests
from pyquery import PyQuery as pq
import pymongo
from config import *

client=pymongo.MongoClient(MONGO_URI)
db=client[MONGO_DB]


base_url='http://weixin.sogou.com/weixin?'
headers={
    'Cookie':'IPLOC=CN1100; SUID=411AF2725F20940A000000005A054ADE; SUV=1510296287205441; ABTEST=0|1510296292|v1; weixinIndexVisited=1; sct=6; JSESSIONID=aaaMUPnUrU10WaFywzv8v; ppinf=5|1510540758|1511750358|dHJ1c3Q6MToxfGNsaWVudGlkOjQ6MjAxN3x1bmlxbmFtZToxODolRTUlOTElQTglRTglOEUlQUJ8Y3J0OjEwOjE1MTA1NDA3NTh8cmVmbmljazoxODolRTUlOTElQTglRTglOEUlQUJ8dXNlcmlkOjQ0Om85dDJsdUtab1NndkdLME5uSS11RUVKUk5HWmNAd2VpeGluLnNvaHUuY29tfA; pprdig=WCK5t2BGiOvUcd0hWshCAvtoK8SoMFv3GzRSAs8SR9JYFXlT19yau6qxPf54MD7D11ST2rBMPmxNI1KkkQcBtc8j7j6mySpSJH-H_WWrrId9zI1L81g9lIQ3s7n0CYpH9hOnP2XXe0ImwVAz1YjZSYGq7NsInerzkAAcrIpaw0A; sgid=29-31883571-AVoJBdZKCpSdKsibbIDcrkaU; PHPSESSID=2qrpqe00ljj3u6mvcubqalk4h1; SUIR=4812FA7B090D55924B0ED3D909CC99E3; SNUID=B79976F18386DE51B46911128466A1DA; ppmdig=1510619687000000c101358797b949f6b5bda5eedec6d3ab',
    'Host':'weixin.sogou.com',
    'Referer':'http://weixin.sogou.com/antispider/?from=%2fweixin%3Fquery%3d%E9%A3%8E%E6%99%AF%26type%3d2%26page%3d90%26ie%3dutf8',
    'Upgrade-Insecure-Requests':'1',
    'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/62.0.3202.89 Safari/537.36'
}
proxy_pool_url='http://127.0.0.1:5000/get'
#一开始不用代理,用自己本机的代理,并且设置全局变量
proxy=None
max_count=5  #

#获取代理
def get_proxy():
    try:
        response=requests.get(PROXY_POOL_URL)
        if response.status_code==200:
            return response.text
        return None
    except ConnectionError:
        return None


#用代理请求时会不一样,所以单独拿出来设置
def get_html(url,count=1): #标示下请求次数,不会一直请求
    print('Crawling',url)   #输出每次请求的url
    print('Trying Count',count)  #输出请求的次数
    global proxy
    if count >= MAX_COUNT:  #请求太多就不用请求了
        print('Tried Too Many Counts')
        return None
    try:
        if proxy:  #判断是否有代理
            #有就重写下,proxies是在response下的代理
            proxies={
                'http':'http://'+proxy
            }
            response = requests.get(url, allow_redirects=False, headers=headers,proxies=proxies)
        else:
            response = requests.get(url, allow_redirects=False, headers=headers)
        #allow_redirects=False不让其自动跳转
        response=requests.get(url,allow_redirects=False,headers=headers)
        if response.status_code==200:
           # print(response.url)
            return response.text
        if response.status_code==302:
            print('status_code',response.status_code)
            # print(response.url)
            proxy=get_proxy()
            if proxy:
                print('Using Proxy',proxy)
                return get_html(url) #得到代理后重新开始获取url
            else:
                print('Get Proxy Filed')
                return None
    except ConnectionError as e:
        print('Error Occurred',e.args) #出现异常,显示异常的实例
        proxy=get_proxy()   #出现异常度可以时下
        count+=1  #若出现请求错误,就请求次数+1
        return get_html(url,count)  #重新第归调用

def get_index(keyword,page):
    data={
        'type': 2,
        'page': page,
        'query': keyword,
        'ie': 'utf8'
    }
    queries=urlencode(data)
    url=base_url+queries
    html=get_html(url)
    return html

def parse_index(html):
    doc=pq(html)
    items=doc('.wrapper #main .news-box .news-list li .txt-box h3 a').items()
    for item in items:
        yield item.attr('href')

def get_detail(url):
    try:
        response=requests.get(url)
        if response.status_code==200:
            return response.text
        return None
    except ConnectionError:
        return None

def parse_detail(html):
    try:
        doc=pq(html)
        title=doc('#activity-name').text()
        content=doc('.rich_media_content').text()
        date=doc('#post-date').text()
        nickname=doc('#js_profile_qrcode > div > strong').text()
        wechat=doc('#js_profile_qrcode .profile_meta .profile_meta_value').text()
        return {
            'title':title,
            'content':content,
            'date':date,
            'nickname':nickname,
            'wechat':wechat
        }
    except XMLSyntaxError:
        return None

#存在数据库中
def save_to_mongo(data):
    #如果后面的data和其他data一样就返回True
    if db['articles'].update({'title':data['title']},{'$set':data},True):
        print('Save to Mongo',data['title'])
    else:
        print('Save to Mongo Failer',data['title'])


def main():
    for page in range(1,101):
        html=get_index(KEYWORD,page)
        article_urls=parse_index(html)
        for article_url in article_urls:
            article_html=get_detail(article_url)
            if article_html:
                article_data=parse_detail(article_html)
                print(article_data)
                save_to_mongo(article_data)

if __name__=='__main__':
    main()






