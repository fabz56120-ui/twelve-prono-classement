import json
import re
from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"
FICHIER_SORTIE = "classement.json"


def nettoyer_texte(texte):
    return re.sub(r"\s+", " ", texte).strip()


def est_nombre(texte):
    return re.match(r"^-?\d+$", texte) is not None


def main():

    print("Ouverture du classement officiel...")

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=True
        )

        page = browser.new_page(
            viewport={
                "width": 1920,
                "height": 1080
            }
        )

        page.set_default_timeout(120000)

        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        print("Page HTML chargée.")

        page.wait_for_timeout(8000)

        page.evaluate(
            """
            window.scrollTo(0, document.body.scrollHeight / 2);
            """
        )

        page.wait_for_timeout(3000)

        texte = page.locator("body").inner_text()

        print("Texte récupéré.")

        # Debug
        with open(
            "debug_classement.txt",
            "w",
            encoding="utf-8"
        ) as fichier:

            fichier.write(texte)

        lignes = []

        for ligne in texte.split("\n"):

            ligne = nettoyer_texte(ligne)

            if ligne:
                lignes.append(ligne)

        print(f"{len(lignes)} lignes trouvées.")

        # -------------------------------------------------
        # TROUVER LA ZONE DU CLASSEMENT
        # -------------------------------------------------

        try:

            debut = lignes.index("Rang")

        except ValueError:

            print("ERREUR : impossible de trouver le classement.")

            browser.close()
            return

        # On commence après :
        #
        # Rang
        # Club
        # 1
        # 2
        # ...
        # 16
        # Pts
        # M
        # etc.

        # On cherche Oyonnax Rugby ou la première équipe
        debut_equipes = None

        for i in range(debut, len(lignes)):

            # Première position suivie plus loin d'un nom
            if lignes[i] == "1":

                # Dans ton texte actuel, la première équipe
                # est après les titres et les positions 1 à 16.
                for j in range(i + 1, min(i + 25, len(lignes))):

                    if lignes[j] == "Oyonnax Rugby":

                        debut_equipes = j
                        break

            if debut_equipes is not None:
                break

        if debut_equipes is None:

            print("ERREUR : impossible de trouver la première équipe.")

            browser.close()
            return

        print(
            "Début des équipes trouvé :",
            lignes[debut_equipes]
        )

        # -------------------------------------------------
        # EXTRACTION DES 16 EQUIPES
        # -------------------------------------------------

        classement = []

        i = debut_equipes

        while (
            i < len(lignes)
            and len(classement) < 16
        ):

            equipe = lignes[i]

            # Les équipes commencent par leur nom.
            # Ensuite on trouve normalement :
            #
            # points
            # matchs
            # victoires
            # nuls
            # défaites
            # bonus
            # points pour
            # points contre
            # différence
            # forme...
            #

            if (
                equipe in [
                    "V",
                    "D",
                    "N"
                ]
                or est_nombre(equipe)
            ):
                i += 1
                continue

            # Vérifie qu'on a assez de données après l'équipe
            if i + 9 >= len(lignes):
                break

            try:

                points = int(lignes[i + 1])
                matchs = int(lignes[i + 2])
                victoires = int(lignes[i + 3])
                nuls = int(lignes[i + 4])
                defaites = int(lignes[i + 5])

                # Bonus présent mais pas affiché dans Unity
                bonus = int(lignes[i + 6])

                points_pour = int(lignes[i + 7])
                points_contre = int(lignes[i + 8])

                difference = int(
                    lignes[i + 9]
                )

            except ValueError:

                i += 1
                continue

            position = len(classement) + 1

            classement.append(
                {
                    "position": position,
                    "equipe": equipe,
                    "victoires": victoires,
                    "nuls": nuls,
                    "defaites": defaites,
                    "pointsPour": points_pour,
                    "pointsContre": points_contre,
                    "difference": difference,
                    "points": points
                }
            )

            print(
                f"{position} - {equipe} | "
                f"V:{victoires} "
                f"N:{nuls} "
                f"P:{defaites} "
                f"BP:{points_pour} "
                f"BC:{points_contre} "
                f"Diff:{difference} "
                f"Pts:{points}"
            )

            # -------------------------------------------------
            # SAUT VERS L'EQUIPE SUIVANTE
            # -------------------------------------------------

            # Après les statistiques il y a :
            #
            # V D V
            # adversaire
            # date
            # domicile / extérieur
            #
            # On cherche donc la prochaine ligne qui peut être
            # suivie immédiatement de statistiques numériques.

            prochain = None

            for j in range(i + 10, len(lignes) - 9):

                candidat = lignes[j]

                # Une équipe doit être suivie par des nombres
                if not est_nombre(candidat):

                    try:

                        int(lignes[j + 1])
                        int(lignes[j + 2])
                        int(lignes[j + 3])
                        int(lignes[j + 4])
                        int(lignes[j + 5])

                        prochain = j
                        break

                    except ValueError:
                        pass

            if prochain is None:
                break

            i = prochain

        # -------------------------------------------------
        # RESULTAT
        # -------------------------------------------------

        resultat = {
            "source": URL,
            "nombre_equipes": len(classement),
            "classement": classement
        }

        with open(
            FICHIER_SORTIE,
            "w",
            encoding="utf-8"
        ) as fichier:

            json.dump(
                resultat,
                fichier,
                ensure_ascii=False,
                indent=4
            )

        print(
            f"{len(classement)} équipes enregistrées dans "
            f"{FICHIER_SORTIE}"
        )

        browser.close()


if __name__ == "__main__":
    main()
