# TutorApp.py
#A typing tutor app to teach Quirkey/Microwriter character chords
# (c)2023 vik@diamondage.co.nz
# Uses graphics.py from https://pypi.org/project/graphics.py
# Documentation at https://mcsp.wartburg.edu/zelle/python/graphics/graphics/graphref.html
# This file may be copied into the current directory if you can't install libraries
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.
#
import time
from graphics import *
import random

# Basic alphanumerics
alphaTable = " eiocadsktrny.fuhvlqz-'gj,wbxmp"
numericTable = " 120(*3$/+;\"?.46-&#)%!@7=,:8x95"

# Relative locations for coloured keycaps
keycapList=[[[0,0],"red"],
            [[40,120],"orange"],
            [[90,140],"yellow"],
            [[140,130],"lime"],
            [[190,100],"blue"],
            [[50,0],"black"]
            ]

win = GraphWin("Quirkey Typing Tutor",1000,600) # create a window
win.setCoords(0, 0, 1000, 600) # set the coordinates of the window; bottom left is (0, 0) and top right is (10, 10)

# Create a set of keycaps
def createKeycaps(offsetx,offsety):
    l=[]    # Temporary list of keycaps to return
    for k in keycapList:
        keySquare=Rectangle(Point(k[0][0]+offsetx,k[0][1]+offsety),Point(k[0][0]+40+offsetx,k[0][1]+40+offsety))
        keySquare.setFill(k[1])
        l.append(keySquare)
    return(l)

# Blank all the keycaps
def blankKeys():
    for k in keycaps:
        k.setFill("white")

# Draw the key pattern for the specified character
def drawKeyPattern(c):
    if c == "space":
      c = " "

    loc=alphaTable.find(c)+1
    i=0
    while loc > 0:
        r = loc & 1
        loc = int(loc / 2)
        if r == 1:
            keycaps[i].setFill(keycapList[i][1])
        i += 1

def pressThisKey(char):
    if char == " ":
        cs = "space"
        target = "space"
    elif char == ",":
        cs = ","
        target = "comma"
    elif char == ".":
        cs = "."
        target = "period"
    elif char == "'":
        cs = "apostrophe"
        target = cs
    else:
        cs = char.upper()
        target = char

    message.setText("Press the \""+cs+"\" pattern\n")
    c=win.getKey().lower()

    drawKeyPattern(char);
    if c == target:
        message.setText("Correct!\n")
        time.sleep(1)
        blankKeys()
        return

    message.setText("Try this pattern\n")
    time.sleep(2.5)
    blankKeys()
    message.setText("Press the \""+cs+"\" pattern\n")
    c=win.getKey().lower()

    if c == target:
        drawKeyPattern(char);
        message.setText("Much better!\n")
        time.sleep(1.5)
        blankKeys()
        return

    drawKeyPattern(char);
    message.setText("Here's the pattern for \""+cs+"\"\n")

    while c != target:
      print("Seeking ", target, ", got ",c)
      c=win.getKey().lower()

    message.setText("That's the one!\n")
    time.sleep(1.5)
    blankKeys()

# Create a random sequence taken from the supplied string
def pressTheseKeys(s):
  i=0
  while i < len(s):
	  pressThisKey(s[random.randint(0,len(s)-1)])
	  i += 1


keycaps=createKeycaps(650,390)
random.seed()

# grand opening of the display
# Add a blank line, or it'll chop off the descendersoeoo        oessmm  ipfoagtet
message = Text(Point(270,400), "Welcome to Quirkey Tutor\n")
message.setSize(29)
message.draw(win)

# Draw the coloured keycaps
for k in keycaps:
    time.sleep(0.1)
    k.draw(win)

time.sleep(2.5)
# Set the key colours all blank
blankKeys()

# Prompt the user for a key
pressTheseKeys("atleathnlbdithljpabcdefghijklmnopqrstuvwxys")

win.close()
