# Quirkey

CircuitPython code for the Pi Pico version of the Quirkey keyboard, based heavily on the work done by Microwriter. The device emulates a USB HID US keyboard and mouse, and requires no specific driver. It does however need the Adafruit HID CircuitPython libraries which can be downloaded from Adafruit's HID example web page or from Github. Once you have installed this on your Pi Pico, just copy the quirkey.py program into the CIRCUITPY device and rename it to code.py - if you have not done this before, it is the standard installation procedure that you will find in the CircuitPython tutorial pages.

## Documentation

There is now a version of The Beginner's Guide in the Documentation folder. Not exactly completed, but it'll get you up and running. Source document will be provided when I don't feel embarrassed about it, but for now it is in PDF format.

Note: For historical reasons, the V3 (microswitch version) assembly instructions and STL files have been left in the Documentation directory. The V4 (keyboard switch) version is located at https://www.printables.com/model/704535. The source files for all of this are in the Quirkey_3D repository on this account.

Assembly and programming details are there, together with 'Cheat Sheets" for the keystrokes in mnemonic form. There is also a list of currently supported characters and key functions.

## 3D Printable Files And Build

Location of the files to 3D print the Quirkey (left hand, right hand, scaleable) are listed at the end. No special materials or supports needed. Other than requiring soldering a dozen or so wires to complete, it's a pretty easy build. The user-ready STL files and assembly doccumentation are here: https://www.printables.com/model/704535

## Left Handers

Changing the LEFT_HANDED flag to "True" flips the most mentally confusing characters like B, D and the brackets, as well as the mouse directions. There is a separate set of documentation for left-handers.

## Typing Tutor

A simple "typing tutor" application is included in TutorApp. Just copy these files into a directory and run TutorApp.py according to the Python operating instructions of your platform (a copy of John Zelle's simple portable graphics utility is included for convenience, should you not have it already installed).

## Device History

The Microwriter and Quinkey were 6-key chord keyboards created in the 80's for use by people with various physical limitations such as brittle bones. They developed a following among all types of users being simple, reliable, easy to use, and effectively allowed instant touch typing at speed. See https://en.wikipedia.org/wiki/Microwriter

3D Files for printing the chord keyboard shell and assembly instructions can be found at https://www.printables.com/model/667870-quirkey-v3-accessibility-keyboard-for-one-handed-u and https://github.com/VikOlliver/Quirkey_3D

An Arduino version for AT32U4 processors is also available at https://github.com/VikOlliver/Microwriter.

The original Microwriter used an RCA 1802 CPU and LCD for the user interface, and uploaded via RS232. A TV interface was also available. The author (Vik Olliver) created the original Amstrad and IBM Quinkey drivers.
