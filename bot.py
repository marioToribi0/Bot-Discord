from asyncio.tasks import run_coroutine_threadsafe
import discord
from discord import message
from discord import channel
from discord.colour import Colour
from discord.ext import commands
from discord import FFmpegPCMAudio, PCMVolumeTransformer
from discord.utils import get as dget
from discord.message import Embed
import datetime
from youtube_dl import YoutubeDL
from requests import get
import requests
import asyncio
from bs4 import BeautifulSoup
import lxml
import random
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import re

CLIENT_ID = 'ID_CLIENT'
CLIENT_SECRET = 'SECRET_KEY'
REDIRECT_URI = 'http://localhost:8080'
CACHE = '.spotipyoauthcache'
TOKEN = 'TOKEN'
FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn'}
URL_QUERY_GOOGLE = 'https://www.google.com/search?q='
COMMAND_PREFIX = '.'
COLOR_BOT = Colour.dark_gold()

messages_without_music = ['Si tendríamos música todo sería mejor.', 'Primero pon una musiquita pa @', "ª", "Deja la chelcha y pon música"]

class GoogleSearch:
    def __init__(self) -> None:
        self.header ={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        }

    def searching_by_name(self, phrase: str):
        query = URL_QUERY_GOOGLE + 'lyrics+letras+'
        next_value = False
        for letter in phrase:
            
            if (letter==' '):
                if (next_value==False):
                    query += '+'
                    next_value = True
                continue
            else:
                next_value = False
                query += letter

        website_html = requests.get(query, headers=self.header).text
        
        # Scrapping
        soup = BeautifulSoup(website_html, 'lxml')
        song = soup.select('[jsname=YS01Ge]')
        lyrics = [lyric.text for lyric in song]

        message = ""
        result = []
        count = 0
        for lyric in lyrics:
            count += len(lyric)
            if (count>=1500):
                result.append(message)
                message = ''
                count = 0
            message += f'{lyric}\n'
        else:
            result.append(message)
        return result

google = GoogleSearch()

#Get videos from links or from youtube search
def search_youtube(query):
    with YoutubeDL({'format': 'bestaudio', 'noplaylist':'True'}) as ydl:
        try: requests.get(query)
        except: info = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else: info = ydl.extract_info(query, download=False)
    return (info, info['formats'][0]['url'])

def search_spotify(url, items) -> list:

    constructor = SpotifyOAuth(client_id=CLIENT_ID, client_secret=CLIENT_SECRET, redirect_uri=REDIRECT_URI, cache_path=CACHE)
    sp = spotipy.Spotify(auth_manager=constructor)

    if (items>=100):
        return ['Uff, no soy capaz de leer todo eso.']
    id_playlist = None
    id_album = None

    # Playlist
    id_playlists = []
    id_playlists.append(re.findall('https://open.spotify.com/playlist/(.+)\?', url))
    id_playlists.append(re.findall('https://open.spotify.com/playlist/(.+)', url))
    status = True
    for i in range(len(id_playlists)):
        if (len(id_playlists[i])!=0):
            id_playlist = id_playlists[i][0]
            status = False
            break

    # Album
    id_albums = []
    id_albums.append(re.findall('https://open.spotify.com/album/(.+)\?', url))
    id_albums.append(re.findall('https://open.spotify.com/album/(.+)', url))
    
    for i in range(len(id_albums)):
        if (len(id_albums[i])!=0):
            id_album = id_albums[i][0]
            status = False
            break

    if (status):
        return 'Esa dirección no es válida.'

    if (id_playlist!=None):
        data = sp.playlist_tracks(id_playlist, limit=items)
        songs = []
        for i in range(len(data['items'])):
            song = f"{(data['items'][i]['track']['artists'][0]['name'])} {(data['items'][i]['track']['name'])}" 
            songs.append(song)

    elif (id_album!=None):
        data = sp.album_tracks(id_album, limit=items)
        songs = []
        for i in range(len(data['items'])):
            song = f"{(data['items'][0]['artists'][0]['name'])} {data['items'][i]['name']} " 
            songs.append(song)
    print(songs)
    return songs

def play_next(ctx, playlist, source, voice, bot):
    if (bot.servers[ctx.voice_client]["loop"]==False and bot.servers[ctx.voice_client]['repeat']==False):
        if len(playlist) >= 1:
            # If song previous not delete song
            if (bot.servers[ctx.voice_client]["previous"]==True):
                video, source, author = bot.servers[ctx.voice_client]["last_song"]
                bot.servers[ctx.voice_client]["previous"] = False
                voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx, playlist, source, voice, bot))
                asyncio.run_coroutine_threadsafe(ctx.send(f"Estás escuchando ahora {video['webpage_url']}"), bot.loop)
            
            else:
                bot.servers[ctx.voice_client]["last_song"] = (playlist[0][0], playlist[0][1])
                del playlist[0]
                voice.play(FFmpegPCMAudio(playlist[0][1], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx, playlist, source, voice, bot))
                asyncio.run_coroutine_threadsafe(ctx.send(f"Estás escuchando ahora {playlist[0][0]['webpage_url']}"), bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("No hay más canciones en la lista de reproducción."), bot.loop)
    else:
        if (bot.servers[ctx.voice_client]['repeat']): 
            bot.servers[ctx.voice_client]["loop"]= False
            bot.servers[ctx.voice_client]['repeat'] = False

        voice.play(FFmpegPCMAudio(playlist[0][1], **FFMPEG_OPTIONS), after=lambda e: play_next(ctx, playlist, source, voice, bot))

def reset_server(id_server: int, bot):
    bot.actual_channel = None
    bot.voice = None
    # Vars
    bot.playlist = []

def context_comprobation(ctx, voice, bot):
    if (voice==None or not voice.is_playing()):    
        message = random.choice(messages_without_music)
        asyncio.run_coroutine_threadsafe(ctx.send(message), bot.loop)
        return False
    asyncio.run_coroutine_threadsafe(ctx.send("Listo."), bot.loop)
    return True

async def send_actual_song(ctx, author, video):
    link = video['webpage_url']
    image = video['thumbnail']
    title = video['title']
    user =  ctx.author.name
    image_user = ctx.author.avatar_url

    embed = Embed(description=title,color=COLOR_BOT, link='https://www.youtube.com/watch?v=hoQmSA6MRAk')
    embed.set_author(name="Estás escuchando ahora:", url=link)
    embed.set_thumbnail(url=image)
    embed.set_footer(text=f"Por: {user}", icon_url=image_user)
    await ctx.send(embed=embed)

async def send_new_song(ctx, author, video):
    link = video['webpage_url']
    image = video['thumbnail']
    title = video['title']
    user =  ctx.author.name
    image_user = ctx.author.avatar_url
    image_user = ctx.author.avatar_url

    embed = Embed(description=title,color=COLOR_BOT, link='https://www.youtube.com/watch?v=hoQmSA6MRAk')
    embed.set_author(name="Se ha agregado a la lista de reproducción:", url=link)
    embed.set_thumbnail(url=image)
    embed.set_footer(text=f"Por: {user}", icon_url=image_user)
    await ctx.send(embed=embed)

class MusicBot(commands.Bot):
    def __init__(self):
        commands.Bot.__init__(self, command_prefix=COMMAND_PREFIX, description=':)', self_bot=False)
        # Attributes
        self.actual_channel = None
        self.voice = None
        # Vars
        self.servers = {}
        # Function
        self.add_commands()

    # Return -1 if the bot is already in a channel 
    async def join(self, ctx, voice):
        actual_server = self.servers.get(ctx.voice_client, {})
        actual_channel = actual_server.get("channel", None)
        channel = ctx.author.voice.channel

        if actual_channel!=channel and actual_channel!=None:
            await ctx.send("Ya estoy en un canal.")
            return -1
        if voice and voice.is_connected():
            await voice.move_to(channel)
        else: 
            voice = await channel.connect() 
        return voice

    def add_commands(self):
        @self.command()
        async def ping(ctx):
            await ctx.send('pong')

        @self.command()
        async def play(ctx, *, query, spotify_var=False, on_time = False):

            voice = dget(self.voice_clients, guild=ctx.guild) 
            channel = ctx.author.voice
            if (channel==None):
                await ctx.send(f"No te veo en un canal, {ctx.author.name}.")
            else:        
                voice = await self.join(ctx, voice)
                
                if (voice==-1):
                    return

                video, source = search_youtube(query)

                # Append new song
                server = self.servers.get(ctx.voice_client, {})
                voice_client_server = server.get("voice_client", None)
                actual_playlist = server.get("playlist", [])
                loop = server.get("loop", False)
                last_song = server.get("last_song", None)
                repeat = server.get("repeat", False)
                previous = server.get("previous", False)
                author = ctx.author.name
                actual_playlist.append((video, source, author))

                self.servers[ctx.voice_client] = server
                self.servers[ctx.voice_client]["voice_client"] = voice_client_server
                self.servers[ctx.voice_client]["playlist"] = actual_playlist
                self.servers[ctx.voice_client]["channel"] = ctx.author.voice.channel
                self.servers[ctx.voice_client]["loop"] = loop
                self.servers[ctx.voice_client]["last_song"] = last_song
                self.servers[ctx.voice_client]["repeat"] = repeat
                self.servers[ctx.voice_client]["previous"] = previous

                print(self.servers[ctx.voice_client]["loop"])
                voice = ctx.guild.voice_client
                
                # New song
                if ((not voice.is_playing()) and spotify_var==False):
                    await send_actual_song(ctx, author, video)
                    voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx, actual_playlist, source, voice, self))
                    
                elif ((not voice.is_playing()) and on_time==True):
                    await send_actual_song(ctx, author, video)
                    voice.play(FFmpegPCMAudio(source, **FFMPEG_OPTIONS), after=lambda e: play_next(ctx, actual_playlist, source, voice, self))
        
                else:
                    await send_new_song(ctx, author, video)
                # Add voice
                self.voice = voice
        
        @self.command()
        async def p(ctx, *, query, spotify_var=False, on_time = False):
            await play(ctx=ctx, query=query)

        @self.command()
        async def loop(ctx, *, query=None, repeat=False):
            try:
                if (self.servers[ctx.voice_client]["loop"]==False):
                    msg = ("¡El bucle se ha activado!")
                else:
                    msg = ("¡El bucle se ha desactivado!")
                self.servers[ctx.voice_client]["loop"] = not self.servers[ctx.voice_client]["loop"] 
            except KeyError:
                msg = ("No hay música reproduciéndose en tu canal.")
            if (repeat==False):
                await ctx.send(msg)

        @self.command()
        async def previous(ctx):
            try:
                self.servers[ctx.voice_client]['previous'] = True
                if (self.servers[ctx.voice_client]["last_song"]!=None):
                    self.servers[ctx.voice_client]["playlist"].insert(0, self.servers[ctx.voice_client]["last_song"])
                    await skip(ctx)
                else:
                    await ctx.send("No hay una canción anterior a esta.")
            except KeyError:
                await ctx.send("No hay música reproduciéndose en tu canal.")

        # This function stop music
        @self.command()
        async def skip(ctx):
            voice = ctx.voice_client
            if (context_comprobation(ctx, voice, self)):
                voice.stop()

        @self.command()
        async def repeat(ctx):
            try:    
                self.servers[ctx.voice_client]["loop"] = True
                self.servers[ctx.voice_client]['repeat'] = True
            except KeyError:
                msg = ("No hay música reproduciéndose en tu canal.")
            
            await skip(ctx)

        @self.command()
        async def pause(ctx):
            voice = ctx.voice_client
            if (context_comprobation(ctx, voice, self)):
                voice.pause()

        @self.command()
        async def resume(ctx):
            voice = ctx.voice_client
            voice.resume()

        @self.command()
        async def playlist(ctx):
            voice = ctx.voice_client
            if (voice==None):
                message = 'Entra a un canal primero :v'
            else:
                songs = self.servers[voice]['playlist']
                if (len(songs)>0):
                    message = 'Lista de reproducción: \n'
                    for count, video in enumerate(songs):
                        message += f'{count+1}. {video[0]["title"]}\n'
                else:
                    message = 'No hay canciones en la lista de reproduccion.'

            await ctx.send(message)
        
        @self.command()
        async def lyrics(ctx):
            if (ctx.voice_client.is_playing()):
                video, source, author = self.servers[ctx.voice_client]['playlist'][0]
                query = video['title']
                
                new_query = ''
                query = query.split(' ')
                for i in query[:-1]:
                    new_query += f'{i} '
                
                message = google.searching_by_name(new_query)
                try:
                    for msg in message:
                        await ctx.send(msg)
                except discord.errors.HTTPException:
                    await ctx.send(f"No pude encontrar letras con este título. \n Puedes usar:      '{COMMAND_PREFIX}search <nombre cancion>'")
            else:
                message = f"No puedo poner letras sin música, {ctx.author.name}."
                await ctx.send(message)

        @self.command()
        async def nowplaying(ctx):
            channel = ctx.voice_client

            if (len(self.servers[channel].get("playlist", []))==0):
                await ctx.send(f'No hay música reproduciéndose 🤔')
            else:
                video = self.servers[channel]["playlist"][0][0]
                author = self.servers[channel]["playlist"][0][2]
                await send_actual_song(ctx, author,video)

        @self.command()
        async def leave(ctx): 
            actual_server = self.servers.get(ctx.voice_client, {})
            actual_channel = actual_server.get("channel", None)
            channel = ctx.author.voice.channel

            if actual_channel!=channel and actual_channel!=None:
                await ctx.send("Luego 😉")
                return -1
            
            if (ctx.voice_client): 
                await ctx.guild.voice_client.disconnect() 
                id_server = 0
                reset_server(id_server, self)
                
            else: 
                await ctx.send("No estoy en ningún canal para salir.")
        
        @self.command()
        async def remove(ctx, query):
            voice = ctx.voice_client
            try:
                query = int(query)
            except TypeError:
                message = f'Ingresa el "{COMMAND_PREFIX}remove <índice canción>"'
            try:
                if (len(self.servers[voice]["playlist"])>query or query<1):
                    message = f'Ese índice no existe en nuestra playlist.'
                if (query==0):
                    skip(ctx)
                else:
                    del self.servers[voice]["playlist"][query-1]
                    message = 'Listo.'
            except KeyError:
                message = random.choice(messages_without_music)
            
            await ctx.send(message)

        @self.command()
        async def credits(ctx):
            message = f'Este proyecto fue creado por Mario Toribio, desde el '\
                f"17/09/21 hasta {datetime.datetime.now().strftime(r'%d/%m/%y')}. "\
                f"\nPuedes agregar este bot a tu server escribiendo la clave :)"
            await ctx.send(message)

        @self.command()
        async def spotify(ctx, link, items):
            elements = search_spotify(link, int(items))
            
            data = []
            for i in range(len(elements)):
                song = random.randint(0,len(elements)-1)
                data.append(elements[song])
                del elements[song]

            if (type(data) == str):
                await ctx.send(data)
            else:
                await play(ctx = ctx, query = data[0], spotify_var=True, on_time=True)
                for msg in data[1:]:
                    await play(ctx = ctx, query = msg, spotify_var=True)

        @self.command()
        async def search(ctx, *, query):
            message = google.searching_by_name(query)
            for msg in message:
                await ctx.send(msg)

        @self.command()
        async def hello(ctx):
            message = Embed(title="Hello",description="It's me",color=COLOR_BOT)
            await ctx.send(embed=message )

        # Events
        @self.event
        async def on_ready():
            print('Dandelion is ready')
            # Status
            await self.change_presence(activity=discord.Game(name=':D'))

        @self.event
        async def on_voice_state_update(member, after, before):
            voice_state = member.guild.voice_client
            if self.servers.get(voice_state, None) is None:
                return 

            if len(voice_state.channel.members) == 1 and voice_state in self.servers.keys():
                await voice_state.disconnect()

bot = MusicBot()
#Listen
bot.run(TOKEN)
