import json
import re
from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"
FICHIER_SORTIE = "classement.json"


def nettoyer_texte(texte):
    return re.sub(r"\s+", " ", texte).strip()


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

        # Timeout global plus long
        page.set_default_timeout(120000)

        # IMPORTANT :
        # On n'utilise PAS networkidle car le site LNR
        # garde probablement des requêtes réseau actives.
        page.goto(
            URL,
            wait_until="domcontentloaded",
            timeout=120000
        )

        print("Page HTML chargée.")

        # Attendre le chargement JavaScript
        page.wait_for_timeout(8000)

        # Petit scroll pour déclencher les éléments chargés dynamiquement
        page.evaluate(
            """
            window.scrollTo(0, document.body.scrollHeight / 2);
            """
        )

        page.wait_for_timeout(3000)

        # Récupération du texte visible
        texte = page.locator("body").inner_text()

        print("Texte récupéré.")

        # Sauvegarde debug
        with open(
            "debug_classement.txt",
            "w",
            encoding="utf-8"
        ) as fichier:

            fichier.write(texte)

        print("Debug enregistré.")

        lignes = []

        for ligne in texte.split("\n"):

            ligne = nettoyer_texte(ligne)

            if ligne:
                lignes.append(ligne)

        print(
            f"{len(lignes)} lignes trouvées."
        )

        # -------------------------------------------------
        # RECHERCHE DES POSITIONS
        # -------------------------------------------------

        classement = []

        for i, ligne in enumerate(lignes):

            # Exemple :
            # 1
            # Provence Rugby
            #
            # ou :
            # 1er
            # Provence Rugby

            position_match = re.match(
                r"^(\d+)(?:er|e|ème|eme)?$",
                ligne,
                re.IGNORECASE
            )

            if not position_match:
                continue

            position = int(
                position_match.group(1)
            )

            # On ne garde que les positions réalistes
            if position < 1 or position > 20:
                continue

            equipe = ""

            # Cherche la prochaine ligne utilisable
            for j in range(
                i + 1,
                min(i + 6, len(lignes))
            ):

                candidat = lignes[j]

                # Ignore les autres chiffres
                if re.match(
                    r"^\d+(?:er|e|ème|eme)?$",
                    candidat,
                    re.IGNORECASE
                ):
                    continue

                # Ignore les éléments inutiles
                if candidat.lower() in [
                    "classement",
                    "matchs",
                    "points",
                    "joués",
                    "gagnés",
                    "nuls",
                    "perdus"
                ]:
                    continue

                # Une équipe doit contenir des lettres
                if re.search(
                    r"[A-Za-zÀ-ÿ]",
                    candidat
                ):
                    equipe = candidat
                    break

            if equipe:

                # Évite les doublons
                existe = False

                for club in classement:

                    if club["position"] == position:
                        existe = True
                        break

                if not existe:

                    classement.append(
                        {
                            "position": position,
                            "equipe": equipe
                        }
                    )

        # Tri
        classement.sort(
            key=lambda x: x["position"]
        )

        resultat = {
            "source": URL,
            "classement": classement
        }

        print(
            f"{len(classement)} équipes trouvées."
        )

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
            f"Classement enregistré dans {FICHIER_SORTIE}"
        )

        browser.close()


if __name__ == "__main__":
    main()
