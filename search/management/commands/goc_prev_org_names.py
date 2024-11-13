PREVIOUS_DEPARTMENT_NAMES = {
    "dfatd-maecd": {"acronym_en": ["gac", "dfait"],
                    "acronym_fr": ["amc", "maeci"],
                    "title_en": ["Foreign Affairs and International Trade Canada", "Department of Foreign Affairs, Trade and Development"],
                    "title_fr": ["Ministère des Affaires étrangères et Commerce international Canada", "Ministère des Affaires étrangères et du Commerce international"]},
    "ic": {"acronym_en": ["ised"],
           "acronym_fr": ["isde"],
           "title_en": ["Industry Canada"],
           "title_fr": ["Industrie Canada"]},
    "pwgsc-tpsgc": {"acronym_en": ["pspc"],
                    "acronym_fr": ["spac"],
                    "title_en": ["Public Works and Government Services Canada"],
                    "title_fr": ["Ministère des Travaux publics et des Services gouvernementaux Canada"]},
    "cra-arc": {"acronym_en": ["ccra"],
                "acronym_fr": ["adrc"],
                "title_en": ["Canada Customs and Revenue Agency"],
                "title_fr": ["Agence des douanes et du revenu du Canada"]},
    "cbsa-asfc": {"acronym_en": ["ccra"],
                "acronym_fr": ["adrc"],
                "title_en": ["Canada Customs and Revenue Agency"],
                "title_fr": ["Agence des douanes et du revenu du Canada"]},
    "ec": {"acronym_en": ["eccc"],
           "acronym_fr": ["eccc"],
           "title_en": ["Environment Canada"],
           "title_fr": ["Environnement Canada"]},
    "aandc-aadnc": {"acronym_en": ["cirnac", "diand"],
                    "acronym_fr": ["rcaanc", "ainc"],
                    "title_en": ["Department of Indian Affairs and Northern Development", "Aboriginal Affairs and Northern Development"],
                    "title_fr": ["Ministère des Affaires indiennes et du Nord canadien", "Affaires autochtones et du développement du Grand Nord"]},
    "esdc-edsc": {"acronym_en": ["hrdc"],
                  "acronym_fr": ["drhc"],
                  "title_en": ["uman Resources Development Canada "],
                  "title_fr": ["Développement des ressources humaines Canada"]},
    "cic": {"acronym_en": ["ircc"],
            "acronym_fr": ["cicr"],
            "title_en": ["Citizenship and Immigration Canada"],
            "title_fr": ["Citoyenneté et Immigration Canada"]},
    "cer-rec": {"acronym_en": ["neb"],
                "acronym_fr": ["rec"],
                "title_en": ["National Energy Board"],
                "title_fr": ["Office national de l'énergie"]},
}


def add_prev_dept_names(org_name:str, data_rec:dict, title_en=None, title_fr=None, acronym_en=None, acronym_fr=None):

    if "owner_title_en" not in data_rec:
        data_rec["owner_title_en"] = [] if title_en is None else title_en
    if "owner_title_fr" not in data_rec:
        data_rec["owner_title_fr"] = [] if title_fr is None else title_fr
    if "owner_org_acronym_en" not in data_rec:
        data_rec["owner_org_acronym_en"] = [] if acronym_en is None else acronym_en
    if "owner_org_acronym_fr" not in data_rec:
        data_rec["owner_org_acronym_fr"] = [] if acronym_fr is None else acronym_fr

    if org_name in PREVIOUS_DEPARTMENT_NAMES:
        data_rec["owner_title_en"].extend(PREVIOUS_DEPARTMENT_NAMES[org_name]["title_en"])
        data_rec["owner_title_fr"].extend(PREVIOUS_DEPARTMENT_NAMES[org_name]["title_fr"])
        data_rec["owner_org_acronym_en"].extend(PREVIOUS_DEPARTMENT_NAMES[org_name]["acronym_en"])
        data_rec["owner_org_acronym_fr"].extend(PREVIOUS_DEPARTMENT_NAMES[org_name]["acronym_fr"])

    return data_rec
