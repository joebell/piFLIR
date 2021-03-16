# testCamAcq

from flircamera import FlirSystem, FlirCamera
import os
import sys
from datetime import datetime, timedelta
import time
import numpy as np
import threading
import matplotlib.pyplot as plt
import RPi.GPIO as GPIO

# Setup a Raspberry Pi GPIO pin for output
pinNumber = 21

# Loop for thread for triggering
def triggerLoop(camera, nFrames, frameRate):

    print('Starting triggerLoop() thread...')

    # Setup a Raspberry Pi GPIO pin for output
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pinNumber, GPIO.OUT)
    GPIO.output(pinNumber, GPIO.LOW)

    frameN = 0
    lastTime = datetime.now()
    while (frameN < nFrames):
        nowTime = datetime.now()
        if ((nowTime - lastTime).total_seconds()) >= (1.0/frameRate):
            # Execute software trigger
            GPIO.output(pinNumber, GPIO.HIGH)
            camera.triggerCmd.Execute()
            GPIO.output(pinNumber, GPIO.LOW)
            lastTime += timedelta(seconds=1.0/frameRate)
            frameN += 1
    return
   
def test(nFrames, frameRate):
    result = True

    fs = FlirSystem()
    camera = fs.cameras[0] 

    camera.cam.BeginAcquisition()

    # Setup a thread to manage software triggering
    # Switch between threads every 100 us
    loopThread = threading.Thread(target=triggerLoop, args=[camera, nFrames, frameRate])
    sys.setswitchinterval(.0001)
    loopThread.start()

    acqTimes = []

    frameBuffer = np.zeros((nFrames,1920*1200),dtype=np.uint8)
    lastTime = datetime.now()
    frameN = 0
    while (frameN < nFrames):
        #  Retrieve next received image
        try:
            image_result = camera.cam.GetNextImage(1000) # Grab timeout 
           
            # Pull the data into a pre-allocated numpy array, works well to 120 Hz, not 150 Hz
            frameBuffer[frameN] = image_result.GetData()
            image_result.Release()

            nowTime = datetime.now()
            acqTimes.append((nowTime - lastTime).total_seconds())
            lastTime = nowTime
            frameN += 1
        except:
            print('Acquisition timeout on frameN: %d' % (frameN))
            break

    print('Acquired %d frames.' % frameN)
    loopThread.join()

    camera.cam.EndAcquisition()
    del camera
    del fs

    print('Std: %.4f' % np.std(acqTimes))
    
    return np.std(acqTimes)

def main():
    
    nFrames = 1000
    frameRates = []
    frameRates.extend(range(30,130,10))

    stdTimes = [] 
    for frameRate in frameRates:
        stdTimes.append(test(nFrames,frameRate))

    plt.plot(frameRates, stdTimes)
    plt.xlabel('Frame rate (Hz)');
    plt.ylabel('Std(frame interval) (s)')
    plt.show()
    

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)

