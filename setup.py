#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

requirements = [x.strip() for x in open("requirements.txt", "r").readlines()]
requirements = [
    f"{line.split('#egg=')[-1]} @ {line}" if "#egg=" in line else line for line in requirements]

setup(
    name='postmaniac',
    version='1.0.0',
    packages=find_packages(),
    license='GNU General Public License v3 (GPLv3)',
    license_files=('LICENSE.md'),
    author='boringthegod',
    author_email='boringthegod@tutanota.com',
    description='Postman OSINT tool to extract creds, token, username, email & more from Postman Public Workspaces.',
    url='https://github.com/boringthegod/postmaniac',
    keywords=["osint", "pentest", "cybersecurity",
              "investigation", "lespireshat", "postman"],
    entry_points={
        'console_scripts': [
            'postmaniac=postmaniac.postmaniac:main'
        ]
    },
    install_requires=requirements
)
