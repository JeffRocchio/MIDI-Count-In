# Notes On MIDI Channel Number

### Index Base is Zero

Internally, in the MIDI message data, the channel numbers start from 0 and range up to a max of 15. Most applications display and treat MIDI channel numbers as starting from 1 and ranging to 16. So be aware of this.

### Channel Numbers Are Mapped to Instrument Patch

A Channel is the virtual conduit to a MIDI synthesizer. Sometimes this is a physical synth device, like an electric keyboard attached to a computer. But for our purposes a Channel is the virtual conduit to an instrument 'patch' in the active soundfont (really the MIDI messages are being sent from the MIDI player to a software sythn, like, e.g., FluidSynth which is rendering the sound from a soundfont file). So when there is a 'program_change' message that specifies to use one of the soundfont's instrument patches (say, e.g., program_change=27 for guitar) that assignment is tied to the channel number given in that message. After that point any 'note_on' for that channel will get directed to the instrument set for that channel#, regardless of which track it is in.

### Every Non-Meta-Message Aimed At a Channel

All performance messages - note-on/off, pitch-bend, volume, etc - are aimed at a specific channel. Per the prior section this means they are affect only the sound of the instrument that has been set for that channel#. This tends to give MIDI, and MIDI players, a strong Channel orientation over a Track orientation.

Ideally, for how I  intend to use MIDI files for learning and practicing songs, I would like the MIDI file to be very much Track oriented and not Channel oriented. Unfortunately the rest of the world wants it all to be Channel oriented. It is hard to find a MIDI player that will clearly show you a view of the score's Parts, using the Part's name (e.g., 'Melody,' 'Harmony,' etc - as exported to the MIDI file in the Track-Name meta-message). The way to deal with this would be to have each channel be used in one, and only one, Track. But as a practical matter this isn't going to happen.

For Musescore - note that I often see tracks exported out of Musescore that have two different channel numbers being used within the same track. As far as I can tell these second channels are for the playback of the so-called "harmony chords."

It is also true that Musescore will produce a MIDI file that uses the same channel number in two different tracks. E.g., in TEST_Cold-Frosty-Morning.mid where I have a part with two staffs - piano style - it puts the notes for the treble staff into one track, and the notes for the bass staff into a separate track; but uses the same channel number for all the notes.

The above doesn't confuse "Durmstick MIDI File Player;" (or other MIDI players that I have tried) it plays just fine. But when I open the 'Channels' view in the player it does list the additional channel #, and it will show what instrument that channel has been mapped to based on the Program_Control message in the MIDI file; but it shows an empty Track-Name/Part-Name field for that channel(when, in reality, that channel # is in a specific track, and that track does have a 'track_name' Meta-message - and meta-messages apply to the whole track, they do not have channel assignments on them). But it has the blank Track Name field because those 'extra' channels *could* appear in multiple tracks, so the MIDI player doesn't really have a definitive Track Name to map to the channel. Although this would also be true for the first channel it sees in a track, yet it will assign the Track Name to that first-seen channel number. So in my mind it really could just use the same rule to apply a Track Name to all channels. But the Durmstick MIDI File Player's author doesn't want to do this. He does note that you can edit that field in the channel viewer to type in a Track Name for it, and you can save those edits for the song and it will remember them.

OK - So when I am adding in a new track that is not in the original MIDI I assign it to a unique channel number so that at least my Count-In track will be a one-for-one matchup with Track/Channel and should be obvious in most MIDI players. The obvious why for me to do this is to find out what is the highest channel number used in the original and then simply go one higher than that. However, this is not such a good idea as channel #9 (#10 if 1 is used a the starting number) should be avoided because it has a special use for percussion. Also, you can't go higher than 15 (16). So what I do is find the first unused channel number that is not channel #9 (10).


### Identifying Channel Number For a Track

As of 7/29/2024: Trying to deal reasonably with conditions where there are multiple channel numbers in one track. Plus deal with the fact that Musescore seems to export tracks even when a part is muted in the mixer prior to export. In those cases there are no 'note_on' messages in the track.

So, what I'm doing is:

   1. I determine a track's channel number during the song.populate_songInfo() function.

   2. I trap certain message types in a case statement as part of the data collection.

   3. Program Change messages (should) always precede the first 'note_on' message. (Because the instrument patch has to be set before any sound can come out, after all). So when I see a 'program_change' message I pick up the channel number from that and store it away in the song.infoTrack 2D matrix.

   4. But then, later in the track, I hit the first 'note-on' message. IF, when I hit that first 'note_on' message, I haven't yet come across a 'program_change' message, then I will set the channel using that first 'note_on' message.

I think the above approach does several things for me:

   1. Musescore *seems* to put the 'program_change' message for the staff notes before the one for the harmony chords. So by picking up the first 'program_change' message I appear to be getting what I'll call the primary channel for that track.

   2. In cases where a track is 'muted' and has no note message I still get a channel number, the one Musescore assigned to that track - because Musescore will write a 'program_change' message. And so in this way the tracks and players all stay OK in the MIDI players.

   3. If there is a case where there is no 'program_change' message in the track, I will still get the channel number from a note_on message. I have seen at least one MIDI file, not from Musescore, where this was the case.

### The Algorythm To Find Open Channel for Added Count-In Track

What I'll do is go through each track in the original MIDI and find the first open channel number that is not channel #10; and use that. I'd like to get this value as part of the song_info data, and store it in the params of the outputMIDI class. <-- See  `_find_openChannel(self, channelList)`

The way I did this it just so happens that I do also pick up the additional channel numbers that Musescore assigned to the muted harmony parts (see doc_NotesProgramChanges.md) such that I am truly obtaining a unique channel number for the count in track.

### Future To Consider

   1. Consider showing more information about Track to Channel mapping in the songInfo display.

   2. Consider user selected options to 'clean up' channels. Remove unused channels. Merger channels to obtain a one-for-one Track to Channel association in the resulting output MIDI. Doing this would make the resulting output MIDI more usable in most MIDI players.

