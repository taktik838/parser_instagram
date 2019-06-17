#!/usr/bin/python3

# ссылка жертвы
target_url = input( 'введите ссылку на жертву:\n' )
# if target_url == '':target_url = 'https://www.instagram.com/instagram/'
from bs4        import BeautifulSoup 
from json       import loads as j_loads
from threading  import Thread
from queue      import Queue
from sys        import argv
import os, time, requests, re

header = {'user-agent':'Mozilla/5.0 (X11; CrOS x86_64 11895.118.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.159 Safari/537.36'}

def my_requests(url):
    # start = time.time()
    while True:
        try:
            r = requests.get( url, headers=header )
        except requests.exceptions.ConnectionError:
            time.sleep(2)
        else:
            if r.status_code == 429:
                time.sleep(2)
            else:
                break
    return r

class Log(Thread):
    count = 0
    work = True
    def __init__(self):
        super().__init__()
    def run(self):
        oldCount = 0
        while Log.work:
            with open( argv[0][:-9] + 'Parse.log', 'w' ) as f:
                log =   'count = ' + str(Log.count) +\
                        '\nspeed = ' + str((Log.count - oldCount)/2) + '/s' +\
                        '\nend cursor = ' + str(lastJpg) +\
                        '\nremaining = ' + str(allJpg.qsize()) +\
                        '\nquery hash = ' + str(queryHash) +\
                        '\nhash photo = ' + str(queryHashPhoto)
                for th in allThread:
                    log += '\n' + str(th.name) + ': ' + str(th.status) 
                f.write(log)
            oldCount = Log.count            
            time.sleep(2)

class Parser(Thread):
    def __init__(self):
        self.status = ''
        super().__init__()

    def parse_videos( self, infoJpg ):
        shortcode = infoJpg['shortcode']
        url = 'https://www.instagram.com/graphql/query/?query_hash='+queryHash+'&variables={"shortcode":"'+shortcode+'"}'
        urlVideo = None
        r = my_requests(url)
        rj = r.json()
        urlVideo = rj['data']['shortcode_media']['video_url']
        r = my_requests(urlVideo)
        time_create = infoJpg['taken_at_timestamp']
        time_create = str(time.ctime(time_create))
        self.status = r.url
        f = open( pathVideo + time_create + '.mp4', 'wb' )
        f.write(r.content)
        f.close()

    def parse_photos( self, infoJpg ):
        urlJpg = infoJpg['display_url']
        r = my_requests(urlJpg)
        time_create = infoJpg['taken_at_timestamp']
        time_create = str(time.ctime(time_create))
        self.status = r.url
        f = open( pathPhoto + time_create + '.jpg', 'wb' )
        f.write(r.content)
        f.close()
        
    def run(self):
        try:
            while not allJpg.empty() or WORK:
                self.status = 'wait'
                Log.count += 1
                infoJpg = allJpg.get()
                self.status = 'https://www.instagram.com/p/' + infoJpg['shortcode']
                if infoJpg['is_video']:
                    self.parse_videos(infoJpg)
                else:
                    self.parse_photos(infoJpg)
        finally:
            # print( r.url )
            self.status = 'end'

def get_query_hash( src ):
    urlInst = 'https://www.instagram.com'
    r = my_requests( urlInst + src )
    js = r.text
    allSub = [m.start() for m in re.finditer( 'const .="*"', js )]
    query_hash = js[allSub[-2]+9:allSub[-2]+41]
    return query_hash

def get_query_hash_for_get_new_photo( src ):
    urlInst = 'https://www.instagram.com'
    r = my_requests( urlInst + src )
    start = [ m.start() for m in re.finditer( 'queryId', r.text ) ][2]
    return r.text[start+9:start+41]

def create_dirs( path ):
    try:
        os.makedirs( path + 'photo' )
    except:pass
    try:
        os.makedirs( path + 'video' )
    except:pass
    pathPhoto = path + 'photo' + os.path.join('a','')[-1]
    pathVideo = path + 'video' + os.path.join('a','')[-1]
    return pathPhoto, pathVideo

def get_new_data( queryHash, userId, after ):
    url =   'https://www.instagram.com/graphql/query/?query_hash=' + str( queryHash ) + \
            '&variables={' +\
                '"id":"' + str( userId ) + '"' +\
                ',"first":100' +\
                ',"after":"' + str( after ) + '"}'
    r = my_requests(url)
    r = r.json()['data']['user']['edge_owner_to_timeline_media']
    return [ 
            r['edges'], 
            r['page_info']['end_cursor']
        ]

        
allThread = []
allJpg = Queue()
lastJpg = ''
WORK = True
if __name__ == "__main__":
    start = time.time()
    # get html
    r = my_requests( target_url )
    soup = BeautifulSoup( r.text, 'html.parser' )

    # create dirs
    path = soup.find('title').text.replace('\n','') + os.path.join('a','')[-1]
    pathPhoto, pathVideo = create_dirs( path )

    # get query_hash
    src = soup.select('script[src*="ProfilePageContainer.js/"]')[0]['src']
    queryHashPhoto = get_query_hash_for_get_new_photo(src)
    src = soup.select('script[src*="/Consumer.js/"]')[0]['src']
    queryHash = get_query_hash( src )
    # queryHash = '477b65a610463740ccdb83135b2014db'

    # create threads and log
    for i in range(20):
        allThread.append( Parser() )
        allThread[i].start()
    Log().start()

    # parse
    script = soup.find( 'body' ).find( 'script' )
    shareData = str(script)[52:-10]
    shareData = j_loads( shareData )
    userId =    shareData['entry_data']['ProfilePage'][0]['logging_page_id'].split( '_' )[-1]
    nowJpg =    shareData['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']
    lastJpg =   shareData['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor']
    while True:
        for infoJpg in nowJpg:
            infoJpg = infoJpg['node']
            allJpg.put(infoJpg)
        if lastJpg is None: break
        nowJpg, lastJpg = get_new_data( queryHashPhoto, userId, lastJpg )
        Log.end_cursor = lastJpg
    WORK = False
    for th in allThread:
        th.join()
    Log.work = False
    end = time.time()
    print( 'время работы: %.2f сек' %(end - start) )