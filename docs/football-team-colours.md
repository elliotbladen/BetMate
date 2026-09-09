# Football team colour audit — 10 September 2026

The live Championship feed contained 24 distinct clubs. Wrexham arrived as
`Wrexham AFC`, which missed the existing `Wrexham` entry. The remaining live UCL
fixtures contained eight unmapped clubs: AS Roma, Bodø/Glimt, Como, Fenerbahce,
RC Lens, Sabah FK, Shakhtar Donetsk and Slavia Praha.

The complete [UEFA 2026/27 league-phase roster](https://www.uefa.com/uefachampionsleague/news/02a8-216cd740d41f-fd3b45ac4a0f-1000--champions-league-league-phase-draw-all-36-teams-learn-their/)
is covered, including clubs absent from the current odds response. Regression
fixtures in `tests/soccer-team-colours.test.ts` cover all 36 UEFA clubs and all
24 Championship feed names. Retain historical clubs for saved fixtures.

## Colour references

Use club identity/home colours for the existing two-colour abbreviation badges.
Hex values are UI palette values, not a claim that every club publishes an
exact digital brand standard. Preserve genuine white/black palettes; a white
badge for Derby, Preston, Bolton or Swansea is not a missing colour.

| Club | Colour identity and reference |
| --- | --- |
| Wrexham | Red/white: [official 2026/27 home kit](https://www.wrexhamafc.co.uk/news/2026/july/28/wrexham-afc-and-macron-unveil-2026-27-home-kit-in-new-york). Existing palette retained; fix the feed alias. |
| Bodø/Glimt | Exact published yellow `#F8DD00` and black `#120F0A`: [official logo guidelines](https://www.glimt.no/om-klubben/bodo-glimts-logo). |
| Roma | [Club specifies Rosso Roma Pantone 202 C and Giallo Roma 130 C](https://www.asroma.com/en/news/41432/roma-officially-return-to-traditional-club-colours). UI equivalents `#862633` / `#F2A900`. |
| Como | Blue/white: [official home-kit announcement](https://comofootball.com/como-1907-e-adidas-presentano-la-maglia-home-per-la-stagione-202627/). |
| Fenerbahçe | Navy/yellow: [Turkish federation kit catalogue](https://www.tff.org/Resources/TFF/Documents/002011/Ligler/forma/katalog_spor_toto1.pdf). |
| Lens | Sang et Or, red/gold: [official club](https://www.rclens.fr/fr/?externalLink=1). |
| Sabah FK | Black/pink (`#E77DA8` sampled from the crest): [official Azerbaijan club crest](https://sabahfc.az/static/dist/img/SABAH%20FC%20LOGO%201.png). This is not the Malaysian Sabah club. |
| Shakhtar | Orange/black: [official crest explanation](https://shakhtar.com/en/club/philosophy-and-crest/). |
| Slavia Praha | Red/white: [official club profile](https://www.slavia.cz/o-klubu). |
| AEK Athens | Yellow/black: [official kit announcement](https://www.aekfc.gr/newsdetails/oi-emfaniseis-tis-aek-gia-ti-sezon-2020-21-125083.htm?lang=el&path=-996666907). |
| LASK | Black/white: [official identity and kit announcement](https://www.lask.at/de/m/news/tradition-trifft-innovation-lask-praesentierte-neuen-auftritt-und-trikot-2023-24). |
| Real Betis | Green/white: [official home-kit announcement](https://en.realbetisbalompie.es/news/current_news/real-betis-and-hummel-unveil-the-2026-27-home-kit-32436). |
| Slovan Bratislava | Sky blue/white: [official club shop](https://shop.skslovan.com/). |
| Stuttgart | White/red: [official club symbols](https://www.vfb.de/de/1893/club/vfb-e-v-/marke/marke/symbole/?data=&mobile=). |
| Viking | Navy/white: [official kit announcement](https://www.vikingfotball.no/nyheter/her-er-historien-om-arets-drakter). |
| Villarreal | Yellow/blue: [official colour history](https://villarrealcf.es/en/from-the-black-and-white-days-to-the-brilliant-successes-in-yellow/). |

## Matching rules

Normalize case, accents, punctuation and whitespace; transliterate Norwegian ø.
Use explicit aliases for different names (Sporting CP, Slavia Prague, Wrexham
AFC, etc.). Never fuzzy-match partial names or strip club prefixes globally.
Unknown names still return null rather than inheriting another team's palette.
NRL and AFL retain their existing exact-name lookup and colours.
