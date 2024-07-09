# boot.py - prevents Quirkey being recognised as a USB storage device unless the little finger key is down.
import storage
import board, digitalio

# If not pressed, the key will be at +V (due to the pull-up).
# https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/circuitpy-midi-serial#circuitpy-mass-storage-device-3096583-4
button = 0
if ( board.board_id == "seeeduino_xiao_rp2040"):
  print("boot: Seediuno XIAO detected. Checking D1 ...")
  button = digitalio.DigitalInOut(board.D1)
else:
  button=digitalio.DigitalInOut(board.GP7)

button.direction = digitalio.Direction.INPUT
button.pull = digitalio.Pull.UP

# Disable devices only if button is not pressed.
if button.value:
    print(f"boot: button not pressed, disabling drive")
    storage.disable_usb_drive()
