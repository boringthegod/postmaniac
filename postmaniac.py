import json
import re
from colorama import Fore, Back, Style
import requests
import argparse
import random
from stringcolor import *
import sys

VERSION = "0.1.1"

def find_croustillant(datacr,keywords):
	#input is dictionary
    if isinstance(datacr, dict):
        for key, value in datacr.items():        
            if key in keywords: 
                bodylist.append(value)
            else:
                find_croustillant(value,keywords)
	#input is a list
    elif isinstance(datacr, list):
        for itemcr in datacr:
            find_croustillant(itemcr,keywords)

def get_unique_dicts(list):
    # Ensure each dictionary is converted to a frozenset of its items, which is hashable and can be used in a set.
    unique_dicts = set(frozenset(d.items()) for d in list)

    # Convert frozensets back to dictionaries and store them in authlistnodoublon.
    output = [dict(d) for d in unique_dicts]

    return output

def main():

    baseUrl          = 'https://www.postman.com/'
    urlProxy         = baseUrl+'_api/ws/proxy'
    urlenvapi        = baseUrl+'_api/environment/'
    urlrequest       = baseUrl+'_api/request/'
    urlApiCollection = baseUrl+'_api/collection/'
    urlApiFolder     = baseUrl+'_api/folder/'

    urlsWorkspaces = []
    urlsteam = []

    parser = argparse.ArgumentParser(description='Postman OSINT tool to extract creds, token, username, email & more from Postman Public Workspaces')
    parser.add_argument('query', type=str, help='name of the target (example: tesla)')
    parser.add_argument('maxresults', type=int, help='max number of results',default=100, nargs='?')

    args = parser.parse_args()
    print("\nScan report for " + f"{args.query}")

    #Read the keywords from the file
    with open('keywords.txt', 'r') as file:
        keywords = [line.strip() for line in file]

    # List of user agents
    with open('useragents.txt', 'r') as file:
        user_agents = [line.strip() for line in file]
    # Choose a random user agent
    random_user_agent = random.choice(user_agents)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:102.0) Gecko/20100101 Firefox/102.0',
        'Content-Type': 'application/json',
    }
    size=100
    pages=1
    if args.maxresults > 100:
        pages=(args.maxresults // 100) + (1 if args.maxresults % 100 != 0 else 0)
    if args.maxresults < 100:
        size=args.maxresults
    data_raw = {
        "service": "search",
        "method": "POST",
        "path": "/search-all",
        "body": {
            "queryIndices": ["collaboration.workspace", "runtime.collection", "runtime.request", "adp.api", "flow.flow",
                             "apinetwork.team"],
            "queryText": f"{args.query}",
            "size": size,
            "from": 0,
            "requestOrigin": "srp",
            "mergeEntities": True,
            "nonNestedRequests": True
        }
    }

    for i in range(pages):
        try:
            remaining_results = args.maxresults - (i * 100)
            data_raw["body"]["size"] = min(remaining_results,100)
            response = requests.post(urlProxy, headers=headers, json=data_raw)
            response.raise_for_status()  # Raise an HTTPError for bad responses (4xx and 5xx)
            data = response.json()  # Parse JSON response if needed
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            sys.exit(1)
        except requests.exceptions.ConnectionError as conn_err:
            print(f"Connection error occurred: {conn_err}")
            sys.exit(1)
        except requests.exceptions.Timeout as timeout_err:
            print(f"Timeout error occurred: {timeout_err}")
            sys.exit(1)

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

        responseid = requests.post(urlProxy, headers=headers, json=data_rawid)
        iddiv = responseid.json()

        if 'error' in iddiv:
            continue

        idwork = iddiv['data'][0]['id']

        data_raw = {
            "service": "workspaces",
            "method": "GET",
            "path": f"/workspaces/{idwork}?include=elements"
        }
        #get Collection
        responsedisco = requests.post(urlProxy, headers=headers, json=data_raw)
        all_uuid = responsedisco.json()

        if 'collections' in all_uuid['data']['elements']:
            urlcollec = all_uuid['data']['elements']['collections']
        else:
            urlcollec = []
        for urlc in urlcollec:
            listeallcollec.append(urlc)

        print(Fore.GREEN + str(len(listeallcollec)) +" Collections found" + Style.RESET_ALL)
        # Print each Collection with line numbers
        for i, urlc in enumerate(listeallcollec, start=1):
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
             # Check if 'data' key exists in the JSON response
            if 'data' in environment:
                nameenv = environment['data']['name']
                env = environment['data']['values']
                #print(f"Environment name: {nameenv}")
            else:
                print("Key 'data' not found in API response.")
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

    #scanning every collection
    for p, coll in enumerate(listeallcollec, start=1):
        print(f'\nScan of collection {coll} [{p}/{len(listeallcollec)}]\n')
        segments = coll.split('/')
        idseg = segments[-1]
        urltrueapi = urlApiCollection + idseg

        #getRequest
        responsecoll = requests.get(urltrueapi, headers=headers)
        collection = responsecoll.json()
        #print(collection)

        owner = collection['data']['owner']
        order = collection['data']['order']
        name = collection['data']['name']
        desc = collection['data']['description']
        print(f"{name}, {desc}")

        #folders of a collection
        folders_order = collection['data']['folders_order']        

        for orde in folders_order:
            urlsubord = urlApiFolder + owner + "-" + orde
            responsesub = requests.get(urlsubord, headers=headers)
            subcollection = responsesub.json()
            print(subcollection)
            if 'error' in subcollection:
                continue
            suborder = subcollection['data']['order']
            folderName = subcollection['data']['name']
            folderDesc = subcollection['data']['description']
            folderVars = subcollection['data']['variables']
            folderAuth = subcollection['data']['auth']
            folderCreated = subcollection['data']['createdAt']
            folderUpdated = subcollection['data']['updatedAt']
            print(f"{folderName},{folderDesc}")

            #finding subfolders (recursive)
            subsubfolders = subcollection['data']['folders_order']
            if len(subsubfolders) != 0:
                for subsubfolder in subsubfolders:
                    urlsubsubord = urlApiFolder + owner + "-" + subsubfolder
                    responsesubsub = requests.get(urlsubsubord, headers=headers)
                    print(responsesubsub)
                    subsubcollection = responsesubsub.json()
                    subsuborder = subsubcollection['data']['order']
                    order.extend(subsuborder)
            else:
                pass
            order.extend(suborder)

        reqtrouv += len(order)  
        print(Fore.GREEN + str(reqtrouv) + " Scanned requests: " + Style.RESET_ALL+"\n")

        pattern = re.compile(r'^\{\{.*\}\}$')
    
        #Requests per folder
        for request in order:
            urlrequestfull = urlrequest + owner + "-" + request
            print(urlrequestfull)

            requestresponse = requests.get(urlrequestfull, headers=headers)

            requestresp = requestresponse.json()
            urlreq = requestresp['data']['url']
            method = requestresp['data']['method']
            data = requestresp['data']['data']
            description = requestresp['data']['description']
            preRequestScript = requestresp['data']['preRequestScript']
            #how to get pre and post scripts?
            auth = requestresp['data']['auth']1
            header = requestresp['data']['headerData']
            pattern = re.compile(r'^\{\{.*\}\}$')
            datamode = requestresp['data']['dataMode']
            #removing values like {{..}}
            filtered_header_data = [item for item in header if
                                    item['key'] not in ['Content-Type', 'Accept', 'x-api-error-detail','x-api-appid'] and not pattern.match(item['value']) and item['value']]
            #Auth
            if auth is not None:
                authlist.append(auth)
            if filtered_header_data:
                headerlist.append(filtered_header_data)
            #body params
            if datamode == "raw":
                body1 = requestresp['data']['rawModeData']
                #checking for keys in body
                try:
                    if body1 is not None and body1.strip():
                        parsed_data = json.loads(body1)
                        find_croustillant(parsed_data,keywords)
                    else:
                        pass
                except json.JSONDecodeError as e:
                    continue
            #more modes for body (form-data, x-www-form-urlencoded, raw, binary)
            #datamode params
            if datamode == "params" and requestresp['data']['data'] is not None and len(requestresp['data']["data"]) > 0:
                datas = requestresp['data']["data"]
                for nom in datas:
                     if nom['key'] in keywords:
                        bodylist.append(nom['value'])

    authlistUnique = []
    authlistUnique = get_unique_dicts(authlist)
    print(Fore.RED + str(len(authlistUnique)) + " Auth token ​​found" + Style.RESET_ALL)

    headerlistUnique = []
    headerlistUnique= get_unique_dicts(headerlist)
    print(Fore.RED + str(len(headerlistUnique)) + " Intersting values in headers" + Style.RESET_ALL)

    bodylistUnique = []
    bodylistUnique = get_unique_dicts(bodylist)    
    print(Fore.RED + str(len(bodylistUnique)) + " Intersting values in bodies" + Style.RESET_ALL)

if __name__ == '__main__':
    main()
