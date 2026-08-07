PumpDoublify
========
Huge thanks to Boxx for writing the original 4 panel -> 8 panel converter, this tool is a small modification for making pump doubles charts, with lots of tweaking done to generate (hopefully) comfortable patterns.
## Features
- Converts 4 panel charts to 10 panel.
- Can batch process recursive folders of songs.
- Removes old autogen charts so you can re-doublify charts when a new version comes out.
- Skips charts which have non-autogen double charts so you can doublify your whole Songs folder and you won't lose anything.
- Generates patterns suitable for stamina & footspeed.
- Uses staged middle positions so transitions never require a foot to leap
  from one pad's center panel directly toward the opposite pad.
- Forbids diagonal movements across the gap between the two pads.
- Limits overlapping holds and new steps to two active feet, ending older
  holds cleanly before a new pair begins.
- Keeps notes played during a hold on the free foot instead of alternating
  back onto the held foot.
- Delays already-due pad transitions to the next measure boundary when an
  eligible step is available; this does not add extra transitions.

## Issues
- Quads & triples will be converted to jumps.
- Holds and rolls keep their source-lane identity, resolve on the panel where
  they started, and are ended cleanly if a generated step must reuse the panel.
- Footswitches will be converted to jacks.
- Does not distinguish between jumps & 1-foot brackets. All will be converted to jumps.
- An all-jump section will not move across the pads.
- Jump patterns are not ideal.

## Usage
- Currently only Windows is supported.
- Download the repository (if you aren't familiar with Github, press the green Code button then "Download ZIP")
- Install python 3.8 or higher (tested with 3.10): https://www.python.org/downloads/
- Depending on the installation, "python" in pumpdoublify.bat might need to be replaced with "py"
- In File Explorer, drag a folder or simfile onto pumpdoublify.bat
- Wait for the message "Press any key to continue . . ." to appear. This may take a while if there are lots of songs.
- Press any key
