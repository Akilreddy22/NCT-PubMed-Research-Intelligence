from app.services.pubmed_service import load_sample_articles, parse_pmc_xml, parse_pubmed_xml

XML = """<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>111</PMID><Article>
<Journal><JournalIssue><PubDate><Year>2024</Year><Month>Mar</Month><Day>15</Day></PubDate></JournalIssue><Title>J Test</Title></Journal>
<ArticleTitle>Effect of <i>drug X</i> on cancer</ArticleTitle>
<Abstract><AbstractText Label="BACKGROUND">Bg.</AbstractText><AbstractText Label="RESULTS">Res.</AbstractText></Abstract>
<AuthorList><Author><LastName>Doe</LastName><ForeName>Jane</ForeName></Author><Author><CollectiveName>Study Group</CollectiveName></Author></AuthorList>
<ELocationID EIdType="doi">10.1/abc</ELocationID>
<PublicationTypeList><PublicationType>Journal Article</PublicationType><PublicationType>Randomized Controlled Trial</PublicationType></PublicationTypeList>
</Article><KeywordList><Keyword>immunotherapy</Keyword></KeywordList></MedlineCitation>
<PubmedData><ArticleIdList><ArticleId IdType="pmc">PMC555</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"""

PMC = """<pmc-articleset><article xmlns:xlink="http://www.w3.org/1999/xlink"><body><p>First paragraph.</p>
<fig id="f1"><label>Figure 1</label><caption><p>Survival curve.</p></caption><graphic xlink:href="fig1"/></fig></body></article></pmc-articleset>"""


def test_parse_pubmed_xml():
    a = parse_pubmed_xml(XML)[0]
    assert a["pmid"] == "111" and a["title"] == "Effect of drug X on cancer"
    assert a["abstract"] == "BACKGROUND: Bg.\nRESULTS: Res."
    assert a["authors"] == ["Jane Doe", "Study Group"]
    assert a["doi"] == "10.1/abc" and a["pmcid"] == "PMC555"
    assert a["publication_date"] == "2024 Mar 15"
    assert a["study_type"] == "Randomized Controlled Trial" and a["keywords"] == ["immunotherapy"]


def test_parse_pmc_figures():
    r = parse_pmc_xml(PMC, "PMC555")
    assert r["full_text"].startswith("First paragraph")
    assert r["figures"][0]["label"] == "Figure 1" and r["figures"][0]["caption"] == "Survival curve."
    assert r["figures"][0]["image_url"].endswith("PMC555/bin/fig1.jpg")


def test_sample_file_loads():
    assert len(load_sample_articles()) == 3
