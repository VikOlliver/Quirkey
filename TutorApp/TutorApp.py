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

# This holds the displayed shift keys
shiftKeysLayout=[]

win = GraphWin("Quirkey Typing Tutor",1000,600) # create a window
win.setCoords(0, 0, 1000, 600) # set the coordinates of the window; bottom left is (0, 0) and top right is (10, 10)

###############################################################################
# Fiddleage to set the text justification in graphics.py
def setJustify(self, option):
    if not option in ["left", "center", "right"]:
        raise GraphicsError(BAD_OPTION)
    self._reconfig("justify", option)


###############################################################################
# Create a set of keycaps somewhere on the screen
def createKeycaps(offsetx,offsety):
    l=[]    # Temporary list of keycaps to return
    for k in keycapList:
        keySquare=Rectangle(Point(k[0][0]+offsetx,k[0][1]+offsety),Point(k[0][0]+40+offsetx,k[0][1]+40+offsety))
        keySquare.setFill(k[1])
        l.append(keySquare)
    return(l)

###############################################################################
# Blank all the keycaps
def blankKeys(keyList):
    for k in keyList:
        k.setFill("white")

###############################################################################
# Draw the key pattern for the specified character
def drawKeyPattern(c):
    if c == "space":
      c = " "

    # Check the alpha table first
    loc=alphaTable.find(c)+1
    # If no joy, check the numeric table
    if loc == 0:
      loc=numericTable.find(c)+1
    i=0
    while loc > 0:
        r = loc & 1
        loc = int(loc / 2)
        if r == 1:
            keycaps[i].setFill(keycapList[i][1])
        i += 1

###############################################################################
# Converts a character to the string that the graphics program weirdly
# converts into character strings. a "," becomes "comma" etc.
def weirdCharConvert(char):
    if char == " ":
        target = "space"
    elif char == ",":
        target = "comma"
    elif char == ".":
        target = "period"
    elif char == "'":
        target = "apostrophe"
    elif char == "!":
        target = "exclam"
    elif char == "?":
        target = "question"
    elif char == ":":
        target = "colon"
    elif char == ";":
        target = "semicolon"
    else:
        target = char
    return target

###############################################################################
# Get a keystroke from window w, filtering out any control or shift key codes
def filteredKey(w):

  while True:
    s=w.getKey()
    # Any simple character can be returned off the bat.
    if len(s) == 1:
      break
    # See if it's a controlley shiftey thing, which has an underscore in
    if s.find("_") < 0:
      break

  return s

###############################################################################
def pressThisKey(char):

    target = weirdCharConvert(char)
    cs = char.upper()
    alphaMessage.setText("Press the \""+cs+"\" pattern\n")
    c=win.getKey().lower()

    drawKeyPattern(char);
    if c == target:
        alphaMessage.setText("Correct!\n")
        time.sleep(1)
        blankKeys(keycaps)
        return

    alphaMessage.setText("Try this pattern\n")
    time.sleep(2.5)
    blankKeys(keycaps)
    alphaMessage.setText("Press the \""+cs+"\" pattern\n")
    c=win.getKey().lower()

    if c == target:
        drawKeyPattern(char);
        alphaMessage.setText("Much better!\n")
        time.sleep(1.5)
        blankKeys(keycaps)
        return

    drawKeyPattern(char);
    alphaMessage.setText("Here's the pattern for \""+cs+"\"\n")

    while c != target:
      print("Seeking ", target, ", got ",c)
      c=win.getKey().lower()

    alphaMessage.setText("That's the one!\n")
    time.sleep(1.5)
    blankKeys(keycaps)

###############################################################################
def pressThisNumber(char):
    target = weirdCharConvert(char)
    cs = char.upper()

    numMessage.setText("Press the \""+cs+"\" pattern\n")
    c=filteredKey(win).lower()
    print("Target: ",target," got: ",c)

    drawKeyPattern(char);
    if c == target:
        numMessage.setText("Correct!\n")
        time.sleep(1)
        blankKeys(keycaps)
        return

    # Did the character typed match the alphabetic cord for that number?
    # If so, the user has not activated numeric mode.
    if alphaTable.find(c.lower()) == numericTable.find(char):
      numMessage.setText("Did you use Command-N?\n")
      time.sleep(2.5)
    else:
      numMessage.setText("Try this pattern\n")
      time.sleep(2.5)

    blankKeys(keycaps)
    numMessage.setText("Press the \""+cs+"\" pattern\n")
    c=win.getKey().lower()

    if c == target:
        drawKeyPattern(char);
        numMessage.setText("Much better!\n")
        time.sleep(1.5)
        blankKeys(keycaps)
        return

    drawKeyPattern(char);
    if alphaTable.find(c.lower()) == numericTable.find(char):
      numMessage.setText("Check you used Command-N\n")
      time.sleep(2.5)

    numMessage.setText("Here's the pattern for \""+cs+"\"\n")

    while c != target:
      c=win.getKey().lower()

    numMessage.setText("That's the one!\n")
    time.sleep(1.5)
    blankKeys(keycaps)


###############################################################################
# Create a random sequence of lower case letters taken from the supplied string
# Avoid using the same character twice.
def pressTheseKeys(s,count):
  i=0
  # Do not use the same character twice
  prevChar=""
  while i < count:
    while True:
      newChar=s[random.randint(0,len(s)-1)]
      if newChar != prevChar or len(s) == 1:
        break
    pressThisKey(newChar)
    prevChar=newChar
    i += 1

###############################################################################
# Create a random sequence of lower case letters taken from the supplied string
# Specifically use prompts that are number and punctuation related.
# Avoid using the same character twice.
def pressTheseNumbers(s,count):
  i=0
  # Do not use the same character twice
  prevChar=""
  while i < count:
    while True:
      newChar=s[random.randint(0,len(s)-1)]
      if newChar != prevChar or len(s) == 1:
        break
    pressThisNumber(newChar)
    prevChar=newChar
    i += 1


###############################################################################
# Test the user on alphabetic characters
def alphabetTutorial():
  global alphaMessage

  alphaMessage = Text(Point(270,400), "Alphabet Tutorial\n")
  alphaMessage.setSize(29)
  alphaMessage.draw(win)
  # Repeated characters are more likely to turn up
  pressTheseKeys("atleathnlbdithljpabcdefghijklmnopqrstuvwxys",20)
  alphaMessage.undraw()

###############################################################################
# Test the user on numeric characters
def numericTutorial():
  global numMessage
  numMessage = Text(Point(270,400), "Numbers Tutorial\n")
  numMessage.setSize(29)
  numMessage.draw(win)
  # Remind the user to turn on numeric mode
  shiftKeysLayout=createKeycaps(650,100)
  blankKeys(shiftKeysLayout)
  # Make the keycaps visible
  for k in shiftKeysLayout:
    k.draw(win)
  # Display a numeric shift pattern
  shiftKeysLayout[5].setFill("black")
  shiftKeysLayout[2].setFill("yellow")
  shiftKeysLayout[3].setFill("lime")
  # Prompt to use it
  numberPromptMessage = Text(Point(270,170), "(Remember, use 'Command-N' first)\n")
  numberPromptMessage.setSize(20)
  numberPromptMessage.draw(win)

  # Repeated characters are more likely to turn up
  pressTheseNumbers("01234567893546789!?.,:;",10)

  # Remove the shift keys layout
  for k in shiftKeysLayout:
    k.undraw()
  # Remove the prompt
  numberPromptMessage.undraw()
  numMessage.undraw()

###############################################################################
# Main
###############################################################################

keycaps=createKeycaps(650,390)
random.seed()

# grand opening of the display
# Add a blank line, or it'll chop off the descendersoeoo        oessmm  ipfoagtet
message = Text(Point(270,500), "Welcome to Quirkey Tutor\n")
message.setSize(29)
message.draw(win)

# Draw the coloured keycaps
for k in keycaps:
    time.sleep(0.1)
    k.draw(win)

time.sleep(2.5)
# Set the key colours all blank
blankKeys(keycaps)

# Pick a tutorial
while True:
  menuMessage = Text(Point(300,300),"Pick a tutorial:\n\n  1. The alphabet\n  2. Numbers & punctuation\n\n  0. Quit\n")
  menuMessage.setSize(29)
  setJustify(menuMessage,"left")
  menuMessage.draw(win)
  # Put up some key press options
  redSquare=Rectangle(Point(50,290),Point(80,320))
  redSquare.setFill("red")
  redSquare.draw(win)
  orangeSquare=Rectangle(Point(50,330),Point(80,360))
  orangeSquare.setFill("orange")
  orangeSquare.draw(win)
  blueSquare=Rectangle(Point(50,210),Point(80,240))
  blueSquare.setFill("blue")
  blueSquare.draw(win)



  c = "9"
  while "012eu ".find(c.lower()) < 0:
    c = win.getKey()
    # Space is an awkward bugger and is returned as a multi-char string
    if c == "space":
      break


  menuMessage.undraw()
  orangeSquare.undraw()
  redSquare.undraw()
  blueSquare.undraw()

  if c == "1" or c.lower() == "e":
    alphabetTutorial()
  elif c == "2" or c == "space":
    numericTutorial()
  elif c == "0" or c.lower() == "u":
    break

win.close()
