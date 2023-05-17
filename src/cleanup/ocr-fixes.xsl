<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
  xmlns:xs="http://www.w3.org/2001/XMLSchema"
  xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl"
  xmlns:map="http://www.w3.org/2005/xpath-functions/map"
  xmlns:local="local"
  exclude-result-prefixes="xs xd"
  expand-text="true"
  version="3.0">
  <xd:doc scope="stylesheet">
    <xd:desc>
      <xd:p><xd:b>Created on:</xd:b> May 12, 2023</xd:p>
      <xd:p><xd:b>Author:</xd:b> pd</xd:p>
      <xd:p>Helper script to correct some OCR mistakes.</xd:p>
      <xd:p>Run from command-line after installing Saxon: 
        <xd:pre>java -jar /opt/Saxonica/SaxonHE12-2/saxon-he-12.2.jar -s:ocr-fixes.xsl -xsl:ocr-fixes.xsl input=bern-addresses/proofread/1903-11-02.txt</xd:pre>
      </xd:p>
    </xd:desc>
  </xd:doc>
  
  <xsl:output method="text" indent="true"/>
  
  <xsl:param name="input" as="xs:string" select="'../../proofread/1900-02-15.txt'"/>

  <xsl:variable name="ocr-fixes" as="map(xs:string, xs:string)" select="map {
        '(.)g\sasse'  : '$1gasse',
        'Aarberger5 asse' : 'Aarbergergasse',
        'Amt-\sj?haus|Amthaiis'  : 'Amthaus',
        'Arcliivstr'  : 'Archivstr',
        'Biichler'    : 'Büchler',
        'Bierkiller'  : 'Bierkeller',
        'Briinisholz' : 'Brünisholz',
        'Biirgi'      : 'Bürgi',
        'Biitikof'    : 'Bütikof',
        '(B|b)iicher' : '$1ücher',
        'Biichi'      : 'Büchi',
        'Bliimli'     : 'Blümli',
        '(B|b)riick'      : '$1rück',
        'Briinnenb.'  : 'Brünnen b.',
        'Biiehsen|Biichsen' : 'Büchsen',
        '(B|b)(l|i)ihl'  : '$1ühl',
        '(B|b)iihhveg'  : '$1ühlweg',
        'Biimpliz'    : 'Bümpliz',
        'Biireau'     : 'Büreau',
        'bevg'        : 'berg',
        'Ghokolade'   : 'Chokolade',
        'Cliristoffel': 'Christoffel',
        'Civiistandsamt'  : 'Civilstandsamt',
        'Diihlhölzli' : 'Dählhölzli',
        'Etfinger|Efiinger'    : 'Effinger',
        'Eiigut'      : 'Eilgut',
        'Elektricitiit' : 'Elektricität',
        'Erlacnstr'   : 'Erlachstr',
        '(e?)n\sweg'     : '$1nweg',
        'Fliickiger'  : 'Flückiger',
        'Froliberg'   : 'Frohberg',
        'fiihrer|fiibrer'     : 'führer',
        'Fiirspr'     : 'Fürspr',
        'giirtnor'    : 'gärtner',
        'Gasgliihlicht' : 'Gasglühlicht',
        'gasse(\d+)'  : 'gasse $1',  
        '(g|G)ehiilf|(G|g)eliiilf' : '$1ehülf',
        'Gemiise'     : 'Gemüse',
        'Gemüsehiindl'  : 'Gemüsehändl',
        'Giimligen'   : 'Gümligen',
        'grabeii'     : 'graben',
        'Griine(ck|gg)'    : 'Grüne$1',
        'Griinig'     : 'Grünig',
        'Giirbe'      : 'Gürbe',
        'Giiterexpedit' : 'Güterexpedit',
        'Ilandels'    : 'Handels',
        'liändler'    : 'händler',
        'heiinweg'    : 'heimweg',
        'Herrn.'      : 'Herm.',
        'llelvetia|Ilelvetia'   : 'Helvetia',
        'Iiirschen|Hirsclien' : 'Hirschen',
        'Hirschenf\sraben'  : 'Hirschengraben',
        'höfii'       : 'höfli',
        'fjheweg'     : 'Höheweg',
        'Hötel'       : 'Hôtel',
        'hiibeli|lnibeli' : 'hübeli',
        'Hiigel'      : 'Hügel',
        'Hiilfs'      : 'Hülfs',
        'Hiinerwadel' : 'Hünerwadel',
        'Hnmboldt'     : 'Humboldt',
        'jiiger'      : 'jäger',
        'Josepliine'  : 'Josephine',
        'Tunkerngasse|Junkern-\s1gasse'  : 'Junkerngasse',
        'Turastrasse' : 'Jurastrasse',
        'Kädereckemvcg' : 'Kädereckenweg',
        'Kirclienfeld|Kirchen-\sIfeld': 'Kirchenfeld',
        'Kiienzi'     : 'Küenzi',
        'Kiipfer'     : 'Küpfer',
        'Liingg\.'    : 'Längg.',
        'Liinggass'   : 'Länggass',
        'Liith(i|y)|Lüt-li(i|y)' : 'Lüth$1',
        'Liitzel'     : 'Lützel',
        'meclianik'   : 'mechanik',
        'Aletzgerg'   : 'Metzgerg',
        'Miiitär'     : 'Militär',
        'Mmeral'      : 'Mineral',
        '(M|m)iihle'  : '$1ühle',
        '(M|m)iiller' : '$1üller',
        'Miinger'     : 'Münger',
        '(M|m)iinster'  : '$1ünster',
        'Miinz'       : 'Münz',
        'AIusik'      : 'Musik',
        'natiirl'     : 'natürl',
        'numiner'     : 'nummer',
        'Pappehveg'   : 'Pappelweg',
        'Pfäffii'     : 'Pfäffli',
        '\spliil\.'   : ' phil.',
        'Reicnen'     : 'Reichen',
        'Riifenacht'  : 'Rüfenacht',
        'Riitlistr'   : 'Rütlistr',
        'Ryffii'      : 'Ryffli',
        'scnaft'      : 'schaft',
        'Schanzen-\s\{strasse' : 'Schanzenstrasse',
        'Schitfl|Scliiffl' : 'Schiffl',
        'Schönbiichler' : 'Schönbächler',
        'Scnosshalde' : 'Schosshalde',
        'Schiirch'    : 'Schürch',
        'Schiirzen'   : 'Schürzen',
        '(S|s)chiitzen'   : '$1chützen',
        'sclnveizer'  : 'schweizer',
        'Sclnvarz|Scliwarz' : 'Schwarz',
        'Schwarzeiiburg'  : 'Schwarzenburg',
        'Seidenvreg'  : 'Seidenweg',
        'Sopliie'     : 'Sophie',
        'Stand weg'   : 'Standweg',
        'strasse(\d+)'  : 'strasse $1',
        'Siidfriichte'  : 'Südfrüchte',
        'Teie-S\sraphen':  'Telegraphen',
        'Yerlag'      : 'Verlag',
        'vveg'        : 'weg',
        'AVegmiiller' : 'Wegmüller',
        'Wiith'       : 'Wüth',
        '\\Vildhain'   : 'Wildhain',
        'Wlttikofen'  : 'Wittikofen',
        'W\syler'     : 'Wyler',
        'ziichter'    : 'züchter',
        'Zurfliih,'   : 'Zurflüh',
        '(Ahor|Kuh|Magazi|Polygo|Sen|Stei|Tur|Wildhai|Zau)enweg'    : '$1nweg'
        }"/>
  
  <xsl:variable name="lines" select="unparsed-text-lines($input)"/>
  
  <xsl:template match="/">
    <xsl:for-each select="$lines">
      <xsl:sequence select="fold-left(map:keys($ocr-fixes), ., function($str, $regex) { replace($str,
        $regex, map:get($ocr-fixes,$regex)) } )"/><xsl:text>
</xsl:text>
    </xsl:for-each>
  </xsl:template>
  
</xsl:stylesheet>
