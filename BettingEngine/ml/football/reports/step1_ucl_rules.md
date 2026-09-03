# Champions League Step 1 — competition-rules contract

The UCL model now uses a frozen 2026/27 rules contract. It records the modern
36-club league phase, eight single-leg matches per club (four home and four
away), two opponents from each of four coefficient pots, the 1–8 direct route,
the 9–24 play-off route and elimination for 25–36.

The knockout phase is two-legged except for the neutral single-match final. The
away-goals rule is permanently disabled. A tied two-legged tie resolves through
30 minutes of extra time and then penalties; the final uses the same extra-time
and penalty treatment.

This contract is deliberately separate from the EPL season model. Every future
fixture is tagged with the rules version, stage and qualification-resolution
method. No model may use a group-stage assumption for a modern league-phase
season.

Primary sources: [UEFA 2026/27 league-phase draw procedure](https://www.uefa.com/uefachampionsleague/news/02a8-215821715a96-9a3b43fad585-1000--uefa-champions-league-league-phase-draw/),
[Article 20 knockout system](https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2026/27/Article-20-Match-system-knockout-phase-Online),
and [Article 21 extra time and penalties](https://documents.uefa.com/r/Regulations-of-the-UEFA-Champions-League-2026/27/Article-21-Knockout-system-extra-time-and-penalty-shoot-outs-Online?contentId=aBOyMYjtgYYIYwn~YRHF5Q).
