#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys

sys.path.append('/var/www/gai.alev.me/')

import web
from pymongo import Connection
import sys
import json
from httplib2 import Http
from urllib import urlencode
import lxml.html
import cgi
import re

connection = Connection()
db = connection['gai']
subs = db['subs']

class Parser:
    def fetchData(self, drivers_license, car_number):
        h = Http()
        data = {'form_type':'vehicle',
        'drivers_license': drivers_license.encode('cp1251'),
        'identification_number': car_number.encode('cp1251')}

        headers = {"Content-Type":"application/x-www-form-urlencoded",
        'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.17 (KHTML, like Gecko) Chrome/24.0.1312.70 Safari/537.17',
        'Cookie':'PHPSESSID=1eb45d2b0912ff25b94fbf93ca1eb256; __utma=266650824.818308535.1360661640.1360661640.1360947773.2; __utmb=266650824.2.10.1360947773; utmcmd=organic|utmctr=(not%20provided)',
        'Accept': '*/*',
        'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding':'gzip,deflate,sdch',
        'Connection':'keep-alive',
        'Host':'73.gibdd.ru',
        'Origin':'http://73.gibdd.ru',
        'Referer':'http://73.gibdd.ru/fines/'}

        resp, content = h.request("http://73.gibdd.ru/fines/", "POST", body=urlencode(data), headers=headers)
        tree = lxml.html.document_fromstring(content)
        result = []
        sum = 0
        for straf in tree.find_class('straf'):
            if len(straf.find_class('non-paid')) > 0:
                date = straf.find_class('news_date')[0].text_content()

                txs = straf.find_class('news_text')
                obj = {'date':date,
                  'number':txs[1].text_content(),
                  'clause':txs[3].text_content(),
                  'amount':txs[5].text_content(),
                  'okato':txs[7].text_content()}
                result.append(obj)
                sum += int(re.match(r'\d+', txs[5].text_content()).group())
        return {"list":result, "sum":sum}

def send_email(email, sum):
    import smtplib

    gmail_user = "privetgai@gmail.com"
    f = open('emailpasswd', 'r')
    gmail_pwd = f.readline()
    FROM = 'privetgai@gmail.com'
    TO = [email]
    SUBJECT = 'Privet iz GAI'
    TEXT = 'Vam nachisleni shtrafi na summu %s, proverte na http://73.gibdd.ru/fines/' % sum

    message = """\From: %s\nTo: %s\nSubject: %s\n\n%s
    """ % (FROM, ", ".join(TO), SUBJECT, TEXT)
    try:
        #server = smtplib.SMTP(SERVER) 
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(gmail_user, gmail_pwd)
        server.sendmail(FROM, TO, message)
        #server.quit()
        server.close()
        print 'successfully sent the mail to ' + email
    except:
        print "Unexpected error:", sys.exc_info()[0]
        print "failed to send mail to "+email

# for cron
def notifyAll(email = None):
    cursor = subs.find()
    rs = []
    parser = Parser()
    for i in cursor:
        data = parser.fetchData(i['svidet'],i['gosnomer'])
        if data['sum'] > 0 or (email != None and i['email'] == email):
            send_email(i['email'], data['sum'])

class fetch:
    def POST(self):
        data = web.input()
        return json.dumps(data)
    def GET(self):
        data = web.input()
        result = {}
        parser = Parser()
        result = parser.fetchData(data.svidet, data.gosnomer)

        stored = subs.find_one({'svidet':data.svidet,'gosnomer':data.gosnomer})
        if stored:
            result['subs'] = stored['email']

        return json.dumps(result)

class subscribe:
    def GET(self):
        data = web.input()
        stored = subs.find_one({'svidet':data.svidet,'gosnomer':data.gosnomer})
        if stored:
	  notifyAll(stored['email'])  
          return json.dumps({'status':1,'desc':stored['email']})
        else:
          subs.insert({'svidet':data.svidet,'gosnomer':data.gosnomer,'email':data.email})
          notifyAll(data.email)
          return json.dumps({'status':0})

urls = (
    '/fetch', fetch,
    '/subscribe', subscribe,
)

web.config.session_parameters["cookie_path"] = "/"
app = web.application(urls, globals())
if __name__ == "__main__": app.run()
application = app.wsgifunc()
