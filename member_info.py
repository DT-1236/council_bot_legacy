import urllib
import time
import matplotlib.pyplot as plt
import re
import xmltodict
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import Levenshtein

data = {"I'm just here so I don't throw errors":"N/A"}

def get_data(name):
    if name not in data.keys():
        with urllib.request.urlopen(r"http://api2.pixelstarships.com/UserService/SearchUsers?searchString=%s"%(name.replace(' ','%20'))) as response:
            response = response.read()
        source = xmltodict.parse(response)
        try:
            data[source['UserService']['SearchUsers']['Users']['User']['@Name']] = source
        except:
            return "Invalid UserName"
    else:
        return "Data for %s was already collected today"%name
    print ("Data for %s was collected successfully"%source['UserService']['SearchUsers']['Users']['User']['@Name'])
    return

def last_login(name):
    result = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)
    if result[1] < 84:
        get_data(name)
    request = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)[0]
    return "Last login for %s was ```\n%s```"%(request, data[request]['UserService']['SearchUsers']['Users']['User']['@LastLoginDate'])

def alliance(name):
    result = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)
    if result[1] < 84:
        get_data(name)
    request = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)[0]
    return "Current alliance for %s is ```\n%s```"%(request, data[request]['UserService']['SearchUsers']['Users']['User']['@AllianceName'])
    
def trophies(name):
    result = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)
    if result[1] < 84:
        get_data(name)
    request = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)[0]
    return "Current trophy count for %s is ```\n%s```"%(request, data[request]['UserService']['SearchUsers']['Users']['User']['@Trophy'])

def refresh(name):
    if name in data.keys():
        phrase = "Entry for %s was updated"%source['UserService']['SearchUsers']['Users']['User']['@Name'])
    else:
        phrase = "Entry for %s was created"%source['UserService']['SearchUsers']['Users']['User']['@Name'])
    with urllib.request.urlopen(r"http://api2.pixelstarships.com/UserService/SearchUsers?searchString=%s"%(name.replace(' ','%20'))) as response:
        response = response.read()
    source = xmltodict.parse(response)
    try:
        data[source['UserService']['SearchUsers']['Users']['User']['@Name']] = source
    except:
        return "Invalid UserName"
    print (phrase)
