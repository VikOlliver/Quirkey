# quirkey.py
# Microwriter reboot on CircuitPython for the Quirkey Keyboard, configured
# for Pico and Seeed XIAO RP2040 (c)2023 vik@diamondage.co.nz
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
# which is the Arduino version of this code for the AT32U4, also available on this github repo
# HID Example code: https://learn.adafruit.com/adafruit-pyruler/circuitpython-hid-keyboard-and-mouse
# API https://docs.circuitpython.org/projects/hid/en/latest/api.html
#
# Changelog:
# V01
# Uses keycodes flag bits to indicate whether a character needs a SHIFT/Alt etc
# Added AltGr shift
# Added proper GPL header
# Support for sending a Windows or Linux UTF character code if UTF_TOKEN bit set
# Improved mouse acceleration algorithm
# Now has repeating keys
# Added a heartbeat indicator LED driver, mostly for debugging
# Wrapped the main code in a 'try' and reboot if, say, the USB goes wrong.
# Added left-hand optimisation. If you're a leftie, set this to "True".
LEFT_HANDED=False
# Which system are we using?
# Valid types are 'linux', 'windows', and 'mac'.
# Need to update Windows to use hex digit entry, ana
# support similar system for Mac.
systemType='windows'

import time
import board
import digitalio
import microcontroller
import traceback
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keyboard_layout_us import KeyboardLayoutUS
from adafruit_hid.keycode import Keycode
from adafruit_hid.mouse import Mouse

# Constants
###########
NUM_KEYS=6
# Delay in 10ms increments before repeat starts
REPEAT_START_DELAY = 220
# Delay in 10ms increments between repeated characters
REPEAT_INTERVAL_DELAY = 4
# After moving this number of ticks, the mouse will accelerate
MOUSE_ACCELERATION_POINT = 40
# Maximum speedup on mouse
MOUSE_MAX_ACCELERATION = 7
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
KEYS_LANGAUGE_SHIFT=KEYS_TOKEN+9  # Currently Pinyin accenting

# Assign keys that are highly sensitive to mental confusion for left/right use
if LEFT_HANDED:
  AMBI_KEY_B=Keycode.D
  AMBI_KEY_D=Keycode.B
  AMBI_KEY_LEFT_PAREN=Keycode.ZERO+SHIFT_TOKEN
  AMBI_KEY_RIGHT_PAREN=Keycode.NINE+SHIFT_TOKEN
  AMBI_KEY_LEFT_BRACKET=Keycode.RIGHT_BRACKET
  AMBI_KEY_RIGHT_BRACKET=Keycode.LEFT_BRACKET
  AMBI_FORWARD_SLASH=Keycode.BACKSLASH
  AMBI_BACKSLASH=Keycode.FORWARD_SLASH
  # Mouse direction key bitmasks
  AMBI_MOUSE_LEFT=16
  AMBI_MOUSE_RIGHT=2
else:
  # Right hand versions
  AMBI_KEY_B=Keycode.B
  AMBI_KEY_D=Keycode.D
  AMBI_KEY_LEFT_PAREN=Keycode.NINE+SHIFT_TOKEN
  AMBI_KEY_RIGHT_PAREN=Keycode.ZERO+SHIFT_TOKEN
  AMBI_KEY_LEFT_BRACKET=Keycode.LEFT_BRACKET
  AMBI_KEY_RIGHT_BRACKET=Keycode.RIGHT_BRACKET
  AMBI_FORWARD_SLASH=Keycode.FORWARD_SLASH
  AMBI_BACKSLASH=Keycode.BACKSLASH
  # Mouse direction key bitmasks
  AMBI_MOUSE_LEFT=2
  AMBI_MOUSE_RIGHT=16

# Variables used to produce a heartbeat LED.
# If you don't want one, define HEARTBEAT_PIN as 0 *AFTER THE keyPorts*
HEARTBEAT_PIN=0
heartbeat_count=0

# Activating a switch grounds the respective pin.
# If we're ona Seeed XIAO board, we need to change that because they label the pins funny
keyPorts=[]
if ( board.board_id == "seeeduino_xiao_rp2040"):
  print(" Seeed XIAO detected. Changing pin config.")
  # Ctrl, pinkie, ring, middle, 1st, thumb pins.
  keyPorts=[board.D8,board.D7,board.D6,board.D5,board.D4,board.D9]
  HEARTBEAT_PIN=board.LED
else:
  # Ctrl, pinkie, ring, middle, 1st, thumb pins.
  keyPorts=[board.GP8,board.GP7,board.GP6,board.GP5,board.GP4,board.GP9]
  HEARTBEAT_PIN=board.GP17

# Set HEARTBEAT_PIN to 0 here if you don't want a heartbeat light

# This will hold the switch objects once the key pins have been initialised.
keySwitches=[]
alphaTable=[Keycode.SPACE,Keycode.E,Keycode.I,Keycode.O,Keycode.C,Keycode.A,AMBI_KEY_D,Keycode.S,
						Keycode.K,Keycode.T,Keycode.R,Keycode.N,Keycode.Y,Keycode.PERIOD,Keycode.F,
						Keycode.U,Keycode.H,Keycode.V,Keycode.L,Keycode.Q,Keycode.Z,Keycode.MINUS,
						Keycode.QUOTE,Keycode.G,Keycode.J,Keycode.COMMA,Keycode.W,AMBI_KEY_B,
						Keycode.X,Keycode.M,Keycode.P]

# Characters available when internal numeric shift (Ctrl-N) is down
							# SPACE 120(
numericTable=[Keycode.SPACE,Keycode.ONE,Keycode.TWO,Keycode.ZERO,AMBI_KEY_LEFT_PAREN,
                # *3$/
                Keycode.EIGHT+SHIFT_TOKEN,Keycode.THREE,Keycode.FOUR+SHIFT_TOKEN,AMBI_FORWARD_SLASH,
                # +;
                Keycode.EQUALS+SHIFT_TOKEN,Keycode.SEMICOLON,
                # "?.
                Keycode.QUOTE+SHIFT_TOKEN,Keycode.FORWARD_SLASH+SHIFT_TOKEN,Keycode.PERIOD,
                # 46-&
                Keycode.FOUR,Keycode.SIX,Keycode.MINUS,Keycode.SEVEN+SHIFT_TOKEN,
                # #)%
                Keycode.THREE+SHIFT_TOKEN,AMBI_KEY_RIGHT_PAREN,Keycode.FIVE+SHIFT_TOKEN,
                # !@7=
                Keycode.ONE+SHIFT_TOKEN,Keycode.TWO+SHIFT_TOKEN,Keycode.SEVEN,Keycode.EQUALS,
                # ,:8x
                Keycode.COMMA,Keycode.SEMICOLON+SHIFT_TOKEN,Keycode.EIGHT,Keycode.GRAVE_ACCENT,
                # 95
                Keycode.NINE,Keycode.FIVE]

# Key codes used when Extra shift (Ctrl-H) is down
extraTable=[0, Keycode.ESCAPE, 0, 0, AMBI_KEY_LEFT_BRACKET, 0, Keycode.DELETE, 0,
           # k
           Keycode.HOME, 0 ,0, AMBI_BACKSLASH, 0, 0, Keycode.END, 0,
           0, 0, 0, AMBI_KEY_RIGHT_BRACKET, Keycode.PAGE_DOWN, 0, 0, 0,
           Keycode.PAGE_UP, 0, Keycode.WINDOWS, 0, 0, 0, 0]

# Keycodes used when Function shift (Ctrl-V) is down
funcTable=[0, Keycode.F1, Keycode.F2, Keycode.F10, 0, Keycode.F11, Keycode.F3, 0,
          # UTF tokens here are for n-tilde and N-tilde
          0, 0, 0, UTF_TOKEN+0xf1, UTF_TOKEN+0xd1, Keycode.F12, Keycode.F4, Keycode.F6,
          # UTF tokens for inverted query and inverted exclamation
          0, 0, 0, UTF_TOKEN+0xbf, 0, UTF_TOKEN+0xa1, 0, Keycode.F7,
          0, 0, 0, Keycode.F8, 0, Keycode.F9, Keycode.F5]

# Key shift internal tokens and some editing keycodes used when shift is down
shiftTable=[KEYS_SHIFT_ON, KEYS_SHIFT_OFF, Keycode.INSERT, KEYS_MOUSE_MODE_ON, Keycode.RETURN, 0, Keycode.BACKSPACE, 0,
          Keycode.LEFT_ARROW, 0, Keycode.TAB, 0, KEYS_NUMERIC_SHIFT, 0, Keycode.RIGHT_ARROW, 0,
          KEYS_EXTRA_SHIFT, KEYS_ALTGR_SHIFT, KEYS_FUNC_SHIFT, 0, Keycode.DOWN_ARROW, 0, KEYS_LANGAUGE_SHIFT, 0,
          Keycode.UP_ARROW, 0, 0, 0, KEYS_CONTROL_SHIFT, 0, KEYS_ALT_SHIFT, 0]

# Accents and pinyin stuff

'''
tones 0-4:

a	ā	&#x101;	á	&#xE1;	ǎ	&#x1CE;	à	&#xE0;
e	ē	&#x113;	é	&#xE9;	ě	&#x11B;	è	&#xE8;
i	ī	&#x12B;	í	&#xED;	ǐ	&#x1D0;	ì	&#xEC;
o	ō	&#x14D;	ó	&#xF3;	ǒ	&#x1D2;	ò	&#xF2;
u	ū	&#x16B;	ú	&#xFA;	ǔ	&#x1D4;	ù	&#xF9;
ü	ǖ	&#x1D6;	ǘ	&#x1D8;	ǚ	&#x1DA;	ǜ	&#x1DC;
A	Ā	&#x100;	Á	&#xC1;	Ǎ	&#x1Cd;	À	&#xC0;
E	Ē	&#x112;	É	&#xC9;	Ě	&#x11A;	È	&#xC8;
I	Ī	&#x12A;	Í	&#xCD;	Ǐ	&#x1CF;	Ì	&#xCC;
O	Ō	&#x14C;	Ó	&#xD3;	Ǒ	&#x1D1;	Ò	&#xD2;
U	Ū	&#x16A;	Ú	&#xDA;	Ǔ	&#x1D3;	Ù	&#xD9;
Ü	Ǖ	&#x1D5;	Ǘ	&#x1D7;	Ǚ	&#x1D9;	Ǜ	&#x1DB;
'''
# Characters that pinyin recognised as vowels that can have accents
# The V key is used for u umlaut, as V is not used in pinyin
vowels=[Keycode.A,Keycode.E,Keycode.I,Keycode.O,Keycode.U,Keycode.V]
# Key bit chords that pinyin uses to apply accents as tones 1-4 (space indicates no accent)
acntKeys=[2,4,8,16];


# The UFT characters of accented vowels when acntKeys are applied to them
utfArray=[
    0x101,0x0E1,0x1CE,0x0E0,    # a
    0x113,0x0E9,0x11B,0x0E8,    # e
    0x12B,0x0ED,0x1D0,0x0EC,    # i
    0x14D,0x0F3,0x1D2,0x0F2,    # o
    0x16B,0x0FA,0x1D4,0x0F9,    # u
    0x1D6,0x1D8,0x1DA,0x1DC,    # ü

    0x100,0x0C1,0x1Cd,0x0C0,    # A
    0x112,0x0C9,0x11A,0x0C8,    # E
    0x12A,0x0CD,0x1CF,0x0CC,    # I
    0x14C,0x0D3,0x1D1,0x0D2,    # O
    0x16A,0x0DA,0x1D3,0x0D9,     # U
    0x1D5,0x1D7,0x1D9,0x1DB     # Ü
]


# Hexadecimal key tokens used to send UTF codes under Linux
hexdigits=[Keycode.ZERO,Keycode.ONE,Keycode.TWO,Keycode.THREE,Keycode.FOUR,Keycode.FIVE,Keycode.SIX,
				Keycode.SEVEN,Keycode.EIGHT,Keycode.NINE,
				Keycode.A,Keycode.B,Keycode.C,Keycode.D,Keycode.E,Keycode.F]

# Hexadecimal key tokens used to send UTF codes under Windows
keypadDigits=[Keycode.KEYPAD_ZERO,Keycode.KEYPAD_ONE,Keycode.KEYPAD_TWO,Keycode.KEYPAD_THREE,
				Keycode.KEYPAD_FOUR,Keycode.KEYPAD_FIVE,Keycode.KEYPAD_SIX,Keycode.KEYPAD_SEVEN,
				Keycode.KEYPAD_EIGHT,Keycode.KEYPAD_NINE]
				
global keyboard
global mouse
global keyboardLayout

# The chord we are repeating
repeatingChord = 0

# >0 when shift is on.
shifted=0 # has a real keyboard key counterpart
# >0 when using numeric table
numericed=0
# >0 when CTRL is on - has a real keyboard key counterpart
controlled=0
# >0 when ALT is on - has a real keyboard key counterpart
alted=0
# >0 when ALTGR is on - has a real keyboard key counterpart
altgred=0
# >0 When extra shift on
extraed=0
# >0 when using function key table
funced=0
# >0 when using anguage-specific accents
# 2 When pinyin mode is locked in.
accented=0

#################################################################################
#################################################################################

#################################################################################
# The keyboard hardware configuration
def setup():
  time.sleep(1)  # Sleep for a bit to avoid a race condition on some systems
  global keyboard
  global keyboardLayout
  global mouse
  global heartbeat_output
  
  keyboard = Keyboard(usb_hid.devices)
  keyboardLayout = KeyboardLayoutUS(keyboard)  # We're in the US :)
  mouse = Mouse(usb_hid.devices)

  # Enable all the key button inputs
  for pin in keyPorts:
    button = digitalio.DigitalInOut(pin)
    button.direction = digitalio.Direction.INPUT
    button.pull = digitalio.Pull.UP
    keySwitches.append(button)

  # If we're using a hearbeat LED, enable that output
  if HEARTBEAT_PIN != 0:
    print("Starting heartbeat LED")
    heartbeat_output = digitalio.DigitalInOut(HEARTBEAT_PIN)
    heartbeat_output.direction = digitalio.Direction.OUTPUT
    heartbeat_output.value = True
    
#################################################################################
# Flash the heartbeat pin periodically
def blink_heartbeat():
  global heartbeat_count
  heartbeat_count = heartbeat_count + 1
  if heartbeat_count < 300:
    heartbeat_output.value=False
  else:
    heartbeat_output.value=True
    if heartbeat_count > 320:
      heartbeat_count = 0

#################################################################################
# Takes the 16-bit UTF character code and uses Linux ALT kepress technology
# to send it to the HID keyboard channel.
# Linux uses SHIFT+CTRL+U <hexcode> release SHIFT+CTRL
def sendUtfCharLinux(utfChar):
	# UTF starts with a U, CTRL+SHIFT held down
    keyboard.press(Keycode.LEFT_SHIFT,Keycode.LEFT_CONTROL)
    keyboard.press(Keycode.U)
    keyboard.release(Keycode.U)
    # Send the three hex digits, high end first
    keyboard.press(hexdigits[(utfChar >> 8) & 15])
    keyboard.release(hexdigits[(utfChar >> 8) & 15])
    keyboard.press(hexdigits[(utfChar >> 4) & 15])
    keyboard.release(hexdigits[(utfChar >> 4) & 15])
    keyboard.press(hexdigits[utfChar & 15])
    keyboard.release(hexdigits[utfChar & 15])

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
    #print("Send Windows UTF char",utfChar)

	# UTF starts with left ALT held down
    keyboard.press(Keycode.LEFT_ALT)

    # Build a list of the keypad digit keys
    digitKeys = []
    while utfChar > 0:
      digitKeys.insert(0,keypadDigits[int(utfChar % 10)])
      utfChar = int(utfChar / 10)
    # Send 'em to the HID keyboard one at a time, always starting with zero
    keyboard.press(keypadDigits[0])
    keyboard.release(keypadDigits[0])
    for k in digitKeys:
      keyboard.press(k)
      keyboard.release(k)
 
    # Finally, we can let go the ALT key
    keyboard.release(Keycode.LEFT_ALT)
    # Now revert to original ALT key modifier.
    if (alted == 2):
        keyboard.press(Keycode.LEFT_ALT)

#################################################################################
# Send the given UTF character using the right system sequence.
def sendUtfChar(c):
  if systemType == "linux":
    sendUtfCharLinux(c)
  else:
    sendUtfCharWindows(c)


#################################################################################
# Return a binary representation of the raw keybits
def keyBits():
  i=0
  k=0

  # Flash the heartbeat LED
  blink_heartbeat()
  # Now add up the input bits
  for switch in keySwitches:
    k *= 2
    if not switch.value:
      k += 1

  return k

#################################################################################
# If the repeating chord is still held down, return it after a brief delay.
# Otherwise, wait until all keys are released and return zero.
def getRepeatingChord():
  k = 0
  global repeatingChord

  while True:
    # Debounce
    while k != keyBits():
      time.sleep(0.01)  # 10ms delay
      k = keyBits()

    # If the chord matches the repeat, delay a bit and return the chord
    if k == repeatingChord:
      time.sleep(0.01*REPEAT_INTERVAL_DELAY)
      return k

    # Whatever the chord changed to, we wait for it to go away
    while keyBits() != 0:
      time.sleep(0.01)
    repeatingChord = 0
    return 0


#################################################################################
# Wait (with debounce) until some keys have been pressed.
# If all keys are released with in repeat time, return the chord.
# If held beyond repeat time, enter repeat mode and return it.
def keyWaitRepeat():
  x = 0
  k = 0
  timer = 0
  global repeatingChord

  # If we're repeating, get repeated chord after delay etc.
  if repeatingChord != 0:
    x = getRepeatingChord()
    if x != 0:
      return x
      #If we drop out here, the repeat has ended. get another chord.

  while True:
    # Debounce
    while k != keyBits():
      time.sleep(0.01)  # 10ms delay
      k = keyBits()
    # We drop out with stable input

    if x != k:
      # the chord changed, so reset the repeat timer
      timer = 0

    # Accumulate keypresses into chord
    x = x | k

    # If all keys are released, return the accumulated chord.
    if x != 0 and k == 0:
      return x
    # Otherwise, do a bit of the repeat wait timer.
    time.sleep(0.01)
    # If keys are still down and we have exceeded repeat time, enter
    # repeat mode and return the chord.
    if k != 0:
      timer += 1
    if timer > REPEAT_START_DELAY:
      repeatingChord = x
      break

  return x

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
  global shifted
  global numericed
  global controlled
  global alted
  global altgred
  global extraed
  global funced
  global accented
  keyboard.release_all()
  shifted = 0
  numericed = 0
  controlled = 0
  alted = 0
  altgred = 0
  extraed = 0
  funced = 0
  accented = 0

#################################################################################
# Check the character X to see if it has any modifier key flags. If necessary
# temporarity press any modifier keys, but if the modifier state is already locked
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

    # If the value has a UTF token bit set, send the character as a UTF sequence
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
  # How far the mouse has moved without a break
  mouseTicks = 0

  while True:
    # Determine if the mouse is accelerating or not. If it is, bump up movement factor
    if mouseTicks > MOUSE_ACCELERATION_POINT:
        mouseMove = int(mouseTicks/MOUSE_ACCELERATION_POINT)
        if mouseMove > MOUSE_MAX_ACCELERATION:
            mouseMove = MOUSE_MAX_ACCELERATION
    else:
        mouseMove = 1

    k = keyBits()
    if k == 30:
      break # Quit mousing if all 4 move keys hit.
    if k == 0:
        # Mouse stopped moving.
        mouseTicks = 0

    if (k & AMBI_MOUSE_LEFT) != 0:
      # Mouse left
      x = -mouseMove

    if (k & AMBI_MOUSE_RIGHT) != 0:
      # Mouse right
      x = mouseMove

    if (k & 4) != 0:
      # Mouse up
      y = -mouseMove

    if (k & 8) != 0:
      # Mouse down
      y = mouseMove;

    # Mouse clicks
    if (k & 1) != 0:
      mouse.press(Mouse.LEFT_BUTTON)
      time.sleep(0.05)
      while (keyBits() & 1) != 0:
        mouse.release(Mouse.LEFT_BUTTON)

    if (k & 32) != 0:
      mouse.press(Mouse.RIGHT_BUTTON)
      time.sleep(0.050)
      while (keyBits() & 32) != 0:
         mouse.release(Mouse.RIGHT_BUTTON)

    # If keys moved, move mouse.
    if (x != 0) or (y != 0):
      mouse.move(x, y, 0)
      time.sleep(0.01)
      mouseTicks += 1
      x = y = 0


  # Wait for all keys up
  while keyBits() != 0:
    time.sleep(0.001)

#################################################################################
# accentedWrite takes the key value and attempts to put a pinyin accent on it.
# This is output as a UTF character using the host PC UTF entry system.
#################################################################################
def accentedWrite(x):
  if not x in vowels:
    # Not a vowel key. Just send the keystroke.
    tokenisedWrite(x)
    return

  # Key needs an accent.Fetch a potential accent pattern
  p = keyWait()
  # if no matching accent character is available, return unaccented char.
  if not p in acntKeys:
    # Special case is the V key, which is repurposed in pinyin to the U umlaut
    if (x == Keycode.V):
      # U umlaut may be capitalised
      if (shifted==0):
        # Not shifted, lower case
        sendUtfChar(0xfc)
      else:
        # Shifted, upper case
        sendUtfChar(0xdc)
    else:
      tokenisedWrite(x)
    return

  a = acntKeys.index(p)


  # We have the key code for character x and accent a upon it.
  # There are 4 accents per char in pinyin.
  # Index the UTF code and send it.
  # First check for shift, which capitalises the accented char and moves up the table
  vidx = vowels.index(x)
  if shifted > 0:
    vidx += 6

  # Calculate the position of the accented character
  sendUtfChar(utfArray[a+4*vidx])
  return

#################################################################################
# Where the magic happens...
def main_loop():
  global shifted
  global numericed
  global controlled
  global alted
  global altgred
  global extraed
  global funced
  global accented

  # Before we leap into action, wait for every key to be released.
  if keyBits() != 0:
    print("Wait for all keys to release...");
    while keyBits() != 0:
      time.sleep(0.001)
    print("Keys released, continuing.")

  while True:
    x = keyWaitRepeat()

    if x < 32 :
      # Here a chord has been pressed without the command key
      if numericed != 0:
          tokenisedWrite(numericTable[x - 1])
      elif extraed != 0:
          tokenisedWrite(extraTable[x - 1])
      elif funced != 0:
          tokenisedWrite(funcTable[x - 1])
      else:
          if accented > 0:
            accentedWrite(alphaTable[x - 1])
          else:
            tokenisedWrite(alphaTable[x-1])

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

      if accented == 1: # Clear a single alt shift.
        accented = 0

      # Clear any internal temporary numeric, extra and func shifts
      numericed &= 2
      extraed &= 2
      funced &= 2
      accented &= 2

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

        elif x == KEYS_LANGAUGE_SHIFT:
          accented += 1
          if accented > 2:
            accented = 2

        elif x == KEYS_MOUSE_MODE_ON:
            mouseMode()


#################################################################################
# We call the setup and main code in here, so we can check if anything crashes
# and issue a reset.

try:
  print("\nInitialising ...")
  setup()
  print("Starting Quirkey v1.03 Main Loop")
  main_loop()
except Exception as e:
  traceback.print_exception(e)
  microcontroller.reset()

