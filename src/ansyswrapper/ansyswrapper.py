
__all__ = ['ANSYSWrapperBase']

import logging
import operator
import math
import os
import pickle
import socket
import subprocess
import sys
import time

from openmdao.main.api import Component
from openmdao.main.attrwrapper import UnitsAttrWrapper
from openmdao.lib.datatypes.api import Float
from openmdao.lib.components.api import ExternalCode
from openmdao.util.filewrap import FileParser

import ansysinfo

#ANSYS_VER = "ANSYS140"
#ANSYS_VER = "ANSYS130"

class ANSYSInstance:
    """Holds information about an instance to be solved by ANSYS Classical Structural. Only used internally by ANSYSRunner."""
    def __init__(self, name, dbfile, index, cdbfile = None, elasticity = [100, 100, 100], poisson = [0.33, 0.33, 0.33]):
        self.name = name
        self.dbfile = dbfile
        self.index = index
        self.cdbfile = cdbfile
        self.elasticity = elasticity
        self.poisson = poisson

    def dump(self):
        s = 'ANSYSInstance ' + self.name
        if self.dbfile:
            s = s +'\ndbfile ' + self.dbfile
        s = s +'\nindex ' + str(self.index)
        if self.cdbfile:
            s = s +'\ncdbfile ' + str(self.cdbfile)
        return s


class ANSYSRunner():
    """Runs ANSYS Classical Structural, possibly for multiple instances of ANSYSWrapperBase.
       There should be only one instance of this class: create it and pass it to the constructor of ANSYSWrapperBase.
       When finished, the user MUST call shutdown() - it is a good idea to put the call to shutdown in a finally clause.
       
       *Parameters*
       
           name: string
               Name used to identify the ANSYSRunner.
               
            workingdir: string
                Full path to directory in which to run ANSYS.
                
            timeout: integer (optional)
                Time to wait for ANSYS commands.  Default 1000.
                
            ANSYS_VER: string (optional)
                ANSYS Version String. Default ANSYS145.
                
            run_under_wing: boolean
                Set to True to if you need to run in a debugger and want to manually start and stop ANSYS. Default False.
                
            logger_name:
                Name of an existing logging::logger to use, if any.  Default None.  If None, a logger will be created with an internal name.
                
       """
    ansys_instances = {} #empty dictionary #TO_CHECK:  can we assume an order????
    name = 'ANSYSWrapperBase'


    def __init__(self, name, workingdir, timeout = '1000', ANSYS_VER = "ANSYS145", run_under_wing = False, logger_name = None):
        if logger_name == None:
            self.logger = logging.getLogger("MSI")
        else:
            self.logger = logging.getLogger(logger_name)
        if len(name) > 20:
            print 'ANSYSRunner name must be < 20 characters'
            self.logger.warning('ANSYSRunner name must be < 20 characters: ' +
                                name)
            self.ok = False
            return

        self.name = name.replace(' ', '')
        self.workingdir = workingdir
        self.timeout = timeout
        self.ansys_inited = False
        self.ok = False
        self.ANSYS_VER = ANSYS_VER
        self.run_under_wing = run_under_wing

        try:
            ansysdir =  os.environ[self.ANSYS_VER + '_DIR']
        except KeyError as ke:
            print 'Cannot find ' + self.ANSYS_VER + '_DIR in environment'
            self.logger.warning('Cannot find ' + self.ANSYS_VER + '_DIR in environment')
            print sys.exc_info()[0]
            print str(ke)
            self.ok = False
            return
        try:
            ansysdir2 =  os.environ['ANSYS_SYSDIR']
        except KeyError as ke:
            print 'Cannot find ANSYS_SYSDIR in environment'
            self.logger.warning('Cannot find ANSYS_SYSDIR in environment')
            print sys.exc_info()[0]
            print str(ke)
            self.ok = False
            return
        self.ansys_exe = os.path.join(ansysdir, 'bin', ansysdir2, self.ANSYS_VER)

        try:
            if not os.path.exists(workingdir):
                os.makedirs(self.workingdir)
        except OSError as oe:
            print 'Error trying to create workingdir ' + self.workingdir
            self.logger.warning('Error trying to create workingdir ' +
                                self.workingdir)
            print sys.exc_info()[0]
            print str(oe)
            self.ok = False
            return

        self.ansysfile = os.path.join(self.workingdir, self.name + '_MSI.dat')
        try:
            self.ansysfd = open(self.ansysfile, 'w', 1)
        except IOError as ioe:
            print 'Error trying to create file ' + self.ansysfile
            self.logger.warning('Error trying to create file ' + self.ansysfile)
            print sys.exc_info()[0]
            print str(ioe)
            self.ok = False
            return
        self.hostname = socket.gethostname()
        signame = ''
        #Fix signame so is a legal signal name 
        #The signal cannot contain characters other than a-z, A-Z, 0-9 and ASCII characters in the range 128-255
        l1 = range(ord('A'), ord('Z')+1)
        l2 = range(ord('a'), ord('z')+1)
        l3 = range(ord('0'), ord('9')+1)
        l4 = range(128, 256)
        l1.extend(l2)
        l1.extend(l3)
        l1.extend(l4)
        for c  in self.name:
            if ord(c) in l1:
                signame += c
            else:
                signame += '0' #an arbitrary substitution of a legal character
        self.from_ansys_signal = 'MSI' + signame + 'fromansyssignal'
        self.to_ansys_signal = 'MSI' + signame + 'toansyssignal'

        self.ansysout = os.path.join(self.workingdir, self.name + '_MSI.out')
        self.instancefile_basename = 'MSI_' + self.name + '_inst'
        self.instancefile_ext = 'txt'
        self.ok = True

        msg = 'TO FORCIBLY STOP ANSYS:\n'
        fname = os.path.join(self.workingdir, 
                             self.instancefile_basename + '.' + self.instancefile_ext)
        msg = msg + 'Put -1 in ' + fname + '\n'
        msg = msg + 'then execute\nWAITFOR /S ' + self.hostname + \
            ' /SI ' + self.to_ansys_signal + '\n'
        print msg
        self.logger.warning(msg)

    def _wait_for_ansys(self, timeout):
        self._check_if_ansys_done()
        if self.logger.isEnabledFor(logging.DEBUG): print 'before wait, ok ' + str(self.ok) + ' timeout ' + str(timeout)
        self.logger.debug('before wait_for_ansys, ok ' + str(self.ok) + ' timeout ' + str(timeout))
        if not self.ok:
            print 'Not self.ok, not _wait_for_ansys'
            self.logger.debug('Not self.ok, not _wait_for_ansys')
            return
        if sys.platform == 'win32':
            try:
                ret = subprocess.call(['WAITFOR', '/T', str(timeout),
                                       self.from_ansys_signal])
                if self.logger.isEnabledFor(logging.DEBUG): print '_wait_for_ansys: ret ' + str(ret)
                self.logger.debug('wait_for_ansys ret ' + str(ret))
            except:
                print 'Error wait for ansys ' + self.from_ansys_signal
                print sys.exc_info()[0]
                self.logger.warning('Error wait for ansys ' +
                                    str(self.from_ansys_signal) + '\n' + str(sys.exc_info()[0]))
                self.ok = False
        else:
            print 'Wrong platform'
            self.logger.debug('wait_for_ansys WRONG PLATFORM')
        if self.logger.isEnabledFor(logging.DEBUG): print 'after wait'
        self.logger.debug('after wait_for_ansys, ok ' + str(self.ok))

    def _signal_ansys(self):
        if self.logger.isEnabledFor(logging.DEBUG): print 'before send'
        self.logger.debug('before signal_ansys')
        if sys.platform == 'win32':
            subprocess.call(['WAITFOR', '/S', self.hostname, '/SI',
                             self.to_ansys_signal])
        else:
            print 'Wrong platform'
            self.logger.debug('signal_ansys WRONG PLATFORM')
        if self.logger.isEnabledFor(logging.DEBUG): print 'after send'
        self.logger.debug('after signal_ansys')

    def _start_ansys(self, timeout, productvar = None):
        if self.logger.isEnabledFor(logging.DEBUG): print 'before start ansys'
        self.logger.debug('before start_ansys')

        try:
            args = [self.ansys_exe, '-dir', self.workingdir, '-b',
                    '-i', self.ansysfile, '-o', self.ansysout,
                    '-MSI_INSTFILE', self.instancefile_basename,
                    '-MSI_INSTEXT', self.instancefile_ext]                      
            if self.logger.isEnabledFor(logging.DEBUG): print args
            self.logger.info('Starting ANSYS, args: ' + str(args))
            if self.run_under_wing:
                self.ansys_po = None
                print 'MANUALLY START ANSYS'
            else:
                self.ansys_po = subprocess.Popen(args)
        except OSError as oe:
            print 'Error trying to start ansys ' + self.ansys_exe
            print sys.exc_info()[0]
            print str(oe)
            self.logger.warning('OSError trying to start ansys ' + self.ansys_exe +
                                '\n' + str(oe))
            self.ok = False
            return
        except:
            #import pdb; pdb.set_trace()
            print 'Error trying to start ansys ' + self.ansys_exe
            print sys.exc_info()[0]
            self.logger.warning('Error trying to start ansys ' + self.ansys_exe +
                                '\n' + str(sys.exc_info()[0]))
            self.ok = False
            return

        self._wait_for_ansys(timeout)
        #import pdb; pdb.set_trace()
        if self.logger.isEnabledFor(logging.DEBUG): print 'after start ansys'
        self.logger.debug('after start_ansys')
##        time.sleep(1) #make sure ansys is really ready
##        print 'after sleep'
        self._check_if_ansys_done()

    def _check_if_ansys_done(self):
        if self.run_under_wing:
            print 'MANUALLY CHECK IF ANSYS RUNNING, if not, set self.ok to False'
            return
        ret = self.ansys_po.poll()
        if ret != None: # has returned
            print 'ANSYS exited with retcode ' + str(ret) + \
                  ' Probably a licensing issue'
            self.logger.warning('ANSYS exited with retcode ' + str(ret) + 
                                ' Probably a licensing issue')
            self.ok = False

    def _send_index_to_ansys(self, index, fname):
        currdir = os.getcwd()
        try:
            os.chdir(self.workingdir)
            try:
                f = open(fname, 'w')
                f.write(str(index) + '\n')
                f.close()
                time.sleep(1) #TO_CHECK:  - why????
                self._signal_ansys() #tell ansys to run instance
                if index >= 0: #not telling ansys to quit
                    self._wait_for_ansys(self.timeout) #wait for ansys to run instance
            except IOError as ioe:
                print 'Error trying to create file ' + fname
                print sys.exc_info()[0]
                print str(ioe)
                self.logger.warning('Error trying to create file ' + fname +
                                    '\n' + str(ioe))
                self.ok = False
        finally:
            os.chdir(currdir)
            print 'After _send_index_to_ansys, ok ' + str(self.ok)
            self.logger.debug('After _send_index_to_ansys, ok ' + str(self.ok))

    def add_instance(self, name, dbfile, cdbfile = None, elasticity = [100, 100, 100], poisson = [0.33, 0.33, 0.33]):
        """Add an instance to be solved by ANSYS Classical Structural."""
        index = -1
        if self.ansys_inited:
            print 'ERROR: attempt to add_instance ' + name + ' after calling init_ansys for ANSYSRunner ' + self.name
            self.logger.error('ERROR: attempt to add_instance ' + name + ' after calling init_ansys for ANSYSRunner ' + self.name)
            self.ok = False
            return index
        if name in self.ansys_instances:
            print 'ERROR:' + name + \
                  ' already used for an ANSYS instance. IGNORED'
            self.logger.warning('ERROR:' + name + 
                                ' already used for an ANSYS instance. IGNORED')
        else:
            index = len(self.ansys_instances) + 1
            self.ansys_instances[name] = ANSYSInstance(name, dbfile, index, cdbfile, elasticity, poisson)
            self.logger.debug('added instance ' + name)
        return index

    def dump(self):
        s = 'ANSYSRunner ' + self.name
        if self.ok:
            if self.ansys_inited:
                s = s + ' ansys_inited'
            else:
                s = s + ' NOT ansys_inited'
            s = s + '\nansysfile ' + self.ansysfile
            s = s + '\nworkingdir ' + self.workingdir
            s = s + '\nansys_exe ' + self.ansys_exe
            s = s + '\nansysout  ' + self.ansysout 
            s = s + '\ninstancefile_basename  ' + self.instancefile_basename 
            s = s + '\ninstancefile_ext  ' + self.instancefile_ext 
            s = s + '\nsignals ' + self.from_ansys_signal + ' ' + \
                self.to_ansys_signal
            s = s + '\nInstances:'
            for k, v in self.ansys_instances.iteritems():
                s = s + '\n' + v.dump()
        else:
            s = s + ' NOT OK'
        return s

    def init_ansys(self, prep7=[], solution=[], post=[], productvar = None, timeout = 10):
        """Initialize the ANSYS Mechanical APDL run.  This method should be called AFTER all ansys_instances have been added."""
        if self.ansys_inited:
            print 'WARNING: attempt to init ANSYS twice for ' + self.name +\
                  ' - IGNORED'
            self.logger.warning('WARNING: attempt to init ANSYS twice for ' +
                                self.name + ' - IGNORED')
        else:
            self.ansysfd.write('/batch\n')
            self.ansysfd.write('/TITLE, ' + 'ANSYSRunner ' + self.name + '\n')


            # Wrapper will write corresponding instance # (starting at 1)
            # to a file named on the ansys command line
            # Wrapper will write -1 to that file to stop
            # inputs for each instance will be in <instancename>.inp
            # outputs for each instance will be in <instancename>.txt
            numinstance = len(self.ansys_instances)

            maxlen = 1
            for v in self.ansys_instances.itervalues():
                if len(v.name) > maxlen: maxlen = len(v.name)

                if v.cdbfile:
                    if len(v.cdbfile) > maxlen: maxlen = len(v.cdbfile)
                if v.dbfile:
                    if len(v.dbfile) > maxlen: maxlen = len(v.dbfile)
                else: # we need to start by making the dbfile, as in CDREAD,DB,'Block01','cdb',,'',''
                    (r,e) = os.path.splitext(v.cdbfile)
                    v.dbfile = r + '.db'
                    if len(e): e = e[1:]   
                    self.ansysfd.write('/COM, make db file ' + r + '.db for ' + v.name + '\n')
                    self.ansysfd.write('CDREAD,DB,' + r + ',' + e + '\n')
                    self.ansysfd.write('/COM, MATERIAL TYPE INFO\n')
                    self.ansysfd.write('MP,EX,1,' + str(v.elasticity[0]) + '\n')
                    self.ansysfd.write('MP,EY,1,' + str(v.elasticity[1]) + '\n')
                    self.ansysfd.write('MP,EZ,1,' + str(v.elasticity[2]) + '\n')
                    self.ansysfd.write('MP, NUXY, 1,' + str(v.poisson[0]) + '\n')
                    self.ansysfd.write('MP, NUYZ, 1,' + str(v.poisson[1]) + '\n')
                    self.ansysfd.write('MP, NUXZ, 1,' + str(v.poisson[2]) + '\n')
                    self.ansysfd.write('/COM, save db file ' + r + '.db for ' + v.name + '\n')
                    self.ansysfd.write('SAVE,' + r + ',db\n')  
                    self.ansysfd.write('/COM, save parameters in ' + r + '.parms for ' + v.name + '\n')
                    self.ansysfd.write('PARSAVE,ALL,' + r + ',parms\n')  
                    self.ansysfd.write('/COM, clear the database\n')
                    self.ansysfd.write('/QUIT\n') 
                    self.ansysfd.write('/CLEAR,NOSTART\n') 
                    self.ansysfd.write('/COM, get parameters from ' + r + '.parms for ' + v.name + '\n')
                    self.ansysfd.write('PARRES,NEW,' + r + ',parms\n')  

            self.ansysfd.write('/prep7\n')

            self.ansysfd.write('/COM, STRING ARRAY for holding instance info\n')
            #holds name, dbfile name & ext
            instance_info_array = 'MSI_' + self.name + '_iia'
            self.ansysfd.write('*DIM,' + instance_info_array + ',STRING,' +
                               str(maxlen) + ',' + str(numinstance) + ',3\n')
            for v in self.ansys_instances.itervalues():
                col = str(v.index)
                self.ansysfd.write(instance_info_array +
                                   '(1,' + col + ',1) = \'' + v.name + '\'\n')
                (r,e) = os.path.splitext(v.dbfile)
                if len(e): e = e[1:]
                self.ansysfd.write(instance_info_array +
                                   '(1,' + col + ',2) = \'' + r + '\'\n')
                self.ansysfd.write(instance_info_array +
                                   '(1,' + col + ',3) = \'' + e + '\'\n')

            instance_var_name = 'MSI_' + self.name + '_ivn'
            self.ansysfd.write('/COM, array to read instance index from file\n')
            self.ansysfd.write('*DIM,' + instance_var_name + ',ARRAY,' + '1\n')

            doparm = 'MSI_DO_PARM'
            self.ansysfd.write(doparm + '=1\n')
            self.ansysfd.write('*DOWHILE,' + doparm + '\n')
            self.ansysfd.write('/COM, Signal ANSYSRunner that ANSYS is ready, then wait\n')
            self.ansysfd.write('/SYS, C:\\Windows\\System32\\waitfor.exe /S ' + self.hostname + ' /SI ' + self.from_ansys_signal + '\n')

            self.ansysfd.write('/COM, Wait for Signal from OpenMDAO\n')
            self.ansysfd.write('/SYS, C:\\Windows\\System32\\waitfor.exe /T ' + self.timeout + ' ' + self.to_ansys_signal + '\n')            
            instfname = 'MSI_INSTFILE'
            instename = 'MSI_INSTEXT'

            self.ansysfd.write('/COM, Read instance index from -' + instfname + ' ' +
                               instename + '\n')
            self.ansysfd.write('*VREAD,' + instance_var_name + '(1),' +
                               instfname + ',' + instename  + '\n')
            self.ansysfd.write('(F2.0)\n')
            self.ansysfd.write('iv=' + instance_var_name + '(1)\n')
            self.ansysfd.write('PARSAV,ALL,\'' + self.name + '\',\'prm\'\n')

            self.ansysfd.write('*IF,iv,LT,0,THEN\n')
            self.ansysfd.write(doparm + '=0\n')
            self.ansysfd.write('*ELSE\n')
            self.ansysfd.write('MSI_I_Name = ' + instance_info_array +
                               '(1,iv,1)\n')
            self.ansysfd.write('finish\n')
            self.ansysfd.write('/FILNAME,STRCAT(\'MSI_ANSYS_\',MSI_I_Name),0\n')

            #  RESUME IT
            self.ansysfd.write('/COM, Resume\n')
            self.ansysfd.write('/prep7\n')
            self.ansysfd.write('resume,'+ instance_info_array + '(1,iv,2), ' +
                               instance_info_array + '(1,iv,3)\n')
            self.ansysfd.write('allsel\n')
            self.ansysfd.write('PARRES,CHANGE,\'' + self.name + '\',\'prm\'\n')
            self.ansysfd.write('/COM, Read loads, etc.\n')
            self.ansysfd.write('/INPUT,' + instance_info_array +
                               '(1,iv,1), inp\n')
            for s in prep7:
                self.ansysfd.write(s + '\n');
            self.ansysfd.write('!finish preprocessing\n')
            self.ansysfd.write('finish\n')
            self.ansysfd.write('/COM, Re-solve the model\n')
            self.ansysfd.write('/sol\n')
            self.ansysfd.write('/INPUT,' + instance_info_array +
                               '(1,iv,1), sol\n')
            self.ansysfd.write('/COM, Post-process to get outputs\n')
            self.ansysfd.write('/post1\n')
            self.ansysfd.write('set,first\n')
            for s in post:
                self.ansysfd.write(s + '\n');
            self.ansysfd.write('*cfopen,' + instance_info_array + '(1,iv,1), ' +
                               'py\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('class FeaPropertiesInPythonFormat:\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('	def __init__(self):\n')
            self.ansysfd.write('*vwrite\n')
            keylist = ['number', 'UX_o', 'UY_o', 'UZ_o', 'UR_o', 'TEMP_o', 'FX_o', 'FY_o', 'FZ_o'] #these must match ansysinfo.outputtypes keys
            s = str(keylist)
            self.ansysfd.write('		self.nodeLabels = ' + s + '\n')
            self.ansysfd.write('*vwrite, units\n')
            self.ansysfd.write('		self.units = %I\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('		self.coordinateSystem = "Cartesian"\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('		self.nodeMap = {\n')
            self.ansysfd.write('*get,nComps,COMP,,ncomp\n')
            self.ansysfd.write('*do,J,1,nComps,1\n')
            self.ansysfd.write('*get,compName,comp,J,name '+
                               '! get the name of the nth component\n')
            self.ansysfd.write('*get,nType,comp,compName,type ' +
                               '! get the type #\n')

            self.ansysfd.write('GETVALS=0\n')
            self.ansysfd.write('allsel\n')
            self.ansysfd.write('cmsel,,compName\n')
            self.ansysfd.write('*IF,nType,EQ,1,THEN !type 1 Nodes\n') 
            self.ansysfd.write('GETVALS=1\n')
            #self.ansysfd.write('prnsol,u,comp ' + '!not needed but useful for debugging\n')
            self.ansysfd.write('*ELSEIF,nType,EQ,6,THEN !type 6 keypoints\n') 
            self.ansysfd.write('allsel\n')
            self.ansysfd.write('cmsel,,compName\n')
            self.ansysfd.write('nslk,S\n')
            self.ansysfd.write('GETVALS=1\n')
            self.ansysfd.write('*ELSEIF,nType,EQ,8,THEN !type 8 surfaces\n') 
            self.ansysfd.write('allsel\n')
            self.ansysfd.write('cmsel,,compName\n')
            self.ansysfd.write('nsla,s,1\n')
            self.ansysfd.write('GETVALS=1\n')
            self.ansysfd.write('*ENDIF\n')
            self.ansysfd.write('*IF,GETVALS,EQ,1,THEN !get values\n')
            self.ansysfd.write('*get,NCOUNT,node,,count ' +
                               '! Get total number of selected nodes\n')
            self.ansysfd.write('*VWRITE, compName\n')
            self.ansysfd.write('			"%s":\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('			[\n')
            self.ansysfd.write('*dim,NARRAY,array,NCOUNT,9 ' +
                               '! Create NCOUNT x 9 array\n')
            #self.ansysfd.write('*vwrite ! Writes a column header\n')
            #self.ansysfd.write('NODE UX UY UZ TEMP FX FY FZ\n')
            self.ansysfd.write('*vget,NARRAY(1,1),node,1,nlist ' +
                               '! Fill first column with node number\n')
            self.ansysfd.write('*DO,I,1,NCOUNT,1 !loop on nodes\n')
            self.ansysfd.write('N = NARRAY(I,1)\n')
            self.ansysfd.write('NARRAY(I,2) = UX(N) ' +
                               '! Fill second column with x-displ\n')
            self.ansysfd.write('NARRAY(I,3) = UY(N) ' +
                               '! Fill third column with y-displ\n')
            self.ansysfd.write('NARRAY(I,4) = UZ(N) ' +
                               '! Fill fourth column with z-displ\n')
            self.ansysfd.write('!We need radial displacement as a signed value\n')
            self.ansysfd.write('rdisp = sqrt(UX(N)**2 + UY(N)**2)\n')
            self.ansysfd.write('*IF,abs(UX(N)), GT, abs(UY(N)), THEN\n')
            self.ansysfd.write('    rdisp = sign(rdisp, UX(N))\n')
            self.ansysfd.write('*else\n')
            self.ansysfd.write('    rdisp = sign(rdisp, UY(N))\n')
            self.ansysfd.write('*endif \n')
            self.ansysfd.write('NARRAY(I,5) = rdisp\n')
            self.ansysfd.write('NARRAY(I,6) = TEMP(N) ' +
                               '! Fill sixth column with TEMP\n')
            self.ansysfd.write('*GET, NARRAY(I,7), NODE, N, RF, FX' +
                               '! Fill seventh column with X Reaction Load\n')
            self.ansysfd.write('*GET, NARRAY(I,8), NODE, N, RF, FY ' +
                               '! Fill eighth column with Y Reaction Load\n')
            self.ansysfd.write('*GET, NARRAY(I,9), NODE, N, RF, FZ ' +
                               '! Fill ninth column with Z Reaction Load\n')
            self.ansysfd.write('*ENDDO\n')
            self.ansysfd.write('*vwrite,' +
                               'NARRAY(1,1),NARRAY(1,2),NARRAY(1,3),NARRAY(1,4),' +
                               'NARRAY(1,5),NARRAY(1,6),NARRAY(1,7),NARRAY(1,8), NARRAY(1,9)  ' +
                               '! Write columns to file\n')
            self.ansysfd.write('			[%I, %G, %G, %G, %G, %G, %G, %G, %G,],\n')
            self.ansysfd.write('*vwrite\n')
            self.ansysfd.write('			],\n')

            self.ansysfd.write('*ENDIF\n')
            self.ansysfd.write('*enddo\n')
            self.ansysfd.write('*vwrite	\n')
            self.ansysfd.write('			}\n') 
            self.ansysfd.write('*cfclose\n')
            self.ansysfd.write('finish\n')
            #self.ansysfd.write('/COM, Signal ANSYSRunner that ANSYS is ready\n')
            #self.ansysfd.write('/SYS,WAITFOR /S ' + self.hostname +
                #' /SI ' + self.from_ansys_signal + '\n')

            self.ansysfd.write('*ENDIF\n')
            self.ansysfd.write('*ENDDO\n')
            #self.ansysfd.write('exit\n')
            self.ansysfd.close()
            self._start_ansys(timeout = timeout, productvar = productvar)
        self.ansys_inited = True
        self.logger.debug('ansys_inited done')
        print 'ansys_inited done'

    def run(self, instancename, prep7=[], solution=[], post=[]):
        """Run instancename.  Assumes input file has been written."""
        if not self.ok:
            print 'ERROR: in AnsysRunner.\n' + self.dump()
            self.logger.warning('ERROR: in AnsysRunner.\n' + self.dump())
            return False
        if not instancename in self.ansys_instances:
            print 'ERROR: ' + instancename + ' not in ansys_instances.\n' + \
                  self.dump()
            self.logger.warning('ERROR: ' + instancename +
                                ' not in ansys_instances.\n' + self.dump())
            return False
        if not self.ansys_inited:
            print 'Calling init_ansys from run'
            self.init_ansys(prep7, solution, post)
            if not self.ok:
                print 'ERROR: in AnsysRunner init_ansys.\n' + self.dump()
                self.logger.warning('ERROR: in AnsysRunner  init_ansys.\n' +
                                    self.dump())
                return False
        instance = self.ansys_instances[instancename]
        if self.logger.isEnabledFor(logging.DEBUG): print 'Running instance ' + instance.dump()
        self.logger.debug('AnsysRunner start run ' + instancename)
        fname = self.instancefile_basename + '.' + self.instancefile_ext
        self._send_index_to_ansys(instance.index, fname)
        self.logger.debug('AnsysRunner after _send_index_to_ansys, ok ' + str(self.ok))
        return self.ok

    def shutdown(self):
        if self.ansys_inited:
            if self.logger.isEnabledFor(logging.DEBUG): print 'Shutting down'
            self.logger.debug('AnsysRunner shutting down')
            fname = self.instancefile_basename + '.' + self.instancefile_ext
            self._send_index_to_ansys(-1, fname)
            self.ansys_inited = False

    def __del__(self):
        #TO_CHECK:  this doesn't seem to get called....
        print 'DELETING AnsysRunner'
        self.shutdown()

class ANSYSWrapperBase(ExternalCode):
    """Base class for wrappers for ANSYS Classical Structural. Used internally by ANSYSWrapperGenerator."""
    components = {} #empty dictionary of dictionaries of node numbers
                    # set by subclass when it parses the components file
    values = {} #empty dictionary of dictionaries of values
    def __init__(self, name, runner, dbfile, cdbfile = None, elasticity = [100, 100, 100], poisson = [0.33, 0.33, 0.33], logger_name = None):
        super(ANSYSWrapperBase, self).__init__()
        if logger_name == None:
            self.logger = logging.getLogger("MSI")
        else:
            self.logger = logging.getLogger(logger_name)
        self.my_name = name.replace(' ', '_')
        self.runner = runner
        self.loadsfile = self.my_name + '.inp'
        self.solutionfile = self.my_name + '.sol'
        if not dbfile and not cdbfile:
            print 'ERROR:' + name + ' must have one of dbfile or cdbfile. IGNORED'
            self.logger.warning('ERROR:' + name + ' must have one of dbfile or cdbfile. IGNORED')
            self.ok = False
        else:
            if dbfile:
                self.deflection_only = False
            else:
                self.deflection_only = True
            self.index = runner.add_instance(self.my_name, dbfile, cdbfile, elasticity, poisson)
            self.ok = True
            self.cachefile = os.path.join(self.runner.workingdir, self.my_name + '_cache.txt')
            if os.path.exists(self.cachefile):
                cachepickle = open(self.cachefile, 'r')
                self.cache = pickle.load(cachepickle)
                cachepickle.close()
                print 'ANSYSWrapper ' + self.my_name + ' loaded cache ' + self.cachefile + '\n' + self.dump_cache()  
            else:
                self.cache = {} #empty dictionary
            self.logger.debug('ANSYSWrapperBase ' + self.dump())
            os.environ['ANSYS_LOCK'] = 'OFF'
            os.environ['ANS_CONSEC'] = 'YES'


    def dump_cache(self):
        s = 'cache(' + self.cachefile + ')\n'
        for k, v in self.cache.iteritems():
            s = s + '\t' + str(k) + ': '
            for v1 in v:
                for i, o in v1.iteritems():
                    s = s + '\t\t' + str(i) + ': '
                    if isinstance(o, list):
                        if len(o) > 10:
                            s = s + str(o[0:10]) + '...\n'
                        else:
                            s = s + str(o) + '\n'
                    else:
                        s = s + str(o) + '\n'
        return s

    def dump(self):
        s = 'ANSYSWrapper ' + self.my_name + '\n'
        s = s + 'index ' + str(self.index) + '\n'
        s = s + 'runner name ' + self.runner.name + '\n'
        s = s + 'components\n'
        for k, c in self.components.iteritems():
            s = s + k + '\n'
            for n, e in c.iteritems():
                s = s + '\t' + n + ': ' + repr(e) + '\n'
        s = s + 'cache(' + self.cachefile + ')\n'
        s = s + self.dump_cache()
        return s

    #def __setattr__(self, name, value):
        #super(ANSYSWrapperBase, self).__setattr__(name, value)
        ## TO_CHECK:  - why did we need this???? self.__dict__[name] = value

    def _set_value_list(self, name, lst):
        self.logger.debug('AnsysWrapper _set_value_list ' + str(name) + ' to list of len ' + str(len(lst)))
        value_dict = {name: lst}
        self.__setattr__(name, lst)
        if len(lst):
            val = max(lst)
            nm = name + '_max'
            self.__setattr__(nm, val)
            value_dict[nm] = val
            self.logger.info(nm +'= ' + str(val))
            val = min(lst)
            nm = name + '_min'
            self.__setattr__(nm, val)
            value_dict[nm] = val
            self.logger.info(nm + ' = ' + str(val))
            val = reduce(operator.add, lst)/len(lst)
            nm = name+'_avg'
            self.__setattr__(nm, val)
            value_dict[nm] = val
            self.logger.info(nm +' = ' + str(val))
        return value_dict

    def get_attr_value(self, name, default = 0.0):
        a = getattr(self, name, default)
        if isinstance(a, UnitsAttrWrapper):
            return a.value
        else:
            return a

    def write_input(self, inputs=[]):
        """Write input file self.loadsfile."""
        currdir = os.getcwd()
        input_cmds = []
        try:
            os.chdir(self.runner.workingdir)
            try:
                f = open(self.loadsfile, 'w')
            except IOError as ioe:
                print 'Error opening loadsfile file ' + self.loadsfile
                print sys.exc_info()[0]
                print str(ioe)
                self.ok = False
                return False
            self.logger.info(self.my_name + ' write input: ' + self.loadsfile)
            self.logger.info('-------------------------------------\n')
            #self.logger.debug('nodeinputtypes ' + str(ansysinfo.nodeinputtypes))
            for k, vv in self.components.iteritems():
                #self.logger.debug('component ' + str(k) + ' ' + str(vv.keys()))
                for name, nodes in vv.iteritems():
                    #self.logger.debug(name)
                    if k == 'surfaces':
                        for i, s in ansysinfo.surfaceinputtypes.iteritems():
                            n = ansysinfo._make_name(name, i)
                            v = self.get_attr_value(n)
                            v = self.convert_units(n, v)
                            #self.logger.debug(n + ' = ' + str(v))
                            if v != 0.0: #write new value
                                l = s[0].replace('%N%', name)
                                l1 = l.replace('%V%', str(v))
                                l2 = '!apply ' + i + ' ' + str(v) + ' to ' + \
                                    ' surface component ' + name
                                f.write(l2 + '\n')
                                f.write(l1 + '\n')
                                self.logger.info(l2)
                                self.logger.info(l1)
                                input_cmds.append(l1)
                    elif k == 'keypoints':
                        for i, s in ansysinfo.keypointinputtypes.iteritems():
                            n = ansysinfo._make_name(name, i)
                            v = self.get_attr_value(n)
                            v = self.convert_units(n, v)
                            #self.logger.debug(n + ' = ' + str(v))
                            if v != 0.0: #write new value
                                l = s[0].replace('%N%', name)
                                l1 = l.replace('%V%', str(v))
                                l2 = '!apply ' + i + ' ' + str(v) + ' to ' + \
                                    ' keypoint component ' + name
                                f.write(l2 + '\n')
                                f.write(l1 + '\n')
                                self.logger.info(l2)
                                self.logger.info(l1)
                                input_cmds.append(l1)
                    elif k == 'nodes':
                        #self.logger.debug('node ' + name)
                        #import pdb; pdb.set_trace()
                        for i, s in ansysinfo.nodeinputtypes.iteritems():
                            n = ansysinfo._make_name(name, i)
                            try:
                                v = self.get_attr_value(n)
                                v = self.convert_units(n, v)
                            except:
                                print 'Exception in gettattr ' + n
                                v = 0.0
                            #self.logger.debug(n + ' = ' + str(v))
                            if v != 0.0: #write new value
                                l = s[0].replace('%N%', name)
                                l1 = l.replace('%V%', str(v))
                                l2 = '!apply ' + i + ' ' + str(v) + ' to ' + \
                                    ' node component ' + name
                                f.write(l2 + '\n')
                                f.write(l1 + '\n')
                                self.logger.info(l2)
                                self.logger.info(l1)
                                input_cmds.append(l1)
                    elif k == 'global':
                        for i, s in ansysinfo.globalinputtypes.iteritems():
                            n = ansysinfo._make_name(name, i)
                            v = self.get_attr_value(n)
                            v = self.convert_units(n, v)
                            initial_v = self.get_attr_value('initial_' + n)
                            if v != initial_v: #write new value
                                l = s[0].replace('%N%', name)
                                l1 = l.replace('%V%', str(v))
                                l2 = '!apply ' + i + ' ' + str(v) + ' to ' + \
                                    ' global component ' + name
                                f.write(l2 + '\n')
                                f.write(l1 + '\n')
                                self.logger.info(l2)
                                self.logger.info(l1)
                                input_cmds.append(l1)


                    elif k == 'coordinputtypes':
                        keys = ansysinfo.coordinputtypes.keys()
                        keys.sort()
                        subs = [ansysinfo.coordinputtypes[k] for k in keys]
                        for bnd, vvv in vv.iteritems():
                            for node, defls in vvv.iteritems(): # node is node number, delfs is list [UX, UY, UZ]
                                for defl, sub in zip(defls, subs):
                                    if defl <> 0:
                                        l = sub[0].replace('%N%', str(node))
                                        l1 = l.replace('%V%', str(defl))
                                        l2 = '!apply deflection ' + str(defl) + ' to ' + ' node ' + str(node)  
                                        f.write(l2 + '\n')
                                        f.write(l1 + '\n')
                                        self.logger.info(l2)
                                        self.logger.info(l1)
                                        input_cmds.append(l1)

            # extra_inputs, set elsewhere, get passed through verbatim
            for line in inputs:
                f.write(line)
                input_cmds.append(line)

            self.logger.info('-------------------------------------\n')
            self.logger.info(self.my_name + ' write input done')

        finally:
            f.close()
            os.chdir(currdir)
            return input_cmds
    def convert_units(self, n, v):
        if v.__class__ == UnitsAttrWrapper:

            units = self.__base_traits__[n].units

            try:    
                v.pq.convert_to_unit(units)
            except:
                print "Units are not set for", n, " in ", self.__class__

            value = v.pq.value            
            return value

        else:
            return v


    def write_solution(self):
        """Write solution commands file self.solutionfile."""
        currdir = os.getcwd()
        needrun = False
        try:
            os.chdir(self.runner.workingdir)
            try:
                f = open(self.solutionfile, 'w')
            except IOError as ioe:
                print 'Error opening solutionfile file ' + self.solutionfile
                print sys.exc_info()[0]
                print str(ioe)
                self.ok = False
                return False

            for s in self.solution():
                f.write(s + '\n');
            needrun = True
            f.close()
        finally:
            os.chdir(currdir)
            return needrun

    def process_output_from_fea_model(self, feaModel):
        """Override if necessary in subclass."""
        nodeLabels = feaModel.nodeLabels
        self.logger.debug('nodeLabels: ' + str(nodeLabels))
        outputs = []
        for component in feaModel.nodeMap:
            self.logger.debug('component: ' + str(component))
            for i, item in enumerate(nodeLabels):
                results = []
                for n in feaModel.nodeMap[component]:
                    results.append( n[i] ) 
                value_dict = self._set_value_list(component+'_'+item, results)
                outputs.append(value_dict.copy())
        return outputs

    def read_output(self):
        """Read output file.
           Uses self.components."""
        fname = os.path.join(self.runner.workingdir, self.my_name + '.py')
        self.logger.debug(self.my_name + ' read feaModel from ' + str(fname))
        outputs = []
        try:
            f = open(fname, 'r')
            exec(f)
            f.close()

            feaModel = FeaPropertiesInPythonFormat()    
            outputs = self.process_output_from_fea_model(feaModel)

        except IOError as ioe:
            s = self.my_name + ' Error trying to read file ' + fname
            print s
            self.logger.warning(s + str(ioe))
            print sys.exc_info()[0]
            print str(ioe)
        except:
            s = self.my_name + ' exception in read_output'
            print s
            self.logger.warning(s)
        finally:
            return outputs

    def _log_values(self, k, name, lbl, vals):
        self.logger.info(str(k))
        self.logger.info('   ' + str(name))
        self.logger.info('      ' + str(lbl))
        s = '      '
        i = 1
        for v in vals:
            s = s + str(v) + ' '
            if i % 10 == 0:
                self.logger.info(s)
                s = '      '
            i = i + 1
        self.logger.info(s)

    def picklecache(self):
        picklefile = open(self.cachefile, 'w')
        pickle.dump(self.cache, picklefile)
        picklefile.close()

    def execute(self):
        """ Write input, signal ansys to run, read output """
        print 'ANSYSWrapperBase: ' + self.my_name + ': execute start'
        self.logger.debug('ANSYSWrapperBase: ' + self.my_name + ': execute start')    
        if self.ok and self.runner.ok:
            self.logger.debug(self.my_name + ' execute')
            input_cmds = tuple(self.write_input( self.extra_inputs() ))
            if self.cache.has_key(input_cmds):
                self.logger.debug(self.my_name + ' found in cache ' + str(input_cmds) )
                output_tuple = self.cache[input_cmds]
                for o in output_tuple:
                    for k, v in o.iteritems():
                        self.__setattr__(k, v)
                #get value from cache
            else:
                self.write_solution()
                ok = self.runner.run(self.my_name, self.prep7(), self.solution(), self.post())
                if ok:
                    s = self.my_name + ' ok after run'
                    print s
                    self.logger.debug(s)
                    outputs = self.read_output()
                    s = self.my_name + ' after read_output'
                    print s
                    self.logger.debug(s)  
                    if outputs <> None:
                        self.cache[input_cmds] = tuple(outputs)
                        self.picklecache()
                else:
                    s = self.my_name + ' not ok after run'
                    self.logger.warning(s)
                    print s
        print 'ANSYSWrapperBase: ' + self.my_name + ': execute end'
        self.logger.debug('ANSYSWrapperBase: ' + self.my_name + ': execute end')    

    def prep7(self):
        """entry point for derived wrappers to add customization to the /PREP7 section"""
        options = []
        return options

    def solution(self):
        """entry point for derived wrappers to add customization to the /SOL section"""
        options = ['solve \n']
        return options

    def post(self):
        """entry point for derived wrappers to add customization to the /POST section"""
        options = []
        return options

    def extra_inputs(self):
        """entry point so the child class can add extra input to the \*.inp file for Ansys"""
        inputs = []
        return inputs


    def __del__(self):
        #TO_CHECK:  this doesn't seem to get called....
        print 'DELETING AnsysWrapper ' + self.my_name
        self.runner.shutdown()

if __name__ == "__main__": # pragma: no cover         

    testdir = 'C:/Projects1/Louis/beamfiles/'
    name = 'beam1_twoLoads'
    ar = ANSYSRunner(name, testdir, logger_name = 'MSI')
    aw = ANSYSWrapperBase(name + 'C', ar, testdir + 'beam1_twoLoads.db',)

    print ( ar.dump() )
    ar.init_ansys(aw.prep7(), aw.solution(), aw.post())
#    aw.execute()

    aw.write_input()
    aw.runner.run(aw.my_name, aw.prep7(), aw.solution(), aw.post())


    ar.shutdown()

