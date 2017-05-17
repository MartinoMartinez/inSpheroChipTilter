# -*- coding: utf-8 -*-
"""
Created on Wed May 17 10:40:21 2017

@author: Martin Leonhardt (martin.leonhardt87@gmail.com)
"""

import tkinter as tk

from libs.inSpheroChipTilterCore import inSpheroChipTilterCore

class tilterControllerApp(inSpheroChipTilterCore):

    def __init__(self, master):
        
        self.master = master
        
        # initialize the tilter core
        inSpheroChipTilterCore.__init__(self)
        
        # check whether GUI is about to close
        master.protocol('WM_DELETE_WINDOW', self.onClose)


        ##############################
        ### - SET TILTING ANGLES - ###
        ##############################
        
        # set positive tilting angle to 45 degree
        self.SetValue('posAngle', 45)
        # set negative tilting angle to 30 degree
        self.SetValue('negAngle', 30)
        
        ##############################
        ### - SET MOTION TIMINGS - ###
        ##############################
        
        # set positive motion time to 12 sec
        self.SetValue('posMotion', 12)
        # set negative motion time to 15 sec
        self.SetValue('negMotion', 15)
        
        #############################
        ### - SET PAUSE TIMINGS - ###
        #############################
        
        # set positive waiting time to 30 sec
        self.SetValue('posPause', '30')
        # set negative waiting time to 1:30
        self.SetValue('negPause', '1:30')
        
        
        # now let's write the setup to the tilter
        self.WriteSetup()
        #self.WriteSetup(mode='force')
        
        
        
        #################################
        ### - DEFINE GUI COMPONENTS - ###
        #################################
        
        # create three buttons: reset, start, stop tilter
        self.resetButton = tk.Button( master, text='Reset tilter' )
        self.startButton = tk.Button( master, text='Start tilter' )
        self.stopButton  = tk.Button( master, text='Stop tilter'  )
        
        # define functions that should be executed when button is clicked
        self.resetButton.config( command=self.onResetClick )
        self.startButton.config( command=self.onStartClick )
        self.stopButton.config ( command=self.onStopClick )
        
        # place the buttons on the window
        self.resetButton.pack()
        self.startButton.pack()
        self.stopButton.pack()
        
    
    def __del__(self):
        inSpheroChipTilterCore.__del__(self)
        
        
    def onResetClick(self):
        self.ResetTilterSetup()
        
    def onStartClick(self):
        self.StartTilter()
        
    def onStopClick(self):
        self.StopTilter()
        
    def onClose(self):
        if self.IsTilting():
            self.StopTilter()
        
        # close GUI
        self.master.destroy()


if __name__ == '__main__':
    
    # define GUI master window
    master = tk.Tk()
    
    # set window title
    master.title('ParaLyzer App')
    
    # initialize controller app
    tilterControllerApp(master)
    
    # start mainloop and show window
    master.mainloop()