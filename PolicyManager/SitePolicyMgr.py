'''
Created on Nov 5, 2018

@author: rp2723
'''

import glob
import os
import sys, getopt
from pathlib import Path

# # This uses ordereddict that preserve YAML order.

import ruamel.yaml
from ruamel.yaml.compat import text_type, binary_type

yaml = ruamel.yaml.YAML()
sitename = ''


class NoAliasDumper(ruamel.yaml.Representer):
    def ignore_aliases(self, data):
        # type: (Any) -> bool
        # https://docs.python.org/3/reference/expressions.html#parenthesized-forms :
        # "i.e. two occurrences of the empty tuple may or may not yield the same object"
        # so "data is ()" should not be used
        if data is None or (isinstance(data, tuple) and data == ()):
            return True
        if isinstance(data, (binary_type, text_type, bool, int, float)):
            return True
        return False


def loadConfig(configYamlFile):
    # # Using a Yaml config file
    # # Awkward accessing teh values, there must be a better mechanism.    
    with open(configYamlFile, 'r') as configfile:
        config = yaml.load(configfile)
    configfile.close()
    return config


def useSite(aString, sitename):
    return aString.replace("SITENAME", sitename)


def getBaremetal(sitename, config):
    # get HostEndpoint YAML file
    baremetalSiteDir = useSite(config['files']['BAREMETAL_SITE_FILE_DIRECTORY'], sitename)

    baremetalYamlList = []
    for baremetalFile in glob.glob(baremetalSiteDir + "/*.yaml"):
        # print('baremetalFile',baremetalFile)
        # Each file can contain multiple entries
        with open(baremetalFile, "r") as bmFile:
            baremetalYamlList.append(list(yaml.load_all(bmFile)))
        bmFile.close()

    return baremetalYamlList


def getFromYamlFile(templateFile):
    # get HostEndpoint YAML file
    templateYamlFile = templateFile

    with open(templateYamlFile) as aYamlFile:
        aYaml = yaml.load(aYamlFile)
    aYamlFile.close()

    return aYaml


def getFromYamlsFiles(templateFile):
    # get HostEndpoint YAML file
    templateYamlFile = templateFile
    aYamlList = []
    with open(templateYamlFile) as aYamlFile:
        aYamlList.append(list(yaml.load_all(aYamlFile)))
    aYamlFile.close()

    return aYamlList


#
# TODO
# 
# Find HostProfile name at
#     Site level, at  aic-clcp-site-manifests/site/SITENAME/profiles/host
#     or 
#    Global level aic-clcp-manifests/global/v4.0/profiles/host
#
# Then within teh profile
#     Iterate through dtaa.interfaces , and see if teh networkName is in the list of networks for an interface.
def getInterfaceName(sitename, config, hostProfile, networkName):
    # get HostEndpoint YAML file
    siteProfileDir = useSite(config['files']['PROFILES_SITE_DIRECTORY'], sitename)
    #
    # At the site level there might be a single file with multiple yamls
    for profileFile in glob.glob(siteProfileDir + "/*.yaml"):
        profileFileSet = getFromYamlsFiles(profileFile)
        for profileFiles in profileFileSet:
            for profile in profileFiles:
                for interface in profile['data']['interfaces']:
                    if networkName in profile['data']['interfaces'][interface]['networks']:
                        return interface

    # At the global level the file will be a single one using the name of the hostprofile
    globalProfileDir = useSite(config['files']['PROFILES_GLOBAL_DIRECTORY'], sitename)
    for profileFile in glob.glob(globalProfileDir + "/" + hostProfile + ".yaml"):
        profile = getFromYamlFile(profileFile)
        for interface in profile['data']['interfaces']:
            if networkName in profile['data']['interfaces'][interface]['networks']:
                return interface

    return 'oam'


# Convention is to use
# Labels
#    host :
#        with possible values of  'nc-control', 'nc-compute' }
#    intf-alias:
#        with value been the interface or network name i.e 'oam'
def addLabels(hostendpoint, baremetalTags, intfName):
    if 'workers' in baremetalTags:
        hostendpoint['metadata']['labels'].insert(len(hostendpoint['metadata']['labels']), 'host', 'nc-compute')
        # hostendpoint['metadata']['labels']['host']='nc-compute'
    if 'masters' in baremetalTags:
        hostendpoint['metadata']['labels'].insert(len(hostendpoint['metadata']['labels']), 'host', 'nc-control')
        # hostendpoint['metadata']['labels']['host'] = 'nc-control'
    # hostendpoint['metadata']['labels']['intf-alias']=intfName
    hostendpoint['metadata']['labels'].insert(len(hostendpoint['metadata']['labels']), 'intf-alias', intfName)


def getHostEndpointDir(sitename, config):
    hostendpointDir = useSite(config['files']['POLICY_SITE_FILE_DIRECTORY'], sitename)
    try:
        heDirPath = Path(hostendpointDir)
        if not heDirPath.exists() or not heDirPath.is_dir():
            os.makedirs(hostendpointDir)
    except OSError:
        print("Creation of the directory %s failed" % hostendpointDir)
    return hostendpointDir


def main(argv):
    config = loadConfig("config.yaml")

    try:
        opts, args = getopt.getopt(argv, "hs:", ["site="])
    except getopt.GetoptError:
        print('HostEndpointMgr.py -s <siteName>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('HostEndpointMgr.py -s <siteName>')
            sys.exit()
        elif opt in ("-s", "--site"):
            sitename = arg

    policies = getFromYamlFile(config['files']['policiesYamlFile'])
    hostendpoint = getFromYamlFile(config['files']['hostendpointYamlFile'])

    # yaml.dump(hostendpoint, sys.stdout)

    """
    kind: HostEndpoint
    metadata:
      name: some.name
      labels: {}
    spec:
      interfaceName: some.name
      node: some.name
      expectedIPs: []
    """
    hostendpointDir = getHostEndpointDir(sitename, config)

    with open(hostendpointDir + '/' + config['files']['POLICIES_SITE_FILE'], 'w') as policiesFile:
        baremetalFileSet = getBaremetal(sitename, config)

        # Lets put all teh HostEnd points in a single file
        #
        # For some reason I have a list of lists at this point
        # rules=[]
        for baremetalFiles in baremetalFileSet:
            for baremetalFile in baremetalFiles:
                if baremetalFile['schema'] == config['intentions']['baremetalSchema']:
                    # print('name', baremetalFile['metadata']['name'])

                    for networkPair in baremetalFile['data']['addressing']:
                        if networkPair['network'] in config['intentions']['baremetalInterfaces']:
                            # print('host_profile',baremetalFile['data']['host_profile'])
                            intfName = getInterfaceName(sitename, config, baremetalFile['data']['host_profile'],
                                                        networkPair['network'])
                            # print('addressing', 'network',networkPair['network'],'address',networkPair['address'])

                            # name of the Artifact is a Convention hostname-interfaceName
                            hostendpoint['metadata']['name'] = baremetalFile['metadata']['name'] + '-' + networkPair[
                                'network']
                            hostendpoint['spec']['interfaceName'] = intfName
                            hostendpoint['spec']['expectedIPs'] = [networkPair['address']]
                            hostendpoint['spec']['node'] = baremetalFile['metadata']['name']

                            # the labels will depend on the Tags
                            # Assumption that networkPair['network'] maps properly to intf name, it does for OAM
                            addLabels(hostendpoint, baremetalFile['data']['metadata']['tags'], networkPair['network'])

                            # Here is where we would write the HostEndPointFile yaml to the rules

                            # pos = len(policies['data']['policy']['hostendpoints']['rules'])
                            # rules.append(hostendpoint)
                            # yaml.dump(hostendpoint, sys.stdout)
                            policies['data']['policy']['hostendpoints']['rules'].append(hostendpoint)
                            # policies['data']['policy']['hostendpoints']['rules'][hostendpoint['spec']['node']]
                            # = hostendpoint
                            # yaml.Representer = NoAliasDumper
                            # yaml.dump(policies, sys.stdout)

        yaml.explicit_start = True
        yaml.explicit_end = True
        yaml.dump(policies, policiesFile)
        policiesFile.close()


# # Given a Site
# # Use Baremetal files to identify the Servers and Generate teh HostEndpoint Artifacts
# # Which should be generated in the 
if __name__ == '__main__':
    main(sys.argv[1:])
