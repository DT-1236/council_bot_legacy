#import urllib
#import time
#import matplotlib.pyplot as plt

#    print (('Data prep complete. Time Elapsed :')+str(time.clock()-time_start))

import discord
from discord.ext import commands
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

description = '''A Council bot to execute council functions.'''
bot = commands.Bot(command_prefix='&', description=description)

class Poll:

    polls={}#Dictionary of polls. Keys are strings which contain poll.name. Values are the Poll objects themselves which contain a dictionary of voter information

    def __init__(self, name):
        self.name = name
        self.deletion = False
        Poll.polls[self.name]=self
        self.votes = {}
        present = [x for x in bot.get_all_members()]
        present.remove([x for x in present if x.name==bot.user.name][0])
        for x in present:
            self.votes[x.name]='No vote recorded' #Keys are strings containing names of present members

    def all_polls():
        return [x.name for x in Poll.polls]

    def results(self):
        tally = zip(Poll.polls[self.name].votes.keys(),Poll.polls[self.name].votes.values())
        return ("Current Results for %s: \n"%(Poll.polls[self.name].name)+"```\n"+"%s\n"*len((Poll.polls[self.name].votes))%tuple([x for x in tally])+"```")

class Secret(Poll):

    def results(self):
        tally = (Poll.polls[self.name].votes.values())
        return ("Current Results for secret poll, %s: \n"%(Poll.polls[self.name].name)+"```\n"+"%s\n"*len((Poll.polls[self.name].votes))%tuple([x for x in tally])+"```")

@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------')

@bot.command(aliases=['Polls','Poll','poll'])
async def polls(*,request : str=''):
    """(): Returns a list of all active polls\n"""
    phrase = "Active polls:\n"+"```\n"+"%s\n"*len(Poll.polls)%(tuple([x for x in Poll.polls]))+"```"
    await bot.say(phrase)
    return

@bot.command(aliases=['Newpoll'])
async def newpoll(*,request : str=''):
    """(poll): Creates new (poll) with all online members in channel"""
    if request and request not in Poll.polls:
        request = Poll(str(request))
        phrase = ("New poll created: %s \nRegistered voters:\n"%(request.name)+"```\n"+"%s\n"*len(set(request.votes))%(tuple(set(request.votes)))+"```")
        await bot.say(phrase)
        return
    elif request:
        await bot.say("%s is already an active poll. Remove it before making it again"%request)
    else:
        await bot.say("I need a name for this poll")
        return

@bot.command(aliases=['Newsecret'])
async def newsecret(*,request : str=''):
    """(secret poll): Creates a new (secret poll) with all online members in channel"""
    if request and request not in Poll.polls:
        request = Secret(str(request))
        phrase = ("New secret poll created: %s \nRegistered voters:\n"%(request.name)+"```\n"+"%s\n"*len(set(request.votes))%(tuple(set(request.votes)))+"```")
        await bot.say(phrase)
        return
    elif request:
        await bot.say("%s is already an active poll. Remove it before making it again"%request)
    else:
        await bot.say("I need a name for this secret poll")
        return

@bot.command(pass_context=True,aliases=['Remove','delete','del','Delete','Del','erase','Erase'])
async def remove(ctx,*,request : str=''):
    """(poll): Deletes (poll). Requires the command to be repeated"""
    writer = ctx.message.author.name
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    if Poll.polls[poll].deletion==True:
        del Poll.polls[poll]
        await bot.say("%s has been removed"%poll)
        print ("%s has removed poll: %s"%(writer,poll))
        return
    else:
        Poll.polls[poll].deletion=True
        await bot.say("%s has been marked for removal. Repeat the remove command to finalize deletion of the poll.\n Otherwise, use the cancel command to reverse this action.\n Use the silence command to remove individual voters from a poll"%poll)
        return

@bot.command()
async def cancel(*,request : str=''):
    """(poll): Cancels the delete action on (poll)"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    Poll.polls[poll].deletion=False
    await bot.say("Deletion order for %s has been cancelled"%poll)

@bot.command()
async def add(*,request : str=''):
    """(poll),(member): Adds another (member) to (poll)"""
    try:
        text = request.split(',',2)
    except:
        await bot.say("Syntax ```\n(poll),(member)```\nMember likely has to be online to be successfully added")
        return
    if text[1][0]==' ':
        text[1]=text[1][1:]
    if process.extractOne("%s"%(text[1]),bot.get_all_members())[1] > 70:
        member = (process.extractOne("%s"%(text[1]),bot.get_all_members())[0])
    else:
        await bot.say("I'm not sure %s is here right now. Try again when they're online"%member)
        return
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    Poll.polls[poll].votes[member.name] = 'No vote recorded'
    await bot.say("%s has been added to %s"%(member, poll))
    phrase = Poll.polls[poll].results()
    await bot.say(phrase)
    return

@bot.command(pass_context=True)
async def silence(ctx,*,request : str=''):
    writer = ctx.message.author.name
    try:
        text = request.split(',',2)
    except:
        await bot.say("Syntax ```\n(poll),(member)```")
        return
    if text[1][0]==' ':
        text[1]=text[1][1:]
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    if process.extractOne("%s"%(text[1]),Poll.polls[poll].votes.keys())[1] > 70:
        member = (process.extractOne("%s"%(text[1]),Poll.polls[poll].votes.keys())[0])
        del Poll.polls[poll].votes[member]
        await bot.say("%s has been removed from %s"%(member, poll))
        print ("%s has removed %s from %s"%(writer,member,poll))
    else:
        await bot.say("I don't think %s is part of %s"%(text[1], poll))
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
    await bot.say(phrase)
    return

@bot.command(aliases=['voter','Voters','Voter'])
async def voters(request : str=''):
    """(poll): Returns a list of recognized voters for (poll)"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    phrase = "Registered voters for %s:\n"%(poll)+"```\n"+"%s\n"*len(set(Poll.polls[poll].votes))%(tuple(set(Poll.polls[poll].votes)))+"```"
    await bot.say(phrase)
    return

@bot.command(pass_context=True,aliases=['result','Result','Results'])
async def results(ctx,*,request : str=''):
    """(poll): Returns current results for (poll). Secret polls will not have names attached to votes"""
    poll = process.extractOne("%s"%(request),Poll.polls.keys())[0]
    phrase = Poll.polls[poll].results()
    await bot.say(phrase)
    return

@bot.command(aliases=['Command','Commands','Commandlist'])
async def commandlist():
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
    await bot.say(phrase)
    return

bot.run('Mjc3MTkxNjczOTk2NTA5MTg0.C3aKYA.UF2sH6PrBdOxT6znHJAd66_k07Q') #Council bot's token
