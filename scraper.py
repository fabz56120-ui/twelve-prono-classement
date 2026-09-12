import json
import re
from playwright.sync_api import sync_playwright


URL = "https://prod2.lnr.fr/classement"
FICHIER_SORTIE = "classement.json"


def nettoyer_texte(texte):
    return re.sub(r"\s+", " ", texte).strip()


def est_position(texte):
    return re.fullmatch(
        r"\d+(?:er|e|ème|eme)?",
        texte.strip(),
        re.IGNORECASE
    ) is not None


def est_nom_equipe(texte):

    texte = nettoyer_texte(texte)

    if len(texte) < 3:
        return False

    # Colonnes du classement à ignorer
    mots_interdits = [
        "rang",
        "equipe",
        "équipe",
        "matchs",
        "joués",
        "joues",
        "j",
        "v",
        "n",
        "d",
        "pts",
        "points",
        "bonus",
        "classement"
    ]

    if texte.lower() in mots_interdits:
        return False

    # Pas uniquement un nombre
    if re.fullmatch(r"\d+", texte):
        return False

    # Il faut contenir des lettres
    if not re.search(r"[A-Za-zÀ-ÿ]", texte):
        return False

    return True


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

        # Attendre le JavaScript du site
        page.wait_for_timeout(10000)

        # Déclencher le chargement complet
        page.evaluate(
            """
            window.scrollTo(0, document.body.scrollHeight);
            """
        )

        page.wait_for_timeout(3000)

        # ---------------------------------------------
        # RECUPERATION DE TOUS LES ELEMENTS VISIBLES
        # ---------------------------------------------

        elements = page.locator("body *")

        total = elements.count()

        print(f"{total} éléments HTML trouvés.")

        classement = []
        positions_trouvees = set()

        for i in range(total):

            try:

                element = elements.nth(i)

                # Seulement les éléments visibles
                if not element.is_visible():
                    continue

                texte = nettoyer_texte(
                    element.inner_text(timeout=3000)
                )

                if not texte:
                    continue

                # On cherche un élément contenant
                # exactement une position : 1, 2, 3, etc.
                if not est_position(texte):
                    continue

                position = int(
                    re.match(
                        r"\d+",
                        texte
                    ).group()
                )

                # PRO D2 = 16 équipes
                if position < 1 or position > 16:
                    continue

                # Evite de traiter plusieurs fois
                # la même position
                if position in positions_trouvees:
                    continue

                # -----------------------------------------
                # RECHERCHE DU PARENT DE LA LIGNE
                # -----------------------------------------

                parent = element.locator("..")

                parent_texte = nettoyer_texte(
                    parent.inner_text(timeout=3000)
                )

                lignes_parent = [
                    nettoyer_texte(x)
                    for x in parent_texte.split("\n")
                    if nettoyer_texte(x)
                ]

                equipe = ""

                # Cherche un nom plausible après la position
                for ligne in lignes_parent:

                    if ligne == texte:
                        continue

                    if est_nom_equipe(ligne):

                        # Ignore les lignes qui ressemblent
                        # aux données statistiques
                        if ligne.lower() not in [
                            "v",
                            "n",
                            "d",
                            "pts"
                        ]:
                            equipe = ligne
                            break

                # -----------------------------------------
                # SI RIEN TROUVE :
                # ON MONTE D'UN NIVEAU HTML
                # -----------------------------------------

                if not equipe:

                    grand_parent = parent.locator("..")

                    gp_texte = nettoyer_texte(
                        grand_parent.inner_text(
                            timeout=3000
                        )
                    )

                    lignes_gp = [
                        nettoyer_texte(x)
                        for x in gp_texte.split("\n")
                        if nettoyer_texte(x)
                    ]

                    for index, ligne in enumerate(lignes_gp):

                        if ligne == texte:

                            # Cherche les 5 éléments suivants
                            for j in range(
                                index + 1,
                                min(
                                    index + 6,
                                    len(lignes_gp)
                                )
                            ):

                                candidat = lignes_gp[j]

                                if est_nom_equipe(
                                    candidat
                                ):
                                    equipe = candidat
                                    break

                            break

                # -----------------------------------------
                # AJOUT DE L'EQUIPE
                # -----------------------------------------

                if equipe:

                    classement.append(
                        {
                            "position": position,
                            "equipe": equipe
                        }
                    )

                    positions_trouvees.add(
                        position
                    )

                    print(
                        f"{position} - {equipe}"
                    )

            except Exception as e:

                # On continue même si un élément
                # pose problème
                continue

        # ---------------------------------------------
        # TRI
        # ---------------------------------------------

        classement.sort(
            key=lambda x: x["position"]
        )

        # ---------------------------------------------
        # SAUVEGARDE DEBUG HTML / TEXTE
        # ---------------------------------------------

        body_text = page.locator(
            "body"
        ).inner_text()

        with open(
            "debug_classement.txt",
            "w",
            encoding="utf-8"
        ) as fichier:

            fichier.write(body_text)

        # ---------------------------------------------
        # RESULTAT
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

        print("")
        print(
            f"{len(classement)} équipes enregistrées."
        )

        if len(classement) != 16:

            print(
                "ATTENTION : le classement "
                "ne contient pas 16 équipes."
            )

        browser.close()


if __name__ == "__main__":
    main()
