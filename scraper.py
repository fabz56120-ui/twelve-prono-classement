import json
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"


def nettoyer(texte):
    return " ".join(texte.split())


def main():

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 1200
            }
        )

        print("Ouverture du classement officiel...")

        page.goto(
            URL,
            wait_until="networkidle",
            timeout=60000
        )

        page.wait_for_timeout(3000)

        # Récupération de toutes les lignes
        lignes = page.locator("tr").all()

        classement = []

        for ligne in lignes:

            cellules = ligne.locator(
                "td"
            ).all()

            if len(cellules) < 3:
                continue

            valeurs = []

            for cellule in cellules:

                texte = nettoyer(
                    cellule.inner_text()
                )

                if texte:
                    valeurs.append(
                        texte
                    )

            if len(valeurs) < 3:
                continue

            print(valeurs)

            classement.append(
                valeurs
            )

        browser.close()

    resultat = {
        "source": URL,
        "competition": "PRO D2",
        "mise_a_jour": datetime.now(
            timezone.utc
        ).isoformat(),
        "classement": classement
    }

    with open(
        "classement.json",
        "w",
        encoding="utf-8"
    ) as fichier:

        json.dump(
            resultat,
            fichier,
            ensure_ascii=False,
            indent=4
        )

    print("")
    print(
        "Classement enregistré :",
        len(classement),
        "lignes"
    )


if __name__ == "__main__":
    main()
