# postmaniaco

Based on https://github.com/boringthegod/postmaniac 

## Description

Postman OSINT tool to **extract creds, token, username, email & more from Postman Public Workspaces**.

The idea is to extract and show data and not to automatically detect sensitive information. For that you can use another tools.  

The main objective is to able to show and extract all data related to a workspace and children:

**Workspace**
- **Workspace vars**
- **Environment vars**
  - **Collections**
    - **Folder**
      - **Subfolder (optional)**
        - **Requests**
          - Overview
          - Params
          - Authorization
            - Basic Auth
            - Bearer Token
            - JWT Bearer
            - Digest Auth
            - OAuth 1.0
            - OAuth 2.0
            - Hawk Authentication
            - AWS Signature
            - NTLM Authentication
            - API Key
            - Akamai EdgeGrid
            - ASAP (Atlassian)
          - Headers
          - **Body**
            - form-data
            - x-www-form-urlencoded
            - raw
            - binary
            - GraphQL
          - **Scripts**
            - Pre-Req
            - Post-Req


        
Also including Teams but this might be removed. 

## Usage

`python3 postmaniac keyword`

[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.fr.html)
