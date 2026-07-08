# World Cup 2026 R32 Remaining 1X2 Pricing

Generated: 2026-07-01 Australia/Sydney.

Source basis:
- Same remaining-game filter as `r32_remaining_ou25_pricing.md`.
- Model: `WorldCupEngine/scripts/price_r32_full.py` Dixon-Coles Poisson from ELO, tactical multipliers, knockout draw mass.
- Market is 90-minute result only: Home / Draw / Away.

| Game | Home | Draw | Away | Model Read |
|---|---:|---:|---:|---|
| France v Sweden | France 1.92 | 3.51 | Sweden 5.12 | France |
| Mexico v Ecuador | Mexico 2.45 | 2.99 | Ecuador 3.89 | Mexico lean |
| England v DR Congo | England 1.61 | 4.06 | DR Congo 7.58 | England |
| Belgium v Senegal | Belgium 2.12 | 3.36 | Senegal 4.36 | Belgium |
| USA v Bosnia-Herzegovina | USA 2.09 | 3.38 | Bosnia-Herzegovina 4.42 | USA |
| Spain v Austria | Spain 1.98 | 3.45 | Austria 4.85 | Spain |
| Portugal v Croatia | Portugal 2.35 | 3.33 | Croatia 3.66 | Portugal lean |
| Switzerland v Algeria | Switzerland 2.05 | 3.40 | Algeria 4.60 | Switzerland |
| Australia v Egypt | Australia 2.97 | 3.12 | Egypt 2.92 | Egypt marginal |
| Argentina v Cabo Verde | Argentina 1.44 | 4.72 | Cabo Verde 10.53 | Argentina |
| Colombia v Ghana | Colombia 2.12 | 3.36 | Ghana 4.36 | Colombia |

## Best Price Targets

Back only if market is above fair:

| Side | Fair | Notes |
|---|---:|---|
| Argentina 90m | 1.44 | Strongest favourite, but likely little value unless market drifts. |
| England 90m | 1.61 | Clean favourite; still needs price above 1.61. |
| France 90m | 1.92 | Better price shape than England/Argentina if market offers 2.00+. |
| Spain 90m | 1.98 | Similar to France; playable only above model. |
| Switzerland 90m | 2.05 | Mid-price favourite. |
| Colombia 90m | 2.12 | Same fair as Belgium, cleaner than Belgium due data-risk note. |
| USA 90m | 2.09 | Host acclimatisation priced in; playable if market >2.09. |
| Mexico 90m | 2.45 | Altitude priced in; draw risk still high. |
| Portugal 90m | 2.35 | Slight 90m lean, but Croatia live underdog. |
| Egypt 90m | 2.92 | Slight 90m lean after Australia injury adjustment. |

## Draw Prices

| Game | Draw Fair |
|---|---:|
| Australia v Egypt | 3.17 |
| Mexico v Ecuador | 2.99 |
| Portugal v Croatia | 3.33 |
| USA v Bosnia-Herzegovina | 3.38 |
| Belgium v Senegal | 3.36 |
| Colombia v Ghana | 3.36 |
| Switzerland v Algeria | 3.40 |
| Spain v Austria | 3.45 |
| France v Sweden | 3.51 |
| England v DR Congo | 4.06 |
| Argentina v Cabo Verde | 4.72 |

Data cautions:
- Belgium has a bracket/data conflict noted in the engine.
- DR Congo group result was estimated in the ELO file.
- Australia now has a confirmed absence adjustment loaded for the Leckie/Italiano injuries.
- Mexico City altitude and USA host acclimatisation are now priced through the environment tier.
- No confirmed absence adjustment is loaded for the other games.
