from urllib.request import urlopen
from bs4 import BeautifulSoup as BS
import pandas as pd

URL = 'https://teamcolorcodes.com/nhl-team-color-codes/'
RAW_HTML = urlopen(URL).read()
BS_OBJ = BS(RAW_HTML, 'html.parser')
COLORS = BS_OBJ.find_all('p')[2].find_all('a')
TC = [[COLORS[i].text, COLORS[0]['style'].split('; ')[0].split(': ')[1]
       .strip(' '), COLORS[i]['style'].split('; ')[1].split(': ')[1]
       .strip(' '), COLORS[i]['style'].split('; ')[2].split(': ')[1]
       .strip(' ')] for i in range(len(COLORS))]

TC_DF = pd.DataFrame(TC, columns=['Team', 'Main', 'Text', 'Accent'])

TC_DF.Accent = ['#'+TC_DF.Accent[ei][1:]*2 if
                len(TC_DF.Accent[ei]) == 4 else TC_DF.Accent[ei]
                for ei in TC_DF.index]

TC_DF.Main = ['#' + TC_DF.Main[ei][1:]*2 if len(TC_DF.Main[ei]) == 4
              else TC_DF.Main[ei] for ei in TC_DF.index]

TC_DF['Abbrev'] = ['ANA', 'ARI', 'BOS', 'BUF', 'CGY', 'CAR', 'CHI', 'COL',
                   'CBJ', 'DAL', 'DET', 'EDM', 'FLA', 'L.A', 'MIN', 'MTL',
                   'NSH', 'N.J', 'NYI', 'NYR', 'OTT', 'PHI', 'PIT', 'STL',
                   'S.J', 'T.B', 'TOR', 'VAN', 'VGK', 'WSH', 'WPG']
