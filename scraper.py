import json
import re
from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"
FICHIER_SORTIE = "classement.json"


def nettoyer_texte(texte):
    return re.sub(r"\s+", " ", texte).strip()


def est_nombre(texte):
    """
    Accepte :
    14
    3
    130
    +67
    -31
    """

    return bool(
        re.match(
            r"^[+-]?\d+$",
            texte.strip()
        )
    )


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

        # Attente du JavaScript
        page.wait_for_timeout(8000)

        # Petit scroll pour déclencher le contenu dynamique
        page.evaluate(
            """
            window.scrollTo(
                0,
                document.body.scrollHeight / 2
            );
            """
        )

        page.wait_for_timeout(3000)

        # Texte visible
        texte = page.locator("body").inner_text()

        print("Texte récupéré.")

        # Sauvegarde debug
        with open(
            "debug_classement.txt",
            "w",
            encoding="utf-8"
        ) as fichier:

            fichier.write(texte)

        # Nettoyage des lignes
        lignes = []

        for ligne in texte.split("\n"):

            ligne = nettoyer_texte(ligne)

            if ligne:
                lignes.append(ligne)

        print(
            f"{len(lignes)} lignes trouvées."
        )

        # ------------------------------------------
        # ON COMMENCE APRES "PROCHAIN MATCH"
        # ------------------------------------------

        debut_classement = -1

        for i, ligne in enumerate(lignes):

            if ligne.lower() == "prochain match":

                debut_classement = i + 1
                break

        if debut_classement == -1:

            print(
                "ERREUR : impossible de trouver "
                "'Prochain match'"
            )

            browser.close()
            return

        print(
            f"Début des équipes trouvé à "
            f"la ligne {debut_classement}"
        )

        classement = []

        # ------------------------------------------
        # RECHERCHE DES EQUIPES
        # ------------------------------------------

        for i in range(
            debut_classement,
            len(lignes)
        ):

            # On a déjà les 16 équipes
            if len(classement) >= 16:
                break

            equipe = lignes[i]

            # Il faut suffisamment de lignes après
            if i + 9 >= len(lignes):
                continue

            # Une équipe doit contenir des lettres
            if not re.search(
                r"[A-Za-zÀ-ÿ]",
                equipe
            ):
                continue

            # Une équipe ne doit pas être
            # une ligne de classement générale
            if equipe.lower() in [
                "classement",
                "rang",
                "club",
                "pts",
                "prochain match"
            ]:
                continue

            # --------------------------------------
            # VERIFICATION DES 9 STATISTIQUES
            #
            # Equipe
            # Pts
            # M
            # G
            # N
            # P
            # Bonus
            # Pts M
            # Pts E
            # Diff
            # --------------------------------------

            statistiques_valides = True

            for j in range(1, 10):

                if not est_nombre(
                    lignes[i + j]
                ):

                    statistiques_valides = False
                    break

            if not statistiques_valides:
                continue

            position = (
                len(classement) + 1
            )

            classement.append(
                {
                    "position": position,
                    "equipe": equipe
                }
            )

            print(
                f"{position} - {equipe}"
            )

        resultat = {
            "source": URL,
            "nombre_equipes": len(classement),
            "classement": classement
        }

        # Sauvegarde JSON
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
            f"{len(classement)} équipes trouvées."
        )

        print(
            f"Classement enregistré dans "
            f"{FICHIER_SORTIE}"
        )

        browser.close()


if __name__ == "__main__":
    main()
