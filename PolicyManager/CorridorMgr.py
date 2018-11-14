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


def getCorridorNumber(corridorName):
    if (corridorName is None):
        return '0'
    elif (corridorName == 'production'):
        return '5'
    else:
        return str(corridorName[-1])


def getTargetCorridorName(corridorRepoName):
    if (corridorRepoName is None):
        return 'corridor-1'
    elif (corridorRepoName == 'production'):
        return 'production'
    else:
        return corridorRepoName[0:len(corridorRepoName)-1] + '-' + corridorRepoName[-1]


def initYamlFile(corridorName):
    ## Check if it exists 
    corridorYamlFile = Path(config['files']['CORRIDOR_FILE_DIRECTORY']+'/'+corridorName+'.yaml')
    corridorPolicyYamlFile = None
    if (corridorYamlFile.exists() and corridorYamlFile.is_file()):
    
        ## use the existing file
        corridorPolicyYamlFile = config['files']['CORRIDOR_FILE_DIRECTORY']+'/'+corridorName+'.yaml'
        with open(corridorPolicyYamlFile) as policyYamlFile:
            corridor=yaml.load(policyYamlFile)
        
        #print ('corridorDirPath.exists()',yaml.dump(corridor, sys.stdout))
        ## If policy is there this is  nothing, since these is an ordered dict, and it cleans it up    
        ## Do not Need to check if the files already has a policy object
        corridor['data'].insert(len(corridor['data']),key='policy',value={'astra':{'priority': 0,'rules': []}})
    else:
        ## Brand new file
        ## theoritically these should not  be used and its creating a default policy of rules if we decide on using it instead
        ## of teh Calico failsafe rules
        ## In that case we need to add the plaeholder and teh rules above as well.
        corridorPolicyYamlFile = config['files']['corridorPolicyYamlFile']
        with open(corridorPolicyYamlFile) as policyYamlFile:
            corridor=yaml.load(policyYamlFile)
            
        # Give the Yaml file a name
        corridor['metadata']['name'] = corridorName
        
        # Deal with the corridor  number 
        corridor['metadata']['labels']['corridor']= getCorridorNumber(corridorName)
        
        print ('!corridorDirPath.exists()')
        print(yaml.dump(corridor, sys.stdout))
        
    policyYamlFile.close()  
    
    return corridor


## BlackList file that need Site Level replacement
### @@TODO need to identify if tehre is anything and what the criteria is
def isSiteLevelPolicy(policyAsString):
    return False


def addAstraPolicyRules(corridorName, corridorPolicyRepoDirName) :
    # Prepare the Output File
    with open(config['files']['CORRIDOR_FILE_DIRECTORY']+'/'+corridorName+'.yaml','w') as corridorFile: 

        for afile in glob.glob(corridorPolicyRepoDirName + '/*.yaml'):
            
            with open(afile, "r") as  policyFile: 
                ## Remove the ---
                policyFile.readline()
                
                ## Need to change  the file contents so that
                ## /n are newlines, and its not a enclosed in "
                cleanString=''
                for line in policyFile.readlines():
                    cleanString += ''.join(line.replace('"','').replace('\\',''))

                if (not isSiteLevelPolicy(cleanString)):
                    corridor['data']['policy'][config['intentions']['corridorPolicyName']]['rules'].append(cleanString)
                else:
                    ## Not sure what to do with  them if Any exists
                    ##
                    pass
            policyFile.close()
        
        ## Needs this values for the dump to add the YAML file separators.
        yaml.explicit_start = True
        yaml.explicit_end = True                
        yaml.dump(corridor,corridorFile)
    corridorFile.close()    


def loadConfig(configYamlFile):
    ## Using a Yaml config file
    ## Awkward accessing teh values, there must be a better mechanism.    
    with open(configYamlFile, 'r') as configfile:
        config = yaml.load(configfile)
    configfile.close()
    return config


if __name__ == '__main__':

    config = loadConfig("config.yaml")
    ## List of Corridors
    ## 
    for corridorRepoName in config['intentions']['corridorNames']:
        
        ## Get the Corridor Yaml file name
        corridorPolicyRepoDirName = glob.glob(config['files']['GIT_REPO_PATH']+"/*"+corridorRepoName+"*")
        
        ## Extract the Corridor name form teh Repo name, doesnt quite us ethe same convention
        corridorName = getTargetCorridorName(corridorRepoName)        
                
        corridor = initYamlFile(corridorName)
 
        addAstraPolicyRules(corridorName, corridorPolicyRepoDirName[0])
