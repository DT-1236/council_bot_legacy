import urllib #For querying URLs
import time #For timestamping operations
import matplotlib.pyplot as plt #For generating plots
import matplotlib.dates as mdates #For manipulating dates on axes
import re #For use of Regular Expressions
import xmltodict #For parsing XML documents into Python dictionary format
import os #For changing directory, allowing saving of files elsewhere
import sys #Solely for dealing with unrecognized Unicode characters
import datetime #For calculating days since today
from fuzzywuzzy import fuzz #For fuzzy searching
from fuzzywuzzy import process
import Levenshtein #For faster fuzzy searching. Needs to be loaded for fuzzywuzzy to recognize it
import pyodbc #For access to SQL server
import requests #For POST HTML Method
from auxiliary_functions import token_refresh as token_refresh

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

def surf(url):
    result = urllib.request.urlopen(url)
    return result.read()

token,server = token_refresh()

search_threshold = 74

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd) #This uses the fancy Unicode replacement character
#non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0x3F)	#This is just for replacement with plain question marks

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
#        with urllib.request.urlopen(r"http://api2.pixelstarships.com/UserService/SearchUsers?searchString=%s"%(name.replace(' ','%20'))) as response:
        with urllib.request.urlopen(r"http://api.pixelstarships.com/UserService/SearchUsers?searchString=%s"%(name.replace(' ','%20'))) as response:
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

def database():
    time_start=time.clock()
    response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListAlliancesByRanking?skip=0&take=100&accessToken=%s'%(server,token)).read()
    response = xmltodict.parse(response)
    top100 = [] #list of top 100 alliance IDs in string form
    results = [['Date', 'Name', 'MemberID', 'UserType', 'TrophyCount', 'AllianceName', 'AllianceID', 'AllianceRank', 'LastLogin']]
    for x in response['AllianceService']['ListAlliancesByRanking']['Alliances']['Alliance']:
        top100.append(x['@AllianceId'])
    for entry in top100:
        response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(server, entry, token)).read()
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
    os.startfile('PSS Text Import.dtsx')
    os.chdir('..')
    print ('database operation complete')
    print ('Full prep complete. Time Elapsed :'+str(time.clock()-time_start))

def complete(request):
    """Returns complete trophy data over time for a player"""
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
    """Returns complete trophy data over time for an alliance"""
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
    """Auxiliary function which attempts to parse through similar entries. e.g. oOFritzOo vs. o0Fritz0o"""
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
    """Returns average member trophy data over time for an alliance"""
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
    """Returns alliance history data for a member"""
    try:
        int(ID)
    except:
        ID = int(member_lookup(ID)[0][1])
    cursor.execute("select Date,AllianceName,AllianceID from dbo.[Full Data] where MemberID = '%s' order by Date asc"%ID)
    history = cursor.fetchall()
    results = [('Date', 'Alliance Name', 'Alliance ID')]
    results.append(history[0])
    for entry in history:
        if entry[-1] != results[-1][-1]:
            results.append(entry)
    return (results, ID)

def inactives(ID):
    """Returns a .txt file containing all members of an alliance and their last login dates"""
    time_start=time.clock()
    try:
        ID = int(ID)
    except:
        return ("Input must be Alliance ID. Use alliance_lookup or (&lookup alliance, [name])")
    roster = cursor.execute("select Name,MemberID from dbo.[Full Data] where AllianceID = %s and Date = '%s'"%(ID,'2017-04-28'))#str(datetime.date.today())))
    roster = roster.fetchall()
    results = []
    for entry in roster:
        info = surf("http://api%s.pixelstarships.com//ShipService/InspectShip?userId=%s&accessToken=%s"%(server, entry[1], token))
        info = xmltodict.parse(info)
        results.append((entry[0],str(date_object(info['ShipService']['InspectShip']['User']['@LastLoginDate']))))
        try:
            print ("%s complete"%entry[0])
        except:
            print ("entry complete. Name is weird.")
    results = sorted(results, key = lambda x: x[1])
    os.chdir('lists')
    output = open('%s - %s Inactives.txt'%(str(datetime.date.today()),allianceIDs[ID]), 'wb')
    for entry in results:
        output.write(str(entry).encode('utf-8'))
        output.write('\n'.encode('utf-8'))
    output.close()
    os.chdir('..')
    print ('Full prep complete. Time Elapsed :'+str(time.clock()-time_start))
    return "Inactive list creation complete"

def top100_dupe_check():
    """Attempts to check all crew of members of top100 alliances for Crew IDs which are suspiciously close together"""
    time_start=time.clock()
    response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListAlliancesByRanking?skip=0&take=100&accessToken=%s'%(server,token)).read()
    response = xmltodict.parse(response)
    top100 = [] #list of top 100 alliance IDs in string form
    results = 'Date&@&Name&@&MemberID&@&AllianceName&@&AllianceID&@&Pairs%|%'
    for x in response['AllianceService']['ListAlliancesByRanking']['Alliances']['Alliance']:
        top100.append(x['@AllianceId'])
    for entry in top100:
        response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(server, entry, token)).read()
        response = xmltodict.parse(response) #This will be the list of members in an alliance
        roster = response['AllianceService']['ListUsers']['Users']['User']
        for member in roster:
            date = str(datetime.date.today())
            name = member['@Name']
            member_id = member['@Id']
            alliance = member['@AllianceName']
            alliance_id = entry
            pairs = duplicates(member_id)
            if pairs:
                results = results+date+'&@&'+name+'&@&'+str(member_id)+'&@&'+alliance+'&@&'+str(alliance_id)+'&@&'+str(pairs)+'%|%'
            print ('%s complete'%member_id)
        try:
            print ('%s : %s complete'%(roster[0]['@AllianceName'], roster[0]['@AllianceId']))
        except:
            print ('%s complete. Alliance name is weird'%roster[0]['@AllianceId'])
    os.chdir('dupes')
    output = open("data.txt", 'wb')
    backup = open("%s.txt"%str(datetime.date.today()), 'wb')
    output.write(results.encode("utf-8"))
    backup.write(results.encode("utf-8"))
    output.close()
    backup.close()
#    os.startfile('PSS Text Import.dtsx') This will be replaced if I create an SSIS package to import crew data over time
    os.chdir('..')
    print ('top100 dupe check operation complete')
    print ('Full prep complete. Time Elapsed :'+str(time.clock()-time_start))

def alliance_dupe_check(ID):
    """Attempts to check all crew of members of a single alliance for Crew IDs which are suspiciously close together"""
    time_start=time.clock()
    results = 'Date&@&Name&@&MemberID&@&AllianceName&@&AllianceID&@&Pairs%|%'
    response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(server, ID, token)).read()
    response = xmltodict.parse(response) #This will be the list of members in an alliance
    roster = response['AllianceService']['ListUsers']['Users']['User']
    for member in roster:
        date = str(datetime.date.today())
        name = member['@Name']
        member_id = member['@Id']
        alliance = member['@AllianceName']
        alliance_id = entry
        pairs = duplicates(member_id)
        if pairs:
            results = results+date+'&@&'+name+'&@&'+str(member_id)+'&@&'+alliance+'&@&'+str(alliance_id)+'&@&'+str(pairs)+'%|%'
        print ('%s complete'%member_id)
    try:
        print ('%s : %s complete'%(roster[0]['@AllianceName'], roster[0]['@AllianceId']))
    except:
        print ('%s complete. Alliance name is weird'%roster[0]['@AllianceId'])
    os.chdir('dupes')
    output = open("data.txt", 'wb')
    backup = open("%s.txt"%str(datetime.date.today()), 'wb')
    output.write(results.encode("utf-8"))
    backup.write(results.encode("utf-8"))
    output.close()
    backup.close()
    os.chdir('..')
    print ('alliance dupe check operation complete')
    print ('Full prep complete. Time Elapsed :'+str(time.clock()-time_start))

def crew_data(ID):
    """Returns crew data for a player"""
    try:
        ID = int(ID)
    except:
        return ("Input must be Member ID. Use member_lookup or (&lookup member, [name])")
    try:
        info = surf("http://api%s.pixelstarships.com//ShipService/InspectShip?userId=%s&accessToken=%s"%(server, ID, token))
        info = xmltodict.parse(info)
    except:
        token_refresh()
        info = surf("http://api%s.pixelstarships.com//ShipService/InspectShip?userId=%s&accessToken=%s"%(server, ID, token))
        info = xmltodict.parse(info)
    try:
        results = [(x['@CharacterName'], x['@CharacterId']) for x in info['ShipService']['InspectShip']['Ship']['Characters']['Character']]
    except:
        print("Operation failed. Either the Member ID is not in Savy's servers or the token is invalid. Refresh token with token_refresh() or &token")
        return "Operation failed. Either the Member ID is not in Savy's servers or the token is invalid. Refresh token with token_refresh() or &token"
    return sorted(results, key = lambda x: x[1])

def duplicates(ID):
    """Returns a list of crew with IDs which are similarly close together"""
    roster = crew_data(ID)
    results = []
    [results.append([roster[x], roster[x-1], (int(roster[x][1]) - int(roster[x-1][1]))]) for x in range(0, len(roster)) if (0 < (int(roster[x][1]) - int(roster[x-1][1])) < 50)]
    return results

def alliance_lookup(name):
    """Returns the top 5 hits for alliances listed in the SQL server"""
    try:
        return [(allianceIDs[int(name)], name)]
    except:
        return [(x[0], alliances[x[0]])for x in process.extract(name, alliances.keys(), scorer = fuzz.token_set_ratio)]

def member_lookup(name):
    """Returns the top 5 hits for players listed in the SQL server"""
    try:
        return [(memberIDs[int(name)], name)]
    except:
        return [(x[0], names[x[0]])for x in process.extract(name, names.keys(), scorer = fuzz.token_set_ratio)]

def recipient(ID):
    """Returns information on recipients of donated crew"""
    try:
        ID = int(ID)
    except:
        ID = member_lookup(ID)[0][1]
    info = surf('http://api%s.pixelstarships.com//ShipService/InspectShip?userId=%s&accessToken=%s'%(server, ID, token))
    info = xmltodict.parse(info)
    alliance = info['ShipService']['InspectShip']['User']['@AllianceId']
    owner = info['ShipService']['InspectShip']['Ship']['@ShipId']
    response = urllib.request.urlopen('http://api%s.pixelstarships.com/AllianceService/ListUsers?allianceId=%s&skip=0&take=100&accessToken=%s'%(server, alliance, token)).read()
    response = xmltodict.parse(response) #This will be the list of members in an alliance
    roster = response['AllianceService']['ListUsers']['Users']['User']
    results = []
    ship = {}
    for member in roster:
        member_id = member['@Id']
        info = surf('http://api%s.pixelstarships.com//ShipService/InspectShip?userId=%s&accessToken=%s'%(server, member_id, token))
        info = xmltodict.parse(info)
        interim = [(x['@CharacterName'], x['@OwnerShipId']) for x in info['ShipService']['InspectShip']['Ship']['Characters']['Character'] if x['@ShipId'] != x['@OwnerShipId']]
        [results.append((x[0], member['@Name'])) for x in interim if x[1]==owner]
    return results

#A list of commonly used numbers personal testing
#main = 4678
#3.0 = 5736
#2.0 = 5507
#DT = 747763
