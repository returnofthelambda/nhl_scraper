import pandas as pd
from bs4 import BeautifulSoup as BS
from urllib.request import urlopen

url = 'https://teamcolorcodes.com/nhl-team-color-codes/'
raw_html=urlopen(url).read()
bsObj=BS(raw_html,'html.parser')
colors=bsObj.find_all('p')[2].find_all('a')
tc=[[colors[i].text,colors[0]['style'].split('; ')[0].split(': ')[1].strip(' '),colors[i]['style'].split('; ')[1].split(': ')[1].strip(' '),colors[i]['style'].split('; ')[2].split(': ')[1].strip(' ')] for i in range(len(colors))]

tc_df=pd.DataFrame(tc,columns=['Team','Main','Text','Accent'])

tc_df.Accent=['#'+tc_df.Accent[ei][1:]*2 if len(tc_df.Accent[ei])==4 else tc_df.Accent[ei] for ei in tc_df.index]

tc_df.Main=['#'+tc_df.Main[ei][1:]*2 if len(tc_df.Main[ei])==4 else tc_df.Main[ei] for ei in tc_df.index]

tc_df['Abbrev']=['ANA','ARI','BOS','BUF','CGY','CAR','CHI','COL','CBJ','DAL','DET','EDM','FLA','L.A','MIN','MTL','NSH','N.J','NYI','NYR','OTT','PHI','PIT','STL','S.J','T.B','TOR','VAN','VGK','WSH','WPG']
