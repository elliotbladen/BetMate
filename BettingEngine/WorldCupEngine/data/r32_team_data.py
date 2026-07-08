# Round of 32 team data - confirmed absences for knockout pricing.
#
# ATTACK_ABSENCES reduces the team's own expected goals.
# DEFENCE_ABSENCES increases the opponent's expected goals against that team.

ATTACK_ABSENCES = {
    "Australia": -0.04,  # Mat Leckie + Jacob Italiano
    "England": -0.01,    # right-back injuries mainly affect buildup
}

DEFENCE_ABSENCES = {
    "Australia": +0.02,  # wingback/fullback losses also blunt transition defence
    "England": +0.05,    # Reece James / Quansah / Livramento
    "Senegal": +0.06,    # Edouard Mendy ruled out
}

ABSENCE_NOTES = {
    "Australia": "Mat Leckie hamstring strain; Jacob Italiano adductor injury",
    "England": "Reece James hamstring; Jarell Quansah twisted ankle; Tino Livramento calf surgery",
    "Senegal": "Edouard Mendy ruled out through injury",
}
