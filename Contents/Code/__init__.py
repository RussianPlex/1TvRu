# -*- coding: utf-8 -*-
#
# Plex plugin for viewing internet archives of the Russian
# TV station "Pervy Canal" ("Channel One") - http://www.1tv.ru/
#
# Плагин для бесплатного просмотра интернет архива российского
# телевизионного канала Первый Канал - http://www.1tv.ru/
#
# @author Alex Titoff <rozdol@gmail.com> - http://rozdol.com/
# @author Zhenya Nyden <yev@curre.net>
#
####################################################################################################
# v0.3 - March 31, 2012
# > Upgrade to Plex plugin framework version 2
# > Updated scraping code to work with the latest site's DOM
# > Bug fixes
#
# v0.2 - January 22, 2011
# > Changed default icon
# > Added russian localization
# > List of channels in MainMenu
#
# v0.1 - January 20, 2011
# > Initial release
#
###################################################################################################

import re

VIDEO_PREFIX = "/video/1tvru"
VERSION = 0.3
NAME = L('Title')
CACHE_INTERVAL = 18
ART  = 'art-default.png'
ICON = 'icon-default.png'
PREFS = 'icon-prefs.png'
BASE_URL = 'http://www.1tv.ru'

TV_ARCHIVE = '%s/videoarchiver' % BASE_URL
V_LINK = ''
TEST = 'http://www.1tv.ru/owa/win/ONE_ONLINE_VIDEOS.news_single_xml?pid=28425'
PLAY_URL = 'http://www.1tv.ru/owa/win/ONE_ONLINE_VIDEOS.news_single_xml?pid='
CLIP = '?file=http://www.1tv.ru/owa/win/ONE_ONLINE_VIDEOS.news_single_xml%3Fpid=28425'
URL = 'http://img2.1tv.ru/images/one/video_player.swf?file='
FULL_URL = 'http://img2.1tv.ru/images/one/video_player.swf?file=http://www.1tv.ru/owa/win/ONE_ONLINE_VIDEOS.news_single_xml%3Fpid=28425'

USER_AGENT = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10.6; ru; rv:1.9.2.13) Gecko/20101203 Firefox/3.6.13 GTB7.1'
ENCODING_1TV_PAGE = 'cp1251'
ENCODING_PLEX = 'utf-8'

PREF_CACHE_TIME_NAME = 'tvru_pref_cache_time'
PREF_CACHE_TIME_DEFAULT = CACHE_1MINUTE

####################################################################################################

def Start():
  Plugin.AddPrefixHandler(VIDEO_PREFIX, MainMenu, L('Title'), ICON, ART)
  Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
  Plugin.AddViewGroup("List", viewMode="List", mediaType="items")
  MediaContainer.art = R(ART)
  MediaContainer.title1 = NAME
  MediaContainer.viewGroup = "List"
  DirectoryItem.thumb = R(ICON)
  VideoItem.thumb = R(ICON)

  # Setting cache expiration time.
  prefCache = Prefs[PREF_CACHE_TIME_NAME]
  if prefCache == u'10 секунд':
    cacheExp = 10
  elif prefCache == u'1/2 минуты':
    cacheExp = 30
  elif prefCache == u'1 минута':
    cacheExp = CACHE_1MINUTE
  elif prefCache == u'10 минут':
    cacheExp = CACHE_1MINUTE * 10
  elif prefCache == u'1 час':
    cacheExp = CACHE_1HOUR
  elif prefCache == u'1 день':
    cacheExp = CACHE_1DAY
  elif prefCache == u'1 неделя':
    cacheExp = CACHE_1DAY
  elif prefCache == u'1 месяц':
    cacheExp = CACHE_1MONTH
  else:
    cacheExp = PREF_CACHE_TIME_DEFAULT
  HTTP.CacheTime = cacheExp

####################################################################################################

def CreatePrefs():
  Prefs.Add(id='username', type='text', default='', label=L('USERNAME'))
  Prefs.Add(id='password', type='text', default='', label=L('PASSWORD'), option='hidden')

####################################################################################################

def ValidatePrefs():
  global logged_in
  u = Prefs.Get('username')
  p = Prefs.Get('password')
  logged_in = False
  logged_in, header, message = Login()
  if (u and p):
    return MessageContainer("Success", "User and password provided ok")
  else:
    return MessageContainer("Error", "You need to provide both a user and password")

####################################################################################################

def ShowMessage(sender, title, message):
  return MessageContainer(title, message)

####################################################################################################

def MainMenu():
  """ Handles creation of the main menu.
  """
  dir = MediaContainer()
  dir.viewGroup = 'List'
  page = getElementFromHttpRequest(TV_ARCHIVE)
  sectionsElems = page.xpath('//div[@class="tv_head"]')
  Log("----> %s Categories" % len(sectionsElems))
  index = 0
  for sectionEl in sectionsElems:
    sectionTitle = sectionEl.xpath('./div[@class="tv_head-ins"]')[0].text.strip()
    quantity = sectionEl.xpath('./div[@class="tv_head-ins"]/span')[0].text.strip()
    sectionUrl = sectionEl.xpath('./div[@class="tv_head-right"]/a')[0].get('href')
    menuItemLabel = sectionTitle + ' ' + quantity
    Log("----> Channel %s = '%s'" % (index, menuItemLabel))
    dir.Append(Function(DirectoryItem(PageBrws, title=menuItemLabel, thumb=''), link=sectionUrl))
    index += 1
  if not len(sectionsElems):
    dir.header = L('CHANNEL')
    dir.message = L('NOTFOUND')

  dir.Append(Function(DirectoryItem(About, title=L('ABOUT'), thumb=R(ICON))))
  return dir


def PageBrws(sender, link):
  sectionAbsoluteUrl = BASE_URL + link
  dir = MediaContainer(title2=sender.itemTitle)
  dir.viewGroup = 'InfoList'
  page = getElementFromHttpRequest(sectionAbsoluteUrl)
  # Parse main content element (it contains image video thumbs, title, and links).
  elements = page.xpath('//div[@id="list_abc_search"]/ul/li')
  Log("----> %s Categories" % len(elements))
  if len(elements) > 0:
    index = 0
    for element in elements:
      title = element.xpath('./div[@class="txt"]/a')[0].text
      date = element.xpath('./div[@class="date"]')[0].text
      link = element.xpath('./div[@class="txt"]/a')[0].get('href')
      Log('title=%s, date=%s, link=%s' % (str(title), str(date), str(link)))
      imgThumbUrlElems = element.xpath('./div[@class="img" or @class="img low"]/a/img')
      if len(imgThumbUrlElems) > 0:
        imgThumbUrl = imgThumbUrlElems[0].get('src')
      else:
        # TODO(zhenya): replace with something different (a local asset).
        imgThumbUrl = 'http://f888.biz/images/default_site.png'
      Log("----> Channel %s = '%s'" % (index, title))
      #dir.Append(Function(DirectoryItem(EPGBrws, title=title, subtitle=date, thumb=''), link=link))
      dir.Append(
        Function(VideoItem(PlayLink, title=title, subtitle=date, summary='', thumb=Function(Thumb, url=imgThumbUrl)),
          link=link))
      index += 1
  else:
    dir.header = L('CHANNEL')
    dir.message = L('NOTFOUND')

  return dir

####################################################################################################

def SearchBrws(sender, link):
  global logged_in
  #logged_in = True
  if logged_in == False:
    Log("----> NOT LOGGED IN! '%s'" % (logged_in))
    dir = MainMenu()
    dir.replaceParent = True
  else:
    Log("----> User is logged in '%s'" % (logged_in))
    dir = MediaContainer(title2=L('SEARCHRESULT'))
    dir.viewGroup = 'InfoList'
    Log("----> URL='%s'" % (BASE_URL + link ))
    #test=HTTP.Request(BASE_URL + link)
    xp = '//tbody/tr[td[@width="55"]]'
    elements = XML.ElementFromString(
      HTTP.Request(BASE_URL + link).replace('<a href="#" class="open_stream"><span class="fade"></span></a>',
        '').decode('utf-8').strip(), isHTML=True).xpath(xp)
    #Log("----> XML: '%s'" % (elements.text))
    Log("----> %s Items found" % len(elements))
    i = 0
    if len(elements) > 0:
      for element in elements:
        i += 1
        id = i
        j = 0
        tokens = element.xpath("./td/a[@title]")
        title = element.xpath("./td/a[@title]")[0].text
        title = re.sub(r'  ', r'', title)
        title = re.sub(r'\n', r'', title)
        linktoday = element.xpath("./td/a[@title]")[0].get('href')
        #title=element.xpath("./td/a[@title]")[0].text
        link = linktoday
        arr = link.split('/')
        id = arr[4]
        duration = "14:00"
        subtitle = element.xpath('./td[@width="150"]/a')[0].text
        date = element.xpath('./td[@style][1]')[0].text
        rating = element.xpath('./td[@width="55"][1]')[0].text
        duration = element.xpath('./td[@width="100"][1]')[0].text
        year = element.xpath('./td[@width="100"][2]')[0].text
        summary = L('AIRED') + ':' + date + '\n\n' + L('DURATION') + ':' + duration + '\n\n' + L(
          'RATING') + ':' + rating + '\n\n' + L('YEAR') + ':' + year
        Log("----> Channel %s = '%s'" % (id, title))
        dir.Append(Function(VideoItem(PlayLink, title=title, subtitle=subtitle, summary=summary, thumb=''), id=id))
        dir.Append(
          Function(DirectoryItem(Search2Brws, title='->' + title, subtitle=subtitle, summary=summary, thumb=''),
            link=link))
    else:
      dir.header = L('ERROR')
      dir.message = L('NOTFOUND')
  return dir

####################################################################################################

def Search2Brws(sender, link):
  global logged_in
  #logged_in = True
  if logged_in == False:
    Log("----> NOT LOGGED IN! '%s'" % (logged_in))
    dir = MainMenu()
    dir.replaceParent = True
  else:
    Log("----> User is logged in '%s'" % (logged_in))
    dir = MediaContainer(title2='Rearch Result')
    dir.viewGroup = 'InfoList'
    Log("----> URL='%s'" % (BASE_URL + link ))
    #test=HTTP.Request(BASE_URL + link)
    xp = '//tbody/tr[td[@width="110"]]'
    elements = XML.ElementFromString(
      HTTP.Request(BASE_URL + link).replace('<a href="#" class="open_stream"><span class="fade"></span></a>',
        '').decode('utf-8').strip(), isHTML=True).xpath(xp)
    #Log("----> XML: '%s'" % (elements.text))
    Log("----> %s Items found" % len(elements))
    i = 0
    if len(elements) > 0:
      for element in elements:
        i += 1
        id = i
        j = 0
        tokens = element.xpath("./td/a[@title]")
        title = element.xpath("./td/a[@title]")[0].text
        title = re.sub(r'  ', r'', title)
        title = re.sub(r'\n', r'', title)
        linktoday = element.xpath("./td/a[@title]")[0].get('href')
        #title=element.xpath("./td/a[@title]")[0].text
        link = linktoday
        arr = link.split('/')
        id = arr[4]
        date = element.xpath('./td[1]')[0].text
        rating = element.xpath('./td[4]')[0].text
        duration = element.xpath('./td[5]')[0].text
        year = element.xpath('./td[6]')[0].text
        subtitle = date
        summary = L('AIRED') + ':' + date + '\n\n' + L('DURATION') + ':' + duration + '\n\n' + L(
          'RATING') + ':' + rating + '\n\n' + L('YEAR') + ':' + year + '\n\nLink:' + link
        Log("----> Channel %s = '%s'" % (id, title))
        dir.Append(Function(VideoItem(PlayLink, title=title, subtitle=subtitle, summary=summary, thumb=''), id=id))
    else:
      dir.header = L('ERROR')
      dir.message = L('NOTFOUND')
  return dir

####################################################################################################

def EPGBrws(sender, link):
  dir = MediaContainer(title3=sender.itemTitle)
  dir.viewGroup = 'InfoList'
  Log("----> URL='%s'" % (BASE_URL + link ))
  #test=HTTP.Request(BASE_URL + link)
  xp = "//tbody/tr"
  elements = XML.ElementFromURL(BASE_URL + link, isHTML=True).xpath(xp)
  Log("----> elements '%s'" % (elements))
  #summary=getDescr(url='http://etvnet.com/tv/novosti-online/sobyitiya/378779/')
  summary = ''
  for element in elements:
    #title = c.get('title').encode('iso-8859-1').decode('utf-8').strip()
    #id = c.get('id')
    id = 1
    subtitle = element.xpath("./td[@width='155']")[0].text.encode('iso-8859-1').decode('utf-8').strip()
    title = element.xpath("./td/a")[0].text.encode('iso-8859-1').decode('utf-8').strip()
    linktoday = element.xpath("./td/a")[0].get('href')
    #linkarchieve=element.xpath("./td/center/a")[0].get('href')
    link = linktoday
    arr = link.split('/')
    id = arr[4]
    duration = "14:00"
    Log("----> title '%s' Dur:%s, SUB:%s" % (title, duration, subtitle))
    dir.Append(Function(VideoItem(PlayLink, title=title, subtitle=subtitle, summary=summary, thumb=''), id=id))
  return dir

####################################################################################################

def PlayLink(sender, link):
  arr = link.split('/')
  pid = arr[2]

  link = PLAY_URL + pid

  url = GetVideoURL(url=link)
  Log("----> play from '%s'" % (url))
  return Redirect(VideoItem(url, 'Title'))

####################################################################################################

def getDescr(url):
  Log("----> GetDescr '%s' " % (url))
  if url:
    try:
      xp = "//div[@class='description'][2]"
      Log("----> xp='%s' " % (xp))
      data = HTTP.Request(url, cacheTime=CACHE_1MONTH).xpath(xp).decode('utf-8').strip()
      Log("----> data='%s' " % (data))
      return data
    except:
      pass
  return L('NOTFOUND')

####################################################################################################

def GetVideoURL(url):
  Log("----> GetVideoURL: '%s'" % (url))
  page = getElementFromHttpRequest(url)
  elements = page.xpath('//item')
  Log("----> %s Items found" % (elements))
  i = 0
  if len(elements) > 0:
    for element in elements:
      i += 1
      link = element.xpath(".//*[@type='http']")[0].get('url')
      Log("----> %s Link" % (link))
  #link='http://www-download.1tv.ru/promorolik/2011/01/DU-20110111-01-01.mp4'
  return link

####################################################################################################

def Login():
  global logged_in
  if logged_in == True:
    return [True, '', '']
  elif not Prefs.Get('username') and not Prefs.Get('password'):
    return [False, L('LOGIN_TITLE'), L('LOGIN_NOT_SET')]
  else:
    #initiate = HTTP.Request(BASE_URL+'/login/', encoding='iso-8859-1', cacheTime=1)
    values = {
      'action': '/login/',
      'username': Prefs.Get('username'),
      'next': '/about',
      'password': Prefs.Get('password'),
      'remember_me': 'on'
    }
    login = HTTP.Request(BASE_URL + '/login/', values=values, encoding='iso-8859-1', cacheTime=1)
    # Check the response and see if the login attempt was successful
    #Log(" --> Response:%s" % login)
    check = re.compile('logout').findall(login)
    if len(check) > 0:
      # If login is successful
      logged_in = True
      Log(' --> Login successful! ')
      return [True, '', '']
    else:
      logged_in = False
      Log(' --> Username/password incorrect!')
      return [False, L('LOGIN_TITLE'), L('LOGIN_ERROR')]

####################################################################################################

def Thumb(url):
  Log("----> %s Image" % (url))
  if url:
    try:
      #data = HTTP.Request(url, cacheTime=CACHE_1MONTH).content
      data = HTTP.Request(url, cacheTime=CACHE_1MONTH)
      Log("----> %s Image Success" % (url))
      return DataObject(data, 'image/jpeg')
    except:
      pass
  return Redirect(R(ICON))

####################################################################################################

def Photo(url):
  try:
    photo_url = HTML.ElementFromURL(url).xpath('//link[@rel="image_src"]')[0].get('href')
    data = HTTP.Request(photo_url, cacheTime=CACHE_1MONTH).content
    return DataObject(data, 'image/jpeg')
  except:
    return Redirect(R(ICON))

####################################################################################################

def Search(sender, query):
  query = re.sub(r' ', r'+', query)
  return SearchBrws('Result', link='/search/?q=' + urllib.quote_plus(query).encode("utf-8"))

####################################################################################################

def About(sender):
  return MessageContainer('About (version ' + str(VERSION) + ')', L('ABOUTTEXT'))

####################################################################################################

def getElementFromHttpRequest(url):
  try:
    Log("----> fetching URL='%s'" % str(url))
    response = HTTP.Request(url, headers={
        'User-agent': USER_AGENT,
        'Accept': 'text/html'})
    response = str(response).decode(ENCODING_1TV_PAGE)
    return HTML.ElementFromString(response)
  except:
    return None
