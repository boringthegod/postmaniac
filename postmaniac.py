import json
import re
from colorama import Fore, Back, Style
import requests
import argparse
import random
from stringcolor import *

VERSION = "0.1.1"

def main():

    baseUrl          = 'https://www.postman.com/'
    url              = baseUrl+'_api/ws/proxy'
    urlenvapi        = baseUrl+'_api/environment/'
    urlrequest       = baseUrl+'_api/request/'
    urlApiCollection = baseUrl+'_api/collection/'
    urlApiFolder     = baseUrl+'_api/folder/'

    urlsWorkspaces = []
    urlsteam = []

    parser = argparse.ArgumentParser(description='Postman OSINT tool to extract creds, token, username, email & more from Postman Public Workspaces')
    parser.add_argument('query', type=str, help='name of the target (example: tesla)')

    args = parser.parse_args()

    #Read the keywords from the file
    with open('keywords.txt', 'r') as file:
        keywords = [line.strip() for line in file]

    print("\nScan report for " + f"{args.query}")
    # List of user agents
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36',
        'Mozilla/5.0 (Linux; Android 11; Pixel 4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Mobile Safari/537.36'
    ]
    # Choose a random user agent
    random_user_agent = random.choice(user_agents)
    
    headers = {
        'User-Agent': random_user_agent,
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

    #probably it needs to run this several times
    scans=3
    for i in range(scans):
        response = requests.post(url, headers=headers, json=data_raw)
        data = response.json()
        data_raw["body"]["from"] += 100

        for item in data['data']:
            if item['document']['documentType'] == 'request':
                if 'publisherHandle' in item['document'] and item['document']['publisherHandle']:
                    if 'slug' in item['document']['workspaces'][0]:
                        urlworkspace = baseUrl + item['document']['publisherHandle'] + '/workspace/' + item['document']['workspaces'][0]['slug']
                        urlsWorkspaces.append(urlworkspace)
                    else:
                        chelou = 'https://go.postman.co/workspace/' + item['document']['workspaces'][0]['id'] + '/request/' + item['document']['id']
                        print("Weird request" + chelou)
                        continue
                else:
                    # Passe à l'élément suivant si publisherHandle est manquant
                    continue
            #teams
            if item['document']['documentType'] == 'team':
                urlteam = baseUrl + item['document']['publicHandle']
                urlsteam.append(urlteam)
            #workspaces
            if item['document']['documentType'] == 'workspace':
                urlworkspace2 = baseUrl + item['document']['publisherHandle']+'/workspace/' + item['document']['slug']
                urlsWorkspaces.append(urlworkspace2)

    urlsWorkspaces = list(set(urlsWorkspaces))
    urlsteam = list(set(urlsteam))
    # Affiche la liste des URLs

    #for lien in urls:
    #    if "/workspace/" not in lien or "https://www.postman.com//" in lien:
    #        urls.remove(lien)

    print("\n"+Fore.RED + str(len(urlsWorkspaces)) +" Workspaces found" + Style.RESET_ALL)
    # Print each URL with line numbers
    for i, workspaceUrl in enumerate(urlsWorkspaces, start=1):
        print(f"{i}. {workspaceUrl}")

    print(Fore.BLUE + str(len(urlsteam)) + " Teams found" + Style.RESET_ALL)

    for i, teamUrls in enumerate(urlsteam, start=1):
        print(f"{i}. {teamUrls}")

    nombrecollection = 0
    nombreenv = 0

    listeallcollec = []

    for o, workspace in enumerate(urlsWorkspaces, start=1):
        if baseUrl+"/" in workspace:
            continue
        print(Fore.YELLOW + f'\nScanning {workspace} [{o}/{len(urlsWorkspaces)}]'+ Style.RESET_ALL+"\n")
        workurlcompl = workspace + "overview"
        match_workspace = re.search(r'https://www.postman.com/([^/]+)/', workspace)
        match_workspacename = re.search(r'/workspace/([^/]+)/?$', workspace)

        worksp = match_workspace.group(1)
        workspnam = match_workspacename.group(1)

        data_rawid = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces?handle={worksp}&slug={workspnam}"
        }

        responseid = requests.post(url, headers=headers, json=data_rawid)
        iddiv = responseid.json()

        if 'error' in iddiv:
            continue

        idwork = iddiv['data'][0]['id']

        data_raw = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces/{idwork}?include=elements"
        }

        responsedisco = requests.post(url, headers=headers, json=data_raw)
        all_uuid = responsedisco.json()

        if 'collections' in all_uuid['data']['elements']:
            urlcollec = all_uuid['data']['elements']['collections']
        else:
            urlcollec = []

        print(Fore.GREEN + str(len(urlcollec)) +" Collections found" + Style.RESET_ALL)
        # Print each Collection with line numbers
        for i, urlc in enumerate(urlcollec, start=1):
            print(f"{i}. {workspace}/collection/{urlc}")

        if 'environments' in all_uuid['data']['elements']:
            urlenv = all_uuid['data']['elements']['environments']
        else:
            urlenv = []

        env_list = [] 

        for urle in urlenv:
            urlenvfinal = workspace + "environment/" + urle
            apienvurl = urlenvapi + urle
            responseapi = requests.get(apienvurl, headers=headers)
            environment = responseapi.json()
            nameenv = environment['data']['name']
            env = environment['data']['values']
            # Check if env exists and is not empty
            if 'data' in environment and 'values' in environment['data'] and environment['data']['values']:
                env_list.append(environment['data']['values'])
        print(Fore.GREEN + str(len(env_list)) +" Environment values found" + Style.RESET_ALL)

        for i, envValue in enumerate(env_list, start=1):
            print(f"{i}. {envValue}")

    print('Done!\n')
    #done scanning for collections and enviroments vars

    reqtrouv = 0
    authlist = []
    headerlist = []
    bodylist = []


    for p, coll in enumerate(listeallcollec, start=1):
        messagescanco = f'Scan of collection {p}/{len(listeallcollec)}'
        print(messagescanco)
        segments = coll.split('/')
        idseg = segments[-1]
        urltrueapi = urlApiCollection + idseg

        responsecoll = requests.get(urltrueapi, headers=headers)
        collection = responsecoll.json()

        owner = collection['data']['owner']
        order = collection['data']['order']
        folders_order = collection['data']['folders_order']
        
        for orde in folders_order:
            urlsubord = urlApiFolder + owner + "-" + orde
            responsesub = requests.get(urlsubord, headers=headers)
            subcollection = responsesub.json()
            if 'error' in subcollection:
                continue
            suborder = subcollection['data']['order']
            subsubfolders = subcollection['data']['folders_order']
            if len(subsubfolders) != 0:
                for subsubfolder in subsubfolders:
                    urlsubsubord = urlApiFolder + owner + "-" + subsubfolder
                    responsesubsub = requests.get(
                        urlsubsubord, headers=headers)
                    subsubcollection = responsesubsub.json()
                    subsuborder = subsubcollection['data']['order']
                    order.extend(subsuborder)
            else:
                pass
            order.extend(suborder)

        reqtrouv += len(order)
        pattern = re.compile(r'^\{\{.*\}\}$')


        def find_croustillant(datacr):
			#input is dictionary
            if isinstance(datacr, dict):
                for key, value in datacr.items():        
                    if key in keywords: 
                        bodylist.append(value)
                    else:
                        find_croustillant(value)
			#input is a list
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
                                    item['key'] not in ['Content-Type', 'Accept', 'x-api-error-detail','x-api-appid'] and not pattern.match(item['value']) and item['value']]
            if auth is not None:
                authlist.append(auth)
            if filtered_header_data:
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
            if datamode == "params" and requestresp['data']['data'] is not None and len(requestresp['data']["data"]) > 0:
                datas = requestresp['data']["data"]
                for nom in datas:
                     if nom['key'] in keywords:
                        bodylist.append(nom['value'])

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

    print(Fore.GREEN + str(reqtrouv) + " Scanned requests: " + Style.RESET_ALL+"\n")
    print(Fore.RED + str(len(authlistnodoublon))   + " Auth token ​​found" + Style.RESET_ALL)
    print(Fore.RED + str(len(headerlistnodoublon)) + " Intersting values in headers" + Style.RESET_ALL)
    print(Fore.RED + str(len(bodylistnodoublon))   + " Intersting values in bodies" + Style.RESET_ALL)

if __name__ == '__main__':
    main()
