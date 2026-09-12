import json
import re
from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"
FICHIER_SORTIE = "classement.json"


def nettoyer_texte(texte):
    return re.sub(r"\s+", " ", texte).strip()


def est_nombre(texte):
    return re.match(r"^[+-]?\d+$", texte) is not None


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

        # Sauvegarde du texte pour debug
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

        # ---------------------------------------------
        # TROUVER LE DEBUT DES DONNEES DU CLASSEMENT
        # ---------------------------------------------

        try:

            index_debut = lignes.index("Prochain match") + 1

        except ValueError:

            print(
                "ERREUR : impossible de trouver "
                "le début du classement."
            )

            browser.close()
            return

        print("Début du classement trouvé.")

        # ---------------------------------------------
        # EXTRACTION DES EQUIPES
        # ---------------------------------------------

        classement = []

        i = index_debut

        while (
            i < len(lignes) - 9
            and len(classement) < 16
        ):

            equipe = lignes[i]

            # Une équipe doit être suivie immédiatement
            # de 9 statistiques :
            #
            # Pts
            # M
            # G
            # N
            # P
            # Bonus
            # Pts M.
            # Pts E.
            # Diff

            if (
                not est_nombre(equipe)
                and re.search(r"[A-Za-zÀ-ÿ]", equipe)
            ):

                statistiques_valides = True

                for j in range(1, 10):

                    if not est_nombre(lignes[i + j]):

                        statistiques_valides = False
                        break

                if statistiques_valides:

                    points = int(lignes[i + 1])
                    matchs = int(lignes[i + 2])
                    victoires = int(lignes[i + 3])
                    nuls = int(lignes[i + 4])
                    defaites = int(lignes[i + 5])

                    # Bonus récupéré mais non affiché
                    bonus = int(lignes[i + 6])

                    points_pour = int(lignes[i + 7])
                    points_contre = int(lignes[i + 8])
                    difference = int(lignes[i + 9])

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

                    # On avance après les statistiques.
                    # La boucle cherchera ensuite la prochaine
                    # équipe qui est suivie de 9 nombres.
                    i += 10

                    continue

            i += 1

        # ---------------------------------------------
        # CREATION DU JSON
        # ---------------------------------------------

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
