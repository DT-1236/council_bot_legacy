import urllib
import time
import matplotlib.pyplot as plt

#    print (('Data prep complete. Time Elapsed :')+str(time.clock()-time_start))

import re
import discord
from discord.ext import commands
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import logging
import Levenshtein

logger = logging.getLogger('discord')
logger.setLevel(logging.CRITICAL)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)


#calendar = {'1':'Jan', '2':'Feb', '3':'Mar', '4':'Apr', '5':'May', '6':'June', '7':'July', '8':'August', '9':'Sep', '10':'Oct', '11':'Nov', '12':'Dec'}
calendar = {'01':' Jan ', '02':' Feb ', '03':' Mar ', '04':' Apr ', '05':' May ', '06':' Jun ', '07':' Jul ', '08':' Aug ', '09':' Sep ', '10':' Oct ', '11':' Nov ', '12':' Dec '}
    
class Poll:

    polls={}#Dictionary of polls. Keys are strings which contain poll.name. Values are the Poll objects themselves which contain a dictionary of voter information

    def __init__(self, ctx, name):
        self.name = name
        self.deletion = False
        Poll.polls[self.name]=self
        self.votes = {}
        present = [x for x in ctx.channel.members if not x.bot and x.status is not discord.Status.offline]
        for x in present:
            self.votes[x.name]='No vote recorded' #Keys are strings containing names of present members

    def all_polls():
        return [x.name for x in Poll.polls]

    def results(self):
        tally = zip(Poll.polls[self.name].votes.keys(),Poll.polls[self.name].votes.values())
        return ("Current Results for Poll:%s \n"%(Poll.polls[self.name].name)+"```\n"+"%s\n"*len((Poll.polls[self.name].votes))%tuple([x for x in tally])+"```")

class Secret(Poll):

    def results(self):
        tally = (Poll.polls[self.name].votes.values())
        return ("Current Results for secret poll, %s: \n"%(Poll.polls[self.name].name)+"```\n"+"%s\n"*len((Poll.polls[self.name].votes))%tuple([x for x in tally])+"```")

class Record: # Do it offline. You're hitting sharky's site too often. Reg-ex the dates. distance from 'sortfield' actually varies accross entries

    record_list={}

    def __init__(self, user_ign):
        time_start = time.clock()
        self.name = user_ign
        Record.record_list[self.name] = self
#        time_start=time.clock()
        with urllib.request.urlopen(r"http://stats.wolfpackpss.com/quickSearch/%s"%(user_ign.replace(' ','%20'))) as response:
            source = response.read()
        user_id=re.search(r"\d+", source.decode("utf-8")).group()
        with urllib.request.urlopen(r'http://stats.wolfpackpss.com/graphDetail/trophy/u-%s'%(user_id)) as response:
            history = response.read()
        history=history.decode("utf-8").lower()#lower() is used to rectify formatting issues
        history=history[history.find(r'{'):] #find the start of the first data set
        date_start=history.find(r'"sortfield"')+13 #finding information regarding the first date in the first data set
        x_coord=[history[date_start+3:date_start+14]]
        print (x_coord)
        x_coord[0]=x_coord[0].replace(x_coord[0][0:2],calendar[x_coord[0][0:2]])
        self.x_coord_short = []
        self.trophies_short = []
        self.username = user_ign.lower()#lower() to match the case of history
        name_start = history.find((r'"%s"')%(self.username))+len(self.username)+4
        trophies = [history[name_start:history.find(r'.')]]
        while history.find(r'{',1)>0:
            history = history[history.find(r'{',1):] #find the next set of data
            trophy = history[name_start:history.find(r'.')]
            current_time = history[date_start:date_start+14]
            if trophy != trophies[-1]: #only append new trophy counts
                trophies.append(trophy)
                print (current_time)
                print (current_time[4:8])
                x_coord.append(current_time[4:8].replace(current_time[4:6],calendar[current_time[4:6]]))
                if x_coord[-2] != current_time[4:8]: #only append new dates
                    self.x_coord_short.append(current_time[4:8].replace(current_time[4:6],calendar[current_time[4:6]]))
                    self.trophies_short.append(trophy)
#        for x in range(0,len(x_coord)-1):
#            x_coord[x]=x_coord[x].replace(x_coord[x][0:2],calendar[x_coord[x][0:2]])
        self.x_coord_long = x_coord
        self.trophies_long = trophies
        if len(self.trophies_short)<11:#these blocks will create a list of the last 10 days with unique trophies
            self.trophies_recent = self.trophies_short
            self.x_coord_recent = self.x_coord_short
        else:
            self.trophies_recent = self.trophies_short[-10:]
            self.x_coord_recent = self.x_coord_short[-10:]
        print (('Data prep complete. Time Elapsed :')+str(time.clock()-time_start))
        print (self.x_coord_short)
        
    def recent_plot(self):
        plt.figure()
        plt.plot(self.x_coord_recent, self.trophies_recent)
        plt.xlabel("Dates")
        plt.ylabel("Trophies")
        plt.title("Recent Activity - %s"%(self.name))
        plt.savefig("%s recent.png"%(self.name))

description = '''A Council bot to execute council functions.'''
bot = commands.Bot(command_prefix='&', description=description)
        
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(aliases=['Recent'])
async def recent(ctx,*,request : str=''):
    if request and request not in Record.record_list:
        Record.record_list[request] = Record(request)
    Record.record_list[request].recent_plot()
    with open('%s recent.png'%Record.record_list[request].name, 'rb') as plot:
        await bot.send_file(ctx.message.channel, plot)

@bot.command(aliases=['Polls','Poll','poll'])
async def polls(ctx,*,request : str=''):
    """(): Returns a list of all active polls\n"""
    phrase = "Active polls:\n"+"```\n"+"%s\n"*len(Poll.polls)%(tuple([x for x in Poll.polls]))+"```"
    await ctx.send(phrase)
    return

@bot.command(pass_context=True,aliases=['Newpoll'])
async def newpoll(ctx,*,request : str=''):
    """(poll): Creates new (poll) with all online members in channel"""
    if request and request not in Poll.polls:
        request = Poll(ctx,str(request))
        phrase = ("New poll created: %s \nRegistered voters:\n"%(request.name)+"```\n"+"%s\n"*len(set(request.votes))%(tuple(set(request.votes)))+"```")
        await ctx.send(phrase)
        return
    elif request:
        await ctx.send("%s is already an active poll. Remove it before making it again"%request)
    else:
        await ctx.send("I need a name for this poll")
        return

@bot.command(aliases=['Newsecret'])
async def newsecret(ctx,*,request : str=''):
    """(secret poll): Creates a new (secret poll) with all online members in channel"""
    if request and request not in Poll.polls:
        request = Secret(ctx,str(request))
        phrase = ("New secret poll created: %s \nRegistered voters:\n"%(request.name)+"```\n"+"%s\n"*len(set(request.votes))%(tuple(set(request.votes)))+"```")
        await ctx.send(phrase)
        return
    elif request:
        await ctx.send("%s is already an active poll. Remove it before making it again"%request)
    else:
        await ctx.send("I need a name for this secret poll")
        return

@bot.command(aliases=['Remove','delete','del','Delete','Del','erase','Erase'])
async def remove(ctx,*,request : str=''):
    """(poll): Deletes (poll). Requires the command to be repeated"""
    writer = ctx.message.author.name
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    if Poll.polls[poll].deletion==True:
        del Poll.polls[poll]
        await ctx.send("%s has been removed by %s"%(poll,writer))
        print ("%s has removed poll: %s"%(writer,poll))
        return
    else:
        Poll.polls[poll].deletion=True
        await ctx.send("%s has been marked for removal. Repeat the remove command to finalize deletion of the poll.\n Otherwise, use the cancel command to reverse this action.\n Use the silence command to remove individual voters from a poll"%poll)
        return

@bot.command()
async def cancel(ctx,*,request : str=''):
    """(poll): Cancels the delete action on (poll)"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    Poll.polls[poll].deletion=False
    await ctx.send("Deletion order for %s has been cancelled"%poll)

@bot.command()
async def add(ctx,*,request : str=''):
    """(poll),(member): Adds another (member) to (poll)"""
    try:
        text = request.split(',',2)
    except:
        await ctx.send("Syntax ```\n(poll),(member)```\nMember likely has to be online to be successfully added")
        return
    if text[1][0]==' ':
        text[1]=text[1][1:]
    member_check = process.extractOne("%s"%(text[1]),bot.get_all_members()) 
    if member_check[1] > 70:
        member = member_check[0]
    else:
        await ctx.send("I'm not sure %s is here right now. Try again when they're online"%member)
        return
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    Poll.polls[poll].votes[member.name] = 'No vote recorded'
    await ctx.send("%s has been added to %s"%(member, poll))
    phrase = Poll.polls[poll].results()
    await ctx.send(phrase)
    return

@bot.command(pass_context=True)
async def silence(ctx,*,request : str=''):
    writer = ctx.message.author.name
    try:
        text = request.split(',',2)
    except:
        await ctx.send("Syntax ```\n(poll),(member)```")
        return
    if text[1][0]==' ':
        text[1]=text[1][1:]
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    if process.extractOne("%s"%(text[1]),Poll.polls[poll].votes.keys())[1] > 70:
        member = (process.extractOne("%s"%(text[1]),Poll.polls[poll].votes.keys())[0])
        del Poll.polls[poll].votes[member]
        await ctx.send("%s has been removed from %s by %s"%(member, poll, writer))
        print ("%s has removed %s from %s"%(writer, member, poll))
    else:
        await ctx.send("I don't think %s is part of %s"%(text[1], poll))
        return

@bot.command(pass_context=True)
async def vote(ctx,*,request : str=''):
    """(poll),(vote): Records your (vote) for (poll)"""
    voter = ctx.message.author.name
    text = request.split(',',2)
    if text[1][0]==' ':
        text[1]=text[1][1:]
    poll = process.extractOne("%s"%(text[0]),Poll.polls.keys())[0] #Gives a string of the poll which is the key to access the Poll object. process returns a tuple with the result in [0] and the match accuracy in [1]
    decision = text[1]
    Poll.polls[poll].votes[voter]=decision #Class Poll, dictionary of all polls, specific poll, dictionary of voters/votes in poll, specific voter value changed to decision
    phrase = Poll.polls[poll].results()
    await ctx.send(phrase)
    return

@bot.command(aliases=['voter','Voters','Voter'])
async def voters(ctx,request : str=''):
    """(poll): Returns a list of recognized voters for (poll)"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    phrase = "Registered voters for %s:\n"%(poll)+"```\n"+"%s\n"*len(set(Poll.polls[poll].votes))%(tuple(set(Poll.polls[poll].votes)))+"```"
    await ctx.send(phrase)
    return

@bot.command(aliases=['result','Result','Results'])
async def results(ctx,*,request : str=''):
    """(poll): Returns current results for (poll). Secret polls will not have names attached to votes"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    phrase = Poll.polls[poll].results()
    await ctx.send(phrase)
    return

@bot.command(aliases=['Command','Commands','Commandlist'])
async def commandlist(ctx):
    """returns commands with acceptable syntax"""
    phrase = """```\nnewpoll - (poll): Creates new (poll) with all online members in channel\n
newsecret - (secret poll): Creates a new (secret poll) with all online members in channel\n
results - (poll): Returns current results for (poll). Secret polls will not have names attached to votes\n
remove - (poll): Deletes (poll). Requires the command to be repeated\n
cancel - (poll): Cancels the delete action on (poll)\n
polls - (): Returns a list of all active polls\n
voters - (poll): Returns a list of recognized voters for (poll)\n
vote - (poll),(vote): Records your (vote) for (poll)\n
add - (poll),(member
): Adds another (member) to (poll)\n
silence - (poll),(member): Removes (member) from (poll)\n
```
"""
    await ctx.send(phrase)
    return

bot.run('Mjc3MTkxNjczOTk2NTA5MTg0.C3aKYA.UF2sH6PrBdOxT6znHJAd66_k07Q') #Council bot's token
