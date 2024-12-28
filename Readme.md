# MIDI Count-In

This is a python script which reads in a MIDI file and pre-pends onto it a bit of silence and an audible count-in sequence. 
## Purpose

To be able to use MIDI audio files for learning and practicing songs. MIDI files are more useful for this purpose because you can control the individual score parts independently of each other. So, for example, you can 'solo' the part you are trying to learn to practice playing it. Then later you can mute that part and practice playing your part along with all the other parts.

In order to use the MIDI file in that way you need to know when to begin playing - just like you do when playing in a group or ensumble. Thus the need for a Count-In sequence prior to start of the song.

## Usage

The python script is invoked from the command line and given an input MIDI file to process. You also supply, on the command line, the file-path where you want the output MIDI file to go.

This script assumes the MIDI file has been created using a Musescore score, exported as a MIDI. However, I have made a good-faith attempt to accommodate MIDI exports from TablEdit as well. But note that TablEdit MIDI exports have some significant differences from Musescore MIDI exports. Perhaps the most important thing with TablEdit MIDI exports is that you must be sure the "Diminish notes by one octave" option is checked in the export dialog.

The count-in is created as a new Track in the output MIDI file and is set to use 'Rom-Toms' as the instrument patch. I did create a custom soundfont that verbally states each number for a spoken count. If your player can use custom soundfonts you could make use of this for a human-spoken Count In sound.

## Instructions

I have not created any instructions on how to use as of yet. First, I'm not a great tech-writer for such things. Secondly, I don't really expect anyone but me to make use of this program.

That said, the basic outline is:

   1. Create, or obtain, a MIDI file (export from a sheet-music app or find one online).
   2. Install Python, or make sure it is installed. Google search for your operating system.
   3. Download midi-countin.py to some appropriate place on your PC.
   4. Using the Python PIP utility, download/install the 'mido' python library (again, consult instructions for doing this based on your OS).
   5. Open a terminal (how you do this will depend on what OS you are running).
   6. Type in python midi-countin -h <- This will present you with very basic help for the program's options.
   7. From the above step - give it a go, running the program against one of your MIDI files.

## References

The following documents are useful for going down the rabbit hole:

In the directory Coding-Documentation see:

   * doc_Notes_ChannelNumbers.md
   * doc_Notes_CountInRules.md
   * doc_Notes_CountInRules_MJfeedback.odt
   * doc_Notes.md
   * doc_Notes_TimeSignature.md

## Coding Documentation

doc_UML.odg
