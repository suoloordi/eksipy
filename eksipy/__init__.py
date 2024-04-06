#!/usr/bin/python
# -*- coding: utf8 -*-

# Unofficial Ekşi Sözlük private API.

# Copyright (C) 2021 Yusuf Usta
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import json
from requests_html import AsyncHTMLSession, HTML
from requests import utils, Session
from requests.models import PreparedRequest
from datetime import datetime
from time import mktime
import os
from eksipy.models import *
from typing import Union, List
import pytz


class Eksi:
    def __init__(self, session: AsyncHTMLSession = None, config={"EKSI_URL": "https://eksisozluk.com/"},
                 user_agent="Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0"):
        """
        Sınıfı başlatır.
        """

        if session == None:
            self.session = AsyncHTMLSession(mock_browser=False)
        else:
            if isinstance(session, AsyncHTMLSession):
                self.session = session
            else:
                self.session = AsyncHTMLSession(mock_browser=False)
        self.config = config
        self.eksi = self.config["EKSI_URL"]
        self.user_agent = user_agent
        cookies = {
            'channel-filter-preference-cookie': 'W3siSWQiOjEsIlByZWYiOnRydWV9LHsiSWQiOjIsIlByZWYiOnRydWV9LHsiSWQiOjQsIlByZWYiOnRydWV9LHsiSWQiOjUsIlByZWYiOnRydWV9LHsiSWQiOjEwLCJQcmVmIjpmYWxzZX0seyJJZCI6MTEsIlByZWYiOmZhbHNlfV0=',
            'app-suggestion': '1',
            'notheme': '1',
            '__RequestVerificationToken': 'LBnt6F8idkaAzx9yQUldrwqFZlMoToxEfZp2PPdSr4VOqk3uts2YWR7WnfvgFhxPxklduENSlHqxGGSWEIakT8-hzpVZj4I_3XU1gkukkgw1',
            'a': 'V+doTEb5lze/NSxGRdAj1NWiHVvZOsKShaq3O2S/K3fT38HmzSeA4CkcFv0BNOF0i4z4WwGjP6XLgqfJSrKOAzF0t+IPQLlANJDC1NpvZHPEhDFDD/DW1Tg2vu8bDDO34CXSWJhUGakaQHfOOEXh+Sat/ouTLGKXhMZg3DSuQhk=',
            'led_msg': '1',
            'led_tra': '',
            'led_evt': '1',
            'cf_clearance': 'nsuA3nQ6KITa7ZFR07tJwHhUQhIH8Eo27trTcJRSe2o-1712419558-1.0.1.1-1iFOsEqvQnhS__QQZWt7jx0jIMSbUp9LBWqxZKxwWH6nZxg91R3y3A99CLAeHrmYQvNy_ZZDy8_07EbHaVX5gg',
        }
        for name, value in cookies.items():
            self.session.cookies.set(name, value)

    def addParamsToUrl(self, url: str, params: dict) -> str:
        """
        Belirtilen parametreleri adrese ekler.
        """

        req = PreparedRequest()
        req.prepare_url(url, params)
        return req.url

    async def bugun(self, page=1) -> List[Topic]:
        """
        Ekşi Sözlükteki bugün bölümü çeker.
        """

        bugun = await self.session.get(
            f'{self.eksi}basliklar/bugun/{page}&_=0', headers={'user-agent':self.user_agent}
        )

        topics = bugun.html.find(
            '#content-body > ul', first=True).find("a")
        basliklar = []

        for topic in topics:
            topic_id = topic.find('a', first=True).pq
            if not topic_id == None:
                if topic_id.find('small'):
                    giri_sayi = topic_id('small').text()
                    topic_id('small').remove()
                else:
                    giri_sayi = None
                baslik = topic_id.text()
                topic_id = int(topic_id("a").attr("href").split(
                    '?day=')[0].split('--')[1])
            else:
                continue

            basliklar.append(
                Topic(
                    self,
                    id=topic_id,
                    title=baslik,
                    giri=giri_sayi
                )
            )
        return basliklar

    async def convertToTopic(self, title) -> str:
        """
        Yazdığınız kelimeleri başlığa çevirir.
        """

        istek = await self.session.get(self.eksi + "?q=" + title, headers={'user-agent':self.user_agent})
        if istek.status_code != 404:
            return istek.url
        else:
            return False

    async def getEntrys(self, baslik: Topic, page=1, day=None, sukela=None) -> List[Entry]:
        """
        Verdiğiniz başlığın entrylerini çeker.
        """

        url = await baslik.getUrl()
        url = self.addParamsToUrl(url, {"p": page})
        if not day == None:
            url = self.addParamsToUrl(url, {"day": day})
        if not sukela == None:
            url = self.addParamsToUrl(url, {"a": sukela})

        topic = await self.session.get(
            url, headers={'user-agent':self.user_agent}
        )

        topic = topic.html.find("#topic", first=True)
        entrys = topic.find("#entry-item-list", first=True).find("li")
        giriler = []
        for entry in entrys:
            duzenleme, tarih = self.convertToDate(entry.find(
                "footer > div.info > div.entry-footer-bottom > div.footer-info > div > a.entry-date", first=True).text)
            giriler.append(
                Entry(
                    self,
                    id=entry.attrs['data-id'],
                    author=User(
                        self,
                        id=entry.attrs['data-author-id'], nick=entry.attrs['data-author']),
                    entry=entry.pq(".content"),
                    topic=baslik,
                    date=tarih,
                    edited=duzenleme,
                    fav_count=entry.attrs['data-favorite-count'],
                    comment=entry.attrs['data-comment-count'],
                )
            )
        return giriler

    async def getEntry(self, entry: int) -> Entry:
        """
        Belirli bir entry çeker.
        """

        url = self.eksi + "entry/" + str(entry)
        topic = await self.session.get(
            url, headers={'user-agent':self.user_agent}
        )

        topic = topic.html.find("#topic", first=True)
        entry = topic.find("#entry-item-list", first=True).find("li")[0]
        tarih = entry.find(
            "footer > div.info > div.entry-footer-bottom > div.footer-info > div > a.entry-date", first=True).text
        duzenleme, tarih = self.convertToDate(tarih)
        return Entry(
            self,
            id=entry.attrs['data-id'],
            author=User(
                self,
                id=entry.attrs['data-author-id'], nick=entry.attrs['data-author']),
            entry=entry.pq(".content"),
            date=tarih,
            edited=duzenleme,
            fav_count=entry.attrs['data-favorite-count'],
            comment=entry.attrs['data-comment-count'],
        )


    def convertToDate(self, date: str) -> tuple:
        """
        Converts Ekşi Sözlük time to Unix time.

        Args:
            date (str): The date string in Ekşi Sözlük format.

        Returns:
            tuple: A tuple containing the edit time (Unix timestamp) and the creation time (Unix timestamp).
        """

        # Set the timezone to Turkey
        tz = pytz.timezone('Europe/Istanbul')

        if '~' in date:
            parcalama = date.split('~')
            parcalama[0] = parcalama[0].strip()
            parcalama[1] = parcalama[1].strip()

            creation_date = tz.localize(datetime.strptime(parcalama[0], "%d.%m.%Y %H:%M" if ':' in parcalama[0] else "%d.%m.%Y"))
            creation_time = creation_date.timestamp()

            if '.' in parcalama[1]:
                edit_date = tz.localize(datetime.strptime(parcalama[1], "%d.%m.%Y %H:%M" if ':' in parcalama[1] else "%d.%m.%Y"))
                edit_time = edit_date.timestamp()
            else:
                edit_time_str = f"{parcalama[0].split(' ')[0]} {parcalama[1]}"
                edit_date = tz.localize(datetime.strptime(edit_time_str, "%d.%m.%Y %H:%M"))
                edit_time = edit_date.timestamp()
        else:
            creation_date = tz.localize(datetime.strptime(date, "%d.%m.%Y %H:%M" if ':' in date else "%d.%m.%Y"))
            creation_time = creation_date.timestamp()
            edit_time = False

        return edit_time, creation_time
        
    async def gundem(self, page=1) -> List[Topic]:
        """
        Gündem feedini çeker
        """

        gundem = await self.session.get(
            f'{self.eksi}basliklar/gundem?p={page}', headers={'user-agent':self.user_agent}
        )

        topics = gundem.html.find(
            '#content-body > ul', first=True).find("a")
        basliklar = []

        for topic in topics:
            topic_id = topic.find('a', first=True).pq
            if not topic_id == None:
                if topic_id.find('small'):
                    giri_sayi = topic_id('small').text()
                    topic_id('small').remove()
                else:
                    giri_sayi = None
                baslik = topic_id.text()
                topic_id = int(topic_id("a").attr("href").split(
                    '?a=')[0].split('--')[1])
            else:
                continue

            basliklar.append(
                Topic(
                    self,
                    id=topic_id,
                    title=baslik,
                    giri=giri_sayi
                )
            )
        return basliklar

    async def debe(self) -> List[Entry]:
        """
        Debe bölümünü çeker
        """

        gundem = await self.session.get(
            f'{self.eksi}/debe', headers={'user-agent':self.user_agent}
        )

        topics = gundem.html.find(
            '#content-body > ul', first=True).find("li")
        basliklar = []

        for topic in topics:
            topic = topic.find("a", first=True)
            basliklar.append(
                Entry(
                    self,
                    id=int(topic.attrs['href'].split('/entry/')[1]),
                    topic=Topic(self, title=topic.text)
                )
            )
        return basliklar

    async def login(self, username: str, password: str):
        """
        Ekşi Sözlüğe giriş yapar.
        """

        giris = await self.session.get(f"{self.eksi}giris", headers={'user-agent':self.user_agent})
        rvt = giris.html.find(
            'input[name="__RequestVerificationToken"]', first=True).attrs['value']
        login = await self.session.request("POST",
                                           "https://eksisozluk.com/giris",
                                           data={
                                               "UserName": username,
                                               "Password": password,
                                               "__RequestVerificationToken": rvt,
                                               "RememberMe": "true",
                                               "ReturnUrl": "https%3A%2F%2Feksisozluk.com%2F"
                                           },
                                           headers={
                                               'User-Agent': self.user_agent,
                                               'Content-Type': 'application/x-www-form-urlencoded',
                                           }
                                           )

        cookies = utils.dict_from_cookiejar(self.session.cookies)
        if "a" in cookies:
            self.User = username
            return True  # user
        else:
            if login.status_code == 404:
                raise Exception(
                    "giriş yaparken captcha geldi herhal. bi login sayfasına bakın.")
            else:
                raise Exception(
                    f"{login.status_code}: giriş başarısırız.")

    def saveSession(self, location=None):
        """
        Ekşi Sözlük cookieslerini bir dosyaya kaydeder. Tekrar giriş yapmak için vakit harcanmaz.
        """

        cookies = []
        for c in self.session.cookies:
            cookies.append({
                "name": c.name,
                "value": c.value,
                "domain": c.domain,
                "path": c.path,
                "expires": c.expires
            })
        if location == None:
            if not os.path.exists("sessions"):
                os.mkdir("sessions")
            location = os.path.join("sessions", f"{self.User}.json")
            veri = json.dumps(cookies)
            open(location, "w+").write(veri)
        else:
            veri = json.dumps(cookies)
            open(location, "w+").write(veri)
        return location

    def loadSession(self, location):
        """
        Ekşi Sözlük cookiesleri yükler.
        """

        veriler = json.loads(open(location, "r").read())
        for c in veriler:
            self.session.cookies.set(**c)
        return True

    async def sendEntry(self, topic: Topic, entry: str, hidden: bool = False):
        """
        Entry gönderir.
        """

        page = await self.session.get(await topic.getUrl(), headers={'user-agent':self.user_agent})

        ReqVerTok = page.html.find(
            'input[name="__RequestVerificationToken"]', first=True).attrs['value']
        Title = page.html.find(
            'input[name="Title"]', first=True).attrs['value']
        Id = page.html.find(
            'input[name="Id"]', first=True).attrs['value']
        InputStartTime = page.html.find(
            'input[name="InputStartTime"]', first=True).attrs['value']

        istek = await self.session.request("POST",
                                           f"https://eksisozluk.com/entry/ekle",
                                           data={
                                               'Title': Title,
                                               'Id': Id,
                                               '__RequestVerificationToken': ReqVerTok,
                                               'ReturnUrl': '',
                                               'Content': entry,
                                               'InputStartTime': InputStartTime,
                                               'AddAsHidden': 'true' if hidden else 'false'
                                           },
                                           headers={"User-Agent": "PostmanRuntime/7.26.10",
                                                    "content-type": "application/x-www-form-urlencoded"},
                                           allow_redirects=False
                                           )

        if istek.status_code == 302:
            entry = istek.headers['location'].split('/')[2]
            return (await self.getEntry(entry))
        else:
            if istek.status_code == 404:
                raise Exception(
                    f"{istek.status_code}: muhtemelen böyle bir entry var ondan gönderemiyoruz. siz gene de bir bakın.")
            else:
                raise Exception(f"{istek.status_code}: bir hata oluştu.")

    async def getTopic(self, title) -> Topic:
        """
        Başlık getirir.
        """

        adres = await self.convertToTopic(title)
        if adres != False:
            baslik = await self.session.get(adres)
            title = baslik.html.find("#title", first=True)
            pager = baslik.html.find("div[class='pager']", first=True)

            return Topic(
                self,
                id=int(title.attrs['data-id']),
                title=title.attrs['data-title'],
                max_page=int(pager.attrs['data-pagecount']),
                current_page=int(pager.attrs['data-currentpage']),
                slug=title.attrs['data-slug'],
                url=adres
            )
        else:
            raise Exception("404: böyle bir başlık yok.")

    async def favEntry(self, entry: Union[Entry, int]):
        """
        Entry favoriler.
        """

        anaistek = await self.session.post(
            f"{self.eksi}entry/favla",
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            data={
                'entryId': entry.id if isinstance(entry, Entry) else entry
            },
            allow_redirects=False
        )

        istek = anaistek.json()
        if istek['Success'] == True:
            return istek['Count']
        else:
            raise Exception(f'{anaistek.status_code}: {istek["ErrorMessage"]}')

    async def unfavEntry(self, entry: Union[Entry, int]):
        """
        Entry favorisi kaldırır.
        """

        anaistek = await self.session.post(
            f"{self.eksi}entry/favlama",
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            data={
                'entryId': entry.id if isinstance(entry, Entry) else entry
            },
            allow_redirects=False
        )

        istek = anaistek.json()
        if istek['Success'] == True:
            return istek['Count']
        else:
            raise Exception(f'{anaistek.status_code}: {istek["ErrorMessage"]}')

    async def deleteEntry(self, entry: Union[Entry, int]):
        """
        Entry siler.
        """

        istek = await self.session.post(
            f"{self.eksi}entry/sil",
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            data={
                'id': entry.id if isinstance(entry, Entry) else entry
            },
            allow_redirects=False
        )

        if istek.status_code == 200:
            return True
        else:
            raise Exception(
                f'{istek.status_code}: kesinlikle bir şeyler oldu.')

    async def autoComplete(self, text: str):
        istek = await self.session.get(
            f'{self.eksi}autocomplete/query?q={text}&_=0',
            headers={
                'x-requested-with': 'XMLHttpRequest',
                'user-agent':self.user_agent
            }
        )
        return istek.json()

    async def upVoteEntry(self, entry: Entry):
        """
        Upvote atar.
        """

        istek = await self.session.post(
            f"{self.eksi}entry/vote",
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            data={
                'id': entry.id,
                'rate': 1,
                'owner': entry.author_id
            },
            allow_redirects=False
        )
        istek = istek.json()

        return istek['Success']

    async def downVoteEntry(self, entry: Entry):
        """
        Downvote atar.
        """

        istek = await self.session.post(
            f"{self.eksi}entry/vote",
            headers={
                'x-requested-with': 'XMLHttpRequest'
            },
            data={
                'id': entry.id,
                'rate': -1,
                'owner': entry.author_id
            },
            allow_redirects=False
        )
        istek = istek.json()

        return istek['Success']

    async def isLogged(self):
        homepage = await self.session.get(
            self.eksi, headers={'user-agent':self.user_agent}
        )

        try:
            homepage.html.find(
                'li[class="not-mobile"]', first=True).find('a', first=True).attrs['title']
            return True
        except:
            return False
