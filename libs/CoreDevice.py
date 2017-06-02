# -*- coding: utf-8 -*-
"""
Created on Wed May 31 14:08:55 2017

@author: localadmin
"""


# in case this guy is used somewhere else
# we need different loading of modules
try:
    from libs.ComDevice import ComDevice
except ImportError:
    from ComDevice import ComDevice
    
try:
    from libs.Logger import Logger
except ImportError:
    from Logger import Logger

try:
    from libs import coreUtilities as coreUtils
except ImportError:
    import coreUtilities as coreUtils
    
    

class CoreDevice(ComDevice, Logger):
    
    def __init__(self, coreStartTime=None, **flags):
        
        self.coreStartTime = coreStartTime if coreStartTime else coreUtils.GetDateTimeAsString()
        logFile            = flags.get( 'logFile'       )
        logLevel           = flags.get( 'logLevel'      )
        detCallback        = flags.get( 'detCallback'   )
        onDetCallback      = flags.get( 'onDetCallback' )
        
        if detCallback:
            flags.pop('detCallback')
        if onDetCallback:
            flags.pop('onDetCallback')
        
        # initialize logger
        Logger.__init__(self, logFile=logFile, logLevel=logLevel, startTime=self.coreStartTime)
        
        # initialize com port
        ComDevice.__init__(self, detCallback, onDetCallback, **flags)

### -------------------------------------------------------------------------------------------------------------------------------

    def __del__(self):
        
        ComDevice.__del__(self)
        Logger.__del__(self)