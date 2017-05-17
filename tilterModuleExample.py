# -*- coding: utf-8 -*-
"""
Created on Wed May 17 10:40:21 2017

@author: Martin Leonhardt (martin.leonhardt87@gmail.com)
"""

from time import sleep, time
from libs.inSpheroChipTilterCore import inSpheroChipTilterCore



# global var for start time of waiting event
sT = None

# to be called when tilting device is waiting on the positive side
def onPosWait():
    print('I am waiting on the positive side...')

# to be called when tilting device moves down on the negative side    
def onNegDown():
    print('I am moving down on the negative side...')

# to be called directly when tilting device is waiting on the negative side to calculate the delay
def onNegWait():
    global sT
    sT = time()

# to be called when tilting device is waiting on the negative side, but delayed by x seconds
def onNegWaitDelay():
    print('I was waiting for %2.3f s to show this.' % (time()-sT))
    
# to be called when tilting device is waiting on the positive side, but only every second time
def onPosWaitEveryTwo():
    print('I am waiting on the positive side...\nBut only every second time I am executed.')


    

# create tilter object and initialize
tilter = inSpheroChipTilterCore()

# reset tilter memory to default values
tilter.ResetTilterSetup()
#tilter.ResetTilterSetup(mode='force')

##############################
### - SET TILTING ANGLES - ###
##############################

# set positive tilting angle to 45 degree
tilter.SetValue('posAngle', 65)
# set negative tilting angle to 30 degree
tilter.SetValue('negAngle', 65)

##############################
### - SET MOTION TIMINGS - ###
##############################

# set positive motion time to 12 sec
tilter.SetValue('posMotion', 10)
# set negative motion time to 15 sec
tilter.SetValue('negMotion', 10)

#############################
### - SET PAUSE TIMINGS - ###
#############################

# set positive waiting time to 30 sec
tilter.SetValue('posPause', '10')
# set negative waiting time to 1:30
tilter.SetValue('negPause', '10')


##############################
### - WRITE TILTER SETUP - ###
##############################

# now let's write the setup to the tilter
tilter.WriteSetup()
#tilter.WriteSetup(mode='force')


##############################
### - START/STOP TILTING - ###
##############################

# start tilting with current setup
tilter.StartTilter()

# sleep for 10 seconds
sleep(10)

# stop tilting
tilter.StopTilter()


#################################
### - DEFINE TILTING EVENTS - ###
#################################
# define event for waiting on the positive side
tilter.SetTilterEvent( 'onPosWait', onPosWait               )

# define event for moving down on the negative side
tilter.SetTilterEvent( 'onNegDown', onNegDown               )

# define event for waiting on the negative side to start the counter for the delay
tilter.SetTilterEvent( 'onNegWait', onNegWait               )

# define event for waiting on the negative side, but delayed by 5 seconds
tilter.SetTilterEvent( 'onNegWait', onNegWaitDelay, delay=5 )

# define stop command when the tilter moves up on the negative side - one cycle finished
#tilter.SetTilterEvent( 'onNegUp'  , tilter.StopTilter       )

# define event to execute the function every second time the tilter is waiting on the positive side
tilter.SetTilterEvent( 'onPosWait', onPosWaitEveryTwo, it=2 )



# start tilting again to see the printouts from the callback functions for the defined events
tilter.StartTilter()



# print current positive angle received from the tilter
print( 'A+ %s' % tilter.GetParameter('A+')   )
 
# print current positive motion time received from the tilter
print( 'M+ %s s' % tilter.GetParameter('M+') )



while tilter.IsTilting():
    print('My pause still takes %s s' % tilter.GetParameter('p'))
    sleep(2)

tilter.__del__()