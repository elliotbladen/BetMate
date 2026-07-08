# ELO ratings — updated through WC2026 Matchday 3 (group stage complete)
# Base: late-2025 eloratings.net. K=40 WC group stage.
#
# R3 UPDATES (derived from R32 bracket image — Jun 24 2026):
#   Scotland beat Brazil  → Sco 1759+31=1790, Bra 1975-31=1944
#   Sweden   beat Japan   → Swe 1828+19=1847, Jpn 1807-19=1788
#   Iran beat Egypt (est.)→ Ira 1762+20=1782, Egy 1755-20=1735
#   (both qualified from Group G per bracket)
#   Other R3 updates assumed minimal (favorites won / dead rubbers).

ELO = {
    # ── GROUP A — R1+R2 complete ─────────────────────────────────────────────
    # R1: Mexico 2-0 SA (+14.1/-14.1), SK 2-1 Czechia (+18.8/-18.8)
    # R2: Mexico 1-0 SK (+18.3/-18.3), Czechia 1-1 SA (-2.6/+2.6)
    # Standings: Mexico 6pts | SK 3pts | Czechia 1pt | SA 1pt
    "Mexico":              1847,   # 1815 +14.1 +18.3
    "South Korea":         1781,   # 1780 +18.8 -18.3
    "Czechia":             1739,   # 1760 -18.8 -2.6
    "Czech Republic":      1739,
    "South Africa":        1699,   # 1710 -14.1 +2.6

    # ── GROUP B — R1+R2 complete ─────────────────────────────────────────────
    # R1: Canada 1-1 Bosnia (-2/+2), Switzerland 1-1 Qatar (-8.6/+8.6)
    # R2: Switzerland 4-1 Bosnia (+13.9/-13.9), Canada 6-0 Qatar (+16.4/-16.4)
    # Standings: Canada 4pts | Switzerland 4pts | Bosnia 1pt | Qatar 1pt
    "Switzerland":         1875,   # 1870 -8.6 +13.9
    "Canada":              1799,   # 1785 -2.0 +16.4
    "Bosnia-Herzegovina":  1738,   # 1750 +2.0 -13.9
    "Qatar":               1702,   # 1710 +8.6 -16.4

    # ── GROUP C — R3 complete ────────────────────────────────────────────────
    # R1: Brazil 1-1 Morocco (-9.5/+9.5), Scotland 1-0 Haiti (+11.6/-11.6)
    # R2: Morocco 1-0 Scotland (+18.1/-18.1), Brazil 3-0 Haiti (+4.2/-4.2)
    # R3: Scotland beat Brazil → Sco +31, Bra -31 (bracket confirms both qualified)
    #     Morocco beat Haiti (assumed, Morocco already qualified)
    # Final standings: Morocco 7pts | Scotland 6pts | Brazil 4pts (best 3rd) | Haiti 0pts
    "Brazil":              1944,   # 1975 -31 (R3 loss to Scotland)
    "Morocco":             1828,   # R3 routine win vs Haiti — minimal ELO change
    "Scotland":            1790,   # 1759 +31 (R3 shock win vs Brazil)
    "Haiti":               1594,

    # ── GROUP D — R1+R2 complete ─────────────────────────────────────────────
    # R1: USA 4-1 Paraguay (+13.6/-13.6), Australia 2-0 Türkiye (+22.6/-22.6)
    # R2: USA 2-0 Australia (+15.7/-15.7), Paraguay 1-0 Türkiye (+23.8/-23.8)
    # Standings: USA 6pts | Australia 3pts | Paraguay 3pts | Türkiye 0pts
    "USA":                 1859,   # 1830 +13.6 +15.7
    "Australia":           1752,   # 1745 +22.6 -15.7
    "Paraguay":            1725,   # 1715 -13.6 +23.8
    "Türkiye":             1744,   # 1790 -22.6 -23.8
    "Turkey":              1744,

    # ── GROUP E — R1+R2 complete ─────────────────────────────────────────────
    # R1: Germany 7-1 Curaçao (+4.4/-4.4), Ivory Coast 1-0 Ecuador (+23.7/-23.7)
    # R2: Germany 2-1 Ivory Coast (+9.8/-9.8), Ecuador 0-0 Curaçao (-10.2/+10.2)
    # Standings: Germany 6pts | Ivory Coast 3pts | Ecuador 1pt | Curaçao 1pt
    "Germany":             1959,   # 1945 +4.4 +9.8
    "Ivory Coast":         1744,   # 1730 +23.7 -9.8
    "Ecuador":             1761,   # 1795 -23.7 -10.2
    "Curaçao":             1586,   # 1580 -4.4 +10.2
    "Curacao":             1586,

    # ── GROUP F — R3 complete ────────────────────────────────────────────────
    # R1: Netherlands 2-2 Japan (-8.4/+8.4), Sweden 5-1 Tunisia (+12.9/-12.9)
    # R2: Netherlands 5-1 Sweden (+15.0/-15.0), Tunisia 0-4 Japan (-14.0/+14.0)
    # R3: Sweden beat Japan → Swe +19, Jpn -19 (bracket confirms both qualified)
    #     Netherlands beat Tunisia (assumed, already qualified)
    # Final standings: Netherlands ≥4pts | Sweden 6pts | Japan 4pts (best 3rd) | Tunisia 0pts
    "Netherlands":         1947,   # R3 routine win vs Tunisia — minimal change
    "Japan":               1788,   # 1807 -19 (R3 loss to Sweden, qualifies as best 3rd)
    "Sweden":              1847,   # 1828 +19 (R3 win vs Japan)
    "Tunisia":             1673,

    # ── GROUP G — R3 complete ────────────────────────────────────────────────
    # Teams: Egypt, Iran, Belgium, New Zealand
    # R1: Belgium 1-1 Egypt (-8.8/+8.8), Iran 2-2 New Zealand (-5.6/+5.6)
    # R2: Belgium 0-0 Iran (-7.2/+7.2), Egypt 3-1 New Zealand (+15.8/-15.8)
    # R3: Iran beat Egypt (est.) → both in bracket (slots 14 + 26)
    #     Belgium dropped points vs NZ (est. draw) keeping Belgium at 3pts
    # Final standings (est.): Iran 5pts | Egypt 4pts | Belgium 3pts | NZ 1pt
    "Egypt":               1735,   # 1755 -20 (est. R3 loss to Iran)
    "Iran":                1782,   # 1762 +20 (est. R3 win vs Egypt, tops group)
    "Belgium":             1879,   # Belgium eliminated — ELO unchanged for reference
    "New Zealand":         1650,

    # ── GROUP H — R1+R2 complete ─────────────────────────────────────────────
    # Teams: Spain, Uruguay, Cape Verde (Cabo Verde), Saudi Arabia
    # R1: Spain 0-0 Cape Verde (-14.0/+14.0), Saudi Arabia 1-1 Uruguay (+8.4/-8.4)
    # R2: Spain 4-0 Saudi Arabia (+8.1/-8.1), Uruguay 2-2 Cape Verde (-9.2/+9.2)
    # Standings: Spain 4pts | Uruguay 2pts | Cape Verde 2pts | Saudi Arabia 1pt
    "Spain":               1984,   # 1990 -14.0 +8.1
    "Uruguay":             1867,   # 1885 -8.4 -9.2
    "Cape Verde":          1713,   # 1690 +14.0 +9.2
    "Cabo Verde":          1713,
    "Saudi Arabia":        1730,   # 1730 +8.4 -8.1

    # ── GROUP I — R1+R2 complete ─────────────────────────────────────────────
    # R1: France 3-1 Senegal (+8.2/-8.2), Norway 4-1 Iraq (+10.3/-10.3)
    # R2: France 3-0 Iraq (+4.7/-4.7), Norway 3-2 Senegal (+14.0/-14.0)
    # Standings: France 6pts | Norway 6pts | Senegal 0pts | Iraq 0pts
    "France":              2023,   # 2010 +8.2 +4.7
    "Norway":              1889,   # 1865 +10.3 +14.0
    "Senegal":             1753,   # 1775 -8.2 -14.0
    "Iraq":                1665,   # 1680 -10.3 -4.7

    # ── GROUP J — R1+R2 complete ─────────────────────────────────────────────
    # R1: Argentina 3-0 Algeria (+4.8/-4.8), Austria 3-1 Jordan (+11.9/-11.9)
    # R2: Argentina 2-0 Austria (+8.1/-8.1), Algeria 2-1 Jordan (+16.8/-16.8)
    # Standings: Argentina 6pts | Austria 3pts (GD 0) | Algeria 3pts (GD -2) | Jordan 0pts
    "Argentina":           2078,   # 2065 +4.8 +8.1
    "Austria":             1824,   # 1820 +11.9 -8.1
    "Algeria":             1732,   # 1720 -4.8 +16.8
    "Jordan":              1641,   # 1670 -11.9 -16.8

    # ── GROUP K — R2 partial (Portugal R2 done; Colombia vs DRC Jun 24 UTC) ──
    # R1: Portugal 1-1 DR Congo (-12.9/+12.9), Colombia 3-1 Uzbekistan (+10.0/-10.0)
    # R2: Portugal 5-0 Uzbekistan (+6.1/-6.1), Colombia vs DR Congo (est. Colombia W +11.8/-11.8)
    # Standings (est.): Portugal 4pts | Colombia 6pts | DR Congo 1pt | Uzbekistan 0pts
    # NOTE: Colombia vs DR Congo played Jun 24 02:00 UTC — ELO is estimated (Colombia win assumed)
    "Portugal":            1958,   # 1965 -12.9 +6.1
    "Colombia":            1877,   # 1855 +10.0 +11.8 (estimated)
    "DR Congo":            1701,   # 1700 +12.9 -11.8 (estimated)
    "Congo DR":            1701,
    "Uzbekistan":          1649,   # 1665 -10.0 -6.1

    # ── GROUP L — R1+R2 complete ─────────────────────────────────────────────
    # R1: England 4-2 Croatia (+13.9/-13.9), Ghana 1-0 Panama (+18.0/-18.0)
    # R2: England 0-0 Ghana (-12.7/+12.7), Croatia 1-0 Panama (+9.9/-9.9)
    # Standings: England 4pts | Ghana 4pts | Croatia 3pts | Panama 0pts
    "England":             1986,   # 1985 +13.9 -12.7
    "Croatia":             1871,   # 1875 -13.9 +9.9
    "Ghana":               1751,   # 1720 +18.0 +12.7
    "Panama":              1657,   # 1685 -18.0 -9.9

    # ── Non-WC teams (pre-tournament baseline) ────────────────────────────────
    "Italy":               1950,
    "Denmark":             1845,
    "Serbia":              1790,
    "Poland":              1780,
    "Ukraine":             1780,
    "Romania":             1720,
    "Greece":              1710,
    "Slovakia":            1730,
    "Costa Rica":          1690,
    "Jamaica":             1645,
    "Honduras":            1640,
    "El Salvador":         1620,
    "Guatemala":           1610,
    "Nigeria":             1740,
    "Cameroon":            1720,
    "Indonesia":           1665,
    "Venezuela":           1750,
    "Chile":               1735,
    "Bolivia":             1665,
    "Peru":                1735,
}
