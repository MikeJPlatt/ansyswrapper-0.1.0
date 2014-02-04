#-------------------------------------------------------------------------------
# Name:        ANSYS Wrapper Generator GUI
# Owner:       Mechanical Solutions Inc.
#
# Author:      Kyle Lavoie, Mechanical Solutions Inc.
#
# Created:     5/14/2013
# Copyright:   (c) Mechanical Solutions Inc.
#-------------------------------------------------------------------------------
import logging
import os
import subprocess
import sys
import time
import string

import ansysinfo

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import ConfigParser
from PyQt4 import QtCore, QtGui
from ui_ANSYS_Wrapper_Generator_3 import *
import openmdao.gui.filemanager

indent1 = '    '
indent2 = indent1 + indent1
indent3 = indent2 + indent1
indent4 = indent3 + indent1
indent5 = indent4 + indent1
indent6 = indent5 + indent1
triplequote = '"""'
CR = "'\\n'"




class MainDlg(QDialog, Ui_Dialog):

    def __init__(self, parent=None, logger_name = None):
        super(MainDlg, self).__init__(parent)
        self.__index = 0
        self.setupUi(self)
        # set initial values
        self.ansysFileDir.setText('C:/') 
        self.ansysFileName.setText('file.db')
        self.genWrapName.setText('file')
        self.ansysVer.setText('v14.5')
        self.logger_name = logger_name

    @pyqtSignature("")
    def on_generateWrap_clicked(self): 

        #Get Input Values
        self.ansysDir= str(self.ansysFileDir.text())
        self.ansysName = str(self.ansysFileName.text())
        self.wrapName = str(self.genWrapName.text())
        self.version = str(self.ansysVer.text())

        testdir = self.ansysDir + '/'

        #Build TestGen\TestOut directory if it dosent already exist
        genfolder = "TestGen"
        outfolder = "TestOut"
        beginpath = self.ansysDir
        firstpath = os.path.join(beginpath, genfolder)
        fullpath = os.path.join(firstpath, outfolder)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)

        #update ANSYS Version
        versionNum = ''.join(filter(lambda x : x.isdigit(), self.version))
        version = "ANSYS" + versionNum

        name = self.wrapName
        genfilename = testdir + 'TestGen/' + self.wrapName+ '.py'
        dbfile = testdir + self.ansysName 
        self.wg = WrapperGenerator(name, genfilename, dbfile, ANSYS_VER = version, logger_name = self.logger_name)
        self.wg.generate()         


    @pyqtSignature("")
    def on_dirBrowse_clicked(self):    

        path = QFileDialog.getExistingDirectory(self,
                                                "Make PyQt - Set Path", self.ansysFileDir.text())
        if path:
            self.ansysFileDir.setText(QDir.toNativeSeparators(path))

    @pyqtSignature("")
    def on_nameBrowse_clicked(self):    

        string = QString("")
        filter = "All (*)"

        qstr = QFileDialog.getOpenFileName(self, QString("Open File"), self.ansysFileDir.text(), QString("ANSYS (*.db)"));
        fileName = os.path.basename(str(qstr))
        self.ansysFileName.setText(fileName)

class WrapperGenerator:
    """Generates an OpenMDAO Wrapper for ANSYS Structural, based on info either
       in a generated component information file, or in the ANSYS db.  
       
       To use: initialize, then call generate().

       *Parameters*
       
           name: string
               Name used to identify the Wrapped Component.
               
            genfilename: string
                Full path to filename of the generate Wrapped Component.
                
            dbfile: string (optional)
                Full path to name of ANSYS Structural .db file.  Default ''.  One of dbfile and componentsfile MUST be set.
                
            componentsfile: string (optional)
                Full path to name of previously created components file for the ANSYS Structural Model.  Default ''.  
                One of dbfile and componentsfile MUST be set.
                
            ANSYS_VER: string (optional)
                ANSYS Version String. Default ANSYS145.
                
            model_file_ext: string (optional)
                File extension for the model file.  Default py.
                
            logger_name: string(optional)
                Name of an existing logging::logger to use, if any.  Default None.  If None, a logger will be created with an internal name.
                
            initial_values_dictionary: dictionary of string to float (optional)
                Values in the original Structural model of the items in ansysinfo globalinputtypes
       """
    ok = True
    components = {} #empty dictionary of dictionaries of node numbers
    prep7 = []
    solution = []
    post = []

    def __init__(self, name, genfilename, dbfile = '', componentsfile = '', ANSYS_VER = 'ANSYS145', model_file_ext = 'py', 
                 logger_name = None, initial_values_dictionary = {'omega_Z':0.0, 'temp_ref':0.0, 'temp_unif':0.0}):
        if logger_name == None:
            self.logger = logging.getLogger("MSI")
        else:
            self.logger = logging.getLogger(logger_name)
        if dbfile == '' and componentsfile == '':
            s = 'AnsysWrapperGenerator for ' + name + ': at least one of dbfile or componentsfile is required'
            print 'ERROR: ' + s
            self.logger.error(s)
            self.ok = False
            return
        self.genfilename = genfilename
        
        self.dbfile = dbfile
        self.componentsfile = componentsfile
        self.name = name
        self.classname = name + 'Wrapper'    
        self.ANSYS_VER = ANSYS_VER
        self.model_file_ext = model_file_ext
        self.initial_values_dictionary = initial_values_dictionary
        self.input_names = set([])
        self.output_names = set([])
        
    def get_model_file_name(self):
        return self.componentsfilebase + '.' + self.model_file_ext

    def _gen_componentsfile(self, path):
        cfile = ''
        try:
            ansysdir =  os.environ[self.ANSYS_VER + '_DIR']
        except KeyError as ke:
            s =  'Cannot find ' + self.ANSYS_VER + '_DIR in environment\n\t' + sys.exc_info()[0] + '\n\t' + str(ke)
            print 'ERROR: ' + s
            self.logger.error(s)            
            self.ok = False
            return cfile
        try:
            ansysdir2 = os.environ['ANSYS_SYSDIR']
        except KeyError as ke:
            s =  'Cannot find ANSYS_SYSDIR in environment\n\t' + sys.exc_info()[0] + '\n\t' + str(ke)
            print 'ERROR: ' + s
            self.logger.error(s)           
            self.ok = False
            return cfile

        ansys_exe = os.path.join(ansysdir, 'bin', ansysdir2, self.ANSYS_VER)
        dbname, dbext = os.path.splitext(self.dbfile)
        if len(dbext): dbext = dbext[1:]

        tempstr = 'tmp_' + time.strftime('%Y_%m_%d__%H_%M_%S')
        inputfile = tempstr + '_gen_comps.dat'
        self.componentsfilebase = 'c_' + tempstr
        try:
            f = open(inputfile, 'w')
            outfile = tempstr + '_ListComps.out'
            #import pdb; pdb.set_trace()
            f.write('/batch\n')
            f.write('/TITLE, List Components of ' + self.name + '\n')
            f.write('/prep7\n')
            f.write('NNAME = \'NODE\'\n')
            f.write('resume,' + dbname + ',' + dbext + '\n')
            f.write('CSYS, 1\n')
            f.write('/STATUS,UNITS\n')
            f.write('*get,units,ACTIVE,0,UNITS\n')
            f.write('*get,nComps,COMP,,ncomp\n')
            f.write('/STATUS,GLOBAL\n')
            f.write('*cfopen,' + self.componentsfilebase + ',' + self.model_file_ext + ',, \n')
            f.write('*vwrite\n')
            f.write('class FeaModelInPythonFormat:\n')
            f.write('*vwrite\n')
            f.write('	def __init__(self):\n')
            f.write('*vwrite\n')
            f.write('		self.nodeLabels = ["number", "x", "y", "z",]\n')
            f.write('*vwrite, units\n')
            f.write('		self.units = %I\n')
            f.write('*vwrite\n')
            f.write('		self.coordinateSystem = "Cartesian"\n')
            f.write('*vwrite\n')
            f.write('		self.smoothingCoordinates = "XYZ"\n')
            f.write('*vwrite\n')
            f.write('		self.nodeMap = {\n')
            f.write('i = 1\n')
            f.write('! one DO loop to fill up the node map\n')
            f.write('*do,i,1,nComps,1\n')
            f.write('	*get,compName,comp,i,name		! get the name of the nth component\n')
            f.write('	*get,nType,comp,compName,type	! get the type #\n')
            f.write('					! 1=Nodes, 2=Elements, 6=Keypoints, 7=Lines, 8=Areas, 9=Volumes\n')
            f.write('	 ! first, print out all of the nodes\n')
            f.write(' ! node components\n')
            f.write('    *if,nType,eq,1,then\n')
            f.write('         allsel\n')
            f.write('        cmsel,,compName\n')
            f.write('        ! keypoint components\n')
            f.write('    *elseif,nType,eq,6,then\n')
            f.write('        allsel\n')
            f.write('        cmsel,,compName\n')
            f.write('        nslk,S\n')
            f.write('    *elseif,nType,eq,8,then\n')
            f.write('        allsel\n')
            f.write('        cmsel,,compName\n')
            f.write('        nsla,s,1\n')
            f.write('    *endif\n')
            f.write('    ! start writing the nodes\n')
            f.write('    *get,nCount,node,,count ! Get total number of selected nodes\n')
            f.write('    *vwrite, compName\n')
            f.write('			"%s" :\n')
            f.write('    *vwrite\n')
            f.write('			[\n')
            f.write('    *dim, nArray, array, nCount,4 ! Create NCOUNT  array\n')
            f.write('    *vget, nArray(1,1), node, 1, nlist ! Fill NARRAY with node numbers\n')
            f.write('    *vget, nArray(1,2), node, 2, loc, X\n')
            f.write('    *vget, nArray(1,3), node, 3, loc, Y\n')
            f.write('    *vget, nArray(1,4), node, 4, loc, Z\n')
            f.write('    *vwrite, nArray(1,1), nArray(1,2), nArray(1,3), nArray(1,4)  ! Write NARRAY to file\n')
            f.write('			[%6D, %10.4F, %10.4F, %10.4F,],\n')
            f.write('    *vwrite\n')
            f.write('			],\n')
            f.write('    *del,nArray,,nopr\n')
            f.write('*enddo 		! finished with the node map\n')
            f.write('*vwrite\n')
            f.write('			}\n')
            f.write('\n')
            f.write('\n')
            f.write('\n')
            f.write('! another DO loop for the facets\n')
            f.write('*vwrite\n')
            f.write('		self.facetMap = {\n')
            f.write('*do,i,1,nComps,1\n')
            f.write('    *get,compName,comp,i,name		! get the name of the nth component\n')
            f.write('    *get,nType,comp,compName,type	! get the type #\n')
            f.write('					! 1=Nodes, 2=Elements, 6=Keypoints, 7=Lines, 8=Areas, 9=Volumes\n')
            f.write('\n')
            f.write('    *if,nType,eq,8,then\n')
            f.write('\n')
            f.write('     allsel\n')
            f.write('     cmsel,,compName\n')
            f.write('     nsla,s,1\n')
            f.write('\n')
            f.write('     nsla,S,0   ! select all nodes internal to the area(s)\n')
            f.write('     esln,S,0   ! select all elements connected to the nodes\n')
            f.write('     nsla,S,1   ! select all nodes internal to the area and\n')
            f.write('\n')
            f.write('     *get,eCount,ELEM,,count    ! number of selected elements\n')
            f.write('     current_element_number=0\n')
            f.write('*vwrite, compName\n')
            f.write('			"%s" :\n')
            f.write('*vwrite\n')
            f.write('			[\n')
            f.write('\n')
            f.write('     *do,AR13,1,eCount          ! loop on all selected nodes\n')
            f.write('         current_element_number=ELNEXT(current_element_number)       ! element number in the list\n')
            f.write('         face_number=NMFACE(current_element_number)       ! face number\n')
            f.write('         *if, face_number, gt, 0, then\n')
            f.write('             *dim,fn,array,8\n')
            f.write('             *do,j,1,8\n')
            f.write('                 fn(j) = ndface(current_element_number, face_number, j) !node numbers for this face\n')
            f.write('             *enddo\n')
            f.write('             *vwrite, current_element_number, face_number, fn(1), fn(2), fn(3), fn(4), fn(5), fn(6), fn(7), fn(8)\n')
            f.write('			[%6d, %6d, %6d, %6d, %6d, %6d, %6d, %6d, %6d, %6d,],\n')
            f.write('\n')
            f.write('                *del,fn,,NOPR\n')
            f.write('            *endif\n')
            f.write('        *enddo\n')
            f.write('        *vwrite\n')
            f.write('			],\n')
            f.write('     *endif\n')
            f.write('*enddo\n')
            f.write('*vwrite		!finished with the element faces\n')
            f.write('			}\n')
            f.write('*CFCLOSE\n')

            f.close()

            cmd = '"' + ansys_exe + '" -b -i ' + inputfile + \
                ' -o ' + outfile + ' -j ' + 'Job_' + tempstr 

            ret = subprocess.call(cmd)

            if ret == 8: # success return
                cfile = self.get_model_file_name()
                #check for errors in ansys error file
                errfile = 'Job_' + tempstr + '.err'
                try:
                    f = open(errfile, 'r')
                except IOError as ioe:
                    s =  'AnsysWrapperGenerator for ' + self.name + ': opening error file ' + errfile
                    s += '\n\tPLEASE CHECK GENERATED WRAPPER ' + cfile + '\n\t' + sys.exc_info()[0] + '\n\t' + str(ioe)
                    print 'ERROR: ' + s
                    self.logger.error(s)          
                    return cfile
                lines = f.readlines()
                f.close()
                for l in lines:
                    if l.count('ERROR'):
                        s =  'AnsysWrapperGenerator for ' + self.name + ': found "ERROR" in ' + errfile
                        s += '\n\tPLEASE CHECK GENERATED WRAPPER ' + cfile
                        print 'ERROR: ' + s
                        self.logger.error(s)          
                        break

            else:
                s =  'AnsysWrapperGenerator for ' + self.name + ': ANSYS returned ' + str(ret) + ' for command ' + cmd
                print 'ERROR: ' + s
                self.logger.error(s)          
            return cfile
        except IOError as ioe:
            s =  'AnsysWrapperGenerator for ' + self.name + ': trying to create file ' + inputfile + ' in directory ' + path
            s += '\n\t' + sys.exc_info()[0] + '\n\t' + str(ioe)
            print 'ERROR: ' + s
            self.logger.error(s)          
            self.ok = False
            return cfile

    def _parse_componentsfile(self, componentsfile):

        try:
            f = open(componentsfile, 'r')
        except IOError as ioe:
            s =  'AnsysWrapperGenerator for ' + self.name + ': opening componentsfile file ' + componentsfile
            s += '\n\t' + sys.exc_info()[0] + '\n\t' + str(ioe)
            print 'ERROR: ' + s
            self.logger.error(s)        
            return False
        exec(f)
        f.close()

        feaModel = FeaModelInPythonFormat()


        self.components['nodes'] = {} # empty dictionary
        for nodeName in feaModel.nodeMap:
            self.components['nodes'][nodeName] = [] # empty list
            for n in feaModel.nodeMap[nodeName]:
                self.components['nodes'][nodeName].append( n[0] ) 

        self.components['surfaces'] = {} # empty dictionary
        for surfaceName in feaModel.facetMap:
            self.components['surfaces'][surfaceName] = [] # empty list
            for n in feaModel.facetMap[surfaceName]:
                self.components['surfaces'][surfaceName].append( [n[0], n[1]] ) 


        self.unitsinfo = ansysinfo.unitsinfodict['0']
        if str(feaModel.units) in ansysinfo.unitsinfodict:
            self.unitsinfo = ansysinfo.unitsinfodict[ str(feaModel.units) ]                   
        else:
            s = 'AnsysWrapperGenerator for ' + self.name + ': unknown units value ' + str(feaModel.units) + ' in components file ' + componentsfile
            print 'WARNING: ' + s
            self.logger.warning(s)        
        s = 'Units info: ' + self.unitsinfo.dump()
        print s
        self.logger.info(s)
        return True

    def _parse_prep7File(self):
        """ Read the extra /PREP7 command file, if it exists. This will have extra 
        commands that wind up in the PREP7 portion of the wrapped ANSYS input file.
        The commands come from model_db_name.prep7.txt from the same directory as the db file."""

        dbname, dbext = os.path.splitext(self.dbfile)
        apdlFile = dbname + '.prep7.txt'
        if os.path.exists( apdlFile ):
            f = open(apdlFile, 'r')
            self.prep7 = f.readlines()
            f.close()

    def _parse_solutionFile(self):
        """ Read the extra /SOL command file, if it exists. This will have extra 
        commands that wind up in the SOL portion of the wrapped ANSYS input file.
        The commands come from model_db_name.solution.txt from the same directory as the db file"""

        dbname, dbext = os.path.splitext(self.dbfile)
        apdlFile = dbname + '.solution.txt'
        if os.path.exists( apdlFile ):
            f = open(apdlFile, 'r')
            self.solution = f.readlines()
            f.close()

    def _parse_postFile(self):
        """ Read the extra /POST command file, if it exists. This will have extra 
        commands that wind up in the POST portion of the wrapped ANSYS input file.
        The commands come from model_db_name.post.txt from the same directory as the db file"""

        dbname, dbext = os.path.splitext(self.dbfile)
        apdlFile = dbname + '.post.txt'
        if os.path.exists( apdlFile ):
            f = open(apdlFile, 'r')
            self.post = f.readlines()
            f.close()

    def _writeline(self, line):
        self.genfile.write(line + '\n')

    def _genheader(self, codepath):
        self._writeline('import logging')
        self._writeline('import operator')
        self._writeline('import math')
        self._writeline('from openmdao.main.api import Component')
        self._writeline('from openmdao.lib.datatypes.api import Array, Float, List, Str')
        self._writeline('from openmdao.lib.components.api import ExternalCode')
        self._writeline('from openmdao.util.filewrap import FileParser')
        self._writeline('from openmdao.util.filewrap import InputFileGenerator')
        self._writeline('from openmdao.main.exceptions import RunInterrupted')
        self._writeline('from pyparsing import ParseBaseException')
        self._writeline('import os.path')
        self._writeline('from os import chdir, getcwd')
        self._writeline('import sys')
        self._writeline('sys.path.insert(0, \'' + codepath.replace('\\', '/') +
                        '\')\n')
        self._writeline('from ansyswrapper.ansyswrapper import ANSYSWrapperBase')
        self._writeline('class ' + self.classname + '(ANSYSWrapperBase):')
        self._writeline(indent1 + triplequote +
                        'A Wrapper for ANSYS Classic Structural ' + self.name + '.' +
                        triplequote)
        self._writeline(indent1 +
                        '#Creates parameters and initializes components.')
        self._writeline(indent1 +
                        '#Base class handles input, execution, and output.')

    def _gendecl(self, k, i, name, units):
        nm = ansysinfo._make_name(name, i)
        self.input_names.add(nm)
        s = indent1 + nm + ' = Float(0.0,' 'iotype = "in",\n' + indent2 + 'desc = " ' + \
            i + ' on ' + k + ' component ' + name + '"'
        if self.unitsinfo.ok and units in self.unitsinfo.info:
            s = s + ',\n' + indent2 + 'units = "' + self.unitsinfo.info[units] + '"'
        s = s + ')'
        self._writeline(s)

    def _gendecls(self):
        self._writeline(indent1 + '#Assumes 0.0 initial value for inputs')
        for k, v in self.components.iteritems():
            for name, nodes in v.iteritems():
                #TO_CHECK  - is there any way to get units?
                if k == 'surfaces':
                    for i, v in ansysinfo.surfaceinputtypes.iteritems():
                        self._gendecl(k, i, name, v[1])
                elif k == 'keypoints':
                    for i, v in ansysinfo.keypointinputtypes.iteritems():
                        self._gendecl(k, i, name, v[1])
                elif k == 'nodes':
                    for i, v in ansysinfo.nodeinputtypes.iteritems():
                        self._gendecl(k, i, name, v[1])
                else:
                    s = 'AnsysWrapperGenerator for ' + name + ': unknown component type ' + k + ' - IGNORED'
                    print 'WARNING: ' + s
                    self.logger.warning(s)        
                for otype, ounits in ansysinfo.outputtypes.iteritems():
                    n = ansysinfo._make_name(name, otype)
                    self.output_names.add(n)
                    if self.unitsinfo.ok and ounits in self.unitsinfo.info:
                        units_str = ',\n' + indent2 + 'units = "' + self.unitsinfo.info[ounits] + '"'
                    else:
                        units_str = ''
                    self._writeline(indent1 + n +
                                    ' = Array(iotype = "out", dtype = "float",\n' + indent2 + 'desc = "' + otype +
                                    ' on nodes of ' + name + '"' + units_str + ')')
                    for ctype in ansysinfo.calctypes:
                        cname = n + '_' + ctype
                        self.output_names.add(cname)
                        self._writeline(indent1 + cname + ' = Float(0.0, iotype = "out",\n' +
                                        indent2 + 'desc = "' + ctype + ' of ' + otype + ' on nodes of ' + name + '"' + units_str + ')')
        for i, v in ansysinfo.globalinputtypes.iteritems():
            iunits = v[1]
            if self.unitsinfo.ok and iunits in self.unitsinfo.info:
                units_str = 'units = "' + self.unitsinfo.info[iunits] + '"'
            else:
                units_str = ''
            global_name = 'FEA_' + i
            self.input_names.add(global_name)
            initial_name = 'initial_' + global_name
            if i in self.initial_values_dictionary:
                initial_value = self.initial_values_dictionary[i]
            else:
                initial_value = 0.0
                s = 'AnsysWrapperGenerator for ' + name + ': ' + i + ' not in initial_values_dictionary; using 0.0 as initial value'
                print 'WARNING: ' + s
                self.logger.warning(s)
            self._writeline(indent1 + global_name + ' = Float(' + str(initial_value) + ', iotype = "in", ' + units_str + ')') 
            self._writeline(indent1 + initial_name  + ' = ' + str(initial_value))
        #an output for the full name of the python results file
        self._writeline(indent1 + 'Results_File = Str(iotype = "out", desc = "Results file in Python Format")')

    def _geninit(self):
        self._writeline(indent1 +
            'def __init__(self, name, runner, dbfile, elasticity = [100, 100, 100], poisson = [0.33, 0.33, 0.33], logger_name = None):')
        self._writeline(indent2 + triplequote + 'Constructor for the ' +
                        self.classname + ' ANSYS OpenMDAO component.' + triplequote)
        self._writeline(indent2 + 'super(' + self.classname +
            ', self).__init__(name = name, runner = runner, dbfile = dbfile, elasticity = elasticity, poisson = poisson, logger_name = logger_name)')
        self._writeline(indent2 + 'self.Results_File = os.path.join(runner.workingdir, self.my_name + ".py")')
        self._writeline(indent2 + 'self.components["global"] = {}')
        self._writeline(indent2 + 'self.components["global"]["FEA"] = []')
        for k, v in self.components.iteritems():
            self._writeline(indent2 +
                            'self.components["' + k + '"] = {} #empty dictionary')
            for name, nodes in v.iteritems():
                self._writeline(indent2 +
                                'self.components["' + k + '"]["' + name + '"] = ' + str(nodes))
        self._writeline(indent2 + 'self.logger.debug("Init: " + self.dump())')
        self._writeline(indent1 + 'def execute(self):')
        self._writeline(indent2 + 'super(' + self.classname + ', self).execute()')

    def _genexecute(self):
        pass


    def _genoptions(self):
        if( self.prep7):
            self._writeline('')
            self._writeline(indent1 + 'def prep7(self):' )
            self._writeline(indent2 + triplequote + 'Entry point for derived wrappers to add customization to the /PREP7 section')
            self._writeline(indent2 + 'Derived from the file:  model_db_name.prep7.txt from same directory as the db file' + triplequote)

            self._writeline(indent2 + 'options = []')
            for line in self.prep7:
                self._writeline(indent2 + 'options.append( ' + '"' + line.strip() + '"' + ' )' )
            self._writeline(indent2 + 'return options')

        if( self.solution):
            self._writeline('')
            self._writeline(indent1 + 'def solution(self):' )
            self._writeline(indent2 + triplequote + 'entry point for derived wrappers to add customization to the /SOL section')
            self._writeline(indent2 + 'Derived from the file:  model_db_name.solution.txt  from same directory as the db file' + triplequote)

            self._writeline(indent2 + 'options = []')
            for line in self.solution:
                self._writeline(indent2 + 'options.append( ' + '"' + line.strip() + '"' + ' )' )
            self._writeline(indent2 + 'return options')

        if( self.post):
            self._writeline('')
            self._writeline(indent1 + 'def post(self):' )
            self._writeline(indent2 + triplequote + 'entry point for derived wrappers to add customization to the /POST section')
            self._writeline(indent2 + 'Derived from the file:  model_db_name.post.txt from same directory as the db file' + triplequote)

            self._writeline(indent2 + 'options = []')
            for line in self.post:
                self._writeline(indent2 + 'options.append( ' + '"' + line.strip() + '"' + ' )' )
            self._writeline(indent2 + 'return options')

    def generate(self):
        """Generate the wrapper."""
        if not self.ok:
            s = 'AnsysWrapperGenerator for ' + self.name + ': see previous errors'
            print 'ERROR: ' + s
            self.logger.error(s)        
            return
        currdir = os.getcwd()
        try:
            path,gen = os.path.split(self.genfilename)
            os.chdir(path)
            if not os.path.exists(self.componentsfile): #need to generate the components file
                self.componentsfile = self._gen_componentsfile(path)
                if not os.path.exists(self.componentsfile): #problem generating it
                    self.ok = False
                    s = 'AnsysWrapperGenerator for ' + self.name + ': trying to create componentsfile ' + self.componentsfile
                    print 'ERROR: ' + s
                    self.logger.error(s)        
                    return
            s = 'AnsysWrapperGenerator for ' + self.name + ': components file: ' + self.componentsfile 
            print s
            self.logger.info(s)
            try:
                self.genfile = open(self.genfilename, 'w')
                #import pdb; pdb.set_trace()
                self.ok = self._parse_componentsfile(self.componentsfile)
                if not self.ok:
                    s = 'AnsysWrapperGenerator for ' + self.name + ': no components found in ' + self.componentsfile
                    print 'ERROR: ' + s
                    self.logger.error(s)        
                    return

                #parse the prep7, sol, and post files
                self._parse_prep7File()
                self._parse_solutionFile()
                self._parse_postFile()

                self._genheader(currdir)
                self._gendecls()
                self._geninit() 
                self._genexecute()
                self._genoptions()
                self.genfile.close()

            except IOError as ioe:
                s = 'AnsysWrapperGenerator for ' + self.name + ': cannot open ' + self.genfilename 
                s += '\n\t' + sys.exc_info()[0] + '\n\t' + str(ioe)
                print 'ERROR: ' + s
                self.logger.error(s)        
                self.ok = False
                return
        finally:
            os.chdir(currdir)
            
if __name__ == "__main__": # pragma: no cover         

    import sys

# Use this code block to run directly
#    name = 'BeamWUnitsTest'
#    dir = 'C:\\Projects_KRL\\OPenMDAO\\Cases\\MSI_Pump_Case\\Case_4\ANSYS'
#    genfilename = os.path.join(dir, name + '.py')
#    dbfile = os.path.join(dir, 'impeller_coarse.db')
#    wg = WrapperGenerator(name, genfilename, dbfile, ANSYS_VER = 'ANSYS145')   
#    wg.generate()


# Use this code block to run through the GUI
    app = QApplication(sys.argv)
    form = MainDlg(logger_name = 'MSI')
    form.show()
    app.exec_()
