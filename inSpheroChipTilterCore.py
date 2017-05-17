# -*- coding: utf-8 -*-
"""
Created on Wed Apr 26 09:49:58 2017

@author: Martin Leonhardt (martin.leonhardt87@gmail.com)
"""

import threading

from time import sleep

import coreUtilities as coreUtils
from ComDevice import ComDevice




class inSpheroChipTilterCore(ComDevice):

    # HEX addresses for certain commands
    # for check sum calculation address needs to be stored as two individual bytes
    _addresses = {
            'posAngle'   : ['0xFF', '0x00'],
            'negAngle'   : ['0xFF', '0x01'],
            'posMotSec'  : ['0xFF', '0x02'],
            'negMotSec'  : ['0xFF', '0x03'],
            'posPauseMin': ['0xFF', '0x04'],
            'negPauseMin': ['0xFF', '0x05'],
            'posPauseSec': ['0xFF', '0x06'],
            'negPauseSec': ['0xFF', '0x07'],
            'horPauseMin': ['0xFF', '0x08'],
            'horPauseSec': ['0xFF', '0x09'],
            'totTimeHrs' : ['0xFF', '0x0A'],
            'totTimeMin' : ['0xFF', '0x0B'],
            'status'     : ['0xFF', '0x0C']
        }
    
    # status bits
    # NOTE: single bits should not touch other values (overwrite)
    #       use OR to set
    #       use ~ to unset
    _statusBits = {
            'stopTilter'  : 0x00,
            'startTilter' : 0x01,
            'plusMinusOff': 0x00,
            'plusMinusOn' : 0x04,
            'resetErrors' : 0x08,
            'soundOff'    : 0x10,
            'tryReconnect': 0x80,
            'noControl'   : 0x00
        }
        
    # parameters received from the tilter
    _parameters = ['ID', 'A+', 'A-', 'M+', 'M-', 'm', 'P+', 'P-', 'p', 'H', 'T', 't', 'S']

    # supported events for callback functions
    _supportedEvents = ['onPosDown', 'onPosUp', 'onNegDown', 'onNegUp', 'onPosWait', 'onNegWait']
        
    # titler can be auto detected through this string
    _usbName = 'USB Serial Port'
    
### -------------------------------------------------------------------------------------------------------------------------------
    
    def __init__(self, **flags):
        
        # check given parameters
        if 'coreStartTime' in flags.keys():
            self.coreStartTime = flags['coreStartTime']
        else:
            self.coreStartTime = coreUtils.GetDateTimeAsString()
            
            
        
        # initialize logger
        if 'logger' in flags.keys():
            self.logger  = flags['logger']
        elif 'logToFile' in flags.keys():
            if flags['logToFile']:
                if 'logFile' in flags.keys():
                    self.logFile = flags['logFile']
                else:
                    self.logFile = 'session_' + self.coreStartTime + '.log'
                    
                self.logger = coreUtils.InitLogger(self.logFile, __name__)
            else:
                self.logger = coreUtils.InitLogger(caller=__name__)
        else:
            self.logger  = coreUtils.InitLogger(caller=__name__)


            
        # setup, if not already done
        if 'comPort' in flags.keys():
            self.comPort = flags['comPort']
        else:
            ComDevice.__init__(self, self._usbName, flags, 'Try to detect inSphero chip tilter...', self.logger)
        
        
        
        
        
        # to stop while loop for reading tilter stream
        self.stopReading     = True
        self.inMessageThread = None
        
        # structure with default values
        self.setup = self.GetDefaultSetup()
        
        self.resetStream = self.GetResetStream()
        
        # in case multiple setups have to be written
        self.setups = []
        
        # list for messages received from the tilter
        self.inMessageQueue = []
        
        # for counting the performed cycles and detecting the position
        self.tilterState = self.GetDefaultTilterState()
        
        # define tilting events
        # internally handled as list to enable multiple function calls for one event (see SetEventHandler)
        self.tilterEvents = self.GetDefaultEventDescriptors()
        
        self.currentParameterSet = self.GetDefaultParameterSet()

### -------------------------------------------------------------------------------------------------------------------------------

    def __del__(self):
        
        # to stop while loop for reading tilter stream
        self.stopReading = True
        
        # just to be save that function execution is over
        sleep(50e-3)
        
        if self.inMessageThread:
            self.inMessageThread.join()
        
        ComDevice.__del__(self, __name__)
        
        # close logger handle
        coreUtils.TerminateLogger(__name__)
        
        
        
        
        
### -------------------------------------------------------------------------------------------------------------------------------
    #######################################################################
    ###               --- TILTER MEMORY AND COMMANDS ---                ###
    #######################################################################
### -------------------------------------------------------------------------------------------------------------------------------
    
    def GenerateByteStream(self, address, value):
    
        command = []
        
        # calculate sum over first three bytes: 2 address bytes + load
        checkSum = int(address[0], 16) + int(address[1], 16) + value
        # take least 8 bits and hexlify
        checkSum = format(checkSum & 0xFF, '#04x')
        # generate command by concatenating bytes, check sum and '#'
        command.append( address[0]            )
        command.append( address[1]            )
        command.append( format(value, '#04x') )
        command.append( checkSum              )
        command.append( hex(ord('#'))         )
        # remove all the nasty '0x' from hex numbers to send clean command
        command = ''.join(command).replace('0x','')
        
        # convert to bytes for sending
        return int(command, 16).to_bytes(5, 'big');
    
### -------------------------------------------------------------------------------------------------------------------------------
    
    def ConvertSetupToStream(self, key, val):
        
        if val != -1:
            self.setup['byteStream'] += self.GenerateByteStream(key, val)
        
### -------------------------------------------------------------------------------------------------------------------------------

    def WriteValueToAddress(self, address, value):
        
        if self.SaveOpenComPort():
            self.WriteStream(self.GenerateByteStream(address, value))
            
            self.SaveCloseComPort()
        
### -------------------------------------------------------------------------------------------------------------------------------

    def WriteSetup(self):
        
        success = False
        
        if self.SaveOpenComPort():
            
            success = self.WriteStream(self.setup['byteStream'])
                
            if not self.SaveCloseComPort():
                success = False
            
        return success
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetResetStream(self):
        
        stream = bytes()
        
        for key, address in self._addresses.items():
            # set following ones to 1 otherwise tilter will get crazy
            if key in ['posAngle', 'negAngle', 'posMotSec', 'negMotSec']:
                stream += self.GenerateByteStream(address, 1)
            else:
                stream += self.GenerateByteStream(address, 0)
                
        return stream
        
    
### -------------------------------------------------------------------------------------------------------------------------------

    def ResetTilterMemory(self):
        
        success = False
        
        if self.SaveOpenComPort():
            
            success = self.ForceWriteStream(self.resetStream)
                    
            if self.SaveCloseComPort():
                self.logger.info('Tilter memory was reset to default.')
                success = True
                
        return success
    
### -------------------------------------------------------------------------------------------------------------------------------

    def ForceWriteStream(self, b):
        
        success = True
        
        # write multiple time to force tilter to accept stream
        for i in range(3):
            if not self.WriteStream(b):
                success = False
                break
            
        return success
    
### -------------------------------------------------------------------------------------------------------------------------------

    def WriteStream(self, b):
        
        success = True
        
        if self.comPortStatus:
            if self.SaveWriteToComPort(b):
                sleep(.05)
                self.logger.debug( 'Sent %s to tilter' % coreUtils.GetTextFromByteStream(b) )
            else:
                success = False
                
        return success
    
### -------------------------------------------------------------------------------------------------------------------------------

    def ReadStream(self):
        
        if self.SaveOpenComPort():
            
            # reset tilter state for new run
            self.tilterState = self.GetDefaultTilterState()
            
            while not self.stopReading:
                
                # after splitting last entry in list is always emtpy, if character was in stream
                # check for this, otherwise wait for new input
                inMsg = self.SaveReadFromComPort('line', decode=True, leaveOpen=True)
                
                if len(inMsg) != 0:
                    self.HandleInMessageQueue(inMsg)
                        
            
                # message are sent every 2s by the tilter
                sleep(1)
        
            # properly close port
            self.SaveCloseComPort()
    
### -------------------------------------------------------------------------------------------------------------------------------

    def HandleInMessageQueue(self, msg):
        
        # store for later handling, if no delimiter was found
        self.inMessageQueue.append(msg)
        
        msgStr = ''.join(self.inMessageQueue)
        
        # is '#' in stream? -> complete message
        if '#' in msgStr:
            
            # in case multiple readings where necessary flatten list to string
            # split again at correct positions with '#'
            # also multiple messages can be handled
            self.inMessageQueue = msgStr.split('#')
            
            while len(self.inMessageQueue) != 0:
                
                # get first message
                msg = self.inMessageQueue.pop(0)
                
                # read parameter values from last message and fill variable
                self.ExtractParameters(msg)
                
                # check pause time
                if self.currentParameterSet['p'] > 0:
                    
                    # only then update the waiting position
                    if not self.tilterState['isWaiting']:
                        # first wait is on positive side
                        if not self.tilterState['posWait']:
                            self.tilterState['posWait'] = True
                            
                            self.EventHandler('onPosWait')
                        
                        # then on the negative side
                        elif self.tilterState['posWait']:
                            self.tilterState['posWait'] = False
                            self.tilterState['negWait'] = True

                            self.EventHandler('onNegWait')
                            
                        self.tilterState['isMoving']  = False
                        self.tilterState['isWaiting'] = True
                        
                # check motion time
                if self.currentParameterSet['m'] > 0:
                    
                    # only then update the moving direction
                    if not self.tilterState['isMoving']:
                        # start with the first movement -> always the positive angle
                        if not any( [self.tilterState['posDown'], self.tilterState['posUp'], self.tilterState['negDown'], self.tilterState['negUp']] ):
                            self.tilterState['posDown'] = True

                            self.EventHandler('onPosDown')
                        
                        # return from waiting on positive side
                        elif self.tilterState['posDown']:
                            self.tilterState['posDown'] = False
                            self.tilterState['posUp']   = True

                            self.EventHandler('onPosUp')
                        
                        # return from waiting on negative side
                        elif self.tilterState['negDown']:
                            self.tilterState['negDown'] = False
                            self.tilterState['negUp']   = True

                            self.EventHandler('onNegUp')
                            
                    
                        # update states
                        self.tilterState['isMoving']  = True
                        self.tilterState['isWaiting'] = False
                            
                    # there might be a transition from up to down if there's not horizontal waiting...
                    # can be detected if the new time if larger than the old one
                    elif self.tilterState['isMoving'] and self.currentParameterSet['m'] > self.tilterState['moveTime']:
                        
                        # transition from posUp to negDown
                        if self.tilterState['posUp']:
                            self.tilterState['posUp']   = False
                            self.tilterState['negDown'] = True

                            self.EventHandler('onNegDown')
                        
                        # transition from negUp to posDown
                        # also we have a full cycle
                        elif self.tilterState['negUp']:
                            self.tilterState['negUp']      = False
                            self.tilterState['posDown']    = True
                            self.tilterState['numCycles'] += 1

                            self.EventHandler('onPosDown')
                        

                    # set new 'old' value for next comparision
                    self.tilterState['moveTime']  = self.currentParameterSet['m']
    
### -------------------------------------------------------------------------------------------------------------------------------

    def ExtractParameters(self, msg):
        
        for key in self._parameters:
            paramSet = msg.split(';')
            for param in paramSet:
                if key in param:
                    val = param.split(key)[-1]
                    
                    try:
                        val = int(val)
                    except ValueError:
                        self.logger.error('Could not extract number from %s' % param)
                    else:
                        self.currentParameterSet[key] = val
    
### -------------------------------------------------------------------------------------------------------------------------------

    def EventHandler(self, event):
        
        # call user defined function
        if self.tilterEvents[event]['defined']:
            
            for funcIdx in range(self.tilterEvents[event]['numFuncs']):
            
                # increment iteration counter
                self.tilterEvents[event]['itercnt'][funcIdx] += 1

                if self.tilterEvents[event]['itercnt'][funcIdx] == self.tilterEvents[event]['itercnt'][funcIdx]:
                    
                    # callback function
                    # if delay is zero, directly call callback
                    if self.tilterEvents[event]['delay'][funcIdx] == 0:
                        self.tilterEvents[event]['cb'][funcIdx]()
                    # otherwise use DelayEvent
                    else:
                        self.eventThread = threading.Thread(target=lambda event=event, func=funcIdx: self.DelayEvent(event, func))
                        self.eventThread.start()
                        self.eventThread.join()
                    
                    
                    # reset iteration counter
                    self.tilterEvents[event]['itercnt'][funcIdx] = 0
    
### -------------------------------------------------------------------------------------------------------------------------------

    def DelayEvent(self, event, func):
        # wait for delay
        sleep(self.tilterEvents[event]['delay'][func])
        # execute after waiting time
        self.tilterEvents[event]['cb'][func]()
    
### -------------------------------------------------------------------------------------------------------------------------------

    def StartTilter(self):
        
        success = True
        
        if not self.comPortStatus:
            self.logger.error('Attempting to start tilter, without proper initialization! Check connection to inSphero tilter!')
            success = False
            
        # com port status is OK
        else:
            
            if self.SaveOpenComPort():
                
                # try to start tilter
                success = self.WriteStream( self.GenerateByteStream(self._addresses['status'], self._statusBits['startTilter']) )
                    
                self.SaveCloseComPort()
                
                if success:
                    self.logger.info('Started tilting.')
                    
                    # initialize new thread
                    self.inMessageThread = threading.Thread(target=self.ReadStream)
                    # once message thread is started loop is running till StopTilter() was called
                    self.stopReading = False
                    # start parallel thread
                    self.inMessageThread.start()
        
        return success
    
### -------------------------------------------------------------------------------------------------------------------------------

    def StopTilter(self):
        
        success = True
        
        if not self.comPortStatus:
            self.logger.error('Could not stop tilting! Check connection to inSphero tilter!')
            success = False
            
        # com port status is OK
        else:
            
            if self.SaveOpenComPort():
                
                # try to stop tilter
                success = self.WriteStream( self.GenerateByteStream(self._addresses['status'], self._statusBits['stopTilter']) )
                    
                self.SaveCloseComPort()
                
                if success:
                    self.logger.info('Stopped tilting.')
            
        # even if something is wrong stop thread
        if not self.stopReading:
            self.stopReading = True
            # end message thread
            self.inMessageThread.join()
            
        return success
        
                
                
                
                
### -------------------------------------------------------------------------------------------------------------------------------
    #######################################################################
    ###                    --- SET/GET FUNCTIONS ---                    ###
    #######################################################################
### -------------------------------------------------------------------------------------------------------------------------------

    def SetValue(self, key, val):
        
        if key in self.setup.keys():
            
            if key not in ['byteStream', 'posPauseRaw', 'negPauseRaw']:
                try:
                    val = int(val)
                except ValueError:
                    self.logger.error('Could not convert \'%s\' to integer' % val)
                else:
                    if key in ['posAngle', 'negAngle', 'posMotSec', 'negMotSec'] and val < 1:
                        val = 1
                        
                    self.setup.update        ( {key: val}                )
                    self.ConvertSetupToStream( self._addresses[key], val )
                    
            elif key in ['posPauseRaw', 'negPauseRaw']:
                
                mins, secs = coreUtils.GetMinSecFromString(val)
                
                if key == 'posPauseRaw':
                    self.setup.update( {'posPauseMin': mins} )
                    self.setup.update( {'posPauseSec': secs} )
                    
                    self.ConvertSetupToStream( self._addresses['posPauseMin'], mins )
                    self.ConvertSetupToStream( self._addresses['posPauseSec'], secs )
                else:
                    self.setup.update( {'negPauseMin': mins} )
                    self.setup.update( {'negPauseSec': secs} )
                    
                    self.ConvertSetupToStream( self._addresses['negPauseMin'], mins )
                    self.ConvertSetupToStream( self._addresses['negPauseSec'], secs )
        
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetValue(self, key):
            
        if key in self.setup.keys():
            return self.setup[key]
        else:
            self.logger.error('%s not in setup' % key)
        
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetParameter(self, key):
            
        if key in self._parameters:
            return self.currentParameterSet[key]
        else:
            self.logger.error('%s not in parameter set' % key)
        
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetParameters(self):
        return self.currentParameterSet
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetDefaultSetup(self):
        return {
            'posAngle'   : -1,
            'negAngle'   : -1,
            'posMotSec'  : -1,
            'negMotSec'  : -1,
            'posPauseRaw': '',
            'posPauseMin': -1,
            'posPauseSec': -1,
            'negPauseRaw': '',
            'negPauseMin': -1,
            'negPauseSec': -1,
            'horPauseMin': -1,
            'horPauseSec': -1,
            'totTimeRaw' : '',
            'totTimeHrs' : -1,
            'totTimeMin' : -1,
            'status'     : -1,
            'byteStream' : bytes(), # each setup should have it's own stream
            'numCycles'  : -1       # also each setup should store the number of cycles it's active
        }
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetDefaultTilterState(self):
        return {
            'isMoving' : False,
            'posDown'  : False,
            'posUp'    : False,
            'negDown'  : False,
            'negUp'    : False,
            'isWaiting': False,
            'posWait'  : False,
            'negWait'  : False,
            'moveTime' : 0,
            'waitTime' : 0,
            'numCycles': 0
        }
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetDefaultEventDescriptors(self):
        
        d = {}
        
        for k in self._supportedEvents:
            d.update( {k: self.GetDefaultEventDescriptor()} )
            
        return d
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetDefaultEventDescriptor(self):
        return {'defined': False, 'numFuncs': 0, 'cb': [], 'iter': [], 'itercnt': [], 'delay': []}
    
### -------------------------------------------------------------------------------------------------------------------------------

    def GetDefaultParameterSet(self):
        
        d = {}
        
        for k in self._parameters:
            d.update({k: 0})
            
        return d

### -------------------------------------------------------------------------------------------------------------------------------

    def SetTilterEvent(self, event, cb, it=1, delay=0):
        
        if event in self.tilterEvents.keys():
            self.tilterEvents[event]['defined'] = True
            
            # append new function to list, if not already exists
            if cb not in self.tilterEvents[event]['cb']:
                self.tilterEvents[event]['cb'].append     ( cb    )
                self.tilterEvents[event]['iter'].append   ( it    )
                self.tilterEvents[event]['itercnt'].append( 0     )
                self.tilterEvents[event]['delay'].append  ( delay )
                # increment func counter
                self.tilterEvents[event]['numFuncs'] += 1

            # if already exist, update values
            else:
                # find index of current callback in list
                for idx in range(self.tilterEvents[event]['numFuncs']):
                    if self.tilterEvents[event]['cb'][idx] == cb:
                        break
                    
                self.tilterEvents[event]['iter'][idx]    = it
                self.tilterEvents[event]['itercnt'][idx] = 0
                self.tilterEvents[event]['delay'][idx]   = delay
    
### -------------------------------------------------------------------------------------------------------------------------------

    def UnsetTilterEvent(self, event, func=None):
        
        if event in self.tilterEvents.keys():
            if func:
                for idx in range(self.tilterEvents[event]['numFuncs']):
                    if self.tilterEvents[event]['cb'][idx] == func:
                        self.tilterEvents[event]['cb'].pop     ( idx )
                        self.tilterEvents[event]['iter'].pop   ( idx )
                        self.tilterEvents[event]['itercnt'].pop( idx )
                        self.tilterEvents[event]['delay'].pop  ( idx )
                        # decrement func counter
                        self.tilterEvents[event]['numFuncs'] -= 1
                        break
                        
                if self.tilterEvents[event]['numFuncs'] == 0:
                    self.tilterEvents[event]['defined'] = False
                    
            # undefine all functions
            else:
                self.tilterEvents[event] = self.GetDefaultEventDescriptor()