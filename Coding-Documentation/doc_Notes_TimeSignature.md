# Notes On Time Signature

When MuseScore exports a MIDI it populates a time_signature meta-message event at the start of any measure that has a different number of beats in it than the song's nominal time signature. In particular it does this for any pickup measure and for final measures that constitute a wrap-around back to the beginning of the pickup measure to start a 'replay' of the song from the beginning.

For example, **The Solstice Maid** is in 3/4 time, with a two-beat pickup measure and a single-beat final measure. In this case *Musescore set the time signature to 2/4 to start the song*, then after two beats it sets the time signature to 3/4 (the song's correct nominal signature). Then at the last measure it set the time signature to 1/4. I have the score repeating for a 2nd play through - but the repeat does NOT include the pickup measure. So, really, I scored it incorrectly because, technically, it doesn't wrap around properly. Nonetheless, Musescore exported it such that after setting the time signature to 1/4 for the final measure, it then goes back to the first measure after the pickup, and sets the time Signature back to 3/4. Then MuseScore populates the repeat of the tune from there, hits the final measure again and sets the time signature to 1/4 again, plays the final beat, then ends the tracks.

Refer to **/Audio_AddCountIn_MIDI/TestScores-and-MIDIs/Test-04_The-Solstice-Maid.txt** to see all the MIDI messages for The Solstice Maid.

## Issues / Decisions

So given this I have three issues:

1. **Incorrect Time Signature Pre-Populate**. On MIDI files with a pickup measure I am reading, and pre-populating, an incorrect time signature.

2. **Make Effective Use of Time Signature Changes**. Should I use this to auto-populate pickup params in the song info data?

3. **How to Assemble?** When I 'assemble' the output MIDI file, how do I treat these situations in combination with the count-in? Should I:

    a. Create a single measure for the counting notes, populating a time signature numerator that matches however many counting beats I have in it? If I do this, what about when the user wants multiple measures of count in? ALL of those stuffed into a single measure? Or separate measures for each, *except* for the last measure + pre-Pickup beats?

    b. Combine any pre-pickup counts with the song's pickup measure to make a full measure at nominal time-signature? Thus re-writing the existing time signature message? Or more likely, removing it.

    c. Put the pre-pickup counts into it's own, non-standard beat-count measure and leave the song's existing pickup measure MIDI events as-is. This would require my writing a time-signature message to match the pre-pickup beat count. Actually this requires first writing the correct nominal time-signature message for however many full-count measures we create, then the non-nominal signature for the pre-pickup measure. And then just append the existing song events, as-is, onto the end of all that.

## Go With Blocks

On the question above, **How to Assemble?**, I've decided to go with option **'c.'** I'm going to think in terms of 'blocks.'

So I'll have a 'bock' for each of:

- **The Pre-Roll Silence Block**. This block will begin with the song's nominal time signature and consist of one empty measure. I am going to use an empty measure for the silence because I think using notes with velocity = 0 will be confusing. Best that it just be empty.

- **The Count-In Block**. This will be begin with the song's nominal time signature meta-message, at time=[end of silent block]. Thus, this time-signature meta-message is actually what creates the pre-roll silence measure.

- **The Song Block(s)**. The original song's MIDI events. Going with option 'c' allows me to simply keep the original input tracks as they are and not have to mess around with adjusting any time signatures, including not having to deal with special conditions on the 'turn around' for cases where we will be adding copies of the original tracks as additional play through repeats. Each repeat will be a block.

## Which Track To Place the Time Signature Messages In

from chatGPT:

In a multi-track MIDI file, time signature change messages can be placed in any track, but there are some conventions and best practices to follow:

1. **Conventionally Placed in Track 0**: Time signature changes are typically placed in the first track (track 0), especially if it is the conductor track or a track that carries other global messages such as tempo changes. This ensures that all tracks can reference a common time signature.

2. **Global Effect**: The time signature change is global; it affects the entire MIDI file, not just the track where it is placed. Therefore, placing it in one track will apply it across all tracks during playback.

3. **MIDI Sequencer Behavior**: Most MIDI sequencers and DAWs (Digital Audio Workstations) expect and handle time signature changes in track 0. While it is technically possible to place them in other tracks, doing so may cause confusion or unexpected behavior in some software.

4. **Compatibility**: For compatibility and ease of editing, it's best to follow the convention of placing time signature changes in track 0. This ensures that the MIDI file behaves predictably across different software and hardware devices.

In summary, while it technically doesn't matter which track time signature change messages are placed in, adhering to the convention of placing them in track 0 is recommended for compatibility and clarity.

**Decision**: So given the above I will add the Count-In track as the last track in the outputMIDI, but place tempo and time-signature message in track-0, which will remain the original song's Track-0.
