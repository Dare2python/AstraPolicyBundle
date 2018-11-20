'''
Created on Nov 19, 2018

@author: sk607s
'''

import glob
import subprocess
import sys

# # This uses ordereddict that preserve YAML order.

import ruamel.yaml

yaml = ruamel.yaml.YAML()


def loadConfig(configYamlFile):
    # # Using a Yaml config file
    # # Awkward accessing teh values, there must be a better mechanism.    
    with open(configYamlFile, 'r') as configfile:
        config = yaml.load(configfile)
    return config


def main():
    config = loadConfig("config.yaml")

    baremetal = config['files']['BAREMETAL_SITE_FILE_DIRECTORY']
    sites_dir = baremetal[:baremetal.find('SITENAME')]

    print(sites_dir)

    for site in glob.iglob(sites_dir + '*'):
        name = site[site.rfind('/')+1:].strip()
        print(name)
        try:
            subprocess.call(["python", "SitePolicyMgr.py", "-s", name])
        except OSError as e:
            print("Execution failed:", e, file=sys.stderr)



if __name__ == '__main__':
    main()
