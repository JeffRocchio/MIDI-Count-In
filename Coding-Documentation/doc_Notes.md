# Purpose

This document holds a variety of notes that represent some subset of MIDI knowledge I have acquired, and decisions I've made, concerning the Python program *midi-countin.py*.

# Other References

In addition to this cover document, see also detailed note documents:

   * /Coding-Documentation/doc_Notes_CountInRules.md
   * /Coding-Documentation/doc_Notes_ChannelNumbers.md
   * /Coding-Documentation/doc_Notes_TimeSignature.md
   * /Coding-Documentation/doc_UML.odg

# MIDI Awareness & Understanding

   1. **MIDI Channels are Synthesizers**. MIDI channels are synthesizer targets (or device targets when, e.g., the MIDI data is being streamed along cables to keyboards and electronic synth boxes). So program-change messages must include a channel number and will only affect the synth that has been set to listen to that channel. Note: program and cc messages to channels will be effective across tracks. So, e.g., if, in track-2, you set channel 3 to trombone then if there are any notes in, say, track-1 whose channel param is channel-3, they will play the trombone sound. So be aware of this.

   2. **New Track Added for Count-In**. Count-In will be put into a new track that is appended to the end of the MIDI file's track list. I considered making the count-in track-0 but in thinking through the implications of that in light of copying the original track content I determined that would add more complexity than is worth it.

   3. **MIDI Time is Offset Time, Not Playhead Time**. MIDI time params in messages are *offset times* from the prior event. They are *not* time since start of the track. There is no MIDI param, or provision, to track the time position along a track like a DAW playhead.

   4. **Time Offsets Apply to Tracks**. The time offset param is applied to the track the message is in. If a track contains messages aimed at multiple channels they are not time offset independent. For example: Say that in a given track there is a note-on / note-off event sequence, aimed at channel-1. Let's say the note-off event has duration 100 clicks (meaning the note is to sound for a duration of 100 MIDI clicks). Now let's say that immediately after that note-off even there is a new note-on event, but aimed at channel- and not at channel-1. This new note will be played immediately after that prior channel-1 note-off even tho it is aimed at a different synth or device. This is because, again, time offsets are track oriented, not channel oriented.

   5. **No Master Playhead**. The time offset params *are track independent*. As events are added to the count-in track and track-0 there is no 'master' clock or time param that I can use to then align the original MIDI content to so that it comes in at the right time point. Because of this the program has to work out time offsets for each track for itself and 'time-shift' the original content as needed to make it all line up at just the right moment to match the end of the count-in. This was a challenge to work out and I make no claim on being efficient in my approach to this, see below.

# Decisions

   1. **Musescore is My Base**. Since I use Musescore for sheet music, that is the application from which all my MIDI files are generated. Thus I have created this program using Musescore's MIDI exports as the basis for what the program expects to see as MIDI file inputs. However, in my Mountain Dulcimer world TablEdit is far and away the dominant sheet music creation program, so I have made an attempt to account for TablEdit generated MIDI files as well. See the below section: **NOTES REGARDING TablEdit MIDI EXPORTS.**

   2. **Use of MIDO Python Library**. I am using the MIDO library to manage and manipulate the MIDI files and events. See @ https://mido.readthedocs.io/en/stable/

   3. **NO GUI**. I am not trying to tackle the creation of GUI interface for this program. I am using as simple a terminal interface as I can get away with. If this program actually proves useful a GUI would be a logical enhancement.

   4. **Global Event to Track-0**. By convention 'global' MIDI events are written into track-0. For my purposes these are time-signature & tempo events. I will follow this convention. NOTE: There is commentary across the internet that Track-0 should be used *only* for tempo-mapping and song-global informational messages and should not contain any note content. Musescore, however, does use Track-0 for both the song's global tempo messages (tempo messages and time-signature messages appear only in Track-0 for Musescore MIDI file exports) and for the performance content of the score's first part.

   5. **Pre-Roll Silence**. Default will be one measure of silence. Specifying it as one measure instead of number of seconds will make it fit much better into the midi framework.
	   1. *Update 12/27/2024*: The way I ended up coding for this I now think it would be fine to set the pre-roll silence at 3 seconds as I had originally intended. I may go back and make that change later.

   6. **Strategy for No Master Playhead - Description**. Here is my approach for handling time offset values as I write out the Count-In to the output MIDI file. First: I'm going to create three variables to keep track of the needed offset times. I need to keep track of offsets for Track-0, the Count-In track, and for 'all other' tracks (if any), which I will represent as 'Track-n.' Second: These are dynamically changing offsets from the last written event in the track, not accumulations from start of the file. Third: Any time I put an event into the output MIDI I do the following - a) For the track I write the event into I zero out that track's offset-from-last-event variable. b) For each of the other tracks, which I didn't write that event into, I add the written event's time param value to those tracks' offset-from-last-event variable. c) When I write the next event, in any track, I use that track's offset-from-last-event variable as the written event's time-offset param.

   7. **Strategy for No Master Playhead - Example**. I start by setting all three of the offset-from-last-event variables to the MIDI click duration of the pre-roll silence. When I write the first Count-In note I set it's note-on time= to the Count-In track's offset-from-last-event variable. This will position the first counting note right after the silence period. I then write that counting-note's note-off event, with a time= value of the counting beat duration. I set the Count-In track's offset-from-last-event variable = 0; I then += the counting beat duration to the offset-from-last-event variables for Track-0 and Track-n. When I write the time signature for the pre-pickup counting measure, into Track-0, I do this: Write the time-signature event into Track-0, using as the time= param the value of Track-0's offset-from-last-event variable. Then set Track-0's offset-from-last-event variable =0. Then, conceptually, += 0 to the offset-from-last-event variables for Count-In track and Track-n since a time-signature message consumes 0 clicks of time (although I may it 1-2 MIDI clicks of 'breathing room' to ensure any MIDI player get all the sequencing right). As I proceed in this manner through the writing of the Count-In I should end up with each of the three offset-from-last-event variables set to a value that will perfectly align each of the original tracks to the exact beat immediately following the last counting note.

   8. **Strategy for No Master Playhead - Dummy Alignment Event**. One more thing - to make copying the original tracks as straight-forward as possible I plan to use each of the offset-from-last-event variables to write a non-playing event, with duration of 1 MIDI click, which will have the effect of setting each track's current time to all be in alignment at the perfect post-count-in beat. Then I can simply copy over the original tracks without having to selectively modify any of those events' time offset params. I have done the same thing at the end of each play-through so that additional play-through repeat track copies can be also simply be copied over without having to manage track alignment.

# Notes and Assumptions Regarding TablEdit MIDI Exports

## TablEdit Exported MIDI File Differences from Musescore

   1. **TablEdit MIDI File Types**. TablEdit allows exporting as MIDI type-0 or Type-1 files. (Musescore exports as Type-1, with no option to select Type-0.)

   2. **TablEdit Exports An Octave Too High**. This seems crazy to me, but it appears that TablEdit exports it's MIDI files with the notes one octave higher than notated. In the MIDI export dialog there is a checkbox for "Diminish Notes by One Octave." *You have to make sure this is checked to get the exported notes into the correct octave*. The explanation for this was provided by TablEdit's owner/author,Matthieu Leschemelle: Sun, Dec 22, 2024 at 11:53 AM. To: Jeffrey Rocchio. "Hi, My implementation is very old, but I seem to remember that I did this to bring myself into line with the MIDI files generated by other software. This is how TablEdit exports one octave up and imports one octave down." Matthieu. || I do believe that Matthieu has it wrong that this is some sort of 'rule.' For what it's worth, here was my response to this: Jeffrey Rocchio. Sun, Dec 22, 12:59 PM. to Matthieu. Interesting. I'm not enough of an expert to say if that is right or not. I know that Musescore does not do that, and exporting a MIDI track out of Ardour does not do that. A look around on the internet didn't yield anything definitive. But when I look at questions/answers in various music notation editor forums I do get the impression that it's a bit complicated. My impression is that the octave shift is not a 'rule,' but is done by some notation software in an attempt to have the output MIDI play in the octave the actual performer would. So, e.g., if the notation is 8va the output MIDI would be shifted from the visual notation accordingly. If an instrument is a 'transposing instrument' then shifts occur to match the as-played transposition. I also can't find anything about this at https://midi.org/, fwiw.

   3. **TablEdit Channel Use Is Confusing**. In inspecting several TableEdit export MIDI files I can't really figure out how it makes channel assignments. So far, in every score I see, it has assigned at least 2 channels to every track (that has note messages in it). If I look at Melanie Johnston's Mountain Dulcimer score for Silent Night - 4-Part, for example, I see that three channels have been assigned to the first part. And it appears that each channel represents one of the TAB's staff lines. A note on line-1 is directed to channel-2, notes on line 2 go to channel-1 and notes on line-3 got to channel-0. But then parts with notes on only two lines have all their notes directed to just one channel; yet that part has two channels defined for it, with the 2nd channel being left empty of any notes. Same with parts that have notes only on the melody TAB line. So...what's going on with that? When viewed in a MIDI player there is a long list of channels but you can't really tell which channels represent what parts in the score. Matthieu's response to this situation: "When TablEdit creates the MIDI buffer, it doesn't know on which channel the notes will be played. It doesn't even know if there will be pitch bends, hence the initialization of the odd channel."

   4. **TablEdit Using Half Number of Ticks Per Beat**. TablEdit is using 240 ticks per beat, whereas Musescore is using 480.

   5. **TablEdit Note Velocities**. TablEdit is using 100 as the base note velocity. Musescore is using 80 as the base velocity. I have normalized the count-in velocities to Musescore, So for TableEdit MIDI files the volume of the count-in will sound soft compared to the tune itself.

   6. **TablEdit Uses Odd-Clocks-Per-Click Value**. In Time-Signature messages there is a param, 'clocks-per-click.' As I understand it this is used to set the timing of a metronome audible 'click.' I guess the idea is that you can then have a metronome 'pulse' on a time base that differs from the tempo. So, e.g., you could have the metronome sound every half-beat, or, say, just once per measure instead of on every beat. The value of this param is technically the number of ticks between metronome pulses. TablEdit seems to be using the value 36, whereas the standard value for this param is 24 -> "The sixth byte of the message defines a metronome pulse in terms of the number of MIDI clock ticks per click. Assuming 24 MIDI clocks per quarter note, if the value of the sixth byte is 48, the metronome will click every two quarter notes, or in other words, every half-note." @ [MIDI Time Signature meta message](https://www.recordingblogs.com/wiki/midi-time-signature-meta-message).

   7. **TablEdit Track Structure** --

		1. **Track-0**: An informational track - Song Title, Key Signature, Time Signature, and Tempo. If the 'export information' box is checked then a copyright message is included as well. TablEdit does not put any note-on/off messages into track-0. This is actually a common practice, and there does seem to be commentary across the internet that this is actually a *recommended* practice - having Track-0 contain only tempo (tempo change messages & Time-Signature messages) and Informational (Key-Signature(s), Song-Title, any Copyright, etc.) content.

		2. **Track-1**: First part in the score. Does not contain a key-signature message. Contains cc messages for channel-0, the channel all the notes are sent to, and the note's channel+1, even tho there are no notes assigned to either channel-0 or that +1 channel number. I have no idea why. Also contains text meta-message for any lyrics in the part (note: even tho the text is for lyrics, TablEdit does not use the purpose-defined Lyrics meta-message for these).

		3. **Track-n**: Additional tracks for each additional part beyond the 1st part in the song. No key signature message in these parts. Contains cc messages for the channel all the notes are sent to, and the note's channel+1, even tho there are no notes assigned to that +1 channel number. I have no idea why.

		4. **Final Track**: TablEdit exports a final track that contains just one message, a meta-message that contains the name of the song. Matthieu on this: "Why not ?"

 8. **Matthieu Leschemelle's Response**: See in doc_Notes_TablEdit-oddities.pdf
## TablEdit Considerations For My Script

   1. **Ticks Per Beat**: Need to read the input file's Ticks Per Beat and retain that value in my output in order to preserve play speed. **<-- Done**.

   2. **Clocks Per Click**: Do I need to do anything about this? I'm not using the MIDI metronome pulse. Do any players use it? I suppose that, ideally, I'd read this value in, save it, then use it for the 1-2 time-signatures that I write for the count-in pre-pend.

   3. Empty Last Track: Don't include the last, empty, track. **<-- This happens automatically as my script automatically sets any track that had no note-on events to 'Remove,' except Track-0 which we must always keep.**

   4. **Missing Key-Signature Messages**. Account for lack of key-signature messages on a per-track basis. **<-- DONE. I check for presence of a key-signature on the original track as I initialize the new output tracks. If there is key-signature in the original I also leave it off the new output track.**

   5. **Note Velocity Differences**: I have normalized the count-in velocities to Musescore, So for TableEdit MIDI files the volume of the count-in will sound soft compared to the tune itself. But of course the user can adjust for this, if desired, in their player. A later enhancement could be to assess for each file's base / average / median note velocity and set the count-in velocity accordingly.

   6. **First Track Empty of Notes**: Copy over the 1st track immediately (i.e., at 'playhead' time 0), then avoid making repeat copies of this track? **<-- I have decided that is not necessary. I do enforce retention of the first track, Track-0, as it does contain critical info. But I otherwise treat it the same as I do for Musescore midi-generated files.**

   7. **Channel Confusion and Unused Channels**: I don't know what to do about this. For now, I'll do nothing. If playing back using a MIDI player that is track oriented vs channel oriented then this isn't much of a problem. But I haven't yet been able to find a player, for Android, that supports both track-orientation and custom soundfont files. I have one for my Linux desktop PC, and the Musk MIDI Player app for iPad works well for this.

  8. **Lyric Text Meta-Messages**: Convert lyrics text messages to MIDI Lyric messages for more effective display in most MIDI players. **<-- Very low priority on this one as I don't really care about lyrics and this would be a challenge give that I see a smattering of additional text messages in the tracks** (for example, what look to be text messages for backing chords names - which I think, unlike Musescore, TablEdit doesn't use Backing-Chord specific objects, it just uses 'text' objects for those, so it can't really make the distinction for exporting either MusicXML or MIDI). NOTE: Musscore doesn't export Lyrics at all, so this is total non-issue with Musescore (except if you actually wanted a karakoe MIDI playback file, which you can't get with Musescore).
