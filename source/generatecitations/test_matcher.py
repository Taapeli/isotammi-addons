from pprint import pprint

import matcher

def test_narc1():
	text = "Kaatuneiden henkilöasiakirjat (kokoelma) - Perhonen Onni Aleksi, 16.10.1907; Kansallisarkisto: https://astia.narc.fi/uusiastia/kortti_aineisto.html?id=2684857838 / Viitattu 26.5.2022"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Kaatuneiden henkilöasiakirjat (kokoelma)"
	assert m.citationpage == "Perhonen Onni Aleksi, 16.10.1907"

def test_narc2():
	text = "Kaatuneiden henkilöasiakirjat (kokoelma) - Perhonen Onni Aleksi, 16.10.1907, jakso 1; Kansallisarkisto: https://astia.narc.fi/uusiastia/viewer/?fileId=5527332269&aineistoId=2684857838 / Viitattu 26.5.2022"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Kaatuneiden henkilöasiakirjat (kokoelma)"
	assert m.citationpage == "jakso 1"

def test_sshy1():
	text = "Tampereen tuomiokirkkoseurakunta - rippikirja, 1878-1887 (MKO166-181 I Aa:17) > 39: Clayhills tjenstespersoner; SSHY: http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=18233&pnum=39 / Viitattu 6.11.2018"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Tampereen tuomiokirkkoseurakunta"
	assert m.citationpage == "Clayhills tjenstespersoner"

def test_sshy2a():
	text = "Tampereen tuomiokirkkoseurakunta rippikirja 1795-1800 (TK630 I Aa:2)  N:o 1 Häggman, Kask, Grefvelin ; SSHY http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=15950&pnum=8 / Viitattu 03.02.2022"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Tampereen tuomiokirkkoseurakunta"
	assert m.citationpage == "N:o 1 Häggman, Kask, Grefvelin"
	
def test_sshy2b():
	text = "Alastaro rippikirja 1751-1757 (JK478 I Aa1:3)  Sivu 10 Laurois Nepponen ; SSHY http://www.sukuhistoria.fi/sshy/sivut/jasenille/paikat.php?bid=15846&pnum=13 / Viitattu 03.02.2022"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Alastaro"
	assert m.citationpage == "Sivu 10 Laurois Nepponen"

def test_svar():
	text = "Hajoms kyrkoarkiv, Husförhörslängder, SE/GLA/13195/A I/12 (1861-1872), bildid: C0045710_00045"
	m = matcher.matchline([text])
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Hajoms kyrkoarkiv"
	assert m.citationpage == "SVAR bildid: C0045710_00045"

def test_kansalliskirjasto():
	lines = """Vasabladet, 18.11.1911, nro 138, s. 4
https://digi.kansalliskirjasto.fi/sanomalehti/binding/1340877?page=4
Kansalliskirjaston Digitoidut aineistot""".splitlines()
	print(lines)
	m = matcher.matchline(lines)
	assert m is not None
	pprint(m.__dict__)
	assert m.reponame == "Kansalliskirjaston Digitoidut aineistot"
	assert m.citationpage == "18.11.1911, nro 138, s. 4"

def test_xxx():
	text = ""
	m = matcher.matchline([text])
	#assert m is not None
	#assert m.reponame == ""
	#assert m.citationpage == ""
