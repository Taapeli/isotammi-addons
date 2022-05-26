import re 
import time

def maketitle(reponame,sourcetitle):
    if reponame.endswith("seurakunnan arkisto"):
        return reponame.replace(" arkisto"," ") + sourcetitle[0].lower() + sourcetitle[1:]
    if reponame.endswith("församlings arkiv"):
        return reponame.replace(" arkiv"," ") + sourcetitle[0].lower() + sourcetitle[1:]
    return "{} - {}".format(reponame,sourcetitle)

class Match:
    def __init__(self, line,reponame,sourcetitle,citationpage,details,url,date):
        self.line = line
        self.reponame = reponame
        self.sourcetitle = sourcetitle
        self.citationpage = citationpage
        self.details = details
        self.url = url
        self.date = date

def matchline(notelines):
    line = notelines[0]
    m = match_narc(line)
    if m: return m
    m = match_narc1(line)
    if m: return m
    m = match_sshy(line)
    if m: return m
    m = match_sshy2(line)
    if m: return m
    m = match_svar(line)
    if m: return m
    m = match_kansalliskirjasto(notelines)
    if m: return m
    return None

def match_narc1(line): 
# Kaatuneiden henkilöasiakirjat (kokoelma) - Perhonen Onni Aleksi, 16.10.1907; Kansallisarkisto: https://astia.narc.fi/uusiastia/kortti_aineisto.html?id=2684857838 / Viitattu 26.5.2022"
    regex_narc = re.compile(r"(.+?) - (.+?); Kansallisarkisto: (.+) / Viitattu (.+)")  # now I have two problems
    m = regex_narc.match(line)
    if not m: return None
    reponame = m.group(1)            
    sourcetitle = maketitle(reponame,m.group(2))
    citationpage = m.group(2)
    url = m.group(3)
    date = m.group(4)
    details = "Kansallisarkisto: {} / Viitattu {}".format(url,date)
    return Match(line,reponame,sourcetitle,citationpage,details,url,date)

def match_narc(line): 
# Liperin seurakunnan arkisto - Syntyneiden ja kastettujen luettelot 1772-1811 (I C:3), jakso 3: kastetut 1772 tammikuu; Kansallisarkisto: http://digi.narc.fi/digi/view.ka?kuid=6593368 / Viitattu 22.10.2018
    regex_narc = re.compile("(.+?) - (.+?), jakso (.+); Kansallisarkisto: (.+) / Viitattu (.+)")  # now I have two problems
    m = regex_narc.match(line)
    if not m: return None
    reponame = m.group(1)            
    sourcetitle = maketitle(reponame,m.group(2))
    citationpage = "jakso " + m.group(3)
    url = m.group(4)
    date = m.group(5)
    details = "Kansallisarkisto: {} / Viitattu {}".format(url,date)
    return Match(line,reponame,sourcetitle,citationpage,details,url,date)

def match_sshy(line):
# Tampereen tuomiokirkkoseurakunta - rippikirja, 1878-1887 (MKO166-181 I Aa:17) > 39: Clayhills tjenstespersoner; SSHY: http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=18233&pnum=39 / Viitattu 6.11.2018
    regex_sshy = re.compile(r"(.+) - (.+) > (.+?): (.*); SSHY: (.+) / Viitattu (.+)")  # now I have two problems
    m = regex_sshy.match(line)
    if not m: return None
    reponame = m.group(1)            
    sourcetitle = "{} {}".format(reponame,m.group(2))
    citationpage = m.group(4).strip()
    url = m.group(5)
    date = m.group(6)
    details = "SSHY: {} / Viitattu {}".format(url,date)
    return Match(line,reponame,sourcetitle,citationpage,details,url,date)

def match_sshy2(line):
# Tampereen tuomiokirkkoseurakunta rippikirja 1795-1800 (TK630 I Aa:2)  N:o 1 Häggman, Kask, Grefvelin ; SSHY http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=15950&pnum=8 / Viitattu 03.02.2022
# Alastaro rippikirja 1751-1757 (JK478 I Aa1:3)  Sivu 10 Laurois Nepponen ; SSHY http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=15846&pnum=13 / Viitattu 03.02.2022
    regex_sshy = re.compile(r"(.+) (\w+ \d{4}-\d{4} \(.+?\)) (.+); SSHY (http.+) / Viitattu (.+)")
    m = regex_sshy.match(line)
    if not m: return None
    reponame = m.group(1)            
    sourcetitle = "{} {}".format(reponame,m.group(2))
    citationpage = m.group(3).strip()
    url = m.group(4)
    date = m.group(5)
    details = "SSHY: {} / Viitattu {}".format(url,date)
    return Match(line,reponame,sourcetitle,citationpage,details,url,date)

def match_svar(line):
# Hajoms kyrkoarkiv, Husförhörslängder, SE/GLA/13195/A I/12 (1861-1872), bildid: C0045710_00045
    if line.find("bildid:") < 0: return None
    i = line.find("bildid:")
    bildid = line[i:].split()[1]
    line = line.replace("bildid:","SVAR bildid:")
    parts = line.split(",")
    reponame = parts[0]
    sourcetitle = ",".join(parts[0:3])
    citationpage = parts[3].strip()
    # https://sok.riksarkivet.se/bildvisning/C0060358_00162
    url = "https://sok.riksarkivet.se/bildvisning/" + bildid
    date = time.strftime("%d.%m.%Y",time.localtime(time.time()))
    details = "SVAR: {} / Viitattu {}".format(url,date)
    return Match(line,reponame,sourcetitle,citationpage,details,url,date)

def match_kansalliskirjasto(lines):
    #Vasabladet, 18.11.1911, nro 138, s. 4
    #https://digi.kansalliskirjasto.fi/sanomalehti/binding/1340877?page=4
    #Kansalliskirjaston Digitoidut aineistot
    
    #Mikkeli, 01.02.1901, nr 13, s. 1
    #https://digi.kansalliskirjasto.fi/sanomalehti/binding/670567?page=1
    #Nationalbibliotekets digitala samlingar
    
    #Mikkeli, 01.02.1901, no. 13, p. 1
    #https://digi.kansalliskirjasto.fi/sanomalehti/binding/670567?page=1
    #National Library's Digital Collections

    if len(lines) < 3 or lines[2] not in {
        "Kansalliskirjaston Digitoidut aineistot",
        "Kansalliskirjaston digitaaliset aineistot",
        "Nationalbibliotekets digitala samlingar",
        "National Library's Digital Collections",
    }: 
        return None
    i = lines[0].find(",")
    if i < 0: return None
    sourcetitle = lines[0][:i].strip()
    citationpage = lines[0][i+1:].strip()
    reponame = lines[2]
    url = lines[1]
    date = time.strftime("%d.%m.%Y",time.localtime(time.time()))
    details = "Kansalliskirjasto: {} / Viitattu {}".format(url,date)
    return Match(lines,reponame,sourcetitle,citationpage,details,url,date)
    
