'''
Created on Nov 1, 2018

@author: rp2723
@author: sk607s
'''

import glob
import os
import sys

from pathlib import Path

# This uses ordereddict that preserve YAML order.
from ruamel.yaml import YAML


## This version will essentially just add the Policy attribute to an existsing corridor file if it exists
# Otherwise it will create a new Corridor file
#
#  These implies  no impacts on teh site level corridor.yaml, otherwise with separate corridor files it will create 
# a Divergence

# I think the only difference will be :
# If the File Does not exit
#     Use the CorridorTemplate only for New file case
#     Set the name
#     Set the Corridor Number
# If the file exists 
#     Use the Appropriate mapping corridor file name form the target repo
#    Add the policy element if its not there
#     If the Policy element exists replace the whole thing. No partial policy updates.

## Rely on ruamel YAML
yaml = YAML()


def getCorridorNumber(cName):
    if cName is None:
        return '0'
    elif cName == 'production':
        return '5'
    else:
        return str(cName[-1])


def getTargetCorridorName(cRepoName):
    if cRepoName is None:
        return 'corridor-1'
    elif cRepoName == 'production':
        return 'production'
    else:
        return cRepoName[0:len(cRepoName) - 1] + '-' + cRepoName[-1]


def initYamlFile(cName):
    ## Check if it exists 
    corridorYamlFile = Path(config['files']['CORRIDOR_FILE_DIRECTORY'] + '/' + cName + '.yaml')
    corridorPolicyYamlFile = None
    if corridorYamlFile.exists() and corridorYamlFile.is_file():
    
        ## use the existing file
        corridorPolicyYamlFile = config['files']['CORRIDOR_FILE_DIRECTORY'] + '/' + cName + '.yaml'
        with open(corridorPolicyYamlFile) as policyYamlFile:
            l_corridor = yaml.load(policyYamlFile)
        
        # print ('corridorDirPath.exists()',yaml.dump(corridor, sys.stdout))
        ## If policy is there this is  nothing, since these is an ordered dict, and it cleans it up    
        ## Do not Need to check if the files already has a policy object
        l_corridor['data'].insert(len(l_corridor['data']), key='policy', value={'astra': {'priority': 0, 'rules': []}})
    else:
        # # Brand new file
        #  theoretically these should not be used and its creating a default policy of rules if we
        #  decide on using it instead # of the Calico failsafe rules
        #  In that case we need to add the placeholder
        #  and the rules above as well.
        corridorPolicyYamlFile = config['files']['corridorPolicyYamlFile']
        with open(corridorPolicyYamlFile) as policyYamlFile:
            l_corridor = yaml.load(policyYamlFile)
            
        # Give the Yaml file a name
        l_corridor['metadata']['name'] = cName
        
        # Deal with the corridor  number 
        l_corridor['metadata']['labels']['corridor'] = getCorridorNumber(cName)
        
        print('!corridorDirPath.exists()')
        print(yaml.dump(l_corridor, sys.stdout))
        
    policyYamlFile.close()  
    
    return l_corridor


## BlackList file that need Site Level replacement
### @@TODO need to identify if there is anything and what the criteria is
def isSiteLevelPolicy(policyAsString):
    return False


def addAstraPolicyRules(c, cName, cPolicyRepoDirName):
    # Prepare the Output File
    with open(config['files']['CORRIDOR_FILE_DIRECTORY']+'/'+cName+'.yaml', 'w') as corridorFile:

        for afile in glob.glob(cPolicyRepoDirName + '/*.yaml'):
            
            with open(afile, "r") as policyFile:
                ## Remove the ---
                policyFile.readline()
                
                ## Need to change  the file contents so that
                ## /n are newlines, and its not a enclosed in "
                cleanString = ''
                for line in policyFile.readlines():
                    cleanString += ''.join(line.replace('"', '').replace('\\', ''))

                if not isSiteLevelPolicy(cleanString):
                    c['data']['policy'][config['intentions']['corridorPolicyName']]['rules'].append(cleanString)
                else:
                    ## Not sure what to do with  them if Any exists
                    ##
                    pass
            policyFile.close()
        
        ## Needs this values for the dump to add the YAML file separators.
        yaml.explicit_start = True
        yaml.explicit_end = True                
        yaml.dump(c, corridorFile)
    corridorFile.close()    


def loadConfig(configYamlFile):
    ## Using a Yaml config file
    ## Awkward accessing the values, there must be a better mechanism.
    with open(configYamlFile, 'r') as configfile:
        l_config = yaml.load(configfile)
    configfile.close()
    return l_config


if __name__ == '__main__':

    config = loadConfig("config.yaml")
    ## List of Corridors
    ## 
    for corridorRepoName in config['intentions']['corridorNames']:
        
        ## Get the Corridor Yaml file name
        corridorPolicyRepoDirName = glob.glob(config['files']['GIT_REPO_PATH']+"/*"+corridorRepoName+"*")
        
        ## Extract the Corridor name form the Repo name, doesn't quite use the same convention
        corridorName = getTargetCorridorName(corridorRepoName)        
                
        corridor = initYamlFile(corridorName)
 
        addAstraPolicyRules(corridor, corridorName, corridorPolicyRepoDirName[0])
