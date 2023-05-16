import json
import re
from colorama import Fore, Back, Style
import requests
import argparse


def main():
    urls = []
    urlsteam = []

    # création d'un objet ArgumentParser
    parser = argparse.ArgumentParser(
        description='Postman OSINT tool to extract creds, token, username, email & more from Postman Public Workspaces')

    # ajout d'un argument 'query' pour spécifier le mot à chercher
    parser.add_argument('query', type=str,
                        help='name of the target (example: tesla)')

    # parse les arguments de ligne de commande
    args = parser.parse_args()

    with open("scan.txt", "w") as f:
        f.write("Rapport du scan de " + f"{args.query}")
        f.write("\n")
        f.write("\n")

    url = 'https://www.postman.com/_api/ws/proxy'
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0',
        'Content-Type': 'application/json',
    }

    data_raw = {
        "service": "search",
        "method": "POST",
        "path": "/search-all",
        "body": {
            "queryIndices": ["collaboration.workspace", "runtime.collection", "runtime.request", "adp.api", "flow.flow",
                             "apinetwork.team"],
            "queryText": f"{args.query}",
            "size": 100,
            "from": 0,
            "requestOrigin": "srp",
            "mergeEntities": True,
            "nonNestedRequests": True
        }
    }

    for i in range(3):
        response = requests.post(url, headers=headers, json=data_raw)
        data = response.json()
        data_raw["body"]["from"] += 100

        for item in data['data']:
            # Si l'élément est de type "request"
            if item['document']['documentType'] == 'request':
                if 'publisherHandle' in item['document'] and item['document']['publisherHandle']:
                    if 'slug' in item['document']['workspaces'][0]:
                        # Construit l'URL
                        urlworkspace = 'https://www.postman.com/' + item['document'][
                            'publisherHandle'] + '/workspace/' + \
                            item['document']['workspaces'][0]['slug'] + '/'
                        urls.append(urlworkspace)
                    else:
                        chelou = 'https://go.postman.co/workspace/' + item['document']['workspaces'][0][
                            'id'] + '/request/' + item['document']['id']
                        with open("scan.txt", "a") as f:
                            f.write("requete chelou" + chelou)
                        continue
                else:
                    # Passe à l'élément suivant si publisherHandle est manquant
                    continue
            if item['document']['documentType'] == 'team':
                urlteam = 'https://www.postman.com/' + \
                          item['document']['publicHandle']
                urlsteam.append(urlteam)
            if item['document']['documentType'] == 'workspace':
                urlworkspace2 = 'https://www.postman.com/' + item['document']['publisherHandle'] + '/workspace/' + \
                                item['document'][
                                    'slug']
                urls.append(urlworkspace2)
        progress = (i + 1) / 3 * 100

        # affichage de la barre de chargement
        bar_length = 60
        filled_length = int(progress / 100 * bar_length)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        print(
            f'\rReconnaissance initiale : [{bar}] {progress:.1f}%', end='', flush=True)

    urls = list(set(urls))
    urlsteam = list(set(urlsteam))
    # Affiche la liste des URLs

    for lien in urls:
        if "/workspace/" not in lien or "https://www.postman.com//" in lien:
            urls.remove(lien)

    nombreworkspace = len(urls)
    nombreteam = len(urlsteam)

    print("\n")
    print(Fore.RED + str(nombreworkspace) +
          " Workspaces trouvés" + Style.RESET_ALL)
    print(urls)
    print("\n")
    print(Fore.BLUE + str(nombreteam) + " Teams trouvées" + Style.RESET_ALL)
    print(urlsteam)

    with open("scan.txt", "a") as f:
        f.write("Workspaces :")
        f.write("\n")
        for worksp in urls:
            f.write(worksp)
            f.write("\n")
        f.write("\n")
        f.write("\n")
        f.write("Teams :")
        f.write("\n")
        for team in urlsteam:
            f.write(team)
            f.write("\n")

    # Discover des collections et env
    nombrecollection = 0
    nombreenv = 0

    listeallcollec = []

    def progress_bar(n, message=''):
        print(f'\r{message} [', end='')
        for o in range(1, n + 1):
            print('#', end='', flush=True)
        print(']', end='')

    for o, worku in enumerate(urls, start=1):
        if "https://www.postman.com//" in worku:
            continue
        message = f'Scan du workspace {o}/{len(urls)}'
        progress_bar(40, message)
        workurlcompl = worku + "overview"
        match_workspace = re.search(r'https://www.postman.com/([^/]+)/', worku)
        match_workspacename = re.search(r'/workspace/([^/]+)/?$', worku)

        worksp = match_workspace.group(1)
        workspnam = match_workspacename.group(1)

        apiurl = 'https://www.postman.com/_api/ws/proxy'

        data_rawid = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces?handle={worksp}&slug={workspnam}"
        }
        # Trouver l'id du workspace

        responseid = requests.post(apiurl, headers=headers, json=data_rawid)

        iddiv = responseid.json()

        if 'error' in iddiv:
            continue

        idwork = iddiv['data'][0]['id']

        # Taper sur le workspace avec l'id pour decouvrir les collections et environnements

        url2 = 'https://www.postman.com/_api/ws/proxy'

        data_raw = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces/{idwork}?include=elements"
        }

        responsedisco = requests.post(url2, headers=headers, json=data_raw)

        all_uuid = responsedisco.json()

        if 'environments' in all_uuid['data']['elements']:
            urlenv = all_uuid['data']['elements']['environments']
        else:
            urlenv = []
        if 'collections' in all_uuid['data']['elements']:
            urlcollec = all_uuid['data']['elements']['collections']
        else:
            urlcollec = []

        with open("scan.txt", "a") as f:
            f.write("\n")
            f.write("Sur le workspace :" + workurlcompl)
            f.write("\n")

        for urlc in urlcollec:
            nombrecollection += 1
            urlcollecfinal = worku + "collection/" + urlc
            listeallcollec.append(urlcollecfinal)
            with open("scan.txt", "a") as f:
                f.write("\n")
                f.write("Collection " + urlcollecfinal)

        urlenvapi = 'https://www.postman.com/_api/environment/'

        with open("scan.txt", "a") as f:
            f.write("\n")
            f.write("\n")
            f.write("Sur le workspace :" + workurlcompl)

        for urle in urlenv:
            urlenvfinal = worku + "environment/" + urle
            apienvurl = urlenvapi + urle
            responseapi = requests.get(apienvurl, headers=headers)
            environment = responseapi.json()
            nameenv = environment['data']['name']
            env = environment['data']['values']
            nombreenv += 1
            with open("scan.txt", "a") as f:
                f.write("\n")
                f.write("Environnement " + nameenv + " : ")
                f.write("\n")
                f.write(str(env))
                f.write("\n")
    print('\nTerminé !')

    print("\n")
    print(Fore.GREEN + str(nombrecollection) +
          " Collections trouvées" + Style.RESET_ALL)
    print(Fore.GREEN + str(nombreenv) +
          " Valeurs d'environnements trouvées" + Style.RESET_ALL)
    print("\n")
    # print(listeallcollec)

    # Discover et scan des requetes de chaque collections

    # for coll in listeallcollec:
    #     print(coll)

    reqtrouv = 0

    authlist = []
    headerlist = []
    bodylist = []

    for p, coll in enumerate(listeallcollec, start=1):
        messagescanco = f'Scan de la collection {p}/{len(listeallcollec)}'
        progress_bar(40, messagescanco)
        segments = coll.split('/')
        idseg = segments[-1]
        urltrueapi = 'https://www.postman.com/_api/collection/' + idseg

        responsecoll = requests.get(urltrueapi, headers=headers)

        # print(urltrueapi)
        collection = responsecoll.json()
        # print(collection)
        owner = collection['data']['owner']
        order = collection['data']['order']
        folders_order = collection['data']['folders_order']

        for orde in folders_order:
            urlsubord = "https://www.postman.com/_api/folder/" + owner + "-" + orde
            responsesub = requests.get(urlsubord, headers=headers)
            subcollection = responsesub.json()
            if 'error' in subcollection:
                continue
            suborder = subcollection['data']['order']
            subsubfolders = subcollection['data']['folders_order']
            if len(subsubfolders) != 0:
                for subsubfolder in subsubfolders:
                    urlsubsubord = "https://www.postman.com/_api/folder/" + owner + "-" + subsubfolder
                    responsesubsub = requests.get(
                        urlsubsubord, headers=headers)
                    subsubcollection = responsesubsub.json()
                    subsuborder = subsubcollection['data']['order']
                    order.extend(subsuborder)
            else:
                pass
            order.extend(suborder)

        reqtrouv += len(order)

        urlrequest = 'https://www.postman.com/_api/request/'
        pattern = re.compile(r'^\{\{.*\}\}$')

        def find_croustillant(datacr):
            if isinstance(datacr, dict):
                for key, value in datacr.items():
                    if key in ["voucher", "username", "password", "email", "token", "accesskey", "creditCard",
                               "creditcard",
                               "phone", "address", "mobilephone", "cellPhone", "code", "authorization_code",
                               "client_id",
                               "client_secret", "name", "apikey", "customer_email", "api_key", "api_secret",
                               "apisecret",
                               "hash", "paypal_token", "identity", "phoneHome", "phoneOffice", "phoneMobile",
                               "consumer_key",
                               "consumer_secret", "access_token"]:
                        # print(value)
                        bodylist.append(value)
                    else:
                        find_croustillant(value)
            elif isinstance(datacr, list):
                for itemcr in datacr:
                    find_croustillant(itemcr)

        for request in order:
            urlrequestfull = urlrequest + owner + "-" + request
            requestresponse = requests.get(urlrequestfull, headers=headers)

            requestresp = requestresponse.json()
            urlreq = requestresp['data']['url']
            auth = requestresp['data']['auth']
            header = requestresp['data']['headerData']
            pattern = re.compile(r'^\{\{.*\}\}$')
            datamode = requestresp['data']['dataMode']
            filtered_header_data = [item for item in header if
                                    item['key'] not in ['Content-Type', 'Accept', 'x-api-error-detail',
                                                        'x-api-appid'] and not pattern.match(item['value']) and item[
                                        'value']]
            if auth is not None:
                # if auth["type"] == "digest":
                #     for element in auth['digest']:
                #         if element['value'] and not pattern.match(element['value']):
                #             print("Sur l'url : " + urlreq)
                #             print(auth)
                # else:
                #     print(urlrequestfull)
                # print("Sur l'url : " + urlreq)
                # print(auth)
                authlist.append(auth)
            if filtered_header_data:
                # print("Sur l'url : " + urlreq)
                # print(filtered_header_data)
                headerlist.append(filtered_header_data)
            if datamode == "raw":
                body1 = requestresp['data']['rawModeData']

                try:
                    if body1 is not None and body1.strip():
                        parsed_data = json.loads(body1)
                        find_croustillant(parsed_data)
                    else:
                        pass
                except json.JSONDecodeError as e:
                    continue
            if datamode == "params" and requestresp['data']['data'] is not None and len(
                    requestresp['data']["data"]) > 0:

                datas = requestresp['data']["data"]
                for nom in datas:
                    # print(urlrequestfull)
                    if nom['key'] in ["voucher", "username", "password", "email", "token", "accesskey", "creditCard",
                                      "creditcard", "phone", "address", "mobilephone", "cellPhone", "code",
                                      "authorization_code", "client_id", "client_secret", "name", "apikey",
                                      "customer_email",
                                      "api_key", "api_secret", "apisecret", "hash", "paypal_token", "identity",
                                      "phoneHome",
                                      "phoneOffice", "phoneMobile", "consumer_key", "consumer_secret", "access_token"]:
                        bodylist.append(nom["value"])
                        # print(nom["value"])

    # Nettoyage des doublons
    authlistnodoublon = []
    unique_set = set()

    for d in authlist:
        s = json.dumps(d, sort_keys=True)
        if s not in unique_set:
            unique_set.add(s)
            authlistnodoublon.append(json.loads(s))

    headerlistnodoublon = []

    for d in headerlist:
        s = json.dumps(d, sort_keys=True)
        if s not in unique_set:
            unique_set.add(s)
            headerlistnodoublon.append(json.loads(s))

    bodylistnodoublon = []

    for d in bodylist:
        s = json.dumps(d, sort_keys=True)
        if s not in unique_set:
            unique_set.add(s)
            bodylistnodoublon.append(json.loads(s))

    print(Fore.GREEN + str(reqtrouv) + " Requêtes scannées :" + Style.RESET_ALL)
    print("\n")
    print(Fore.RED + str(len(authlistnodoublon)) +
          " valeurs d'authentification trouvées" + Style.RESET_ALL)
    print(Fore.RED + str(len(headerlistnodoublon)) +
          " valeurs intéressantes en headers trouvées" + Style.RESET_ALL)
    print(Fore.RED + str(len(bodylistnodoublon)) +
          " valeurs intéressantes en body trouvées" + Style.RESET_ALL)

    with open("scan.txt", "a") as f:
        f.write("Valeurs d'authentification trouvées :")
        f.write("\n")
        f.write("\n")
        f.write(str(authlistnodoublon))
        f.write("\n")
        f.write("\n")
        f.write("Valeurs intéressantes en headers trouvées :")
        f.write("\n")
        f.write("\n")
        f.write(str(headerlistnodoublon))
        f.write("\n")
        f.write("\n")
        f.write("Valeurs intéressantes en body trouvées :")
        f.write("\n")
        f.write("\n")
        f.write(str(bodylistnodoublon))


if __name__ == '__main__':
    main()
