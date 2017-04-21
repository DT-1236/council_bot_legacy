import urllib #For querying URLs
import time #For timestamping operations
import matplotlib.pyplot as plt #For generating plots
import matplotlib.dates as mdates #For manipulating dates on axes
import re #For use of Regular Expressions
import xmltodict #For parsing XML documents into Python dictionary format
import os #For changing directory, allowing saving of files elsewhere
import sys
import datetime #For calculating days since today
from fuzzywuzzy import fuzz #For fuzzy searching
from fuzzywuzzy import process
import Levenshtein #For faster fuzzy searching. Needs to be loaded for fuzzywuzzy to recognize it
import pyodbc #For access to SQL server

cnxn = pyodbc.connect('DRIVER={SQL Server};SERVER=GUNGNIR\DTSQL;DATABASE=PSS') #Connect to my SQL. I dont' think anyone but Gungnir can do this currently
cursor = cnxn.cursor()

cursor.execute('select DISTINCT(Name),MemberID from dbo.[Full Data] order by Name asc')
names = {} #Name to MemberID
memberIDs = {} #MemberID to Name
for entry in cursor.fetchall():
    names[entry[0]] = entry[1]
    try: #It might be slow, but I'm going to try to catch name changes here
        memberIDs[entry[1]].append(entry[0])
    except:
        memberIDs[entry[1]] = entry[0]

cursor.execute('select DISTINCT(AllianceName),AllianceID from dbo.[Full Data]')
alliances = {} #AllianceName to AllianceID
allianceIDs = {} #AllianceID to AllianceName
for entry in cursor.fetchall():
    alliances[entry[0]] = entry[1]
    allianceIDs[entry[1]] = entry[0]

data = {"I'm just here so I don't throw errors":"N/A"}
interim = open("token.json", "r")
token = interim.read()
token = token[1+(token.find('=', token.find("Token"))):]
interim.close()

#alliances = {} #A Holdover from the 'members' function
search_threshold = 74

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd) #This uses the fancy Unicode replacement character. Too bad SQL doesn't understand it well
#non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0x3F)	#This is just for plain question marks

def date_object(raw):
    year = int(raw[0:4])
    if int(raw[5]) == 0:
        month = int(raw[6])
    else:
        month = int(raw[5:7])
    if int(raw[8]) == 0:
        day = int(raw[9])
    else:
        day = int(raw[8:10])
    return datetime.date(year, month, day)

def date_graph(names, axes):
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    for x in range(0, len(names)):
        plt.plot(axes[x][0], axes[x][1], label = names[x])
    plt.legend(loc=0)
    plt.gcf().autofmt_xdate()
    os.chdir('plots')
    plt.savefig("plot.png")
    plt.close()
    os.chdir('..')

def get_data(name): # Have to check of len(source['UserService']['SearchUsers']['Users']['User']) > 1
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

def allegiance(name):
    result = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)
    if result[1] < 84:
        get_data(name)
    request = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)[0]
    if '@AllianceName' in data[request]['UserService']['SearchUsers']['Users']['User']:
        phrase = "Current alliance for %s is ```\n%s```"%(request, data[request]['UserService']['SearchUsers']['Users']['User']['@AllianceName'])
    else:
        phrase = "%s does not appear to be in an alliance at this time."
    return phrase
    
def trophies(name):
    result = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)
    if result[1] < 84:
        get_data(name)
    request = process.extractOne(name, data.keys(), scorer = fuzz.token_sort_ratio)[0]
    return "Current trophy count for %s is ```\n%s```"%(request, data[request]['UserService']['SearchUsers']['Users']['User']['@Trophy'])
    
def refresh(name):
    if name in data.keys():
        phrase = "Entry for %s was updated"%source['UserService']['SearchUsers']['Users']['User']['@Name']
    else:
        phrase = "Entry for %s was created"%source['UserService']['SearchUsers']['Users']['User']['@Name']
    with urllib.request.urlopen(r"http://api2.pixelstarships.com/UserService/SearchUsers?searchString=%s"%(name.replace(' ','%20'))) as response:
        response = response.read()
    source = xmltodict.parse(response)
    try:
        data[source['UserService']['SearchUsers']['Users']['User']['@Name']] = source
    except:
        return "Invalid UserName"
    print (phrase)
"""
def members(alliance_id):
    with urllib.request.urlopen(r"http://api2.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s"%(alliance_id,token)) as response:
        response = response.read()
    source = xmltodict.parse(response)
    roster = source['AllianceService']['ListUsers']['Users']['User']
    results = []
    inactives = []
    actives = []
    active_trophies = 0
    for member in roster:
        name = member['@Name']
        trophies = member['@Trophy']
        lastLogin = date_object(member['@LastLoginDate'])
        results.append([name, trophies, lastLogin])
        elapsed = (lastLogin-lastLogin.today()).days
        if elapsed < -7:
            inactives.append([name, trophies, elapsed])
        else:
            actives.append([name, trophies])
            active_trophies += int(trophies)
    alliance_name = roster[0]['@AllianceName']
    output = open("%s.txt"%alliance_name, 'wb')
    if alliance_name not in alliances:
        alliances[alliance_name] = {'actives':actives, 'active trophies':active_trophies, 'inactives':inactives}
    for entry in results:
        try:
            output.write(("%s\n"%entry).encode("utf-8"))
        except:
            for item in range(0, len(entry)):
                entry[item] = entry[item].translate(non_bmp_map)
            output.write(("%s\n"%entry).encode("utf-8"))
    output.close()
    output = open("%s inactives.txt"%alliance_name, 'wb')
    for entry in inactives:
        try:
            output.write(("%s\n"%entry).encode("utf-8"))
        except:
            for item in range(0, len(entry)):
                entry[item] = entry[item].translate(non_bmp_map)
            output.write(("%s\n"%entry).encode("utf-8"))
    output.close()
    return
"""
def database():
    time_start=time.clock()
    with urllib.request.urlopen('http://api.pixelstarships.com/AllianceService/ListAlliancesByRanking?skip=0&take=100&accessToken=%s'%token) as response:
#    with urllib.request.urlopen('http://api2.pixelstarships.com/AllianceService/ListAlliancesByRanking?skip=0&take=100&accessToken=%s'%token) as response:
        response = response.read()
    response = xmltodict.parse(response)
    top100 = [] #list of top 100 alliance IDs in string form
    results = [['Date', 'Name', 'MemberID', 'UserType', 'TrophyCount', 'AllianceName', 'AllianceID', 'AllianceRank', 'LastLogin']]
    for x in response['AllianceService']['ListAlliancesByRanking']['Alliances']['Alliance']:
        top100.append(x['@AllianceId'])
    for entry in top100:
        with urllib.request.urlopen('http://api.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(entry, token)) as response:
#        with urllib.request.urlopen('http://api2.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(entry, token)) as response:
            response = response.read()
        response = xmltodict.parse(response) #This will be the list of members in an alliance
        roster = response['AllianceService']['ListUsers']['Users']['User']
        for member in roster:
            date = str(datetime.date.today())
            name = member['@Name']
            member_id = member['@Id']
            user_type = member['@UserType']
            alliance = member['@AllianceName']
            alliance_id = entry
            trophies = member['@Trophy']
            alliance_rank = member['@AllianceMembership']
            last_login = str(date_object(member['@LastLoginDate']))
            results.append([date,name,member_id,user_type,trophies,alliance,entry,alliance_rank,last_login])
        try:
            print ('%s : %s complete'%(entry, roster[0]['@AllianceName']))
        except:
            print ('%s complete. Alliance name is weird'%entry)
    os.chdir('data')
    output = open("data.txt", 'wb')
    backup = open("%s.txt"%str(datetime.date.today()), 'wb')
    for entry in results:
        try:
            output.write(('&@&'.join(entry)+'%|%').encode("utf-8"))
            backup.write(('&@&'.join(entry)+'%|%').encode("utf-8"))
        except:
            for item in range(0, len(entry)):
                entry[item] = entry[item].translate(non_bmp_map)
            output.write(('&@&'.join(entry)+'%|%').encode("utf-8"))
            backup.write(('&@&'.join(entry)+'%|%').encode("utf-8"))
    output.close()
    backup.close()    
    os.chdir('..')
    print ('database operation complete')
    print ('Full prep complete. Time Elapsed :'+str(time.clock()-time_start))

def complete(request):
    request = multi_input('member', request)
    results = [request[1],[]]
    for entry in request[0]:
        cursor.execute("select Date,TrophyCount,Name from PSS.dbo.[Full Data] where MemberID = %s order by Date asc"%entry)
        query = cursor.fetchall()
        xcoord = [datetime.datetime.strptime(x[0], '%Y-%m-%d') for x in query]
        ycoord = [x[1] for x in query]
        results[1].append([xcoord, ycoord])
    date_graph(results[0], results[1])
    return (results[0],request[0])

def alliance(request):
    request = multi_input('alliance', request)
    results = [request[1],[]]
    for entry in request[0]:
        cursor.execute("select Date,sum(TrophyCount) from dbo.[Full Data] where AllianceID = %s GROUP BY Date order by Date asc"%entry)
        query = cursor.fetchall()
        xcoord = [datetime.datetime.strptime(x[0], '%Y-%m-%d') for x in query]
        ycoord = [x[1] for x in query]
        results[1].append([xcoord, ycoord])
    date_graph(results[0], results[1])
    return (results[0],request[0])

def multi_input(scope, interim):
    interim = interim.split(',')
    request = []
    if scope == 'alliance':
        source = alliances
        sourceID = allianceIDs
    if scope == 'member':
        source = names
        sourceID = memberIDs
    for entry in interim:
        try:
            int(entry)
            request.append(int(entry))
        except:
            similarity_check = process.extract(entry, source.keys(), scorer = fuzz.token_set_ratio)
            if similarity_check[0][1] == similarity_check[1][1]: #This will weight entries which contain the complete query. e.g. Zakidos will be higher than Little Zakidos when searching just Zakidos
                similarity_check = process.extract(entry, source.keys(), scorer = fuzz.ratio, processor = lambda x:x)
            entry = similarity_check[0][0]
            request.append(source[entry])
    request_names = [sourceID[x] for x in request]
    return request, request_names

def average(request):
    request = multi_input('alliance', request)
    results = [request[1],[]]
    for entry in request[0]:
        cursor.execute("select Date,AVG(TrophyCount) from dbo.[Full Data] where AllianceID = %s GROUP BY Date order by Date asc"%entry)
        query = cursor.fetchall()
        xcoord = [datetime.datetime.strptime(x[0], '%Y-%m-%d') for x in query]
        ycoord = [x[1] for x in query]
        results[1].append([xcoord, ycoord])
    date_graph(results[0], results[1])
    return (results[0],request[0])

def history(ID):
    try:
        int(ID)
    except:
        ID = member_lookup(ID)[0][1]
    cursor.execute("select Date,AllianceName,AllianceID from dbo.[Full Data] where MemberID = '%s' order by Date asc"%ID)
    history = cursor.fetchall()
    results = [('Date', 'Alliance Name', 'Alliance ID')]
    results.append(history[0])
    for entry in history:
        if entry[-1] != results[-1][-1]:
            results.append(entry)
    return (results, ID)

def alliance_lookup(name):
    return [(x[0], alliances[x[0]])for x in process.extract(name, alliances.keys(), scorer = fuzz.token_set_ratio)]

def member_lookup(name):
    return [(x[0], names[x[0]])for x in process.extract(name, names.keys(), scorer = fuzz.token_set_ratio)]
    
#cursor.execute("select Date,TrophyCount from PSS.dbo.[Full Data] where MemberID = 747763 order by Date asc")
