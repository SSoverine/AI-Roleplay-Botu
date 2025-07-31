import discord
import re
import asyncio
from random import randint
from time import sleep
from pymongo import MongoClient
from discord.ext import commands
from google import genai
from google.genai import types

#TEMEL DEĞİŞKENLER

roleplays = []
npcs = []
events = []

client = genai.Client(api_key="API_KEY")
Bot = commands.Bot(command_prefix="s!", intents=discord.Intents.all(), help_command=None)

#BUTON SINIFLARI

class EventView(discord.ui.View):
    event = None
    user = None

    def __init__(self, event, user):
        super().__init__()
        self.event = event
        self.user = user

    @discord.ui.button(label="Reddet", style=discord.ButtonStyle.red)
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.event.isWaiting = False
        if interaction.user.id == self.user:
            self.event.users.append(self.user)
            await interaction.message.delete()

    @discord.ui.button(label="Kabul Et", style=discord.ButtonStyle.green)
    async def accept_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id == self.user:
            self.event.user = self.user
            res = await asyncio.to_thread(lambda: self.event.chat.send_message("//Eventi başlat. Asla ve asla, kullanıcının ne yaptığını, ne düşündüğünü vs. gibi şeyleri yazma. Sadece, çevresel olayları yönet. Ama kullanıcının rahatça seçebileceği, anlayabileceği şeyleri eklemeyi de unutma. Rolün bitmesi gerektiğinde veya sonuca ulaştığında, bitti. şeklinde çıktı ver."))

            await interaction.message.edit(content=res.text, view=self, embed=None)

class RpView(discord.ui.View):
    chat = None

    def __init__(self, chat):
        super().__init__()
        self.chat = chat

    @discord.ui.button(label="Sil", style=discord.ButtonStyle.primary)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.message.delete()
        await asyncio.to_thread(lambda: self.chat.send_message("//Son yazdığın emoteu silindi, buna mesaja vereceğin cevapda geçerli sayılmayacak. Bir sonraki mesaja cevap vereceksin. Event bittiğinde, bitir şeklinde bir cevap ver."))

    @discord.ui.button(label="Değiştir", style=discord.ButtonStyle.primary)
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        res = await asyncio.to_thread(lambda: self.chat.send_message("//Bu rolünü beğenmedim. Değiştir."))
        
        messages = await splitMessage(res.text)

        await interaction.edit_original_response(content=messages[0], view=self)

        if len(messages)>1:
            for msg in messages[1:]:
                await interaction.channel.send(content=msg, view=self)


class NpcView(discord.ui.View):
    texts = []
    index = 0

    def __init__(self, embeds):
        super().__init__()
        self.texts = embeds

    @discord.ui.button(label="Geri", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = self.index-1
        if self.index < 0:
            self.index = len(self.texts)-1

        await interaction.response.edit_message(embed=self.texts[self.index], view=self)

    @discord.ui.button(label="İleri", style=discord.ButtonStyle.primary)
    async def forward_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.index = self.index+1
        if self.index == len(self.texts):
            self.index = 0

        await interaction.response.edit_message(embed=self.texts[self.index], view=self)

#SINIFLAR

class RolePlay:
    chat = None
    channel = None
    isPaused = False
    hist = []
    users = []

    def getChannel(self, ch):
        if ch == self.channel:
            return True
        else:
            False

    def __init__(self, channel, hist, user):
        self.channel = channel
        self.hist = hist
        self.users.append(user)
        self.chat = client.chats.create(model="gemini-2.5-flash", history=self.hist)

class Mission:
    pass

class NPC:
    name = ""
    chat = None
    channel = None
    channel_id = None
    isPaused = False
    isActive = False
    description = ""
    prompt = ""
    avatarUrl = ""
    hist = []

    def setChannel(self, channel):
        self.channel = channel
        self.channel_id = int(re.sub(r"\D", "", channel))

    def __init__(self, name, description, channel, prompt, avatarUrl):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.channel = channel
        self.avatarUrl = avatarUrl
        self.hist = [
            {"role": "user","parts": [{"text": prompt}]}
        ]
        self.chat = client.chats.create(model="gemini-2.5-flash", history=self.hist)
        self.channel_id = int(re.sub(r"\D", "", channel))
        
class Event:
    name = ""
    possibility = 0
    channel = ""
    prompt = ""
    reward = ""

    isPaused = False
    channel_id = None
    isWaiting = False
    chat = None
    user = "nothing"
    users = []
    hist = []

    def __init__(self, name, possibility, channel, prompt, reward):
        self.name = name
        self.possibility = possibility
        self.channel = channel
        self.prompt = prompt
        self.reward = reward

        self.hist = [{"role": "user","parts": [{"text": prompt}]}]
        self.chat = client.chats.create(model="gemini-2.5-flash", history=self.hist)

        self.channel_id = int(re.sub(r"\D", "", channel))

#DATABASE

mongo = MongoClient("mongodb://localhost:27017")
db = mongo.shiva
npcsColl = db.NPCS
eventsColl = db.Events

results = npcsColl.find({})

for result in results:
    npcs.append(NPC(result["name"], result["description"], result["channel"], result["prompt"], result["url"]))

results = eventsColl.find({})

for result in results:
    events.append(Event(result["name"], result["possibility"], result["channel"], result["prompt"], result["reward"]))

#FONKSİYONLAR

async def sendEmbed(ctx, desc, titlee, footer="", color=discord.Colour.light_grey(), delay=None):
    embed = discord.Embed(
        colour=color,
        description=desc,
        title=titlee
    )

    embed.set_footer(text=footer)
    embed.set_author(name="Shiva™ Roleplay Botu")

    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/841788409613385769/1385377123711189032/1000049875.png?ex=685729fd&is=6855d87d&hm=489e8757409b7e64581d6f8190d7b1aed0eab1845bb04f7d3dcc0798e4115fae&")
    embed.set_image(url="https://cdn.discordapp.com/attachments/1271955629094866954/1385317957009412126/image.png?ex=68579ba2&is=68564a22&hm=9e44511e6d870207a0736c8e0f4b26c3a0d51c635bc506eaa07ae20d052f5dfa&")
    await ctx.send(embed=embed, delete_after=delay)

async def splitMessage(msg):
    return [msg[i:i+2000] for i in range(0, len(msg), 2000)]

#EVENTLER

@Bot.event
async def on_ready():
    await Bot.change_presence(status=discord.Status.do_not_disturb, activity=discord.Activity(type=discord.ActivityType.watching, name="s!help"))
    print("Bot hazır!")

@Bot.event
async def on_message(message:discord.Message):
    message.channel
    if message.content.startswith("//") or message.content.startswith("s!") or message.author == Bot.user or message.webhook_id is not None:
        await Bot.process_commands(message)
        return

    isRoleplaying = False
    isNpcActive = False

    isPaused = False
    users = []
    chat = None
    Npc:NPC = None

    event = None

    for role in roleplays:
        if role.getChannel(message.channel):
            isRoleplaying = True
            isPaused = role.isPaused
            chat = role.chat
            users = role.users
            break

    for npc in npcs:
        if message.guild.get_channel(npc.channel_id) == message.channel and npc.isActive:
            isNpcActive = npc.isActive
            isPaused = npc.isPaused
            chat = npc.chat
            Npc = npc
            
            
    for event in events:
        if message.guild.get_channel(event.channel_id) == message.channel and not message.author.id in event.users:
            number = randint(0,100)
            print(number)
            print(event.user)


            if message.author.id == event.user:
                users.append(message.author.id)
                isRoleplaying = True
                isPaused = event.isPaused
                chat = event.chat
                event = event
                break
            elif number <= int(event.possibility) and event.user == "nothing" and not event.isWaiting:
                embed = discord.Embed(
                    colour=discord.Colour.dark_gold(),
                    description="**" + event.name + "** isimli event gerçekleşti. Eventi kabul etmek istiyor musun? Eğer rededersen bir gün boyunca aynı evente yakalanma ihtimalin olmayacak."+ npc.channel,
                    title="**" + npc.name + "**"
                )

                embed.set_author(name="Shiva™ Roleplay Botu")

                event.isWaiting = True

                embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/841788409613385769/1385377123711189032/1000049875.png?ex=685729fd&is=6855d87d&hm=489e8757409b7e64581d6f8190d7b1aed0eab1845bb04f7d3dcc0798e4115fae&")
                embed.set_image(url="https://cdn.discordapp.com/attachments/1271955629094866954/1385317957009412126/image.png?ex=68579ba2&is=68564a22&hm=9e44511e6d870207a0736c8e0f4b26c3a0d51c635bc506eaa07ae20d052f5dfa&")
                await message.channel.send(embed=embed, view=EventView(event, message.author.id))
            elif event.user == "nothing":
                event.users.append(message.author.id)


    if message.content.startswith("s!"):
        await Bot.process_commands(message)
        return
    elif (isRoleplaying or isNpcActive) and not message.content.startswith("//") and not isPaused:
        print("Buraya girildi.")
        webhooks = await message.channel.webhooks()

        name = "Roleplayer"
        avatar = "https://pngimg.com/d/letter_r_PNG93904.png"
    
        if Npc==None and not message.author.id in users:
            return
        
        res = await asyncio.to_thread(lambda: chat.send_message(message.author.display_name + ": " + message.content))

        if Npc != None:
            Npc.hist.append({"role":"user", "parts":[{"text":message.author.display_name + ": " + message.content}]})
            Npc.hist.append({"role":"model", "parts":[{"text": res.text}]})
            npcsColl.update_one({"name": Npc.name}, {"$set": {"hist": Npc.hist}})
            name = Npc.name
            avatar = Npc.avatarUrl
        elif event != None:
            if res.text.lower().endswith("bitti."):
                await sendEmbed(message.channel, "Event bitti. " + event.reward + " ödülünü almak için bir yetkiliyi etiketleyiniz.", "**Event Bitti!**")
                event.user = None
            event.hist.append({"role":"user", "parts":[{"text":message.author.display_name + ": " + message.content}]})
            event.hist.append({"role":"model", "parts":[{"text": res.text}]})
            eventsColl.update_one({"name": event.name}, {"$set": {"hist": event.hist}})
            name = "Eventer"
            avatar = "https://cdn.discordapp.com/attachments/1350191014350159882/1386702123097526445/image.png?ex=685aaa7d&is=685958fd&hm=6a5bcab766595c9f386bfa70dfaeab327ab0812bb94dac35beb0cf486d37a21b&"

        webhook = discord.utils.get(webhooks, name=name)

        if not webhook:
            webhook = await message.channel.create_webhook(name=name)

        print(res.text)
        
        messages = await splitMessage(res.text)
        for msg in messages:
            await webhook.send(msg,username=name,avatar_url=avatar, view=RpView(chat))

    elif isRoleplaying and isPaused and not message.content.startswith("//"):
        await asyncio.to_thread(lambda: chat.send_message(message.author.display_name + ": " + message.content + " Şuanda duraklatıldın. Role cevap veremezsin. İzleyici modundasın, tekrar başlatıldığında sana bu mesajı vermeyeceğiz."))

        if Npc!= None:
            Npc.hist.append({"role":"user", "parts":[{"text":message.author.display_name + ": " + message.content}]})
            npcsColl.update_one({"name": Npc.name}, {"$set": {"hist": Npc.hist}})

    await Bot.process_commands(message)


#ROL DIŞI KOMUTLAR


#hikaye ekleme

@Bot.command()
async def help(ctx, commands = ""):
    if commands=="npc":
        await sendEmbed(ctx,
        "NPC yapay zekası, girdiğiniz prompta göre diğer insanlarla rol yapabilir. Yapay zekanın hareket edişi tamamen sizin girdiğiniz prompta bağlıdır. Attığı emoteları tekrardan değiştirmesini sağlayabilir veya silmesini sağlayabilirsiniz. Hafızası her emotede kaydedilir ve geçmiş konuşmalarınızı durdursanız bile hatırlayabilir. Aktifken tıpkı bir üye gibi rol yapabilir." \
        "\n\n**s!addnpc npc adı | açıklama | kanal | prompt->** Kanalın içerisinde bir NPC oluşturur. Bu NPC, girdiğiniz prompta göre diğer kullanıcılarla rol yapabilir ve etkileşime girebilir." \
        "\n\n**s!removenpc npc adı ->** İsmini girdiğiniz NPC'yi kaldırır."
        "\n\n**s!stopinteraction ->** Kanalda etkileşimde bulduğunuz NPC'yi bir süreliğine deaktif eder. Bu NPC'yle istediğiniz zaman etkileşime girerek kaldığınz yerden devam edebilirsiniz. NPC deaktifken yapay zeka sizin yazdığınız rolleri işlemez." \
        "\n\n**s!pausenpc ->** Kanalda etkileşimde bulunduğunuz veya etkileşimi duraklatılmış bir NPC varsa, rolü kısa süreliğine duraklatır veya tekrar başlatır. NPC duraklatılmışken yapay zeka halen daha kanala attığınız emoteları işlemeye devam eder." \
        "\n\n**s!movenpc isim | #kanal->** Kanaldaki bir NPC'yi başka bir kanala taşır. NPC, o kanalda kaldığı yerden devam eder." \
        "\n\n**s!interactnpc npc adı ->** NPC'yle etkileşime girmenizi sağlayarak NPC'yi aktif kılar." \
        "\n\n**s!shownpcs @kullanıcı ->** Sunucudaki tüm NPC'leri gösterir."
        ,"**NPC Yapay Zekası ve Komutları**")
    elif commands=="role":
        await sendEmbed(ctx,
        "Rol yapay zekası, girdiğiniz prompta göre rol yapabilir veya rolü eventleyebilir. Yapay zekanın hareket edişi tamamen sizin girdiğiniz prompta bağlıdır. Attığı emoteları tekrardan değiştirmesini sağlayabilir veya silmesini sağlayabilirsiniz. Hafızası herhangi bir yere kaydedilmez ve kapatıldıktan sonra bir daha başlatılamaz." \
        "\n\n**s!startrole prompt->** Kanal içerisinde bir rol yapay zekası başlatır. Bu yapay zeka, girdiğiniz prompta göre rolleri    leyebilir veya karakter oynayabilir." \
        "\n\n**s!stoprole ->** Kanalda devam eden bir rol varsa o rolü sonsuza kadar kapatır." \
        "\n\n**s!pauserole ->** Kanalda durdurulmuş veya devam eden bir rol varsa, rolü kısa süreliğine durdurur veya tekrar başlatır. Rol durmuşken yapay zeka halen daha attığınız emoteları işlemeye devam eder." \
        "\n\n**s!moverole #kanal->** Kanaldaki bir rolü başka bir kanala taşır. Rol, o kanalda kaldığı yerden devam eder." \
        "\n\n**s!roleadduser @kullanıcı ->** Kanaldaki role başka bir kullanıcıyı ekler. O kullanıcının emoteları da yapay zeka tarafından işlenmeye başlar." \
        "\n\n**s!roleremoveuser @kullanıcı ->** Kanaldaki role eklenmiş bir kullanıcıyı rolden çıakrtır."
        ,"**Rol Yapay Zekası ve Komutları**")
    else:
        await sendEmbed(ctx,"**s!help npc ->** NPC komutları ve yapay zekası hakkında bilgi verir.\n\n**s!help role ->** Rol yapay zekası ve komutları hakkında bilgi verir.","**Yardım Komutları**")

#EVENT KOMUTLARI

@Bot.command()
@commands.has_permissions(manage_roles=True)
async def addevent(ctx,*,prompt):
    parameters = prompt.split("|")
    events.append(Event(parameters[0].strip(), parameters[1].strip(), parameters[2].strip(), parameters[3].strip(), parameters[4].strip()))
    eventsColl.insert_one({"name":parameters[0].strip(), "possibility":parameters[1],"channel":parameters[2].strip(),"prompt":parameters[3].strip(),"reward":parameters[4].strip()})

    await sendEmbed(ctx, "**Event İsmi: **" + parameters[0] + "\n**Event Gerçekleşme İhtimali: **" + parameters[1] + "%\n**Event Kanalı: **" + parameters[2] + "\n**Prompt: **" + parameters[3] + "\n**Ödül: **" + parameters[4], "**Event Oluşturuldu!**", "Event komutları için s!help event komutunu kullanabilirsiniz.")

@Bot.command()
@commands.has_permissions(manage_roles=True)
async def removeevent(ctx,*,name):
    for event in events:
        if event.name == name.strip():
            events.remove(event)
            eventsColl.delete_one({"name":event.name})
            await sendEmbed(ctx,name + " başlıklı event kaldırıldı. Tüm eventleri görmek için, s!showevents komutunu kullanabilirsiniz.","**Event Kaldırıldı!**", color = discord.Colour.dark_red())
            return
    await sendEmbed(ctx, name + " isimli bir event bulamadım. Lütfen, büyük küçük harf yazımına dikkat et.", "**Hata!**", color=discord.Colour.red())

@Bot.command()
@commands.has_permissions(manage_roles=True)
async def forcestartevent(ctx,*,name):
    for event in events:
        if event.name == name.strip():
            event.possibility = 100
            events.users = []
            eventsColl.delete_one({"name":event.name})
            await sendEmbed(ctx,name + " başlıklı event kanala gelen ilk kullanıcıda tetiklenecek. Tüm eventleri görmek için, s!showevents komutunu kullanabilirsiniz.","**Event Kaldırıldı!**", color = discord.Colour.dark_red())
            return
    await sendEmbed(ctx, name + " isimli bir event bulamadım. Lütfen, büyük küçük harf yazımına dikkat et.", "**Hata!**", color=discord.Colour.red())




#NPC KOMUTLARI

@Bot.command()
@commands.has_permissions(manage_roles=True)
async def addnpc(ctx,*,prompt):
    parameters = prompt.split("|")
    
    if ctx.message.attachments:
        for attachment in ctx.message.attachments:
            parameters.append(attachment.url)
    else:
        parameters.append("https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSYz8zEAFyjZKTNeQW-MRagzdrD-bTFpArsiA&s")

    npcs.append(NPC(parameters[0].strip(), parameters[1].strip(), parameters[2].strip(), parameters[3].strip(), parameters[4].strip()))
    npcsColl.insert_one({"name":parameters[0].strip(), "description":parameters[1].strip(),"channel":parameters[2].strip(),"prompt":parameters[3].strip(),"url":parameters[4].strip()})

    await sendEmbed(ctx, "**İsim:**" + parameters[0] + "\nAçıklama: " + parameters[1] + "\n**Kanal: **" + parameters[2] + "\n**Prompt: **" + parameters[3], "**NPC Oluşturuldu!**", color = discord.Colour.green())

@Bot.command()
@commands.has_permissions(manage_roles=True)
async def removenpc(ctx,*,name):
    for npc in npcs:
        if npc.name == name.strip():
            npcsColl.delete_one({"name":npc.name})
            npcs.remove(npc)
            await sendEmbed(ctx,name + " isimli NPC kaldırıldı. NPCleri görmek için, s!shownpcs komutunu kullanabilirsiniz.","**NPC Kaldırıldı!**", color = discord.Colour.dark_red())
            return
    await sendEmbed(ctx, name + " isimli bir NPC bulamadım. Lütfen, büyük küçük harf yazımına dikkat et.", "**Hata!**", color=discord.Colour.red())

@Bot.command()
async def shownpcs(ctx):
    embeds = []
    
    for npc in npcs:
        embed = discord.Embed(
            colour=discord.Colour.light_gray(),
            description="**İsim: **" + npc.name + "\n**Açıklama: **" + npc.description + "\n**Kanal: **" + npc.channel,
            title="**" + npc.name + "**"
        )

        embed.set_author(name="Shiva™ Roleplay Botu")

        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/841788409613385769/1385377123711189032/1000049875.png?ex=685729fd&is=6855d87d&hm=489e8757409b7e64581d6f8190d7b1aed0eab1845bb04f7d3dcc0798e4115fae&")
        embed.set_image(url="https://cdn.discordapp.com/attachments/1271955629094866954/1385317957009412126/image.png?ex=68579ba2&is=68564a22&hm=9e44511e6d870207a0736c8e0f4b26c3a0d51c635bc506eaa07ae20d052f5dfa&")

        embeds.append(embed)

    await ctx.send(embed=embeds[0], view=NpcView(embeds))

@Bot.command()
async def interactnpc(ctx,*,parameter):
    await ctx.message.delete()
    name = parameter.strip()

    for npc in npcs:
        if npc.name == name and ctx.guild.get_channel(npc.channel_id) == ctx.channel:
            npc.isActive = True
            await sendEmbed(ctx, npc.name + " isimli bot aktif edildi. İyi eğlenceler!", "**NPC Aktif!**", "NPC'yi başka bir kanala hareket ettirmek için **s!movenpc** komutunu kullanabilirsiniz.",delay=5)
            return
    await sendEmbed(ctx, "Bu kanalda " + name + " isimli bir NPC bulamadım. Lütfen, büyük küçük harf yazımına ve doğru kanalda olduğuna dikkat et.", "**Hata!**", color=discord.Colour.red(),delay=5)

@Bot.command()
async def pausenpc(ctx):
    await ctx.message.delete()
    for npc in npcs:
        if ctx.guild.get_channel(npc.channel_id) == ctx.channel:
            npc.isPaused = not npc.isPaused
            if(npc.isPaused):
                await sendEmbed(ctx,npc.name + " isimli NPC duraklatıldı. Etkileşime devam etmek için tekrardan s!pausenpc komutunu kullanabilirsiniz.", "**Etkileşim Duraklatıldı!**",delay=5)
            else:
                await sendEmbed(ctx, npc.name + " isimli NPC tekrardan başlatıldı. Etkileşimi tekrar durdurmak için s!pausenpc komutunu kullanabilirsiniz.", "**Etkileşim Devam Ediyor!**",delay=5)
        else:
            continue
        return

    await sendEmbed(ctx,"Üzgünüm! Bu kanalda başlatılmış bir rol bulamadım.", "**Hata!**", color=discord.Colour.red(),delay=5)

@Bot.command()
async def stopinteraction(ctx):
    await ctx.message.delete()
    for npc in npcs:
        if ctx.guild.get_channel(npc.channel_id) == ctx.channel:
            npc.isActive = False
            await sendEmbed(ctx, npc.name + " isimli bot deaktif edildi. ", "**NPC Deaktif Edildi!**", "NPC'yle role kaldığın yerden devam ettirmek için s!interactnpc komutuyla tekrardan aktif edebilirsin.",delay=5)
            return
    await sendEmbed(ctx, "Bu kanalda aktif hiçbir NPC bulamadım.", "**Hata!**", color=discord.Colour.red(),delay=5)

@Bot.command()
async def movenpc(ctx,*,prompt):
    await ctx.message.delete()
    name, channel = prompt.split("|")
    for npc in npcs:
        if npc.name == name:
            npc.setChannel(channel)
            npcsColl.update_one({"name": npc.name}, {"$set": {"channel": channel}})
            await sendEmbed(ctx, npc.name + " isimli botun kanalı: " + channel + "olarak ayarlandı.", "**NPC Hareket Etti!**", "NPC'yle role kaldığın yerden " + channel + " kanalında devam edebilirsin.", color=discord.Colour.green(),delay=5)
            return
    await sendEmbed(ctx, name + "isminde hiçbir NPC bulamadım.", "**Hata!**", color=discord.Colour.red(),delay=5)


#ROL KOMUTLARI

@Bot.command()
async def startrole(ctx,*,prompt):
    await ctx.message.delete()
    hist = [
        {"role": "user","parts": [{"text": prompt}]}
    ]
    #KULLANICI BİLGİSİDE ROLE GÖNDERİLECEK.

    roleplays.append(RolePlay(ctx.channel, hist, ctx.author.id))

    await sendEmbed(ctx, "Prompt: " + prompt + " olarak ayarlandı. Role başlayabilirsiniz. İyi eğlenceler!", "**Prompt Ayarlandı**", "Rolü durdurmak için s!stopRole komutunu, rolü duraklatmak için ise s!pauserole komutunu kullanabilirsiniz.", delay=5)

@Bot.command()
async def pauserole(ctx):
    await ctx.message.delete()
    for roleplay in roleplays:
        if roleplay.getChannel(ctx.channel):
            roleplay.isPaused = not roleplay.isPaused
            if(roleplay.isPaused):
                await sendEmbed(ctx,"Rol duraklatıldı. Role devam etmek için tekrardan s!pauserole komutunu kullanabilirsiniz.", "**Rol Duraklatıldı!**",delay=5)
            else:
                await sendEmbed(ctx,"Rol kaldığı yerden devam ediyor. Rolü tekrar durdurmak için s!pauserole komutunu kullanabilirsiniz.", "**Rol Devam Ediyor!**",delay=5)
        else:
            continue
        return

    await sendEmbed(ctx,"Üzgünüm! Bu kanalda başlatılmış bir rol bulamadım.", "**Hata!**", color=discord.Colour.red(), delay=5)


@Bot.command()
async def stoprole(ctx):
    await ctx.message.delete()
    for role in roleplays:
        if role.getChannel(ctx.channel):
            roleplays.remove(role)

            await sendEmbed(ctx,"Rol bitti, tekrar rol yapmak için s!startrole komutuyla promptunuzu girerek role tekrar başlayabilirsiniz.", "**Rol Bitti!**",delay=5)

@Bot.command()
async def moverole(ctx, channel):
    await ctx.message.delete()
    for role in roleplays:
        if role.channel == ctx.channel:
            role.channel = ctx.guild.get_channel(int(re.sub(r"\D", "", channel)))
            await sendEmbed(ctx, "Bu kanaldaki rol " + channel + " kanalına taşındı.", "**Rol Kanalı Değişti!**", "Role kaldığın yerden " + channel + " kanalında devam edebilirsin.", color=discord.Colour.green(),delay=5)
            return
    await sendEmbed(ctx, "Bu kanalda hiçbir rol bulamadım.", "**Hata!**", color=discord.Colour.red(),delay=5)

@Bot.command()
async def roleadduser(ctx,user:discord.Member):
    await ctx.message.delete()
    for role in roleplays:
        if role.channel == ctx.channel:
            if user.id in role.users:
                await sendEmbed(ctx, user.mention + " kullanıcısı zaten bu rolde ekli.", "**Kullanıcı Zaten Ekli!**", color=discord.Colour.yellow(),delay=5)
            role.users.append(user.id)
            await sendEmbed(ctx, user.mention + " kullanıcısı bu kanalda yapılan role eklendi.", "**Kullanıcı Role Eklendi!**", color=discord.Colour.green(),delay=5)
            return
    await sendEmbed(ctx, "Kullanıcı bulunamadı. Doğru kişiyi etiketlediğinizden emin olunuz.", "**Hata!**", color=discord.Colour.red(),delay=5)

@Bot.command()
async def roleremoveuser(ctx,user:discord.Member):
    await ctx.message.delete()
    for role in roleplays:
        if role.channel == role.channel:
            if user.id in role.users:
                role.users.remove(user.id)
                await sendEmbed(ctx, user.mention + " kullanıcısı rolden çıkartıldı.", "**Kullanıcı Rolden Çıkartıldı!**", color=discord.Colour.green(),delay=5)
                return
    await sendEmbed(ctx, "Kullanıcı bulunamadı. Doğru kişiyi etiketlediğinizden emin olunuz.", "**Hata!**", color=discord.Colour.red(),delay=5)

Bot.run("API_KEY")