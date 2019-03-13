#!/usr/bin/env python3
import logging
import sys
import streamlink
import numpy as np
import os.path
import time
import math
import win32gui, win32ui, win32con, win32api

try:
    import cv2
except ImportError:
    sys.stderr.write("requires opencv-python")
    raise

threshold = [0.75,0.55,0.7,0.7,0.7,0.75,0.75,0.7,0.78,0.7]

P1p = 0
P2p = 0

class winCapture:
    def __init__(self):
        self.hwnd = win32gui.FindWindow(None, r'Twitch - Google Chrome')
        self.w = 0
        self.h = 0
        self.inner_w = 0
        self.inner_h = 0
        self.hwndDC = win32gui.GetWindowDC(self.hwnd)
        self.mfcDC = win32ui.CreateDCFromHandle(self.hwndDC)
        self.saveDC = self.mfcDC.CreateCompatibleDC()

    def getSize(self):
        left, top, right, bot = win32gui.GetWindowRect(self.hwnd)
        self.w = right - left
        self.h = bot - top
        #print (left, top, right, bot)
        left, top, right, bot = win32gui.GetClientRect(self.hwnd)
        self.inner_w = right - left
        self.inner_h = bot - top
        #print (left, top, right, bot)
   
    def getframe(self):
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(self.mfcDC, self.w, self.h)
        self.saveDC.SelectObject(saveBitMap)
        self.saveDC.BitBlt((0, 0), (self.w, self.h), self.mfcDC, (0, 0), win32con.SRCCOPY)
        #saveBitMap.SaveBitmapFile(self.saveDC, 'test.jpg')
        signedIntsArray = saveBitMap.GetBitmapBits(True)
        img = np.frombuffer(signedIntsArray, dtype='uint8')
        img.shape = (self.h,self.w,4)
        win32gui.DeleteObject(saveBitMap.GetHandle())
        chromeUrlBar = 37
        # border
        x = math.floor((self.w - self.inner_w)/2)
        # border & chromeUrlBar
        y = self.h - self.inner_h - x + chromeUrlBar
        w = self.inner_w
        h = self.inner_h - chromeUrlBar
        img = img[y:y+h, x:x+w]
        return (img,
        img[int(h*0.85):int(h*0.922), int(w*0.26):int(w*0.353)],
        img[int(h*0.85):int(h*0.922), int(w*0.644):int(w*0.737)])
        
    def stop(self):
        self.mfcDC.DeleteDC()
        self.saveDC.DeleteDC()
        win32gui.ReleaseDC(self.hwnd, self.hwndDC)

def convertBW(input):
    frame = input.copy()
    frame[:, :, 1] = 0
    frame[:, :, 0] = 0
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame = cv2.threshold(frame, 128, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    return frame

def matchTemplate(template, percent):
    percent = cv2.resize(percent, (200, 44), interpolation=cv2.INTER_CUBIC)
    tw, th = template[0].shape[::-1]
    fw = percent.shape[::-1][0]
    global P1p
    global P2p
    p1Percent = 0
    p2Percent = 0
    mask = np.zeros(percent.shape[:2], np.uint8)
    for tempNum in [9,8,7,6,5,4,3,2,1,0]:
        res = cv2.matchTemplate(percent,template[tempNum],cv2.TM_CCOEFF_NORMED)
        loc = np.where( res >= threshold[tempNum])
        for pt in zip(*loc[::-1]):
            if mask[int(pt[1] + th/2), int(pt[0] + tw/2)] != 255:
                mask[pt[1]:pt[1]+th, pt[0]:pt[0]+tw] = 255
                if pt[0] > 0.7*fw:
                    if (tempNum == 0) and (p2Percent ==0) and (P2p!=0):
                        P2p = 0
                        print(P1p,P2p)
                    p2Percent += tempNum
                elif pt[0] > 0.6*fw:
                    p2Percent += tempNum*10
                elif pt[0] > 0.5*fw:
                    p2Percent += tempNum*100
                elif pt[0] > 0.25*fw:
                    if (tempNum == 0) and (p1Percent ==0) and (P1p!=0):
                        P1p = 0
                        print(P1p,P2p)
                    p1Percent += tempNum
                elif pt[0] > 0.1*fw:
                    p1Percent += tempNum*10
                elif pt[0] > 0:
                    p1Percent += tempNum*100

    if p1Percent > P1p and (p1Percent - P1p < 100):
        P1p = p1Percent
        print(P1p,P2p)
    if p2Percent > P2p and (p2Percent - P2p < 100):
        P2p = p2Percent
        print(P1p,P2p)
    return percent

def main():
    win = winCapture()
    win.getSize()
    fps = 30
    frame_time = int((1.0 / fps) * 1000.0)
    template = []
    for num in range(10):
        template.append(cv2.imread('./template/'+str(num)+'.png',0))
    while True:
        try:
            (frame,frame_1p,frame_2p) = win.getframe()
            frame_p = np.concatenate((frame_1p, frame_2p), axis=1)
            percent = convertBW(frame_p)
            matchTemplate(template, percent)
            #cv2.imshow('frame', frame)

            frame_p = cv2.resize(frame_p, (0,0), fx=3, fy=3)
            cv2.imshow('percent', frame_p)
            if cv2.waitKey(frame_time*10) & 0xFF == ord('q'):
                win.stop()
                break
        except KeyboardInterrupt:
            win.stop()
            break
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()