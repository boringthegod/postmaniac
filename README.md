# postmaniac

![](assets/long_banner.png)

# Description

Postman OSINT tool to **extract creds, token, username, email & more from Postman Public Workspaces**.

It is designed to perform OSINT recognition on a target for pentesting, bugbounty and more, in order to get the maximum information from the requests left by developers on the Postman public workspaces.

Bonus:

- No need to be authenticated

- No API blocking / No rate-limit

# Requirements

[Python 3](https://www.python.org/download/releases/3.0/)

# Installation

### With PyPI

`pip3 install postmaniac`

### With Github

```bash
# clone the repo
$ git clone https://github.com/boringthegod/postmaniac.git

# change the working directory to postmaniac
$ cd postmaniac

# install postmaniac
$ python3 setup.py install
```

### With Docker

You can pull the Docker image with:

```bash
docker pull ghcr.io/boringthegod/postmaniac:latest
```

And then launch the tool **by not forgetting to specify your volume** to be able to read the file scan.txt written in output

`docker run -v scan:/output ghcr.io/boringthegod/postmaniac query`

# Usage

postmaniac can be run from the CLI and rapidly embedded within existing python applications.

```bash
usage: postmaniac [-h] query

Postman OSINT tool to extract creds, token, username, email & more from Postman Public Workspaces

positional arguments:
  query       name of the target (example: tesla)

options:
  -h, --help  show this help message and exit
```

All the interesting information (whether in the environment values of the Postman Workspace, or in authentication values, in the headers or directly in the body of each request) is retrieved and **written in the scan.txt file**

## Demo

![](https://github.com/boringthegod/postmaniac/blob/master/assets/demo.gif)

# Details

## Disclaimer

This tool is for educational purposes only, I am not responsible for its use.

## License

[GNU General Public License v3.0](https://www.gnu.org/licenses/gpl-3.0.fr.html)
