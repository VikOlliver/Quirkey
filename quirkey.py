# quirkey.py
# Microwriter reboot on Arduino for the Quirkey Keyboard (c)2023 vik@diamondage.co.nz
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
#
# Uses key tables loosely borrowed from the Microwriter https://en.wikipedia.org/wiki/Microwriter
# Designed to run on CircuitPython. An Arduino version of AT32U4 "Microwriter" is available on github
# HID Example code: https://learn.adafruit.com/adafruit-pyruler/circuitpython-hid-keyboard-and-mouse
# API https://docs.circuitpython.org/projects/hid/en/latest/api.html
#
# Changelog:
# V01
# Uses keycodes flag bits to indicate whether a character needs a SHIFT/Alt etc
# Added AltGr shift
# Added proper GPL header
# Support for sending a Windows or Linux UTF character code if UTF_TOKEN bit set

# Which system are we using?
# Valid types are 'linux', 'windows', and 'mac'.
# Sorry Mac people, Apple are not UTF freindly
systemType='linux'

import time
import board
import digitalio
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode

# Constants
NUM_KEYS=6
MOUSE_DELAY_MAX=30
# If this flag is set, the character is sent as a UTF sequence
UTF_TOKEN=4096
# If this flag is set, the character must be shifted
SHIFT_TOKEN=8192
# Our own key token constants for our key table
KEYS_TOKEN=1024
KEYS_SHIFT_ON=KEYS_TOKEN+0
KEYS_SHIFT_OFF=KEYS_TOKEN+1
KEYS_NUMERIC_SHIFT=KEYS_TOKEN+2
KEYS_CONTROL_SHIFT=KEYS_TOKEN+3
KEYS_ALT_SHIFT=KEYS_TOKEN+4
KEYS_EXTRA_SHIFT=KEYS_TOKEN+5
KEYS_MOUSE_MODE_ON=KEYS_TOKEN+6
KEYS_FUNC_SHIFT=KEYS_TOKEN+7
KEYS_ALTGR_SHIFT=KEYS_TOKEN+8

# Ctrl, pinkie, ring, middle, 1st, thumb pins.
# Activating a switch grounds the respective pin.
keyPorts=[board.GP8,board.GP7,board.GP6,board.GP5,board.GP4,board.GP9]
# This will hold the switch objects once the key pins have been initialised.
keySwitches=[]
alphaTable=[Keycode.SPACE,Keycode.E,Keycode.I,Keycode.O,Keycode.C,Keycode.A,Keycode.D,Keycode.S,
						Keycode.K,Keycode.T,Keycode.R,Keycode.N,Keycode.Y,Keycode.PERIOD,Keycode.F,
						Keycode.U,Keycode.H,Keycode.V,Keycode.L,Keycode.Q,Keycode.Z,Keycode.MINUS,
						Keycode.QUOTE,Keycode.G,Keycode.J,Keycode.COMMA,Keycode.W,Keycode.B,
						Keycode.X,Keycode.M,Keycode.P]

# Characters avaiable when internal numeric shift (Ctrl-N) is down
							# SPACE 120(
numericTable=[Keycode.SPACE,Keycode.ONE,Keycode.TWO,Keycode.ZERO,Keycode.NINE+SHIFT_TOKEN,
                # *3$/
                Keycode.EIGHT+SHIFT_TOKEN,Keycode.THREE,Keycode.FOUR+SHIFT_TOKEN,Keycode.FORWARD_SLASH,
                # +;
                Keycode.EQUALS+SHIFT_TOKEN,Keycode.SEMICOLON,
                # "?.
                Keycode.QUOTE+SHIFT_TOKEN,Keycode.FORWARD_SLASH+SHIFT_TOKEN,Keycode.PERIOD,
                # 46-&
                Keycode.FOUR,Keycode.SIX,Keycode.MINUS,Keycode.SEVEN+SHIFT_TOKEN,
                # #)%
                Keycode.THREE+SHIFT_TOKEN,Keycode.ZERO+SHIFT_TOKEN,Keycode.FIVE+SHIFT_TOKEN,
                # !@7=
                Keycode.ONE+SHIFT_TOKEN,Keycode.TWO+SHIFT_TOKEN,Keycode.SEVEN,Keycode.EQUALS,
                # ,:8x
                Keycode.COMMA,Keycode.SEMICOLON+SHIFT_TOKEN,Keycode.EIGHT,Keycode.X,
                # 95
                Keycode.NINE,Keycode.FIVE]

# Key codes used when Extra shift (Ctrl-H) is down
extraTable=[0, Keycode.ESCAPE, 0, 0, 0, Keycode.LEFT_BRACKET, Keycode.DELETE, 0,
           # k
           Keycode.HOME, 0 ,0 , 0, 0, 0, Keycode.END, 0,
           0, Keycode.FORWARD_SLASH, 0, Keycode.RIGHT_BRACKET, Keycode.PAGE_DOWN, 0, 0, 0,
           Keycode.PAGE_UP, 0, 0, 0, 0, 0, 0]

# Keycodes used when Function shift (Ctrl-V) is down
funcTable=[0, Keycode.F1, Keycode.F2, Keycode.F10, 0, Keycode.F11, Keycode.F3, 0,
          0, 0, 0, 0, 0, Keycode.F12, Keycode.F4, Keycode.F6,
          0, 0, 0, 0, 0, 0, 0, Keycode.F7,
          0, 0, 0, Keycode.F8, 0, Keycode.F9, Keycode.F5]

# Key shift internal tokens and some editing keycodes used when shift is down
shiftTable=[KEYS_SHIFT_ON, KEYS_SHIFT_OFF, Keycode.INSERT, KEYS_MOUSE_MODE_ON, Keycode.RETURN, 0, Keycode.BACKSPACE, 0,
          Keycode.LEFT_ARROW, 0, Keycode.TAB, 0, KEYS_NUMERIC_SHIFT, 0, Keycode.RIGHT_ARROW, 0,
          KEYS_EXTRA_SHIFT, KEYS_ALTGR_SHIFT, KEYS_FUNC_SHIFT, 0, Keycode.DOWN_ARROW, 0, 0, 0,
          Keycode.UP_ARROW, 0, 0, 0, KEYS_CONTROL_SHIFT, 0, KEYS_ALT_SHIFT, 0]

# Hexadecimal key tokens used to send UTF codes under Linux
hexdigits=[Keycode.ZERO,Keycode.ONE,Keycode.TWO,Keycode.THREE,Keycode.FOUR,Keycode.FIVE,Keycode.SIX,
				Keycode.SEVEN,Keycode.EIGHT,Keycode.NINE,
				Keycode.A,Keycode.B,Keycode.C,Keycode.D,Keycode.E,Keycode.F]

# Hexadecimal key tokens used to send UTF codes under Windows
keypadDigits=[Keycode.KEYPAD_ZERO,Keycode.KEYPAD_ONE,Keycode.KEYPAD_TWO,Keycode.KEYPAD_THREE,
				Keycode.KEYPAD_FOUR,Keycode.KEYPAD_FIVE,Keycode.KEYPAD_SIX,Keycode.KEYPAD_SEVEN,
				Keycode.KEYPAD_EIGHT,Keycode.KEYPAD_NINE]
				
global keyboard
global keyboardLayout

# >0 when shift is on.
shifted=0
# >0 when using numeric table
numericed=0
# >0 when CTRL is on
controlled=0
# >0 when ALT is on
alted=0
# >0 when ALTGR is on
altgred=0
# >0 When extra shift on
extraed=0
# >0 when using function key table
funced=0
#################################################################################
#################################################################################

#################################################################################
# The keyboard hardware configuration
def setup():
  time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
  global keyboard
  global keyboardLayout
  keyboard = Keyboard(usb_hid.devices)
  keyboardLayout = KeyboardLayoutUS(keyboard)  # We're in the US :)

  for pin in keyPorts:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    keySwitches.append(button)

#################################################################################
# Takes the 16-bit UTF character code and uses Linux ALT kepress technology
# to send it to the HID keyboard channel.
# Linux uses SHIFT+CTRL+U <hexcode> release SHIFT+CTRL
def sendUtfCharLinux(utfChar):
    print("Send Linux UTF char",utfChar)
	# UTF starts with a U, CTRL+SHIFT held down
    Keyboard.send(Keycode.LEFT_SHIFT,Keycode.LEFT_CONTROL)
    Keyboard.press(Keycode.U)
    # Send the three hex digits, high end first
    Keyboard.send(hexdigit[(utfChar >> 16) & 255],
    	hexdigit[(uftChar >> 8) & 255],
    	hexdigit[utfChar & 255])

    # Now signal keys up, and revert to original shift key modifiers.
    keyboard.release(Keycode.LEFT_CONTROL)
    keyboard.release(Keycode.LEFT_SHIFT)
    if (shifted == 2):
        keyboard.press(Keycode.LEFT_SHIFT)
    if (controlled == 2):
        keyboard.press(Keycode.LEFT_CONTROL)

#################################################################################
# Takes the 16-bit UTF character code and uses Windows ALT kepress technology
# to send it to the HID keyboard channel.
# Windows uses ALT NUMERIC_PLUS <decimal value using keypad> release ALT
def sendUtfCharWindows(utfChar):
    print("Send Windows UTF char",utfChar)

	# UTF starts with left ALT held down
    Keyboard.send(Keycode.LEFT_ALT);
    Keyboard.press(Keycode.NUMERIC_PLUS)

    # Build a list of the keypad digit keys
    while utfChar > 0:
        digitKeys.insert(0,keypadDigits[utfChar % 10])
        utfChar = utfChar / 10
    # Send 'em to the HID keyboard
    keyboard.send(digitKeys)
    # Finally, we can let go the ALT key
    keyboard.release(Keycode.LEFT_ALT)
    # Now revert to original ALT key modifier.
    if (alted == 2):
        keyboard.press(Keycode.LEFT_ALT)

#################################################################################
# Return a binary representation of the raw keybits
def keyBits():
  i=0
  k=0

  for switch in keySwitches:
    k *= 2
    if not switch.value:
      k += 1

  return k

#################################################################################
# Wait (with debounce) until some keys have been pressed, and all keys are released.
def keyWait():
  x = 0
  k = 0

  while True:
    # Debounce
    while k != keyBits():
      time.sleep(0.01)  # 10ms delay
      k = keyBits()
    x = x | k
    if x != 0 and k == 0:
      break

  return x

#################################################################################
# Tell the keyboard to release all keys, and turn off all our internal shifts
def everythingOff():
  keyboard.release_all()
  shifted = 0
  numericed = 0
  controlled = 0
  alted = 0
  altgred = 0
  extraed = 0
  funced = 0

#################################################################################
# Check the character X to see if it has any modifier key flags. If necessary
# temporarity press any modifier keys, but if the modifer state is already locked
# (shifted,alted etc.) do not change the modifier key state.
# i.e. if sending a shifted 4 ($ key) only press the shift key if shift is not
# locked (has a vale of 2).
def tokenisedWrite(x):
    c = x & 0xff
    # If the key needs a shift, press shift
    if (x & SHIFT_TOKEN) != 0:
        keyboard.press(Keycode.LEFT_SHIFT)
        keyboard.press(c)
        keyboard.release(c)
    	if (shifted < 2):
        	keyboard.release(Keycode.LEFT_SHIFT)

    # If the value has a UTF token bit set, send the charcter as a UTF sequence
    elif (x & UTF_TOKEN) != 0:
    	if ( systemType == 'linux' ):
            sendUtfCharLinux(x & 0xfff)
        elif ( systemType == 'windows' ):
            sendUtfCharWindows(x & 0xfff)
	    # Mac users are SOL as Mac keyboards do not support UTF.

    # No special token. Press and release the key.
    else:
        keyboard.press(c)
        keyboard.release(c)

#################################################################################
# Uses finger keys as LUDR, thumb as click 1 & 2.
# All 4 fingers exit mouse mode.

def mouseMode():
  k = 0
  x= 0
  y=0
  mouseDelay = MOUSE_DELAY_MAX

  Mouse.begin();
  while True:
    k = keyBits()
    if k == 30:
      break # Quit mousing if all 4 move keys hit.
    if k == 0:
      mouseDelay = MOUSE_DELAY_MAX

    if (k & 2) != 0:
      # Mouse left
      x = -1

    if (k & 16) != 0:
      # Mouse right
      x = 1

    if (k & 4) != 0:
      # Mouse up
      y = -1

    if (k & 8) != 0:
      # Mouse down
      y = 1;

    # Mouse clicks
    if (k & 1) != 0:
      Mouse.press(MOUSE_LEFT)
      time.sleep(0.05)
      while (keyBits() & 1) != 0:
        Mouse.release(MOUSE_LEFT)

    if (k & 32) != 0:
      Mouse.press(MOUSE_RIGHT)
      time.sleep(0.050)
      while (keyBits() & 32) != 0:
         Mouse.release(MOUSE_RIGHT)

    # If keys moved, move mouse.
    if (x != 0) or (y != 0):
      Mouse.move(x, y, 0)
      time.sleep(mouseDelay/1000)
      mouseDelay -= 1
      x = y = 0

    # If acceleration is at maximum, do not exceed it!
    if mouseDelay < 4:
      mouseDelay = 4

  Mouse.end()
  # Wait for all keys up
  while keyBits() != 0:
    time.sleep(0.001)

#################################################################################
print("QuirkeyV01 setup ...")
setup()
print("Starting Quirkey Main Loop")

while True:
  x = keyWait()

  if x < 32 :
    # Here a chord has been pressed without the control key
    if numericed != 0:
        tokenisedWrite(numericTable[x - 1])
    elif extraed != 0:
        tokenisedWrite(extraTable[x - 1])
    elif funced != 0:
        tokenisedWrite(funcTable[x - 1])
    else:
        tokenisedWrite(alphaTable[x - 1])

    # Having done whatever the chord was supposed to do, we see if any temporary
    # keyboard shifts need to be cleared
    if shifted == 1: # Clear a single shift.
      shifted = 0
      keyboard.release(Keycode.LEFT_SHIFT)

    if controlled == 1: # Clear a single control shift.
      controlled = 0
      keyboard.release(Keycode.LEFT_CONTROL)

    if alted == 1: # Clear a single alt shift.
      alted = 0
      keyboard.release(Keycode.LEFT_ALT)

    if altgred == 1: # Clear a single alt shift.
      altgred = 0
      keyboard.release(Keycode.RIGHT_ALT)

    # Clear any internal temporary numeric, extra and func shifts
    numericed &= 2
    extraed &= 2
    funced &= 2

  else:
    # Must be a shift function then
    x = shiftTable[x - 32]
    if x < 256:
      # This was a keycode to press and release
      tokenisedWrite(x)
    else:
      # Its a more complicated keypress requiring a function.
      if x == KEYS_SHIFT_ON:
          shifted += 1
          if shifted > 2:
            shifted = 2
          keyboard.press(Keycode.LEFT_SHIFT)

      elif x == KEYS_CONTROL_SHIFT:
          controlled += 1
          if controlled > 2:
            controlled = 2
          keyboard.press(Keycode.LEFT_CONTROL)

      elif x == KEYS_SHIFT_OFF:
          everythingOff()

      elif x == KEYS_NUMERIC_SHIFT:
            numericed += 1
            if numericed > 2:
                numericed = 2;

      elif x == KEYS_EXTRA_SHIFT:
          extraed += 1
          if extraed > 2:
            extraed = 2;

      elif x == KEYS_ALT_SHIFT:
          alted += 1
          if alted > 2:
            alted = 2
          keyboard.press(Keycode.LEFT_ALT)

      elif x == KEYS_ALTGR_SHIFT:
          altgred += 1
          if altgred > 2:
            altgred = 2
          keyboard.press(Keycode.RIGHT_ALT)

      elif x == KEYS_FUNC_SHIFT:
          funced += 1
          if funced > 2:
            funced = 2

      elif x == KEYS_MOUSE_MODE_ON:
          mouseMode()
