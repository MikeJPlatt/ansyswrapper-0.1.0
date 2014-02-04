"""Holds info about how to use ANSYS Classic Structural."""

#Information about input variables of an OpenMDAO ANSYS Component
# %N% is name of component, %V% is value
# keys much match those in AnsysUnitsInfo
surfaceinputtypes = { 
    'PRESS_i' : ['sfa,%N%,1,pres,%V%', 'pressure'],
#    'TEMP_i'  : ['da,%N%,temp,%V%', 'temperature']
    }
keypointinputtypes = {
    'FX_i' : ['fk,%N%,fx,%V%', 'force'],
    'FY_i' : ['fk,%N%,fy,%V%', 'force'],
    'FZ_i' : ['fk,%N%,fz,%V%', 'force'],
    'TEMP_i' : ['dk,%N%,all,%V%', 'temperature'],
    'UX_i' : ['dk,%N%,ux,%V%', 'length'],
    'UY_i' : ['dk,%N%,uy,%V%', 'length'],
    'UZ_i' : ['dk,%N%,uz,%V%', 'length']
    }
nodeinputtypes = {
    'FX_i' : ['f,%N%,fx,%V%','force'],
    'FY_i' : ['f,%N%,fy,%V%','force'],
    'FZ_i' : ['f,%N%,fz,%V%','force'],
    'TEMP_i' : ['d,%N%,all,%V%', 'temperature'],
    'UX_i' : ['d,%N%,ux,%V%', 'length'],
    'UY_i' : ['d,%N%,uy,%V%', 'length'],
    'UZ_i' : ['d,%N%,uz,%V%', 'length']
    }
coordinputtypes  = { # for applying deflection at individual nodes
    'UX_i' : ['d,%N%,ux,%V%', 'length'],
    'UY_i' : ['d,%N%,uy,%V%', 'length'],
    'UZ_i' : ['d,%N%,uz,%V%', 'length']
    }
globalinputtypes = {
    'omega_Z' : ['OMEGA,,,%V%','speed'],
    'temp_ref' : ['TREF,%V%','temperature'],
    'temp_unif' : ['TUNIF,%V%','temperature']
    }
# if any items are added to globalinputtypes, their initial_ parameters should be added to ansysWrapperGenerator __init__

#TO_CHECK: complete above, and add nodeinputtypes

#Information about output variables of an OpenMDAO ANSYS Component
# values must  match those in AnsysUnitsInfo
outputtypes = {'number': '',
               'UX_o': 'length', 'UY_o': 'length', 'UZ_o': 'length','UR_o': 'length',
               'TEMP_o': 'temperature',
               'FX_o': 'force', 'FY_o': 'force', 'FZ_o': 'force'}
calctypes = ['max', 'min', 'avg']

#Information about unit strings
class AnsysUnitsInfo:
    """Information about units used in ANSYS."""
    info = {} # empty dictionary
    def __init__(self, length = 'm', mass = 'kg', time = 's',
                 temperature = 'degK', speed = 'rad/s', ok = True):
        self.ok = ok
        if self.ok:
            self.info['length'] = length
            self.info['mass'] = mass
            self.info['time'] = time
            self.info['temperature'] = temperature
            self.info['speed'] = speed
            self.info['force'] = \
                '(' + self.info['length'] + '*' + self.info['mass'] + ')/(' + \
                self.info['time'] + '**2)'
            self.info['pressure'] = '(' + self.info['mass'] + ')/(' + \
                self.info['length'] + '**2)'
            self.info['heat'] = '(' + self.info['force'] + ')*(' + \
                self.info['length'] + ')'
    def dump(self, prefix = ''):
        s = prefix + 'AnsysUnitsInfo'
        p2 = prefix + '   '
        if self.ok:
            s = s + ' ok\n'
        else:
            s = s + ' NOT ok\n' + p2
        for k, v in self.info.iteritems():
            s = s + p2 + k + ': ' + v + '\n'
        return s


unitsindices = {
    'default' : '-1',
    'USER' : '0',
    'SI' : '1',
    'MKS' : '5',
    'uMKS' : '7',
    'CGS' : '2',
    'MPA' : '6',
    'BFT' : '3',
    'BIN' : '4',
    }
unitsinfodict = {} #empty dictionary
unitsinfodict[unitsindices['default']] = AnsysUnitsInfo() # default
# user, which we can't handle
unitsinfodict[unitsindices['USER']] = AnsysUnitsInfo(ok = False)
unitsinfodict[unitsindices['SI']] = AnsysUnitsInfo()
unitsinfodict[unitsindices['MKS']] = AnsysUnitsInfo(temperature = 'degC')
unitsinfodict[unitsindices['uMKS']] = AnsysUnitsInfo(length = 'um',
    temperature = 'degC')
unitsinfodict[unitsindices['CGS']] = AnsysUnitsInfo(length = 'cm', mass = 'g',
    temperature = 'degC')
unitsinfodict[unitsindices['MPA']] = AnsysUnitsInfo(length = 'mm', mass = 'Mg',
    temperature = 'degC')
unitsinfodict[unitsindices['BFT']] = AnsysUnitsInfo(length = 'ft',
    mass = 'slug', temperature = 'degF')
unitsinfodict[unitsindices['BIN']] = AnsysUnitsInfo(length = 'inch',
    mass = 'lbm', temperature = 'degF') #TO_CHECK:  check if mass is correct

def dump_unitsinfodict():
    s = 'unitsinfodict:\n'
    for k, v in unitsinfodict.iteritems():
        s = s + '   ' + k + ':\n' + v.dump('      ') + '\n'
    return s

#Utility functions
def _make_name(name, extension):
    return name + '_' + extension
