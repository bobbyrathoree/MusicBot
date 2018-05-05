#!/usr/bin/env python3

from __future__ import unicode_literals
import os
import logging
from urllib.request import urlopen

import youtube_dl
from bs4 import BeautifulSoup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram.ext.dispatcher import run_async
from pony.orm import db_session, select

from database import db
from credentials import TOKEN

from user import User


DB_NAME = 'db.sqlite'

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',              #basic commands to print the server logs
    level=logging.INFO)

u = Updater(TOKEN)                                                              #token updater
dp = u.dispatcher

db.bind('sqlite', DB_NAME, create_db=True)
db.generate_mapping(create_tables=True)







def start(bot, update):                                                         #function implementation when a bot is started/restarted
    chat_id = update.message.chat_id

    bot.sendMessage(chat_id,
                    text="Hello, please type a song name to start download")


def admin(bot, update):                                                         #function implementation where the admin can view the latest song requests
    chat_id = update.message.chat_id
    username = update.message.chat.username

    with db_session:
        users = len(select(u.user_id for u in User))
        last5 = '\n'.join(select(u.title for u in User)[:][-5:])

    if username == 'Humblefool':
        bot.sendMessage(chat_id,
                        text="{} users registered.\n\n{}".format(users, last5))

#text = NULL


@run_async
def music(bot, update):                                                         #function implementation where the all the bot messages (song and lyrics)
                                                                                # are sent
    user_id = update.message.from_user.id
    username = update.message.chat.username
    first_name = update.message.from_user.first_name
    last_name = update.message.from_user.last_name
    chat_id = update.message.chat_id
    text = update.message.text

    title, video_url = search(text)
    lyrics = get_lyrics(text)
    if not lyrics:
        lyrics="Sorry no lyrics found :( "
    with db_session:
        User(user_id=user_id,
             username=username,
             first_name=first_name,
             last_name=last_name,
             title=title,
             video_url=video_url)

    bot.sendMessage(chat_id,
                    text="Request received, downloading now...")

    download(title, video_url)
    bot.sendAudio(chat_id,
                  audio=open(title + '.mp3', 'rb'),
                  title=title)
    bot.sendMessage(chat_id, text=lyrics)
    os.remove(title + '.mp3')

def get_lyrics(song):                                                           #function implementation to scrape lyrics of particular song

    t=song.split()
    x=len(t)
    q=t[0]
    for i in range(1,x):
        q = q + "+" + t[i]


    url="http://search.azlyrics.com/search.php?q="+q
    s= urlopen(url).read()

    soup=BeautifulSoup(s,'html.parser')


    productLinks = [td.a for td in soup.findAll('td', {'class':"text-left visitedlyr"})]

    for link in productLinks:

        url1= link['href']

        s1=urlopen(url1).read()

        soup1=BeautifulSoup(s1,'html.parser')
        for link in soup1.find_all('div',{'class':None}):
            lyr_text = link.text


    return lyr_text

def search(text):                                                               #function implementation to find the particular link to download
    query = '+'.join(text.lower().split())

    url = 'https://www.youtube.com/results?search_query=' + query
    content = urlopen(url).read()
    soup = BeautifulSoup(content, 'html.parser')
    tag = soup.find('a', {'rel': 'spf-prefetch'})
    title = tag.text
    video_url = 'https://www.youtube.com' + tag.get('href')

    return title, video_url


def download(title, video_url):                                                 #function implementing youtube_dl library to download the particular song

    ydl_opts = {
        'outtmpl': title + '.%(ext)s',
        'format': 'bestaudio/best', 'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([video_url])



dp.add_handler(CommandHandler("start", start))                                  # CommandHandler to start the bot giving /start command in the chat window
dp.add_handler(CommandHandler("admin", admin))                                  # CommandHandler to check the last 5 song requests, /admin command can be used only by the admin
dp.add_handler(MessageHandler([Filters.text], music))                           # MessageHandler to send the messages using the music function

u.start_polling()
u.idle()
