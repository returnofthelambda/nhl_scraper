def game_scrape(gameId,season, *cleand):
    from bs4 import BeautifulSoup
    #import re
    from urllib.request import urlopen
    #import pandas as pd
    
    try:
        cleand[0]
    except IndexError:
        cleand=[["gameId","skater","shift","period","shiftStart","shiftEnd"]]

    season=str(season)+str(int(season)+1)
    
    for team in ['H','V']:

        url='http://www.nhl.com/scores/htmlreports/'+season+'/T'+team+gameId+'.HTM'
        raw_html = urlopen(url).read()
        bsObj=BeautifulSoup(raw_html,"html.parser")
        #names
        skaters_clean = [ name.text.strip().split(" ")[2] + " " + name.text.strip(" ").split()[1][:-1] for name in bsObj.find_all("td", "playerHeading") ]
        
        #data points
        shiftData = [ x.text.strip() for x in bsObj.find_all("td","lborder") ]

        team = bsObj.find("td", "teamHeading").text

        #gameId=int(re.search('T\w(\d{6})',url).group(0)[2:])
        i,j,jump=0,-1,6
        skip=False
        while i<len(shiftData):
            if shiftData[i] == "Shift #":
                i+=6
                jump=6
                skip=False
            elif shiftData[i] == "":
                i+=8
                jump=7
                skip=True
            if skip==False:
                if shiftData[i]=='1':
                    j+=1
                cleand.append([gameId,skaters_clean[j],int(shiftData[i]),int(shiftData[i+1]),shiftData[i+2].split(' ')[0],shiftData[i+3].split(' ')[0]])
            i+=jump

    return cleand
